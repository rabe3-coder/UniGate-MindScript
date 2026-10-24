import os,subprocess,tempfile,time,urllib.request,urllib.error,json,sqlite3,socket,sys
root=os.path.dirname(os.path.abspath(__file__))
with tempfile.TemporaryDirectory() as d:
 env=os.environ.copy();env['MINDSCRIPT_DB']=d+'/test.db';env['MINDSCRIPT_PORT']='18889'
 p=subprocess.Popen([sys.executable,root+'/server.py'],cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 try:
  for _ in range(70):
   try:urllib.request.urlopen('http://127.0.0.1:18889/',timeout=.5);break
   except Exception: time.sleep(.1)
  else:raise RuntimeError('Server startup failed '+p.stderr.read().decode())
  def request(route,body=None,cookie=None):
   data=json.dumps(body).encode() if body is not None else None
   headers={'Content-Type':'application/json'} if data else {}
   if cookie: headers['Cookie']=cookie
   rq=urllib.request.Request('http://127.0.0.1:18889/api/'+route,data=data,headers=headers)
   try:
    with urllib.request.urlopen(rq,timeout=5) as r:return r.status,json.loads(r.read()),r.headers
   except urllib.error.HTTPError as e:return e.code,json.loads(e.read()),e.headers
  code,res,hd=request('login',{'username':'affairs','password':'Demo123!'})
  print('login',code);cookie=hd['Set-Cookie'].split(';')[0]
  code,st,hd=request('students',cookie=cookie);uid=st['students'][0]['id']
  code,summary,_=request(f'affairs/academic?id={uid}',cookie=cookie)
  print('empty',code,summary['academic']['summary'])
  cid=summary['courses'][0]['id']
  for body in [dict(operation='plan_add',user_id=uid,course_id=cid,required=True,reason='Assign required academic course'),dict(operation='grade_record',user_id=uid,course_id=cid,score=93,reason='Verified demonstration grade')]:
   code,res,_=request('affairs/academic',body,cookie);print('write',code,res.get('academic',{}).get('summary',{}).get('gpa_4_demo'),res.get('error'))
  code,pr,_=request(f'affairs/student/profile?id={uid}',cookie=cookie)
  print('profile',code,pr['academic_plan']['summary']['graduation_assessment'])
  code,res,_=request('login',{'username':'student','password':'Demo123!'})
  studentcookie=_['Set-Cookie'].split(';')[0]
  code,res,_=request('affairs/academic',dict(operation='grade_record',user_id=uid,course_id=cid,score=100,reason='Not authorized'),studentcookie)
  print('unauthorized',code)
  con=sqlite3.connect(d+'/test.db');print('db tables',[x[0] for x in con.execute("select name from sqlite_master where type='table' and name in ('student_plan','course_grades')")]);con.close()
 finally:
  p.terminate();p.wait(timeout=3)
