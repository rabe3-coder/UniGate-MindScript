"""Enrollment application operations (one function per endpoint)."""
from app.domain.errors import AppError
from app.core.clock import now
from app.core.security import require
from app.infrastructure.database import one, setting, transaction, audit
from app.services.swaps import invalidate_after_drop
from app.services.registration import permitted, validate_section, min_credits, enroll_basket, registered, promote_waitlist

def op_register(c, user, payload, respond, headers, request_path, method, path):
    body = payload
    return respond(enroll_basket(c, user, body.get('section_ids', []), body.get('request_key', '')))


def op_drop(c, user, payload, respond, headers, request_path, method, path):
    require(user, ['student'])
    body = payload
    eid = int(body.get('enrollment_id', 0))
    with transaction(c):
        permitted(c, user)
        entry = one(c, 'SELECT e.section_id,c.credits FROM enrollments e JOIN sections s ON s.id=e.section_id JOIN courses c ON c.id=s.course_id\n                            WHERE e.id=? AND e.user_id=?', (eid, user['id']))
        if not entry:
            raise AppError('Enrollment not found', 404)
        current = registered(c, user['id'])
        remainder = sum((x['credits'] for x in current)) - entry['credits']
        if setting(c, 'phase') != 'add_drop' and 0 < remainder < min_credits(c, user):
            raise AppError('Dropping would violate minimum credits / الانسحاب يخالف الحد الأدنى للساعات', 409, 'MIN_CREDITS')
        c.execute('DELETE FROM enrollments WHERE id=?', (eid,))
        invalidate_after_drop(c, user['id'], entry['section_id'])
        promotion = promote_waitlist(c, entry['section_id'], user['id'])
        audit(c, user['id'], 'DROP', 'enrollment', {'enrollment_id': eid, 'promotion': promotion})
    return respond({'success': True, 'promotion': promotion})


def op_waitlist_join(c, user, payload, respond, headers, request_path, method, path):
    require(user, ['student'])
    sid = int(payload.get('section_id', 0))
    with transaction(c):
        permitted(c, user)
        s = validate_section(c, user, sid)
        if one(c, 'SELECT COUNT(*) n FROM enrollments WHERE section_id=?', (sid,))['n'] < s['capacity']:
            raise AppError('Seat available: register instead / يوجد مقعد متاح؛ سجّل مباشرة', 409, 'SEAT_AVAILABLE')
        if one(c, "SELECT 1 FROM waitlist WHERE user_id=? AND section_id=? AND status='waiting'", (user['id'], sid)):
            raise AppError('Already waitlisted / موجود مسبقًا بقائمة الانتظار', 409, 'DUPLICATE_WAITLIST')
        c.execute('INSERT INTO waitlist(user_id,section_id,status,joined_at,note) VALUES(?,?,?, ?,?)\n                       ON CONFLICT(user_id,section_id) DO UPDATE SET status=excluded.status,joined_at=excluded.joined_at,note=excluded.note', (user['id'], sid, 'waiting', now(), ''))
        audit(c, user['id'], 'WAITLIST_JOIN', 'waitlist', {'section_id': sid})
    return respond({'success': True})


def op_waitlist_leave(c, user, payload, respond, headers, request_path, method, path):
    require(user, ['student'])
    wid = int(payload.get('waitlist_id', 0))
    with transaction(c):
        result = c.execute("UPDATE waitlist SET status='cancelled' WHERE id=? AND user_id=? AND status='waiting'", (wid, user['id']))
        if not result.rowcount:
            raise AppError('Active waitlist entry not found', 404)
        audit(c, user['id'], 'WAITLIST_LEAVE', 'waitlist', {'waitlist_id': wid})
    return respond({'success': True})

