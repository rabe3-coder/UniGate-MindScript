"""End-to-end HTTP tests of section swap and access controls on an isolated database.
No third-party dependencies or user's actual registration.sqlite3 required.
"""
from pathlib import Path
import http.cookiejar
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error

ROOT=Path(__file__).resolve().parent


def request(base, path, cookie=None, data=None, origin=None):
    payload=json.dumps(data).encode('utf-8') if data is not None else None
    headers={'Content-Type':'application/json'} if data is not None else {}
    if cookie:headers['Cookie']=cookie
    if origin:headers['Origin']=origin
    req=urllib.request.Request(base+'/api/'+path,data=payload,headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=5) as response:
            return response.status,json.load(response),response.headers
    except urllib.error.HTTPError as error:
        return error.code,json.load(error),error.headers


def run():
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'http.sqlite3'
        probe=socket.socket();probe.bind(('127.0.0.1',0));port=probe.getsockname()[1];probe.close()
        base='http://127.0.0.1:'+str(port)
        env={**os.environ,'MINDSCRIPT_DB':str(path),'MINDSCRIPT_PORT':str(port),'MINDSCRIPT_QUIET':'1'}
        process=subprocess.Popen([sys.executable,str(ROOT/'server.py')],cwd=str(ROOT),env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        try:
            for _ in range(60):
                try:
                    with urllib.request.urlopen(base,timeout=.4):break
                except Exception:time.sleep(.1)
            else:raise RuntimeError('Server failed to start')
            def login(username):
                status,out,headers=request(base,'login',data={'username':username,'password':'Demo123!'})
                assert status==200,(username,out)
                return headers['Set-Cookie'].split(';')[0]
            c1=login('student');c2=login('student2');finance=login('finance')
            status,out,_=request(base,'swap',cookie=finance)
            assert status==403,out
            # Prepare one seat in each reciprocal section in the isolated DB.
            import sqlite3
            db=sqlite3.connect(path)
            db.execute('PRAGMA foreign_keys=ON')
            a=db.execute("SELECT s.id FROM sections s JOIN courses c ON c.id=s.course_id WHERE c.code='CS102' AND s.label='A'").fetchone()[0]
            b=db.execute("SELECT s.id FROM sections s JOIN courses c ON c.id=s.course_id WHERE c.code='CS102' AND s.label='B'").fetchone()[0]
            u=db.execute("SELECT id FROM users WHERE username='student'").fetchone()[0]
            db.execute('UPDATE sections SET capacity=1 WHERE id IN (?,?)',(a,b))
            db.execute("INSERT INTO enrollments(user_id,section_id,created_at,origin) VALUES(?,?,datetime('now'),'http-test')",(u,b))
            db.commit();db.close()
            status,out,_=request(base,'swap/request',cookie=c2,data={'from_section_id':a,'to_section_id':b})
            assert status==201 and out['status']=='pending',(status,out)
            status,out,_=request(base,'swap/request',cookie=c1,data={'from_section_id':b,'to_section_id':a})
            assert status==201 and out['status']=='matched',(status,out)
            assert not any(k in out for k in ('other_student','matched_username','matched_user_id'))
            for cookie,expected in ((c1,'A'),(c2,'B')):
                status,out,_=request(base,'me',cookie=cookie)
                assert status==200 and any(x['code']=='CS102' and x['label']==expected for x in out['schedule']),out
            status,out,_=request(base,'swap',cookie=c1)
            assert status==200 and out['requests'][0]['status']=='matched'
            status,out,_=request(base,'swap/request',cookie=c1,
                                 data={'from_section_id':a,'to_section_id':b},
                                 origin='https://untrusted.invalid')
            assert status==403 and out['code']=='ORIGIN',(status,out)
            admin=login('admin')
            status,out,_=request(base,'admin/reset',cookie=admin,data={'confirmation':'RESET DEMO'})
            assert status==200,out
            with sqlite3.connect(path) as after:
                assert after.execute('SELECT COUNT(*) FROM swap_requests').fetchone()[0]==0
            print('PASS: HTTP swap request/match, permissions, privacy, security Origin check, reset')
        finally:
            process.terminate()
            process.communicate(timeout=5)


if __name__=='__main__': run()
