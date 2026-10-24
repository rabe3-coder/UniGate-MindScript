"""Isolated integration tests for student sign-up, persistent draft basket, staff-only provisioning."""
import http.cookiejar
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent

class Client:
    def __init__(self,base):
        self.base=base
        self.jar=http.cookiejar.CookieJar()
        self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
    def request(self,route,data=None):
        request=urllib.request.Request(self.base+'/api/'+route,
             data=json.dumps(data).encode('utf-8') if data is not None else None,
             headers={'Content-Type':'application/json'} if data is not None else {})
        try:
            with self.opener.open(request,timeout=8) as res:return res.status,json.load(res)
        except urllib.error.HTTPError as err:return err.code,json.load(err)


def boot(database):
    port_sock=socket.socket();port_sock.bind(('127.0.0.1',0));port=port_sock.getsockname()[1];port_sock.close()
    env={**os.environ,'MINDSCRIPT_DB':str(database),'MINDSCRIPT_PORT':str(port),'MINDSCRIPT_QUIET':'1'}
    env.pop('MINDSCRIPT_TEST_DEMO',None)
    proc=subprocess.Popen([sys.executable,str(ROOT/'server.py')],cwd=ROOT,env=env,
                          stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    base=f'http://127.0.0.1:{port}'
    for _ in range(55):
        try:
            with urllib.request.urlopen(base,timeout=.4):break
        except (urllib.error.URLError,ConnectionError):time.sleep(.1)
    else:
        proc.terminate();raise RuntimeError(proc.communicate(timeout=5))
    return proc,base


def fresh_test(temp):
    db=Path(temp)/'accounts.sqlite3'
    proc,base=boot(db)
    try:
        c=Client(base)
        code,_=c.request('login',{'username':'admin','password':'Demo123!'})
        assert code==401
        code,x=c.request('signup',{'name':'ربيع أحمد','student_number':'202600189','password':'StrongStudent4!',
                                    'role':'admin','is_active':1})
        assert code==201,(code,x)
        assert x['role']=='student'
        code,view=c.request('bootstrap')
        assert code==200 and view['user']['role']=='student' and view['user']['username']=='202600189'
        code,b=c.request('basket')
        assert code==200 and b['section_ids']==[]
        code,cat=c.request('catalog');sid=next(x['id'] for x in cat['sections'] if x['code']=='ENG101')
        code,payload=c.request('basket',{'action':'add','section_id':sid})
        assert code==200 and payload['section_ids']==[sid]
        assert c.request('logout',{})[0]==200
        code,x=c.request('signup',{'name':'نسخة ثانية','student_number':'202600189','password':'LongStudent9%'})
        assert code==409 and x['code']=='DUPLICATE_STUDENT_NUMBER'
        assert c.request('login',{'username':'202600189','password':'wrong-password'})[0]==401
        new_browser=Client(base)
        assert new_browser.request('login',{'username':'202600189','password':'StrongStudent4!'})[0]==200
        assert new_browser.request('basket')[1]['section_ids']==[sid]
        assert new_browser.request('me')[1]['schedule']==[]
        # After relogin, a confirmed enrollment should persist independently.
        assert new_browser.request('payment/request',{'request_key':'newstudentpay0001','outcome':'success'})[0]==200
        cat=new_browser.request('catalog')[1]['sections']
        ids=[next(s['id'] for s in cat if s['code']==code and s['label']=='A')
             for code in ['ENG101','PHY101','HUM101','ETH101']]
        checkout=new_browser.request('register',{'section_ids':ids,'request_key':'newstudentcheckout0001'})
        assert checkout[0]==200,checkout
        assert len(new_browser.request('me')[1]['schedule'])==4
        # One selected draft has become a confirmed section and is atomically removed.
        assert new_browser.request('basket')[1]['section_ids']==[]
        assert new_browser.request('affairs/student/create',{})[0]==403
        assert new_browser.request('admin/reset',{'confirmation':'RESET DEMO'})[0]==403
        # No other student's choices can be seen.
        other=Client(base)
        assert other.request('signup',{'name':'محمد محمود','student_number':'202600190','password':'AnotherPass9!'})[0]==201
        assert other.request('basket')[1]['section_ids']==[]
        assert other.request('basket',{'action':'remove','section_id':sid})[1]['section_ids']==[]
        assert new_browser.request('basket')[1]['section_ids']==[]
        # All self-created accounts are students regardless of unexpected form fields.
        # Logout all; provision via the privileged local CLI module, not via HTTP.
    finally:
        proc.terminate();proc.wait(timeout=8)
    from app.core import config
    from app.infrastructure.database import one
    import manage_staff
    old_db=config.DB_PATH
    try:
        config.DB_PATH=db
        data=[manage_staff.Staff('ADMIN','admin','root_supervisor','مدير النظام','SecureAdmin2026!'),
              *[manage_staff.Staff('AFFAIRS_'+str(i),'affairs','affairs_officer_'+str(i),
                    'موظف شؤون الطلاب '+str(i),'SecretAffairs2026!') for i in range(1,4)]]
        manage_staff.provision(data,('admin','affairs'))
        c=sqlite3.connect(db)
        assert c.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND is_active=1").fetchone()[0]==1
        assert c.execute("SELECT COUNT(*) FROM users WHERE role='affairs' AND is_active=1").fetchone()[0]==3
        assert c.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0]==2
        assert c.execute("SELECT COUNT(*) FROM student_basket").fetchone()[0]==0
        assert c.execute("SELECT COUNT(*) FROM enrollments").fetchone()[0]==4
        c.close()
    finally:config.DB_PATH=old_db
    proc,base=boot(db)
    try:
        root=Client(base);officers=[Client(base) for _ in range(3)]
        assert root.request('login',{'username':'root_supervisor','password':'SecureAdmin2026!'})[0]==200
        assert root.request('bootstrap')[1]['user']['role']=='admin'
        for i,officer in enumerate(officers,1):
            assert officer.request('login',{'username':'affairs_officer_'+str(i),'password':'SecretAffairs2026!'})[0]==200
            assert officer.request('bootstrap')[1]['user']['role']=='affairs'
            assert officer.request('admin/settings',{'key':'phase','value':'regular'})[0]==403
        assert root.request('students')[0]==200
        assert root.request('login',{'username':'admin','password':'Demo123!'})[0]==401
        student=Client(base)
        assert student.request('login',{'username':'202600189','password':'StrongStudent4!'})[0]==200
        assert student.request('basket')[1]['section_ids']==[]
        assert len(student.request('me')[1]['schedule'])==4
        assert root.request('signup',{'name':'مدير ثاني','student_number':'202600191','password':'AnotherPass9!'})[0]==409
    finally:proc.terminate();proc.wait(timeout=8)
    print('PASS: student-only signup; duplicate rejection; DB persistence, session separation, staff roles and secure local provisioning')


def upgrade_test(temp):
    # Emulates an existing v2 database: verifies old student records survive and
    # publicly known admin/affairs demo credentials are automatically disabled.
    from app.infrastructure.database import init_db,connect
    from app.core import config
    from app.core.clock import now
    from app.core.crypto import password_hash
    db=Path(temp)/'old.sqlite3'
    old=config.DB_PATH
    try:
        config.DB_PATH=db
        os.environ['MINDSCRIPT_TEST_DEMO']='1'
        init_db()
        os.environ.pop('MINDSCRIPT_TEST_DEMO',None)
        c=connect();student=c.execute("SELECT id FROM users WHERE username='student'").fetchone()['id']
        c.execute("UPDATE users SET name_ar='اسم الطالب المعدل', student_number='CUSTOM884' WHERE id=?",(student,))
        c.close()
        # simulate schema already upgraded but provisioning marker absent
        c=connect();c.execute("DELETE FROM settings WHERE key='staff_provisioning_migration_v1'");c.close()
        init_db()
        c=connect()
        assert c.execute("SELECT name_ar FROM users WHERE id=?",(student,)).fetchone()['name_ar']=='اسم الطالب المعدل'
        assert c.execute("SELECT COUNT(*) n FROM users WHERE role='student' AND is_active=1").fetchone()['n']==5
        assert c.execute("SELECT COUNT(*) n FROM users WHERE role<>'student' AND is_active=1").fetchone()['n']==0
        c.close()
    finally:
        config.DB_PATH=old
        os.environ.pop('MINDSCRIPT_TEST_DEMO',None)
    print('PASS: migration preserves students and disables legacy privileged demo accounts')

if __name__=='__main__':
    with tempfile.TemporaryDirectory() as temp:
        fresh_test(temp)
    with tempfile.TemporaryDirectory() as temp:
        upgrade_test(temp)
