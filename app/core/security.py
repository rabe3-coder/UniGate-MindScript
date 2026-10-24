"""Authentication and authorization (database-independent access checks)."""
from http.cookies import SimpleCookie
import hashlib
from datetime import datetime, timezone, timedelta
from app.domain.errors import AppError
from app.infrastructure.database import one

def user_from_cookie(c, raw):
    cookie=SimpleCookie()
    try: cookie.load(raw)
    except Exception: return None
    item=cookie.get('ms_session')
    if not item: return None
    token=item.value
    row=one(c,'''SELECT u.id,u.username,u.name_ar,u.name_en,u.role,u.graduate,u.honors,u.hold FROM sessions s
        JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND u.is_active=1''',(hashlib.sha256(token.encode()).hexdigest(),))
    if not row:
        return None
    session = one(c,'SELECT created_at FROM sessions WHERE token_hash=?',
                  (hashlib.sha256(token.encode()).hexdigest(),))
    try:
        started = datetime.fromisoformat(session['created_at'])
        if started.tzinfo is None:
            started=started.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc)-started > timedelta(hours=12):
            c.execute('DELETE FROM sessions WHERE token_hash=?',
                      (hashlib.sha256(token.encode()).hexdigest(),))
            return None
    except (TypeError,ValueError,KeyError):
        return None
    return dict(row)

def require(user, roles=None):
    if not user: raise AppError('Please sign in / يرجى تسجيل الدخول',401,'AUTH')
    if roles and user['role'] not in roles: raise AppError('Access denied / غير مصرح بهذه العملية',403,'FORBIDDEN')

