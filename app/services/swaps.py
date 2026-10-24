"""Atomic section swaps for the same course.

One transaction deletes both old enrollments and recreates the two opposite
assignments. Intermediate states are invisible outside the transaction; any
failure rolls both students back. Old enrollment IDs and creation timestamps
are preserved, while audit records the operation. First-in-first-out matching
of reciprocal pending requests is deterministic.
"""
from __future__ import annotations
from app.core.clock import now
from app.core.security import require
from app.domain.errors import AppError
from app.domain.rules import conflicts
from app.infrastructure.database import one, all_rows, audit, transaction
from app.services.registration import permitted, registered
from app.repositories.enrollments import enrollment_by_student_and_section, section_by_id


def _sections(c,from_id,to_id):
    source=section_by_id(c,from_id)
    target=section_by_id(c,to_id)
    if not source or not target or from_id==to_id:
        raise AppError('Invalid section swap / طلب تبديل غير صالح',400,'INVALID_SWAP')
    if source['course_id']!=target['course_id']:
        raise AppError('Swaps must stay within the same course / التبديل ضمن المقرر نفسه',409,'SWAP_COURSE')
    return source,target


def _validate(c,user,from_id,to_id):
    permitted(c,user)
    source,target=_sections(c,from_id,to_id)
    enrolled=enrollment_by_student_and_section(c,user['id'],from_id)
    if not enrolled:raise AppError('Original enrollment is no longer active / التسجيل الأصلي غير قائم',409,'SWAP_NOT_ENROLLED')
    for scheduled in registered(c,user['id']):
        if scheduled['section_id']!=from_id and conflicts(target,scheduled):
            raise AppError('Target section conflicts with timetable / الشعبة المطلوبة تتعارض مع الجدول',409,'SWAP_CONFLICT')
    return enrolled


def swap_overview(c,user):
    require(user,['student'])
    schedule=registered(c,user['id'])
    destinations=[]
    for enrolled in schedule:
        others=all_rows(c,'''SELECT id,label,weekday,start_time,end_time,capacity,
            (SELECT COUNT(*) FROM enrollments e WHERE e.section_id=s.id) AS enrolled
            FROM sections s WHERE s.course_id=? AND s.id<>? ORDER BY s.label''',
            (enrolled['course_id'],enrolled['section_id']))
        destinations.append({'source':enrolled,'targets':others})
    requests=all_rows(c,'''SELECT r.id,r.from_section_id,r.to_section_id,r.status,r.created_at,r.processed_at,
        r.explanation,source.label AS source_label,target.label AS target_label,co.code
        FROM swap_requests r JOIN sections source ON source.id=r.from_section_id
        JOIN sections target ON target.id=r.to_section_id
        JOIN courses co ON co.id=source.course_id
        WHERE r.user_id=? ORDER BY r.id DESC LIMIT 30''',(user['id'],))
    return {'options':destinations,'requests':requests,'policy':'FIFO, atomic, identity-private'}


def request_swap(c,user,from_id,to_id):
    require(user,['student'])
    if type(from_id) is not int or type(to_id) is not int:
        raise AppError('Section identifiers must be integers',400)
    with transaction(c):
        _validate(c,user,from_id,to_id)
        if one(c,"SELECT id FROM swap_requests WHERE user_id=? AND status='pending'",(user['id'],)):
            raise AppError('Cancel your previous pending swap first / ألغِ طلب التبديل السابق أولًا',409,'SWAP_ALREADY_PENDING')
        cur=c.execute('''INSERT INTO swap_requests(user_id,from_section_id,to_section_id,status,created_at)
            VALUES(?,?,?,'pending',?)''',(user['id'],from_id,to_id,now()))
        own_id=cur.lastrowid
        audit(c,user['id'],'SWAP_REQUESTED','swap',{'request_id':own_id,'from':from_id,'to':to_id})
        # Always choose earliest eligible reciprocal request. No student identities
        # are exposed to the other participant in the response.
        waiting=all_rows(c,'''SELECT id,user_id FROM swap_requests
            WHERE status='pending' AND from_section_id=? AND to_section_id=? AND user_id<>?
            ORDER BY created_at,id''',(to_id,from_id,user['id']))
        for pending in waiting:
            other=one(c,'SELECT * FROM users WHERE id=?',(pending['user_id'],))
            if not other or other['role']!='student':continue
            try:
                previous=_validate(c,dict(other),to_id,from_id)
            except AppError as err:
                c.execute("UPDATE swap_requests SET status='invalid',processed_at=?,explanation=? WHERE id=?",
                          (now(),err.code,pending['id']))
                audit(c,None,'SWAP_INVALIDATED','swap',{'request_id':pending['id'],'reason':err.code})
                continue
            mine=_validate(c,user,from_id,to_id)
            # Atomic delete/reinsert is used because an UPDATE would temporarily
            # exceed a FULL target section and trip the DB capacity trigger.
            c.execute('DELETE FROM enrollments WHERE id IN (?,?)',(mine['id'],previous['id']))
            for enrollment,target in ((mine,to_id),(previous,from_id)):
                c.execute('''INSERT INTO enrollments(id,user_id,section_id,created_at,origin)
                    VALUES(?,?,?,?,?)''',(enrollment['id'],enrollment['user_id'],target,enrollment['created_at'],'swap'))
            stamp=now()
            c.execute('''UPDATE swap_requests SET status='matched',processed_at=?,matched_request_id=?
                WHERE id=?''',(stamp,pending['id'],own_id))
            c.execute('''UPDATE swap_requests SET status='matched',processed_at=?,matched_request_id=?
                WHERE id=?''',(stamp,own_id,pending['id']))
            audit(c,None,'SWAP_EXECUTED','swap',{'request_ids':[pending['id'],own_id],
                         'from_section_id':from_id,'to_section_id':to_id,'atomic':True})
            return {'success':True,'request_id':own_id,'status':'matched','message':'Atomic swap completed'}
        return {'success':True,'request_id':own_id,'status':'pending',
                'message':'Waiting for a compatible reciprocal request'}


def cancel_swap(c,user,request_id):
    require(user,['student'])
    if type(request_id) is not int:raise AppError('Invalid request ID')
    with transaction(c):
        changed=c.execute("""UPDATE swap_requests SET status='cancelled',processed_at=?,explanation='Cancelled by requester'
            WHERE id=? AND user_id=? AND status='pending'""",(now(),request_id,user['id']))
        if changed.rowcount!=1:raise AppError('Pending swap request not found',404,'SWAP_NOT_FOUND')
        audit(c,user['id'],'SWAP_CANCELLED','swap',{'request_id':request_id})
    return {'success':True}


def invalidate_after_drop(c,user_id,section_id):
    c.execute('''UPDATE swap_requests SET status='invalid',processed_at=?,explanation='Original enrollment dropped'
        WHERE user_id=? AND from_section_id=? AND status='pending' ''',(now(),user_id,section_id))
