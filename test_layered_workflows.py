"""Isolated regression checks for client change requests and layered persistence.
Run: python test_layered_workflows.py (never edits your production/demo database).
"""
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
from app.core import config
from app.core.clock import now
from app.infrastructure.database import connect, init_db, one, transaction
from app.services.swaps import request_swap, swap_overview
from app.services.waitlist_priority import ordered_candidates
from app.domain.errors import AppError


def student(c,name):
    return dict(one(c,'SELECT * FROM users WHERE username=?',(name,)))


def section(c,code,label):
    return one(c,'''SELECT s.id FROM sections s JOIN courses cr ON cr.id=s.course_id
       WHERE cr.code=? AND s.label=?''',(code,label))['id']


def new_env(dirpath):
    config.DB_PATH=dirpath/'test.sqlite3'
    init_db()
    return connect()


def test_atomic_swap(folder):
    c=new_env(folder)
    a,b=section(c,'CS102','A'),section(c,'CS102','B')
    u=student(c,'student');v=student(c,'student2')
    # v already enrolled in A at seed; place u in the other full section.
    with transaction(c):
        c.execute('UPDATE sections SET capacity=1 WHERE id IN (?,?)',(a,b))
        c.execute('INSERT INTO enrollments(user_id,section_id,created_at,origin) VALUES(?,?,?,?)',
                  (u['id'],b,now(),'test'))
    first=request_swap(c,v,a,b)
    assert first['status']=='pending',first
    second=request_swap(c,u,b,a)
    assert second['status']=='matched',second
    assert one(c,'SELECT section_id FROM enrollments WHERE user_id=?',(u['id'],))['section_id']==a
    assert one(c,'SELECT section_id FROM enrollments WHERE user_id=?',(v['id'],))['section_id']==b
    for sid in (a,b):
        assert one(c,'SELECT COUNT(*) n FROM enrollments WHERE section_id=?',(sid,))['n']==1
    assert all(x['status']=='matched' for x in swap_overview(c,u)['requests'])
    # The database trigger rejects an additional unguarded seat insertion.
    try:
        c.execute('INSERT INTO enrollments(user_id,section_id,created_at,origin) VALUES(?,?,?,?)',
                  (student(c,'honors')['id'],a,now(),'attack'))
        raise AssertionError('capacity trigger allowed an overbooking')
    except sqlite3.IntegrityError as exc:
        assert 'SECTION_FULL' in str(exc),str(exc)
    # No other student's name / username in the returned swap request.
    assert 'student2' not in str(second)
    c.close()
    print('PASS: atomic mutual swap, matching, capacity trigger, privacy')


def test_fifo(folder):
    c=new_env(folder)
    a,b=section(c,'CS102','A'),section(c,'CS102','B')
    v=student(c,'student2');graduate=student(c,'graduate');u=student(c,'student')
    with transaction(c):
        c.execute('UPDATE sections SET capacity=2 WHERE id=?',(a,))
        c.execute('UPDATE sections SET capacity=1 WHERE id=?',(b,))
        c.execute('INSERT INTO enrollments(user_id,section_id,created_at,origin) VALUES(?,?,?,?)',
                  (graduate['id'],a,now(),'test'))
        c.execute('INSERT INTO enrollments(user_id,section_id,created_at,origin) VALUES(?,?,?,?)',
                  (u['id'],b,now(),'test'))
    first=request_swap(c,v,a,b)
    second=request_swap(c,graduate,a,b)
    assert first['status']=='pending' and second['status']=='pending'
    matched=request_swap(c,u,b,a)
    assert matched['status']=='matched'
    assert one(c,'SELECT section_id FROM enrollments WHERE user_id=?',(v['id'],))['section_id']==b
    assert one(c,'SELECT section_id FROM enrollments WHERE user_id=?',(graduate['id'],))['section_id']==a
    assert one(c,'SELECT status FROM swap_requests WHERE id=?',(second['request_id'],))['status']=='pending'
    c.close()
    print('PASS: oldest reciprocal swap request wins; later request stays pending')


def test_graduate_fairness(folder):
    c=new_env(folder)
    a=section(c,'ETH101','A')
    graduate=student(c,'graduate');normal=student(c,'student');older=student(c,'student2')
    code_id=one(c,"SELECT id FROM courses WHERE code='ETH101'")['id']
    with transaction(c):
        c.execute('INSERT INTO student_plan(user_id,course_id,required,assigned_at) VALUES(?,?,1,?)',
                  (graduate['id'],code_id,now()))
        # Competing requests for the same section, all currently waiting.
        start=datetime.now(timezone.utc)
        for uid,joined in [
            (normal['id'],(start-timedelta(hours=1)).isoformat()),
            (graduate['id'],(start-timedelta(minutes=10)).isoformat())]:
            c.execute("INSERT INTO waitlist(user_id,section_id,status,joined_at,note) VALUES(?,?,'waiting',?,'')",
                      (uid,a,joined))
    items=ordered_candidates(c,a)
    assert [x['user_id'] for x in items][:2]==[graduate['id'],normal['id']]
    assert items[0]['priority_reason']=='NEEDED_FOR_GRADUATION'
    # Protect a student who has waited days, even if five graduates join later.
    with transaction(c):
        c.execute("INSERT INTO waitlist(user_id,section_id,status,joined_at,note) VALUES(?,?,'waiting',?,'')",
                  (older['id'],a,(datetime.now(timezone.utc)-timedelta(days=4)).isoformat()))
    items=ordered_candidates(c,a)
    assert items[0]['user_id']==older['id']
    assert items[0]['priority_reason']=='AGE_PROTECTED'
    c.close()
    print('PASS: graduating-needed course priority and 24h anti-starvation demo rule')


def test_migration_preserves_names(folder):
    c=new_env(folder)
    c.execute("UPDATE users SET name_ar='ربيع أحمد' WHERE username='student'")
    uid=student(c,'student')['id']
    c.execute('INSERT INTO student_plan(user_id,course_id,required,assigned_at) VALUES(?,?,1,?)',
              (uid,one(c,"SELECT id FROM courses WHERE code='CS101'")['id'],now()))
    c.close()
    init_db()  # second startup must be idempotent and preserve modifications
    c=connect()
    assert student(c,'student')['name_ar']=='ربيع أحمد'
    assert one(c,'SELECT COUNT(*) n FROM student_plan WHERE user_id=?',(uid,))['n']==1
    assert one(c,'SELECT COUNT(*) n FROM sqlite_master WHERE name="swap_requests"')['n']==1
    c.close()
    print('PASS: idempotent migrations preserve names and academic records')


if __name__=='__main__':
    with tempfile.TemporaryDirectory() as d:
        base=Path(d)
        for name,fn in [('swap',test_atomic_swap),('fifo',test_fifo),('priority',test_graduate_fairness),('migration',test_migration_preserves_names)]:
            p=base/name;p.mkdir()
            fn(p)
