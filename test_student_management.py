"""Isolated tests for Student Affairs student search, creation and academic profile.
Run: python test_student_management.py (stdlib only, never changes registration.sqlite3).
"""
import http.cookiejar
import json
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as scratch:
    db = Path(scratch) / 'test.sqlite3'
    # Create an isolated fixture from the schema/seed routine, not a shipped database file.
    # This permits distributing source code without users or credentials in GitHub.
    from app.core import config as cfg
    from app.infrastructure.database import init_db
    original_db = cfg.DB_PATH
    original_demo = os.environ.get('MINDSCRIPT_TEST_DEMO')
    try:
        cfg.DB_PATH = db
        os.environ['MINDSCRIPT_TEST_DEMO'] = '1'
        init_db()
    finally:
        cfg.DB_PATH = original_db
        if original_demo is None:
            os.environ.pop('MINDSCRIPT_TEST_DEMO', None)
        else:
            os.environ['MINDSCRIPT_TEST_DEMO'] = original_demo
    probe = socket.socket()
    probe.bind(('127.0.0.1', 0))
    port = probe.getsockname()[1]
    probe.close()
    env = {**os.environ, 'MINDSCRIPT_DB': str(db), 'MINDSCRIPT_PORT': str(port), 'MINDSCRIPT_QUIET': '1', 'MINDSCRIPT_TEST_DEMO': '1'}
    process = subprocess.Popen([sys.executable, str(ROOT / 'server.py')], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    cookies = http.cookiejar.CookieJar()
    client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))

    def call(path, body=None):
        request = urllib.request.Request('http://127.0.0.1:' + str(port) + '/api/' + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={'Content-Type': 'application/json'})
        try:
            with client.open(request, timeout=10) as result:
                return result.status, json.load(result)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    try:
        for _ in range(50):
            try:
                call('catalog')
                break
            except (urllib.error.URLError, ConnectionError):
                time.sleep(.1)
        assert call('login', {'username':'affairs','password':'Demo123!'})[0] == 200
        payload = {'username':'newstudentcheck','name_ar':'ليلى ناصر','name_en':'Layla Nasser',
          'student_number':'NEWSTU889','email':'layla@example.org','phone':'+963999000111',
          'reason':'إنشاء حساب اختباري للتأكد من قواعد البيانات'}
        code, created = call('affairs/student/create', payload)
        assert code == 201, created
        assert created['temporary_password'] != 'Demo123!'
        student_id = created['student_id']
        assert call('affairs/student/create', payload)[0] == 409
        assert len(call('students?q='+urllib.parse.quote('ليلى'))[1]['students']) == 1
        assert len(call('students?q=NEWSTU889')[1]['students']) == 1
        assert len(call('students?q=%')[1]['students']) == 0
        code, profile = call('affairs/student/profile?id='+str(student_id))
        assert code == 200, profile
        assert profile['academic_summary']['registered_credits'] == 0
        assert all(key in profile for key in ('completed','payments','waitlist','exception','history'))
        assert call('logout', {})[0] == 200
        assert call('login', {'username':'student','password':'Demo123!'})[0] == 200
        assert call('affairs/student/create', {**payload, 'username':'differentstudent','student_number':'NEWSTU990'})[0] == 403
        assert call('affairs/student/profile?id='+str(student_id))[0] == 403
        print('PASS: student creation, validation, Arabic/name/number search, academic profile, role permissions; isolated database')
    finally:
        process.terminate()
        process.wait(timeout=5)
