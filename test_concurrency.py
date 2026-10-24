"""Seat integrity test using two independent SQLite connections and simultaneous commits."""
import sys,tempfile,threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).parent))
import server
with tempfile.TemporaryDirectory() as dirname:
    path=Path(dirname)/'race.sqlite3'
    server.DB_PATH=path
    server.init_db()
    c=server.connect()
    section=server.one(c,"SELECT s.id FROM sections s JOIN courses c ON s.course_id=c.id WHERE c.code='CS102' AND s.label='A'")['id']
    c.execute('DELETE FROM enrollments WHERE section_id=?',(section,))
    opts=['CS102','ENG101','PHY101','ETH101']
    ids=[server.one(c,'SELECT s.id FROM sections s JOIN courses c ON s.course_id=c.id WHERE c.code=? AND s.label=\'A\'',(code,))['id'] for code in opts]
    c.close()
    barrier=threading.Barrier(2)
    def take(username):
        cx=server.connect()
        u=dict(server.one(cx,'SELECT * FROM users WHERE username=?',(username,)))
        barrier.wait()
        try: return 'ok',server.enroll_basket(cx,u,ids,'race-key-'+username)
        except server.AppError as e:return 'failed',e.code
        finally:cx.close()
    with ThreadPoolExecutor(max_workers=2) as executor:
        a=executor.submit(take,'student');b=executor.submit(take,'student2')
        results=[a.result(),b.result()]
    assert sorted(x[0] for x in results)==['failed','ok'],results
    assert any(x[1]=='FULL' for x in results if x[0]=='failed'),results
    c=server.connect()
    assert server.one(c,'SELECT COUNT(*) n FROM enrollments WHERE section_id=?',(section,))['n']==1
    assert server.one(c,'SELECT COUNT(*) n FROM enrollments')['n']==4
    c.close()
print('PASS: two simultaneous independent SQLite writers; exactly one 12-credit basket committed; no overbooking or partial basket')
