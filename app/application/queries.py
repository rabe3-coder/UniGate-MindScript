"""Queries application operations (one function per endpoint)."""
from app.domain.errors import AppError
from app.core.security import require
from app.infrastructure.database import all_rows
from app.services.read_models import stats, catalog, me
from app.services.waitlist_priority import ordered_candidates
from urllib.parse import parse_qs, urlparse

def op_bootstrap(c, user, payload, respond, headers, request_path, method, path):
    return respond({'user': user, 'stats': stats(c)})


def op_catalog(c, user, payload, respond, headers, request_path, method, path):
    return respond({'sections': catalog(c, user)})


def op_me(c, user, payload, respond, headers, request_path, method, path):
    return respond(me(c, user))


def op_activity(c, user, payload, respond, headers, request_path, method, path):
    require(user, ['affairs', 'admin', 'finance', 'head'])
    return respond({'audit': all_rows(c, 'SELECT a.id,a.action,a.entity,a.details,a.created_at,u.username AS actor\n                        FROM audit a LEFT JOIN users u ON u.id=a.actor_id ORDER BY a.id DESC LIMIT 120')})


def op_students(c, user, payload, respond, headers, request_path, method, path):
    require(user, ['affairs', 'head', 'finance', 'admin'])
    from urllib.parse import parse_qs
    q = parse_qs(urlparse(request_path).query).get('q', [''])[0].strip()
    if len(q) > 100:
        raise AppError('Search query too long / البحث طويل')
    pattern = '%' + q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
    sql = "SELECT u.id,u.username,u.name_ar,u.name_en,u.student_number,u.graduate,u.honors,u.hold,\n                      (SELECT COALESCE(SUM(c.credits),0) FROM enrollments e JOIN sections s ON s.id=e.section_id JOIN courses c ON c.id=s.course_id WHERE e.user_id=u.id) AS credits,\n                      (SELECT COUNT(*) FROM payments p WHERE p.user_id=u.id AND p.status='confirmed') AS confirmed_payments\n                      FROM users u WHERE u.role='student' AND\n                      (? = '' OR u.name_ar LIKE ? ESCAPE '\\' OR u.name_en LIKE ? ESCAPE '\\' OR u.student_number LIKE ? ESCAPE '\\' OR u.username LIKE ? ESCAPE '\\')\n                      ORDER BY u.id LIMIT 200"
    return respond({'students': all_rows(c, sql, (q, pattern, pattern, pattern, pattern)), 'query': q})


def op_payments(c, user, payload, respond, headers, request_path, method, path):
    require(user, ['finance', 'admin'])
    return respond({'payments': all_rows(c, 'SELECT p.id,p.reference,p.status,p.gateway_status,p.created_at,u.username,u.name_ar,u.name_en\n                      FROM payments p JOIN users u ON u.id=p.user_id ORDER BY p.id DESC LIMIT 100')})


def op_waitlist(c, user, payload, respond, headers, request_path, method, path):
    require(user, ['head', 'affairs', 'admin'])
    records=all_rows(c, '''SELECT w.id,w.section_id,w.status,w.joined_at,w.note,u.username,c.code,s.label
        FROM waitlist w JOIN users u ON u.id=w.user_id JOIN sections s ON s.id=w.section_id
        JOIN courses c ON c.id=s.course_id ORDER BY w.id DESC LIMIT 150''')
    cache={}
    for entry in records:
        if entry['status']!='waiting':continue
        sid=entry['section_id']
        if sid not in cache:
            cache[sid]={x['id']:(rank,x['priority_reason'])
                       for rank,x in enumerate(ordered_candidates(c,sid),1)}
        rank=cache[sid].get(entry['id'])
        if rank:
            entry['priority_position'],entry['priority_reason']=rank
    return respond({'waitlist':records})
