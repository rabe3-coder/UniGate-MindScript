"""Enrollment use cases. Seat-changing writes must run in BEGIN IMMEDIATE transactions."""
import sqlite3
import json
from app.domain.errors import AppError
from app.domain.rules import conflicts
from app.services.waitlist_priority import ordered_candidates
from app.repositories.enrollments import schedule_for_student, occupied_seats, section_with_course
from app.core.clock import now
from app.core.security import require
from app.infrastructure.database import one, all_rows, setting, transaction, audit

def permitted(c,user):
    if setting(c,'registration_enabled')!='true': raise AppError('Registration is temporarily suspended / التسجيل متوقف مؤقتًا',409,'READ_ONLY')
    phase=setting(c,'phase')
    if phase=='closed': raise AppError('Registration window is closed / نافذة التسجيل مغلقة',409,'CLOSED')
    if phase=='early' and not user['graduate']:
        raise AppError('Early window is for graduating students only / التسجيل المبكر للخريجين فقط',409,'PRIORITY')
    if user['hold']: raise AppError('Student account is on administrative hold / يوجد قيد إداري على الحساب',409,'HOLD')
    if not one(c,"SELECT 1 FROM payments WHERE user_id=? AND status='confirmed' LIMIT 1",(user['id'],)):
        raise AppError('Fee verification required before registration / يلزم تأكيد دفع الرسم',409,'PAYMENT_REQUIRED')

def course_eligible(c,uid,cid):
    course=one(c,'SELECT prerequisite_id, code FROM courses WHERE id=?',(cid,))
    if not course: return (False,'Unknown course / مقرر غير موجود')
    if one(c,'SELECT 1 FROM completed WHERE user_id=? AND course_id=? AND passed=1',(uid,cid)):
        return (False,'Already passed / تم اجتياز المقرر سابقًا')
    pre=course['prerequisite_id']
    if pre and not one(c,'SELECT 1 FROM completed WHERE user_id=? AND course_id=? AND passed=1',(uid,pre)):
        prec=one(c,'SELECT code FROM courses WHERE id=?',(pre,))['code']
        return (False,'Missing prerequisite / المتطلب السابق غير مستوفى: '+prec)
    return (True,'Eligible / مؤهل')

def registered(c,uid):
    return schedule_for_student(c,uid)


def max_credits(c,user):
    return int(setting(c,'honors_max') if user['honors'] else setting(c,'max_credits'))

def min_credits(c,user):
    x=one(c,'SELECT min_override FROM exceptions WHERE user_id=?',(user['id'],))
    return x['min_override'] if x else int(setting(c,'min_credits'))

def validate_section(c,user,section_id,existing=None):
    s=section_with_course(c,section_id)
    if not s: raise AppError('Section not found / الشعبة غير موجودة',404)
    s=dict(s)
    ok,reason=course_eligible(c,user['id'],s['course_id'])
    if not ok: raise AppError(reason,409,'PREREQUISITE')
    current=existing if existing is not None else registered(c,user['id'])
    if any(e['course_id']==s['course_id'] for e in current):
        raise AppError('Course is already registered / المقرر مسجل مسبقًا',409,'DUPLICATE_COURSE')
    if any(conflicts(s,e) for e in current):
        raise AppError('Schedule conflict / تعارض في الجدول',409,'SCHEDULE_CONFLICT')
    return s

def enroll_basket(c,user,ids,key):
    require(user,['student'])
    if not isinstance(ids,list) or not ids or len(ids)>15 or not all(isinstance(i,int) for i in ids):
        raise AppError('Choose one or more valid sections / اختر شعبًا صالحة')
    if len(set(ids)) != len(ids): raise AppError('Duplicate sections in basket / تكرار شُعب في السلة')
    if not isinstance(key,str) or not 8<=len(key)<=100: raise AppError('Invalid request key / مفتاح الطلب غير صالح')
    with transaction(c):
        prior=one(c,'SELECT response_json FROM registration_requests WHERE user_id=? AND request_key=?',(user['id'],key))
        if prior: return dict(json.loads(prior['response_json']),replayed=True)
        permitted(c,user)
        current=registered(c,user['id'])
        chosen=[]
        for sid in ids:
            s=validate_section(c,user,sid,current+chosen)
            count=occupied_seats(c,sid)
            if count>=s['capacity']: raise AppError('Section '+s['code']+'-'+s['label']+' is full / الشعبة ممتلئة',409,'FULL')
            chosen.append(s)
        total=sum(e['credits'] for e in current)+sum(e['credits'] for e in chosen)
        if total>max_credits(c,user): raise AppError('Exceeds credit maximum / تجاوز الحد الأعلى للساعات',409,'MAX_CREDITS')
        # Check the minimum at first basket confirmation, not on each course selection.
        if not current and total<min_credits(c,user) and setting(c,'phase')!='add_drop':
            raise AppError('Minimum '+str(min_credits(c,user))+' credits required / الحد الأدنى للساعات غير مكتمل',409,'MIN_CREDITS')
        for s in chosen:
            c.execute('INSERT INTO enrollments(user_id,section_id,created_at,origin) VALUES(?,?,?,?)',(user['id'],s['id'],now(),'basket'))
        # Remove only the successfully enrolled sections from saved drafts,
        # in the SAME transaction as the actual enrollment.
        c.executemany('DELETE FROM student_basket WHERE user_id=? AND section_id=?',
                      [(user['id'],sid) for sid in ids])
        resp={'success':True,'codes':[s['code']+'-'+s['label'] for s in chosen],'credits':total,'request_key':key}
        c.execute('INSERT INTO registration_requests(user_id,request_key,status,response_json,created_at) VALUES(?,?,?,?,?)',
                  (user['id'],key,'confirmed',json.dumps(resp),now()))
        audit(c,user['id'],'REGISTER_BASKET','enrollment',resp)
        return resp

def promote_waitlist(c,sid,actor=None):
    """Educational DEMO policy: auto-allocation, preserving queue order; university policy not asserted."""
    promoted=[]; skipped=[]
    section=one(c,'SELECT capacity,course_id FROM sections WHERE id=?',(sid,))
    if not section: return {'promoted':promoted,'skipped':skipped}
    while one(c,'SELECT COUNT(*) AS n FROM enrollments WHERE section_id=?',(sid,))['n'] < section['capacity']:
        candidates=ordered_candidates(c,sid)
        w=candidates[0] if candidates else None
        if not w: break
        uid=w['user_id']
        candidate=one(c,'SELECT * FROM users WHERE id=?',(uid,))
        reason=None
        try:
            if candidate['hold']: raise AppError('Administrative hold / قيد إداري')
            if not one(c,"SELECT 1 FROM payments WHERE user_id=? AND status='confirmed'",(uid,)):
                raise AppError('Unverified payment / رسم غير مؤكد')
            info=validate_section(c,dict(candidate),sid)
            current_credits=sum(e['credits'] for e in registered(c,uid))
            if current_credits+info['credits']>max_credits(c,dict(candidate)):
                raise AppError('Credit maximum / تجاوز الحد الأعلى')
            if current_credits==0 and info['credits']<min_credits(c,dict(candidate)) and setting(c,'phase')!='add_drop':
                raise AppError('Minimum credit requirement / الحد الأدنى للساعات؛ يحتاج الطالب إلى مسار معتمد')
        except AppError as e: reason=str(e)
        if reason:
            c.execute("UPDATE waitlist SET status='skipped',note=? WHERE id=?",(reason,w['id']))
            skipped.append({'user_id':uid,'reason':reason})
            audit(c,actor,'WAITLIST_SKIP','waitlist',{'section_id':sid,'user_id':uid,'reason':reason})
            continue
        try:
            c.execute('INSERT INTO enrollments(user_id,section_id,created_at,origin) VALUES(?,?,?,?)',(uid,sid,now(),'waitlist-demo'))
            c.execute("UPDATE waitlist SET status='promoted',note='Auto-allocated under demo policy' WHERE id=?",(w['id'],))
            promoted.append(uid)
            audit(c,actor,'WAITLIST_PROMOTE','enrollment',{'section_id':sid,'user_id':uid,'policy':'graduate_priority_age_protection_demo','priority_reason':w['priority_reason']})
        except sqlite3.IntegrityError:
            c.execute("UPDATE waitlist SET status='skipped',note='Duplicate enrollment' WHERE id=?",(w['id'],))
            skipped.append({'user_id':uid,'reason':'duplicate enrollment'})
    return {'promoted':promoted,'skipped':skipped,'policy':'graduate_priority_age_protection_demo'}

