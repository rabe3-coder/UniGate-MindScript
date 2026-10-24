"""Admin application operations (one function per endpoint)."""
from app.domain.errors import AppError
import os
from app.core.security import require
from app.infrastructure.database import transaction, audit, seed, RESET_LOCK

def op_admin_settings(c, user, payload, respond, headers, request_path, method, path):
    require(user, ['admin'])
    body = payload
    key = body.get('key')
    value = str(body.get('value'))
    accepted = {'phase': ['regular', 'early', 'add_drop', 'closed'], 'registration_enabled': ['true', 'false']}
    if key not in accepted or value not in accepted[key]:
        raise AppError('Unknown setting or value')
    with transaction(c):
        c.execute('UPDATE settings SET value=? WHERE key=?', (value, key))
        audit(c, user['id'], 'SETTING_CHANGE', 'settings', {'key': key, 'value': value})
    return respond({'success': True})


def op_admin_reset(c, user, payload, respond, headers, request_path, method, path):
    require(user, ['admin'])
    if os.environ.get('MINDSCRIPT_TEST_DEMO')!='1':
        raise AppError('Reset is disabled to protect registered students / إعادة الضبط معطلة لحماية حسابات الطلاب',403,'RESET_DISABLED')
    body = payload
    if body.get('confirmation') != 'RESET DEMO':
        raise AppError('Type RESET DEMO to confirm')
    with RESET_LOCK, transaction(c):
        for table in ['student_basket', 'swap_requests', 'course_grades', 'student_plan', 'audit', 'registration_requests', 'waitlist', 'enrollments', 'payments', 'exceptions', 'completed', 'sections', 'courses', 'sessions', 'users', 'settings']:
            c.execute('DELETE FROM ' + table)
        seed(c)
    return respond({'success': True, 'message': 'Database reset; sign in again'})

