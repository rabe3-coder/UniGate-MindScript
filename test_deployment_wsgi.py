"""Standalone WSGI compatibility, sessions, roles, persistence and origin checks.
Runs against an isolated temporary SQLite database, never the user's real one.
"""
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from wsgiref.util import setup_testing_defaults

TEMP = tempfile.TemporaryDirectory()
os.environ['MINDSCRIPT_DB'] = str(Path(TEMP.name) / 'web.sqlite3')
os.environ['UNIGATE_PUBLIC_ORIGIN'] = 'https://demonstration.pythonanywhere.com'
os.environ['UNIGATE_SQLITE_JOURNAL'] = 'DELETE'
os.environ.pop('MINDSCRIPT_TEST_DEMO', None)

from app.wsgi import application
from app.infrastructure.database import connect, one


def send(method, route, payload=None, cookie=None, origin=None, scheme='https'):
    body=json.dumps(payload or {}, ensure_ascii=False).encode() if method=='POST' else b''
    env={}
    setup_testing_defaults(env)
    env.update({'REQUEST_METHOD':method, 'PATH_INFO':route, 'wsgi.input':io.BytesIO(body),
                'CONTENT_LENGTH':str(len(body)), 'CONTENT_TYPE':'application/json' if method=='POST' else '',
                'wsgi.url_scheme':scheme, 'REMOTE_ADDR':'127.0.0.1'})
    if cookie: env['HTTP_COOKIE']=cookie
    if origin: env['HTTP_ORIGIN']=origin
    captured={}
    def start(status, headers, exc_info=None):
        captured.update({'status':int(status.split()[0]), 'headers':dict(headers)})
    raw=b''.join(application(env,start))
    try: data=json.loads(raw)
    except Exception: data=raw.decode('utf-8',errors='replace')
    return captured['status'],data,captured['headers']


class DeployedWSGI(unittest.TestCase):
    def test_01_static_html_and_health(self):
        st,data,_=send('GET','/')
        self.assertEqual(st,200)
        self.assertIn('UniGate',data)
        self.assertEqual(send('GET','/healthz')[1]['status'],'ok')
        self.assertEqual(send('GET','/app/infrastructure/database.py')[0],404)

    def test_02_signup_login_logout_and_persistence(self):
        st, data, _=send('POST','/api/signup', {'name':'طالب تجريبي','student_number':'202699991','password':'AcademicDemo123!'}, origin='https://demonstration.pythonanywhere.com')
        self.assertEqual(st,201,data)
        # Signup duplicated student number is rejected even if session omitted.
        st, _, _=send('POST','/api/signup', {'name':'طالب مكرر','student_number':'202699991','password':'AcademicDemo123!'}, origin='https://demonstration.pythonanywhere.com')
        self.assertEqual(st,409)
        st,data,headers=send('POST','/api/login',{'username':'202699991','password':'AcademicDemo123!'},origin='https://demonstration.pythonanywhere.com')
        self.assertEqual(st,200,data)
        self.assertIn('Secure',headers.get('Set-Cookie',''))
        cookie=headers['Set-Cookie'].split(';',1)[0]
        self.assertEqual(send('GET','/api/me',cookie=cookie)[0],200)
        # Persistent user remains after running idempotent schema initializer again.
        from app.infrastructure.database import init_db
        init_db()
        c=connect()
        try: self.assertEqual(one(c,"SELECT count(*) as n FROM users WHERE student_number=?",('202699991',))['n'],1)
        finally: c.close()
        self.assertEqual(send('POST','/api/logout',{},cookie=cookie,origin='https://demonstration.pythonanywhere.com')[0],200)
        self.assertEqual(send('GET','/api/me',cookie=cookie)[0],401)

    def test_03_reject_cross_site_and_student_role_forgery(self):
        p={'name':'زائر تجريبي','student_number':'202699992','password':'AcademicDemo123!', 'role':'admin'}
        self.assertEqual(send('POST','/api/signup',p,origin='https://evil.example')[0],403)
        self.assertEqual(send('POST','/api/signup',p)[0],403)
        self.assertEqual(send('POST','/api/signup',p,origin='https://demonstration.pythonanywhere.com')[0],201)
        c=connect()
        try:self.assertEqual(one(c,"SELECT role FROM users WHERE username='202699992'")['role'],'student')
        finally:c.close()

    def test_04_sensitive_routes_not_public(self):
        for route in ['/api/activity','/api/students','/api/affairs/student/profile','/api/payments']:
            self.assertEqual(send('GET',route)[0],401,route)
        self.assertEqual(send('GET','/unknown')[0],404)
        self.assertEqual(send('POST','/api/login', {'username':'x', 'password':'y'}, origin='https://demonstration.pythonanywhere.com')[0],401)

    def test_05_https_redirect(self):
        st,_,headers=send('GET','/', scheme='http')
        self.assertEqual(st,308)
        self.assertEqual(headers['Location'],'https://demonstration.pythonanywhere.com/')


if __name__=='__main__': unittest.main(verbosity=2)
