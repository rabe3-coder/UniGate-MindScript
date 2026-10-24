"""Persist student cart selections across logins and devices. Draft does not reserve seats."""
from app.core.clock import now
from app.core.security import require
from app.domain.errors import AppError
from app.infrastructure.database import all_rows, one, transaction


def basket_sections(c,uid):
    return [r['section_id'] for r in all_rows(c,
        'SELECT section_id FROM student_basket WHERE user_id=? ORDER BY added_at,section_id',(uid,))]

def op_basket(c,user,payload,respond,headers,request_path,method,path):
    require(user,['student'])
    uid=user['id']
    if method=='GET':return respond({'section_ids':basket_sections(c,uid)})
    action=payload.get('action')
    if action not in ('add','remove','clear'):
        raise AppError('Invalid basket action / إجراء سلة غير صالح',400,'VALIDATION')
    with transaction(c):
        if action=='clear':
            c.execute('DELETE FROM student_basket WHERE user_id=?',(uid,))
        else:
            section_id=payload.get('section_id')
            if not isinstance(section_id,int) or isinstance(section_id,bool) or section_id<1:
                raise AppError('Invalid section / شعبة غير صالحة',400,'VALIDATION')
            if action=='add':
                section=one(c,'SELECT course_id FROM sections WHERE id=?',(section_id,))
                if not section:
                    raise AppError('Section not found / الشعبة غير موجودة',404,'NOT_FOUND')
                duplicate=one(c,"""SELECT 1 FROM student_basket b JOIN sections s ON s.id=b.section_id
                    WHERE b.user_id=? AND s.course_id=?""",(uid,section['course_id']))
                if duplicate:
                    raise AppError('Choose one section per course / اختر شعبة واحدة للمقرر',409,'DUPLICATE_COURSE')
                existing=one(c,"""SELECT 1 FROM enrollments e JOIN sections s ON s.id=e.section_id
                    WHERE e.user_id=? AND s.course_id=?""",(uid,section['course_id']))
                if existing:
                    raise AppError('Course already enrolled / المقرر مسجل مسبقاً',409,'DUPLICATE_COURSE')
                c.execute('INSERT OR IGNORE INTO student_basket(user_id,section_id,added_at) VALUES(?,?,?)',(uid,section_id,now()))
            else:
                c.execute('DELETE FROM student_basket WHERE user_id=? AND section_id=?',(uid,section_id))
    return respond({'section_ids':basket_sections(c,uid)})
