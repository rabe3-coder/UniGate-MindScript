"""Read projections tailored to course registration dashboards."""
from app.infrastructure.database import one, all_rows, setting
from app.services.registration import course_eligible, registered, min_credits, max_credits
from app.services.waitlist_priority import ordered_candidates

def catalog(c,user):
    sections=all_rows(c,'''SELECT s.id,s.course_id,s.label,s.capacity,s.weekday,s.start_time,s.end_time,s.instructor,
        c.code,c.name_ar,c.name_en,c.credits,p.code AS prerequisite,
        (SELECT COUNT(*) FROM enrollments e WHERE e.section_id=s.id) AS enrolled,
        (SELECT COUNT(*) FROM waitlist w WHERE w.section_id=s.id AND w.status='waiting') AS waiting
        FROM sections s JOIN courses c ON c.id=s.course_id LEFT JOIN courses p ON p.id=c.prerequisite_id ORDER BY c.code,s.label''')
    for s in sections:
        if user['role']=='student':
            s['eligible'],s['eligibility_reason']=course_eligible(c,user['id'],s['course_id'])
        else: s['eligible'],s['eligibility_reason']=None,None
    return sections

def me(c,user):
    if user['role']!='student': return {'user':user}
    entries=all_rows(c,'''SELECT w.id,w.section_id,w.status,w.joined_at,w.note,s.label,c.code,c.name_ar,c.name_en FROM waitlist w
                JOIN sections s ON s.id=w.section_id JOIN courses c ON c.id=s.course_id WHERE w.user_id=? ORDER BY w.id DESC''',(user['id'],))
    for entry in entries:
        if entry['status']=='waiting':
            ranked=ordered_candidates(c,entry['section_id'])
            mine=next(((position,x) for position,x in enumerate(ranked,1) if x['id']==entry['id']),None)
            if mine:
                entry['priority_position']=mine[0]
                entry['priority_reason']=mine[1]['priority_reason']
    return {'user':user,'schedule':registered(c,user['id']),
            'credits':sum(x['credits'] for x in registered(c,user['id'])),
            'min_credits':min_credits(c,user),'max_credits':max_credits(c,user),
            'completed':all_rows(c,'''SELECT c.code,c.name_ar,c.name_en,co.passed FROM completed co JOIN courses c ON c.id=co.course_id WHERE co.user_id=?''',(user['id'],)),
            'waitlist':entries,
            'payments':all_rows(c,'SELECT id,reference,status,gateway_status,created_at,request_key FROM payments WHERE user_id=? ORDER BY id DESC',(user['id'],))}

def stats(c):
    result={key:one(c,'SELECT COUNT(*) AS n FROM '+table)['n'] for key,table in [('users','users'),('courses','courses'),('sections','sections'),('enrollments','enrollments'),('payments','payments'),('waitlist','waitlist')]}
    result.update({'phase':setting(c,'phase'),'registration_enabled':setting(c,'registration_enabled')=='true',
                   'min_credits':int(setting(c,'min_credits')),'max_credits':int(setting(c,'max_credits')),
                   'honors_max':int(setting(c,'honors_max')),'waitlist_policy':'graduation_priority_with_24h_protection_demo'})
    return result

