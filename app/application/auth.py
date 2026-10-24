"""Student-only self-registration and safe session issuance."""
import hashlib
import re
import secrets
from http.cookies import SimpleCookie
from app.core.clock import now
from app.core.config import PUBLIC_ORIGIN
from app.core.crypto import password_hash, password_ok
from app.domain.errors import AppError
from app.infrastructure.database import one, transaction, audit

STUDENT_NUMBER = re.compile(r'[A-Za-z0-9_-]{3,24}\Z')

def issue_session(c, user_id):
    token = secrets.token_urlsafe(32)
    digest = hashlib.sha256(token.encode('ascii')).hexdigest()
    c.execute('INSERT INTO sessions(token_hash,user_id,created_at) VALUES(?,?,?)',
              (digest, user_id, now()))
    secure = '; Secure' if PUBLIC_ORIGIN.startswith('https://') else ''
    return f'ms_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200{secure}'

def op_signup(c, user, payload, respond, headers, request_path, method, path):
    """Public route, but role is hard-coded to student on the server."""
    if user:
        raise AppError('Sign out before creating a new account / سجل الخروج أولاً',409,'ALREADY_LOGGED_IN')
    if not all(isinstance(payload.get(k),str) for k in ('name','student_number','password')):
        raise AppError('Name, university number and password are required / الحقول الثلاثة مطلوبة',400,'VALIDATION')
    name = payload['name'].strip()
    number = payload['student_number'].strip()
    password = payload['password']
    if not 3 <= len(name) <= 100 or any(ord(ch)<32 for ch in name):
        raise AppError('Full name must be 3–100 characters / الاسم الكامل غير صالح',400,'VALIDATION')
    if not STUDENT_NUMBER.fullmatch(number):
        raise AppError('University number must contain 3–24 Latin letters, digits, - or _ / الرقم الجامعي غير صالح',400,'VALIDATION')
    if not 10 <= len(password) <= 128 or not any(ch.isalpha() for ch in password) or not any(ch.isdigit() for ch in password):
        raise AppError('Password must be 10–128 characters with letters and digits / كلمة المرور لا تقل عن 10 رموز وتتضمن حروفاً وأرقاماً',400,'VALIDATION')
    with transaction(c):
        if one(c,'SELECT id FROM users WHERE student_number=? COLLATE NOCASE OR username=? COLLATE NOCASE',(number,number)):
            raise AppError('University number is already registered / الرقم الجامعي مسجل مسبقاً',409,'DUPLICATE_STUDENT_NUMBER')
        record = c.execute("""INSERT INTO users(username,name_ar,name_en,role,password_hash,
                    graduate,honors,hold,student_number,phone,email,is_active)
                    VALUES(?,?,?,'student',?,0,0,0,?,'','',1)""",
                    (number,name,name,password_hash(password),number))
        user_id=record.lastrowid
        audit(c,user_id,'SELF_SIGNUP','student',{'student_id':user_id,'student_number':number})
        cookie=issue_session(c,user_id)
    return respond({'success':True,'role':'student','student_number':number},201,cookie)

def op_login(c, user, payload, respond, headers, request_path, method, path):
    identifier = payload.get('username','')
    password = payload.get('password','')
    if not isinstance(identifier,str) or not isinstance(password,str) or len(identifier)>128 or len(password)>256:
        raise AppError('Invalid credentials / بيانات الدخول غير صحيحة',401,'AUTH')
    identifier=identifier.strip()
    account=one(c,"""SELECT * FROM users
        WHERE (username=? COLLATE NOCASE OR (role='student' AND student_number=? COLLATE NOCASE))
        AND is_active=1 ORDER BY CASE WHEN username=? COLLATE NOCASE THEN 0 ELSE 1 END LIMIT 1""",
        (identifier,identifier,identifier))
    if not account or not password_ok(password,account['password_hash']):
        raise AppError('Invalid credentials / بيانات الدخول غير صحيحة',401,'AUTH')
    cookie=issue_session(c,account['id'])
    audit(c,account['id'],'LOGIN','session',{'user_id':account['id']})
    return respond({'success':True},cookie=cookie)

def op_logout(c, user, payload, respond, headers, request_path, method, path):
    cookies=SimpleCookie()
    try:cookies.load(headers.get('Cookie',''))
    except Exception:pass
    if cookies.get('ms_session'):
        digest=hashlib.sha256(cookies['ms_session'].value.encode('ascii')).hexdigest()
        c.execute('DELETE FROM sessions WHERE token_hash=?',(digest,))
    return respond({'success':True},cookie='ms_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0' + ('; Secure' if PUBLIC_ORIGIN.startswith('https://') else ''))
