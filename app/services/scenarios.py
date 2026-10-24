"""Isolated illustrative edge-case simulations; never mutate production records."""
import sqlite3
from app.domain.errors import AppError
from app.infrastructure.database import one

def sandbox(case):
    """Independent SQLite test scenarios: no live project records are mutated."""
    x=sqlite3.connect(':memory:',isolation_level=None)
    x.row_factory=sqlite3.Row
    lines=[]
    def log(ar,en): lines.append({'ar':ar,'en':en})
    if case==1:
        x.execute('CREATE TABLE seat(capacity INTEGER, allocated INTEGER CHECK(allocated<=capacity))')
        x.execute('INSERT INTO seat VALUES(1,0)')
        values=[]
        for label in ['A','B']:
            changed=x.execute('UPDATE seat SET allocated=allocated+1 WHERE allocated<capacity').rowcount
            values.append(changed)
            log(('الطالب '+label+': حُجز المقعد بنجاح' if changed else 'الطالب '+label+': تم الرفض، الشعبة ممتلئة'),('Student '+label+': seat confirmed' if changed else 'Student '+label+': rejected; full'))
        safe=(values==[1,0] and one(x,'SELECT allocated FROM seat')['allocated']==1)
    elif case==2:
        x.execute('CREATE TABLE payment(ref TEXT UNIQUE, request_key TEXT UNIQUE, status TEXT)')
        x.execute("INSERT INTO payment VALUES('PAY-101','same-request','pending')")
        log('تم خصم افتراضي دون وصول إشعار؛ الحالة قيد التحقق','Simulated debit without callback; payment pending verification')
        x.execute("INSERT OR IGNORE INTO payment VALUES('PAY-102','same-request','pending')")
        log('إعادة الطلب بالمفتاح نفسه لم تُنشئ دفعة ثانية','Retry with same key created no second charge record')
        x.execute("UPDATE payment SET status='confirmed' WHERE ref='PAY-101'")
        log('بعد المطابقة بالمرجع الأصلي أصبحت الدفعة مؤكدة','Reconciliation using original reference confirmed payment')
        safe=one(x,'SELECT COUNT(*) n FROM payment')['n']==1
    elif case==3:
        x.execute('CREATE TABLE grade(user_id INTEGER,prerequisite_passed INTEGER)')
        x.execute('INSERT INTO grade VALUES(1,1)')
        log('برمجة 2 متاحة لأن المتطلب السابق مستوفى','Programming II starts eligible')
        x.execute('UPDATE grade SET prerequisite_passed=0 WHERE user_id=1')
        log('تم تعديل العلامة من المصدر الأكاديمي: الأهلية أصبحت غير مستوفاة','Grade appeal changed official prerequisite to failed; now ineligible')
        log('التسجيل السابق يحتاج مراجعة سياسة ولا يُلغى تلقائيًا','Pre-existing enrollments require policy review; no automatic cancellation')
        safe=one(x,'SELECT prerequisite_passed FROM grade')['prerequisite_passed']==0
    elif case==4:
        x.execute('CREATE TABLE queue(rank INTEGER PRIMARY KEY,eligible INTEGER,connected INTEGER)')
        x.executemany('INSERT INTO queue VALUES(?,?,?)',[(1,0,0),(2,1,1)])
        log('تحرر مقعد الساعة 2 صباحًا؛ أول المنتظرين غير متصل','Seat freed at 2 a.m.; first person offline')
        chosen=None
        for w in x.execute('SELECT * FROM queue ORDER BY rank'):
            if not w['eligible']:
                log('تم تخطي الأول لوجود تعارض، لا لأنه غير متصل','First skipped due to schedule conflict, not because offline')
                continue
            chosen=w['rank']; log('حصل المرشح الثاني المؤهل على المقعد','Second eligible candidate was allocated the seat'); break
        safe=chosen==2
    elif case==5:
        x.execute('CREATE TABLE section(id INTEGER PRIMARY KEY,available INTEGER)')
        x.executemany('INSERT INTO section VALUES(?,?)',[(1,1),(2,1),(3,1),(4,1),(5,0)])
        x.execute('BEGIN')
        success=True
        for i in range(1,6):
            if x.execute('UPDATE section SET available=available-1 WHERE id=? AND available>0',(i,)).rowcount==0:
                success=False
                log('فشل المقرر الخامس: الشعبة ممتلئة','Fifth course failed: section full')
                break
        x.execute('ROLLBACK' if not success else 'COMMIT')
        log('تم التراجع عن السلة كاملة وفق سياسة الكل أو لا شيء التجريبية','Entire basket rolled back under the demo all-or-nothing policy')
        safe=one(x,'SELECT SUM(available) n FROM section')['n']==4
    elif case==6:
        available=9; minimum=12
        log('إجمالي الساعات المؤهلة: 9؛ الحد الأدنى: 12','Eligible credit total: 9; required minimum: 12')
        declined=available<minimum
        log('تم الرفض مع توضيح السبب وإمكانية طلب استثناء إداري','Rejected with explicit reason and administrative exception route')
        log('يمكن لشؤون الطلاب اعتماد استثناء موثق؛ النظام لا يمنحه تلقائيًا','Student affairs may approve a documented exception; never automatic')
        safe=declined
    elif case==7:
        x.execute('CREATE TABLE capacity(maximum INTEGER,allocated INTEGER)')
        x.execute('INSERT INTO capacity VALUES(40,40)')
        x.execute('CREATE TABLE queue(rank INTEGER PRIMARY KEY, status TEXT)')
        x.executemany("INSERT INTO queue VALUES(?,'waiting')",[(i,) for i in range(1,31)])
        x.execute('UPDATE capacity SET maximum=50')
        seats=10
        for row in x.execute("SELECT rank FROM queue WHERE status='waiting' ORDER BY rank LIMIT ?",(seats,)).fetchall():
            x.execute("UPDATE queue SET status='promoted' WHERE rank=?",(row['rank'],))
            x.execute('UPDATE capacity SET allocated=allocated+1')
        log('رئيس القسم رفع السعة المعتمدة من 40 إلى 50','Department head increased authorized capacity from 40 to 50')
        log('عُولجت قائمة من 30 منتظرًا حسب الأولوية: تمت ترقية أول 10','30-person waitlist processed in order: first 10 promoted')
        safe=one(x,"SELECT COUNT(*) n FROM queue WHERE status='waiting'")['n']==20 and one(x,'SELECT allocated FROM capacity')['allocated']==50
    else: raise AppError('Unknown scenario / سيناريو غير موجود',404)
    x.close()
    return {'case':case,'steps':lines,'passed':bool(safe),'isolated':True}

