"""Integration checks against a running local server. Seeded demo database can be reset afterward."""
import requests
from concurrent.futures import ThreadPoolExecutor
import os
BASE='http://127.0.0.1:'+os.environ.get('TEST_PORT','8765')+'/api/'

def login(username):
    s=requests.Session(); r=s.post(BASE+'login',json={'username':username,'password':'Demo123!'}); assert r.status_code==200,(username,r.text); return s

def j(s,method,path,body=None,status=200):
    r=s.request(method,BASE+path,json=body,timeout=20)
    assert r.status_code==status,(path,r.status_code,r.text)
    return r.json()

admin=login('admin');student=login('student');student2=login('student2');head=login('head');affairs=login('affairs');finance=login('finance')
assert j(student,'GET','bootstrap')['user']['role']=='student'
cat=j(student,'GET','catalog')['sections']
assert len(cat)>=20
cs102a=next(s for s in cat if s['code']=='CS102' and s['label']=='A')
assert cs102a['capacity']==1 and cs102a['enrolled']==1
assert j(student,'GET','me')['credits']==0
# Basket full + initial minimum checks
picks=[next(s['id'] for s in cat if s['code']==code and s['label']=='A') for code in ['PHY101','ENG101','ETH101']]
r=student.post(BASE+'register',json={'section_ids':picks,'request_key':'test-min-req-001'})
assert r.status_code==409 and r.json()['code']=='MIN_CREDITS',r.text
# 4 courses (12 credits) with nonconflicting days + timings, but one schedule conflict would reject
picks=[next(s['id'] for s in cat if s['code']==code and s['label']=='A') for code in ['CS102','PHY101','ENG101','ETH101']]
r=student.post(BASE+'register',json={'section_ids':picks,'request_key':'test-full-req-001'})
assert r.status_code==409 and r.json()['code']=='FULL',r.text
assert j(student,'GET','me')['credits']==0
# choose 4 nonconflicting, student passed CS101 so CS101 cannot register
picks=[next(s['id'] for s in cat if s['code']==code and s['label']=='A') for code in ['ENG101','PHY101','HUM101','ETH101']]
r=j(student,'POST','register',{'section_ids':picks,'request_key':'test-checkout-0001'});assert r['credits']==12
again=j(student,'POST','register',{'section_ids':picks,'request_key':'test-checkout-0001'});assert again['replayed']
assert j(student,'GET','me')['credits']==12
# Existing CS102 last seat is full: joining works, dropping student2 releases and promotes first waiting student
j(student,'POST','waitlist/join',{'section_id':cs102a['id']})
assert any(w['status']=='waiting' for w in j(student,'GET','me')['waitlist'])
en2=j(student2,'GET','me')['schedule'];eid=next(x['enrollment_id'] for x in en2 if x['code']=='CS102' and x['label']=='A')
r=j(student2,'POST','drop',{'enrollment_id':eid});assert r['promotion']['promoted'],r
assert any(x['code']=='CS102' for x in j(student,'GET','me')['schedule'])
# Finance pending with same key should not create duplicate
pp=j(student,'POST','payment/request',{'request_key':'idem-test-1000','outcome':'pending'})['payment']
pp2=j(student,'POST','payment/request',{'request_key':'idem-test-1000','outcome':'success'})['payment']
assert pp2['id']==pp['id'] and pp2['replayed']
j(finance,'POST','payment/reconcile',{'payment_id':pp['id'],'status':'confirmed'})
# department head raises capacity, record as audit
j(head,'POST','section/capacity',{'section_id':cs102a['id'],'capacity':3})
# Affairs grade appeal: remove prereq after enrollment (must not silently drop)
cs101=next(x for x in cat if x['code']=='CS101')
suid=j(admin,'GET','students')['students'][0]['id']
x=j(affairs,'POST','affairs/grade',{'user_id':suid,'course_id':cs101['course_id'],'passed':False})
assert any(x['code']=='CS102' for x in j(student,'GET','me')['schedule'])
assert x['review_enrollments']
# emergency stop, preserve read routes
j(admin,'POST','admin/settings',{'key':'registration_enabled','value':'false'})
assert j(student,'GET','catalog')['sections']
rr=student.post(BASE+'register',json={'section_ids':[cat[0]['id']],'request_key':'emergency-stop-123'})
assert rr.status_code==409 and rr.json()['code']=='READ_ONLY',rr.text
j(admin,'POST','admin/settings',{'key':'registration_enabled','value':'true'})
# sandbox 7
for case in range(1,8):
 r=j(student,'POST','lab/run',{'case':case});assert r['passed'],r
# roles
assert student.get(BASE+'students').status_code==403
assert finance.post(BASE+'section/capacity',json={'section_id':cs102a['id'],'capacity':4}).status_code==403
# reset
j(admin,'POST','admin/reset',{'confirmation':'RESET DEMO'})
assert login('student').get(BASE+'me').json()['credits']==0
print('PASS: login roles, catalog, minimum, atomic basket, idempotency, waitlist promotion, finance, head, grade appeal, pause, lab 7, role ACL, reset')
