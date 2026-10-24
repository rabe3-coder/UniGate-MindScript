"""Students application operations (one function per endpoint)."""
from app.domain.errors import AppError
from app.core.crypto import password_hash
from app.core.security import require
from app.infrastructure.database import one, all_rows, transaction, audit
from app.services.academics import academic_report
import secrets
import re
from urllib.parse import parse_qs, urlparse

def op_affairs_student_create(c, user, payload, respond, headers, request_path, method, path):
    require(user, ['affairs', 'admin'])
    fields = ('username', 'name_ar', 'name_en', 'student_number', 'phone', 'email')
    if any((not isinstance(payload.get(k, ''), str) for k in fields)):
        raise AppError('Invalid student fields / بيانات طالب غير صالحة')
    v = {k: payload.get(k, '').strip() for k in fields}
    reason = str(payload.get('reason', '')).strip()
    if not re.fullmatch('[A-Za-z][A-Za-z0-9_.-]{2,31}', v['username']):
        raise AppError('Username must be 3–32 Latin characters/digits / اسم المستخدم غير صالح')
    if not 2 <= len(v['name_ar']) <= 100 or not 2 <= len(v['name_en']) <= 100:
        raise AppError('Names must be 2–100 characters / الاسم غير صالح')
    if any((ord(ch) < 32 for k in ('name_ar', 'name_en') for ch in v[k])):
        raise AppError('Invalid character in name')
    if not re.fullmatch('[A-Za-z0-9_-]{3,24}', v['student_number']):
        raise AppError('Student number is required (3–24 letters/digits) / الرقم الجامعي مطلوب')
    if v['phone'] and (not re.fullmatch('\\+?[0-9 ()-]{7,22}', v['phone'])):
        raise AppError('Invalid phone / رقم هاتف غير صالح')
    if v['email'] and (len(v['email']) > 254 or not re.fullmatch('[^\\s@]+@[^\\s@]+\\.[^\\s@]+', v['email'])):
        raise AppError('Invalid email / بريد إلكتروني غير صالح')
    if not 6 <= len(reason) <= 500:
        raise AppError('Provide an auditable reason / سبب الإنشاء مطلوب')
    temp_password = secrets.token_urlsafe(18)
    with transaction(c):
        if one(c, 'SELECT 1 FROM users WHERE username=? COLLATE NOCASE', (v['username'],)):
            raise AppError('Username already exists / اسم المستخدم موجود', 409, 'DUPLICATE_USERNAME')
        if one(c, 'SELECT 1 FROM users WHERE student_number=?', (v['student_number'],)):
            raise AppError('Student number already exists / الرقم الجامعي موجود', 409, 'DUPLICATE_STUDENT_NUMBER')
        cur = c.execute("INSERT INTO users(username,name_ar,name_en,role,password_hash,graduate,honors,hold,student_number,phone,email)\n                            VALUES(?,?,?,'student',?,0,0,0,?,?,?)", (v['username'], v['name_ar'], v['name_en'], password_hash(temp_password), v['student_number'], v['phone'], v['email']))
        uid = cur.lastrowid
        audit(c, user['id'], 'STUDENT_CREATED', 'student', {'student_id': uid, 'username': v['username'], 'student_number': v['student_number'], 'reason': reason})
    return respond({'success': True, 'student_id': uid, 'username': v['username'], 'temporary_password': temp_password}, 201)


def op_affairs_student_profile(c, user, payload, respond, headers, request_path, method, path):
    require(user, ['affairs', 'admin'])
    if method == 'GET':
        from urllib.parse import parse_qs
        args = parse_qs(urlparse(request_path).query)
        uid = int(args.get('id', ['0'])[0])
        student = one(c, "SELECT id,username,name_ar,name_en,student_number,phone,email,graduate,honors,hold FROM users WHERE id=? AND role='student'", (uid,))
        if not student:
            raise AppError('Student not found / الطالب غير موجود', 404)
        schedule = all_rows(c, 'SELECT c.code,s.label,e.created_at FROM enrollments e JOIN sections s ON s.id=e.section_id\n                            JOIN courses c ON c.id=s.course_id WHERE e.user_id=? ORDER BY c.code', (uid,))
        history = all_rows(c, "SELECT a.action,a.details,a.created_at,u.username AS actor FROM audit a\n                            LEFT JOIN users u ON u.id=a.actor_id WHERE a.entity='student' AND\n                            (a.action='STUDENT_PROFILE_UPDATE' AND json_extract(a.details,'$.student_id')=?)\n                            ORDER BY a.id DESC LIMIT 25", (uid,))
        completed = all_rows(c, 'SELECT cr.code,cr.name_ar,cr.name_en,cr.credits,co.passed FROM completed co JOIN courses cr ON cr.id=co.course_id WHERE co.user_id=? ORDER BY cr.code', (uid,))
        waitlist = all_rows(c, 'SELECT cr.code,cr.name_ar,cr.name_en,s.label,w.status,w.joined_at FROM waitlist w JOIN sections s ON s.id=w.section_id JOIN courses cr ON cr.id=s.course_id WHERE w.user_id=? ORDER BY w.joined_at DESC', (uid,))
        payments = all_rows(c, 'SELECT reference,status,gateway_status,created_at FROM payments WHERE user_id=? ORDER BY id DESC LIMIT 50', (uid,))
        exception = one(c, 'SELECT min_override,reason FROM exceptions WHERE user_id=?', (uid,))
        credits = one(c, 'SELECT COALESCE(SUM(cr.credits),0) AS total FROM enrollments e JOIN sections s ON e.section_id=s.id JOIN courses cr ON s.course_id=cr.id WHERE e.user_id=?', (uid,))['total']
        passed_credits = sum((item['credits'] for item in completed if item['passed']))
        return respond({'student': dict(student), 'schedule': schedule, 'history': history, 'completed': completed, 'waitlist': waitlist, 'payments': payments, 'exception': dict(exception) if exception else None, 'academic_plan': academic_report(c, uid), 'academic_summary': {'registered_credits': credits, 'passed_credits': passed_credits, 'registered_sections': len(schedule), 'completed_courses': sum((1 for item in completed if item['passed']))}})
    body = payload
    uid = int(body.get('user_id', 0))
    fields = ('name_ar', 'name_en', 'student_number', 'phone', 'email')
    if any((not isinstance(body.get(k), str) for k in fields)):
        raise AppError('Invalid profile fields', 400)
    values = {k: body[k].strip() for k in fields}
    reason = str(body.get('reason', '')).strip()
    if not 2 <= len(values['name_ar']) <= 100 or not 2 <= len(values['name_en']) <= 100:
        raise AppError('Names must be 2–100 characters / الأسماء بين 2 و100 حرف')
    if any((ord(ch) < 32 for k in ('name_ar', 'name_en') for ch in values[k])):
        raise AppError('Invalid control character in name')
    if values['student_number'] and (not re.fullmatch('[A-Za-z0-9_-]{3,24}', values['student_number'])):
        raise AppError('Student number: 3–24 Latin letters/digits, - or _')
    if values['phone'] and (not re.fullmatch('\\+?[0-9 ()-]{7,22}', values['phone'])):
        raise AppError('Invalid phone number / رقم الهاتف غير صالح')
    if values['email'] and (len(values['email']) > 254 or not re.fullmatch('[^\\s@]+@[^\\s@]+\\.[^\\s@]+', values['email'])):
        raise AppError('Invalid email address / البريد غير صالح')
    if not 6 <= len(reason) <= 500:
        raise AppError('Reason must be 6–500 characters / سبب التعديل مطلوب')
    with transaction(c):
        old = one(c, "SELECT id,username,name_ar,name_en,student_number,phone,email FROM users WHERE id=? AND role='student'", (uid,))
        if not old:
            raise AppError('Student not found', 404)
        if values['student_number'] and one(c, 'SELECT 1 FROM users WHERE student_number=? AND id<>?', (values['student_number'], uid)):
            raise AppError('Student number already exists / الرقم الجامعي مستخدم', 409, 'DUPLICATE_STUDENT_NUMBER')
        changes = {key: {'old': old[key], 'new': values[key]} for key in fields if old[key] != values[key]}
        if changes:
            c.execute("UPDATE users SET name_ar=?,name_en=?,student_number=?,phone=?,email=? WHERE id=? AND role='student' ", (*(values[k] for k in fields), uid))
            audit(c, user['id'], 'STUDENT_PROFILE_UPDATE', 'student', {'student_id': uid, 'changes': changes, 'reason': reason})
    return respond({'success': True, 'changed_fields': list(changes), 'student_id': uid})

