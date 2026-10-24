"""Priority for graduating students, with bounded waiting for non-graduates.

Client requirements: needed-to-graduate course gets priority; a non-graduate
cannot be bypassed forever. The 24-hour protection is a DEMO choice, NOT
an approved university rule. Approval and policy review are required before
production deployment.
"""
from datetime import datetime, timezone, timedelta
from app.infrastructure.database import all_rows, one, setting


def _aware(value):
    try:
        date=datetime.fromisoformat(value)
        return date if date.tzinfo else date.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)


def is_needed_for_graduation(c, user_id, course_id):
    # Merely flagging a user as a graduate is insufficient: the specific
    # course must be required in their recorded plan and not yet passed.
    return bool(one(c, """SELECT 1 FROM users u
        JOIN student_plan p ON p.user_id=u.id AND p.course_id=? AND p.required=1
        LEFT JOIN completed co ON co.user_id=u.id AND co.course_id=p.course_id
        WHERE u.id=? AND u.graduate=1 AND COALESCE(co.passed,0)=0""",
        (course_id,user_id)))


def ordered_candidates(c,section_id,at=None):
    at=at or datetime.now(timezone.utc)
    hours=int(setting(c,'waitlist_protection_hours') or 24)
    items=all_rows(c, """SELECT w.*,s.course_id FROM waitlist w
        JOIN sections s ON s.id=w.section_id
        WHERE w.section_id=? AND w.status='waiting'
        ORDER BY w.joined_at,w.id""",(section_id,))
    for item in items:
        age=at-_aware(item['joined_at'])
        protected=age>=timedelta(hours=hours)
        graduate=is_needed_for_graduation(c,item['user_id'],item['course_id'])
        # Old requests are protected regardless of student category.
        item['priority_tier']=0 if protected else (1 if graduate else 2)
        item['priority_reason']=('AGE_PROTECTED' if protected else
                                 'NEEDED_FOR_GRADUATION' if graduate else 'FIFO')
    items.sort(key=lambda x:(x['priority_tier'],_aware(x['joined_at']),x['id']))
    return items
