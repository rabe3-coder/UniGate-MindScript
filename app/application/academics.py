"""Academics application operations (one function per endpoint)."""
from app.domain.errors import AppError
from app.core.clock import now
from app.core.security import require
from app.infrastructure.database import one, all_rows, setting, transaction, audit
from app.services.academics import academic_report
from urllib.parse import parse_qs, urlparse

def op_affairs_academic(c, user, payload, respond, headers, request_path, method, path):
    require(user, ['affairs', 'admin'])
    if method == 'GET':
        from urllib.parse import parse_qs
        args = parse_qs(urlparse(request_path).query)
        try:
            uid = int(args.get('id', ['0'])[0])
        except (ValueError, TypeError):
            raise AppError('Invalid student ID')
        return respond({'academic': academic_report(c, uid), 'courses': all_rows(c, 'SELECT id,code,name_ar,name_en,credits FROM courses ORDER BY code')})
    body = payload
    try:
        uid = int(body.get('user_id'))
        cid = int(body.get('course_id'))
    except (ValueError, TypeError):
        raise AppError('Invalid student or course ID')
    reason = body.get('reason', '')
    if not isinstance(reason, str) or not 6 <= len(reason.strip()) <= 500:
        raise AppError('Documented reason is required (6–500 characters) / السبب مطلوب')
    kind = body.get('operation')
    with transaction(c):
        if not one(c, "SELECT 1 FROM users WHERE id=? AND role='student'", (uid,)):
            raise AppError('Student not found', 404)
        if not one(c, 'SELECT 1 FROM courses WHERE id=?', (cid,)):
            raise AppError('Course not found', 404)
        if kind == 'plan_add':
            required = body.get('required', True)
            if type(required) is not bool:
                raise AppError('Invalid required flag')
            c.execute('INSERT INTO student_plan(user_id,course_id,required,assigned_at) VALUES(?,?,?,?) ON CONFLICT(user_id,course_id) DO UPDATE SET required=excluded.required', (uid, cid, int(required), now()))
        elif kind == 'plan_remove':
            c.execute('DELETE FROM student_plan WHERE user_id=? AND course_id=?', (uid, cid))
        elif kind == 'grade_record':
            raw = body.get('score')
            if isinstance(raw, bool) or not isinstance(raw, (int, float)) or (not 0 <= raw <= 100):
                raise AppError('Score must be between 0 and 100 / العلامة من 0 إلى 100')
            score = float(raw)
            passed = int(score >= float(setting(c, 'academic_pass_score') or 60))
            c.execute('INSERT INTO course_grades(user_id,course_id,score,updated_at,updated_by) VALUES(?,?,?,?,?) ON CONFLICT(user_id,course_id) DO UPDATE SET score=excluded.score,updated_at=excluded.updated_at,updated_by=excluded.updated_by', (uid, cid, score, now(), user['id']))
            c.execute('INSERT INTO completed(user_id,course_id,passed) VALUES(?,?,?) ON CONFLICT(user_id,course_id) DO UPDATE SET passed=excluded.passed', (uid, cid, passed))
        else:
            raise AppError('Unknown academic operation')
        audit(c, user['id'], 'ACADEMIC_' + kind.upper(), 'academic', {'student_id': uid, 'course_id': cid, 'operation': kind, 'score': body.get('score') if kind == 'grade_record' else None, 'required': body.get('required') if kind == 'plan_add' else None, 'reason': reason.strip()})
    return respond({'success': True, 'academic': academic_report(c, uid)})


def op_affairs_grade(c, user, payload, respond, headers, request_path, method, path):
    require(user, ['affairs', 'admin'])
    body = payload
    uid = int(body.get('user_id', 0))
    cid = int(body.get('course_id', 0))
    passed = bool(body.get('passed'))
    with transaction(c):
        if not one(c, "SELECT 1 FROM users WHERE id=? AND role='student'", (uid,)):
            raise AppError('Student not found')
        if not one(c, 'SELECT 1 FROM courses WHERE id=?', (cid,)):
            raise AppError('Course not found')
        if one(c, 'SELECT 1 FROM course_grades WHERE user_id=? AND course_id=?', (uid, cid)):
            raise AppError('A numeric grade exists. Use the academic profile grade editor / توجد علامة رقمية، استخدم محرر العلامات', 409, 'GRADE_CONFLICT')
        c.execute('INSERT INTO completed(user_id,course_id,passed) VALUES(?,?,?)\n                       ON CONFLICT(user_id,course_id) DO UPDATE SET passed=excluded.passed', (uid, cid, int(passed)))
        affected = all_rows(c, 'SELECT c.code FROM enrollments e JOIN sections s ON s.id=e.section_id JOIN courses c ON c.id=s.course_id\n                            WHERE e.user_id=? AND c.prerequisite_id=?', (uid, cid))
        audit(c, user['id'], 'GRADE_APPEAL', 'academic', {'student_id': uid, 'course_id': cid, 'passed': passed, 'requires_policy_review': affected})
    return respond({'success': True, 'review_enrollments': affected, 'note': 'Existing enrollment is flagged for review; not automatically cancelled.'})


def op_affairs_hold(c, user, payload, respond, headers, request_path, method, path):
    require(user, ['affairs', 'admin'])
    body = payload
    uid = int(body.get('user_id', 0))
    hold = int(bool(body.get('hold')))
    with transaction(c):
        result = c.execute("UPDATE users SET hold=? WHERE id=? AND role='student'", (hold, uid))
        if not result.rowcount:
            raise AppError('Student not found', 404)
        audit(c, user['id'], 'ADMIN_HOLD', 'student', {'student_id': uid, 'hold': hold})
    return respond({'success': True})


def op_affairs_exception(c, user, payload, respond, headers, request_path, method, path):
    require(user, ['affairs', 'admin'])
    body = payload
    uid = int(body.get('user_id', 0))
    minimum = int(body.get('min_override', 0))
    reason = str(body.get('reason', '')).strip()
    if not 1 <= minimum <= 12 or len(reason) < 6:
        raise AppError('Minimum credits 1–12 and documented reason (≥6 characters) required')
    with transaction(c):
        if not one(c, "SELECT 1 FROM users WHERE id=? AND role='student'", (uid,)):
            raise AppError('Student not found')
        c.execute('INSERT INTO exceptions(user_id,min_override,reason,approved_by) VALUES(?,?,?,?)\n                      ON CONFLICT(user_id) DO UPDATE SET min_override=excluded.min_override,reason=excluded.reason,approved_by=excluded.approved_by', (uid, minimum, reason, user['id']))
        audit(c, user['id'], 'MINIMUM_EXCEPTION', 'student', {'student_id': uid, 'min_override': minimum, 'reason': reason, 'demo_approval': True})
    return respond({'success': True})

