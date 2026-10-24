"""SQLite adapter: connections, version-safe additive schema upgrades, seed data."""
import json
import sqlite3
import threading
import os
from contextlib import contextmanager
from app.core import config
from app.core.clock import now
from app.core.crypto import password_hash

def connect(path=None):
    c = sqlite3.connect(str(path or config.DB_PATH), timeout=20, isolation_level=None, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    c.execute('PRAGMA busy_timeout=20000')
    # PythonAnywhere's shared/network storage is not suitable for SQLite WAL.
    # Default WAL remains unchanged for local Windows installs.
    if path is None:
        mode = os.environ.get('UNIGATE_SQLITE_JOURNAL', 'WAL').upper()
        if mode not in ('WAL', 'DELETE'):
            raise ValueError('UNIGATE_SQLITE_JOURNAL must be WAL or DELETE')
        c.execute(f'PRAGMA journal_mode={mode}')
    return c

@contextmanager
def transaction(c):
    c.execute('BEGIN IMMEDIATE')
    try:
        yield
        c.execute('COMMIT')
    except BaseException:
        c.execute('ROLLBACK')
        raise

def one(c, sql, params=()):
    return c.execute(sql, params).fetchone()

def all_rows(c, sql, params=()):
    return [dict(r) for r in c.execute(sql, params).fetchall()]

def audit(c, actor, action, entity, detail):
    c.execute('INSERT INTO audit(actor_id,action,entity,details,created_at) VALUES(?,?,?,?,?)',
              (actor, action, entity, json.dumps(detail, ensure_ascii=False), now()))

def setting(c, name):
    r = one(c, 'SELECT value FROM settings WHERE key=?', (name,))
    return r['value'] if r else None

def init_db():
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = connect()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, name_ar TEXT NOT NULL, name_en TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('student','affairs','head','finance','admin')), password_hash TEXT NOT NULL,
        graduate INTEGER DEFAULT 0, honors INTEGER DEFAULT 0, hold INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS courses(id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, name_ar TEXT NOT NULL, name_en TEXT NOT NULL,
        credits INTEGER NOT NULL CHECK(credits BETWEEN 1 AND 6), prerequisite_id INTEGER REFERENCES courses(id));
    CREATE TABLE IF NOT EXISTS sections(id INTEGER PRIMARY KEY, course_id INTEGER NOT NULL REFERENCES courses(id), label TEXT NOT NULL,
        capacity INTEGER NOT NULL CHECK(capacity>0), weekday INTEGER NOT NULL CHECK(weekday BETWEEN 0 AND 6),
        start_time INTEGER NOT NULL, end_time INTEGER NOT NULL, instructor TEXT NOT NULL, UNIQUE(course_id,label),
        CHECK(start_time < end_time));
    CREATE TABLE IF NOT EXISTS completed(user_id INTEGER REFERENCES users(id), course_id INTEGER REFERENCES courses(id), passed INTEGER NOT NULL,
        PRIMARY KEY(user_id,course_id));
    CREATE TABLE IF NOT EXISTS enrollments(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), section_id INTEGER NOT NULL REFERENCES sections(id),
        created_at TEXT NOT NULL, origin TEXT NOT NULL DEFAULT 'student', UNIQUE(user_id, section_id));
    CREATE TABLE IF NOT EXISTS waitlist(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), section_id INTEGER NOT NULL REFERENCES sections(id),
        status TEXT NOT NULL DEFAULT 'waiting', joined_at TEXT NOT NULL, note TEXT NOT NULL DEFAULT '', UNIQUE(user_id,section_id));
    CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), request_key TEXT NOT NULL,
        reference TEXT UNIQUE NOT NULL, status TEXT NOT NULL, gateway_status TEXT NOT NULL, created_at TEXT NOT NULL,
        UNIQUE(user_id,request_key));
    CREATE TABLE IF NOT EXISTS registration_requests(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), request_key TEXT NOT NULL,
        status TEXT NOT NULL, response_json TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(user_id,request_key));
    CREATE TABLE IF NOT EXISTS exceptions(user_id INTEGER PRIMARY KEY REFERENCES users(id), min_override INTEGER NOT NULL, reason TEXT NOT NULL, approved_by INTEGER REFERENCES users(id));
    CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, actor_id INTEGER REFERENCES users(id), action TEXT NOT NULL, entity TEXT NOT NULL, details TEXT NOT NULL, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS idx_enroll_sec ON enrollments(section_id);
    CREATE INDEX IF NOT EXISTS idx_waitlist_sec ON waitlist(section_id,status,joined_at,id);
    CREATE INDEX IF NOT EXISTS idx_pay_user ON payments(user_id,status);
    ''')
    # Backward-compatible migration: preserve existing students and enrollments.
    existing_columns = {row['name'] for row in c.execute('PRAGMA table_info(users)')}
    for column in ('student_number', 'phone', 'email'):
        if column not in existing_columns:
            c.execute(f'ALTER TABLE users ADD COLUMN {column} TEXT NOT NULL DEFAULT \'\'')
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_student_number ON users(student_number) WHERE student_number <> ''")
    # Staff accounts must be provisioned locally. Historical demo admin/staff
    # credentials are deactivated exactly once, preserving all user IDs/history.
    cols = {row['name'] for row in c.execute('PRAGMA table_info(users)')}
    if 'is_active' not in cols:
        c.execute('ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1))')
    if 'staff_slot' not in cols:
        c.execute('ALTER TABLE users ADD COLUMN staff_slot TEXT')
    c.execute('CREATE UNIQUE INDEX IF NOT EXISTS uq_users_staff_slot ON users(staff_slot) WHERE staff_slot IS NOT NULL')
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_users_username_ci ON users(username COLLATE NOCASE)")
    c.execute("""CREATE TABLE IF NOT EXISTS student_basket(
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      section_id INTEGER NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
      added_at TEXT NOT NULL,
      PRIMARY KEY(user_id, section_id))""")
    # Only sandbox tests can retain the historic publicly known test credentials.
    is_test = os.environ.get('MINDSCRIPT_TEST_DEMO') == '1'
    if not one(c,"SELECT 1 FROM settings WHERE key='staff_provisioning_migration_v1'"):
        if not is_test:
            c.execute("UPDATE users SET is_active=0 WHERE role<>'student'")
            c.execute("DELETE FROM sessions WHERE user_id IN (SELECT id FROM users WHERE role!='student')")
        c.execute("INSERT INTO settings(key,value) VALUES('staff_provisioning_migration_v1','done')")

    # Additive academic migration; leave existing courses, registrations and completion flags intact.
    c.executescript("""
    CREATE TABLE IF NOT EXISTS student_plan (
      user_id INTEGER NOT NULL REFERENCES users(id), course_id INTEGER NOT NULL REFERENCES courses(id),
      required INTEGER NOT NULL DEFAULT 1 CHECK(required IN (0,1)),
      assigned_at TEXT NOT NULL, PRIMARY KEY(user_id,course_id));
    CREATE TABLE IF NOT EXISTS course_grades (
      user_id INTEGER NOT NULL REFERENCES users(id), course_id INTEGER NOT NULL REFERENCES courses(id),
      score REAL NOT NULL CHECK(score>=0 AND score<=100),
      updated_at TEXT NOT NULL, updated_by INTEGER REFERENCES users(id),
      PRIMARY KEY(user_id,course_id));
    """)
    # Client change: student-to-student atomic section swaps, one open request per student.
    c.executescript("""
    CREATE TABLE IF NOT EXISTS swap_requests(
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id),
        from_section_id INTEGER NOT NULL REFERENCES sections(id),
        to_section_id INTEGER NOT NULL REFERENCES sections(id),
        status TEXT NOT NULL DEFAULT 'pending'
            CHECK(status IN ('pending','matched','cancelled','invalid')),
        created_at TEXT NOT NULL,
        matched_request_id INTEGER REFERENCES swap_requests(id),
        processed_at TEXT,
        explanation TEXT NOT NULL DEFAULT '',
        CHECK(from_section_id <> to_section_id));
    CREATE UNIQUE INDEX IF NOT EXISTS uq_active_swap_user
        ON swap_requests(user_id) WHERE status='pending';
    CREATE INDEX IF NOT EXISTS idx_swap_match
        ON swap_requests(from_section_id,to_section_id,status,created_at,id);
    """)
    # Database-level defense in depth; direct SQL cannot exceed section capacity.
    c.executescript("""
    CREATE TRIGGER IF NOT EXISTS trg_enrollment_capacity_insert
    BEFORE INSERT ON enrollments
    WHEN (SELECT COUNT(*) FROM enrollments WHERE section_id=NEW.section_id) >=
         (SELECT capacity FROM sections WHERE id=NEW.section_id)
    BEGIN SELECT RAISE(ABORT,'SECTION_FULL'); END;
    CREATE TRIGGER IF NOT EXISTS trg_enrollment_course_insert
    BEFORE INSERT ON enrollments
    WHEN EXISTS(
      SELECT 1 FROM enrollments e JOIN sections old ON old.id=e.section_id
      JOIN sections incoming ON incoming.id=NEW.section_id
      WHERE e.user_id=NEW.user_id AND old.course_id=incoming.course_id)
    BEGIN SELECT RAISE(ABORT,'DUPLICATE_COURSE'); END;
    CREATE TRIGGER IF NOT EXISTS trg_enrollment_capacity_update
    BEFORE UPDATE OF section_id ON enrollments
    WHEN NEW.section_id<>OLD.section_id AND
         (SELECT COUNT(*) FROM enrollments WHERE section_id=NEW.section_id) >=
         (SELECT capacity FROM sections WHERE id=NEW.section_id)
    BEGIN SELECT RAISE(ABORT,'SECTION_FULL'); END;
    CREATE TRIGGER IF NOT EXISTS trg_enrollment_course_update
    BEFORE UPDATE OF section_id ON enrollments
    WHEN NEW.section_id<>OLD.section_id AND EXISTS(
      SELECT 1 FROM enrollments e JOIN sections old ON old.id=e.section_id
      JOIN sections incoming ON incoming.id=NEW.section_id
      WHERE e.user_id=NEW.user_id AND e.id<>OLD.id
        AND old.course_id=incoming.course_id)
    BEGIN SELECT RAISE(ABORT,'DUPLICATE_COURSE'); END;
    """)
    # This anti-starvation period is an explicitly documented DEMO policy.
    c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('waitlist_protection_hours','24')")
    # Demonstration-only grading rules; NOT the university's official GPA policy.
    c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('academic_pass_score','60')")
    c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('academic_gpa_policy','DEMO_BANDS_4')")
    if one(c,'SELECT COUNT(*) AS n FROM courses')['n']==0:
        seed(c)
    elif os.environ.get('MINDSCRIPT_TEST_DEMO') == '1' and one(c,'SELECT COUNT(*) AS n FROM users')['n']==0:
        seed_test_accounts(c)
    c.close()

def seed_test_accounts(c):
    """ONLY for isolated automated tests. Never enable for a real deployment."""
    accounts = [
        ('student','لين الحسن','Leen Al Hassan','student',0,0),
        ('student2','عمر الخطيب','Omar Al Khatib','student',0,0),
        ('graduate','سارة محمود','Sara Mahmoud','student',1,0),
        ('honors','يوسف منصور','Yousef Mansour','student',0,1),
        ('student9','نور أحمد','Noor Ahmad','student',0,0),
        ('affairs','موظف شؤون الطلاب','Student Affairs Officer','affairs',0,0),
        ('head','رئيس القسم','Department Head','head',0,0),
        ('finance','مسؤول المالية','Finance Officer','finance',0,0),
        ('admin','مدير النظام','System Administrator','admin',0,0),
    ]
    p = password_hash(config.DEMO_PASSWORD)
    c.executemany('INSERT INTO users(username,name_ar,name_en,role,graduate,honors,password_hash,is_active) VALUES(?,?,?,?,?,?,?,1)',
                  [(u,ar,en,role,g,h,p) for u,ar,en,role,g,h in accounts])


def seed(c):
    """Seed demo course catalog; user accounts are NEVER publicly seeded."""
    is_test = os.environ.get('MINDSCRIPT_TEST_DEMO') == '1'
    if is_test:
        seed_test_accounts(c)
    rows = [
        ('CS101','مدخل إلى البرمجة','Introduction to Programming',3,None),
        ('MATH101','رياضيات 1','Mathematics I',3,None),
        ('ENG101','اللغة الإنجليزية','English Language',3,None),
        ('PHY101','فيزياء عامة','General Physics',3,None),
        ('HUM101','مهارات التواصل','Communication Skills',3,None),
        ('CS102','برمجة 2','Programming II',3,'CS101'),
        ('CS103','هياكل البيانات','Data Structures',3,'CS102'),
        ('CS210','قواعد البيانات','Databases',3,'CS102'),
        ('CS220','هندسة البرمجيات','Software Engineering',3,'CS102'),
        ('MATH102','رياضيات 2','Mathematics II',3,'MATH101'),
        ('STAT201','الاحتمالات والإحصاء','Probability and Statistics',3,'MATH101'),
        ('NET201','شبكات الحاسوب','Computer Networks',3,'CS101'),
        ('CS230','نظم التشغيل','Operating Systems',3,'CS103'),
        ('AI301','مقدمة في الذكاء الاصطناعي','Introduction to AI',3,'CS103'),
        ('ETH101','أخلاقيات التقنية','Technology Ethics',3,None),
        ('DES101','التفكير التصميمي','Design Thinking',3,None),
        ('CS310','النظم الموزعة','Distributed Systems',3,'NET201'),
        ('PRJ401','مشروع التخرج','Graduation Project',3,'CS220')
    ]
    for code,ar,en,cr,pre in rows:
        pre_id=one(c,'SELECT id FROM courses WHERE code=?',(pre,))['id'] if pre else None
        c.execute('INSERT INTO courses(code,name_ar,name_en,credits,prerequisite_id) VALUES(?,?,?,?,?)',(code,ar,en,cr,pre_id))
    course_sections = [
        ('CS101','A',42,0,9,11),('CS101','B',40,2,11,13),
        ('MATH101','A',40,1,9,11),('MATH101','B',40,3,9,11),
        ('ENG101','A',40,2,9,11),('PHY101','A',40,3,11,13),
        ('HUM101','A',40,0,11,13),('CS102','A',1,1,11,13),('CS102','B',40,4,9,11),
        ('CS103','A',40,0,9,11),('CS210','A',40,2,11,13),('CS220','A',40,3,9,11),
        ('MATH102','A',40,0,9,11),('STAT201','A',40,2,9,11),
        ('NET201','A',40,1,9,11),('CS230','A',40,4,11,13),('AI301','A',40,4,9,11),
        ('ETH101','A',40,1,13,15),('DES101','A',40,3,13,15),
        ('CS310','A',40,2,13,15),('PRJ401','A',40,0,13,15),
    ]
    for code,label,cap,day,start,end in course_sections:
        cid=one(c,'SELECT id FROM courses WHERE code=?',(code,))['id']
        c.execute('INSERT INTO sections(course_id,label,capacity,weekday,start_time,end_time,instructor) VALUES(?,?,?,?,?,?,?)',
                  (cid,label,cap,day,start,end,'Demo Faculty'))
    prereqs={'student':['CS101','MATH101'],'student2':['CS101','MATH101'],
             'graduate':['CS101','CS102','CS103','MATH101','NET201'],
             'honors':['CS101','CS102','MATH101'],
             'student9':['CS101','MATH101','ENG101','PHY101','HUM101','CS102','CS103','CS210','CS220','MATH102','STAT201','NET201','CS230','AI301','ETH101','DES101','CS310','PRJ401']}
    # The 'student9' account is a regular sandbox student; nine-credit insufficiency is demonstrated in the scenario lab.
    for username,passed in (prereqs.items() if is_test else []):
        uid=one(c,'SELECT id FROM users WHERE username=?',(username,))['id']
        for code in passed:
            cid=one(c,'SELECT id FROM courses WHERE code=?',(code,))['id']
            c.execute('INSERT INTO completed(user_id,course_id,passed) VALUES(?,?,1)',(uid,cid))
    for username in (['student','student2','graduate','honors','student9'] if is_test else []):
        uid=one(c,'SELECT id FROM users WHERE username=?',(username,))['id']
        c.execute('INSERT INTO payments(user_id,request_key,reference,status,gateway_status,created_at) VALUES(?,?,?,?,?,?)',
                  (uid,'seed-prepay','DEMO-'+username,'confirmed','success',now()))
    if is_test:
        uid=one(c,"SELECT id FROM users WHERE username='student2'")['id']
        sid=one(c,"SELECT s.id FROM sections s JOIN courses c ON c.id=s.course_id WHERE c.code='CS102' AND s.label='A'")['id']
        c.execute('INSERT INTO enrollments(user_id,section_id,created_at,origin) VALUES(?,?,?,?)',(uid,sid,now(),'seed'))
    for key,value in [('phase','regular'),('registration_enabled','true'),('min_credits','12'),('max_credits','18'),('honors_max','21'),('waitlist_policy','automatic_demo')]:
        c.execute('INSERT INTO settings(key,value) VALUES(?,?)',(key,value))
    audit(c,None,'SEED','demo',{'note':'Seeded sample course inventory only; client revised target is 250 courses and 2500 sections.'})


RESET_LOCK = threading.RLock()
