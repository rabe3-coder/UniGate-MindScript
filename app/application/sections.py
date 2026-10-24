"""Sections application operations (one function per endpoint)."""
from app.domain.errors import AppError
from app.core.security import require
from app.infrastructure.database import one, transaction, audit
from app.services.registration import promote_waitlist
import sqlite3

def op_section_capacity(c, user, payload, respond, headers, request_path, method, path):
    require(user, ['head', 'admin'])
    body = payload
    sid = int(body.get('section_id', 0))
    cap = int(body.get('capacity', 0))
    with transaction(c):
        sec = one(c, 'SELECT * FROM sections WHERE id=?', (sid,))
        if not sec:
            raise AppError('Section not found', 404)
        n = one(c, 'SELECT COUNT(*) n FROM enrollments WHERE section_id=?', (sid,))['n']
        if cap < n or cap < 1 or cap > 300:
            raise AppError('Capacity must be ≥ confirmed enrollments and ≤ 300 / السعة غير مقبولة')
        c.execute('UPDATE sections SET capacity=? WHERE id=?', (cap, sid))
        promotion = promote_waitlist(c, sid, user['id']) if cap > sec['capacity'] else {'promoted': [], 'skipped': []}
        audit(c, user['id'], 'CAPACITY_CHANGE', 'section', {'section_id': sid, 'old': sec['capacity'], 'new': cap, 'promotion': promotion})
    return respond({'success': True, 'promotion': promotion})


def op_section_create(c, user, payload, respond, headers, request_path, method, path):
    require(user, ['head', 'admin'])
    body = payload
    try:
        cid = int(body['course_id'])
        cap = int(body['capacity'])
        day = int(body['weekday'])
        start = int(body['start_time'])
        end = int(body['end_time'])
        label = str(body['label']).strip().upper()[:12]
    except Exception:
        raise AppError('Invalid section information')
    if not (1 <= cap <= 300 and 0 <= day <= 6 and (7 <= start < end <= 22) and label):
        raise AppError('Invalid section fields')
    with transaction(c):
        if not one(c, 'SELECT 1 FROM courses WHERE id=?', (cid,)):
            raise AppError('Unknown course')
        try:
            c.execute('INSERT INTO sections(course_id,label,capacity,weekday,start_time,end_time,instructor) VALUES(?,?,?,?,?,?,?)', (cid, label, cap, day, start, end, 'New demo instructor'))
        except sqlite3.IntegrityError:
            raise AppError('Section label already exists', 409)
        sid = c.execute('SELECT last_insert_rowid()').fetchone()[0]
        audit(c, user['id'], 'SECTION_OPEN', 'section', {'section_id': sid, 'capacity': cap})
    return respond({'success': True, 'section_id': sid})

