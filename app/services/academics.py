"""Academic transcripts, plan progress and nonofficial GPA reporting."""
from app.domain.errors import AppError
from app.domain.rules import grade_points
from app.infrastructure.database import one, all_rows, setting

def academic_report(c, uid):
    """Graded-only GPA, per-student explicit plan, honest handling of unknown legacy grades."""
    if not one(c,"SELECT 1 FROM users WHERE id=? AND role='student'",(uid,)):
        raise AppError('Student not found / الطالب غير موجود',404)
    passing=float(setting(c,'academic_pass_score') or '60')
    rows=all_rows(c,"""SELECT p.course_id,p.required,c.code,c.name_ar,c.name_en,c.credits,
           g.score,co.passed AS legacy_passed,
           (SELECT COUNT(*) FROM sections s WHERE s.course_id=c.id) AS offered
           FROM student_plan p JOIN courses c ON c.id=p.course_id
           LEFT JOIN course_grades g ON g.user_id=p.user_id AND g.course_id=p.course_id
           LEFT JOIN completed co ON co.user_id=p.user_id AND co.course_id=p.course_id
           WHERE p.user_id=? ORDER BY c.code""",(uid,))
    grades=all_rows(c,"""SELECT c.code,c.name_ar,c.name_en,c.credits,g.score,g.updated_at
        FROM course_grades g JOIN courses c ON c.id=g.course_id
        WHERE g.user_id=? ORDER BY c.code""",(uid,))
    for x in grades:
        x['passed']=x['score']>=passing
        x['grade_points']=grade_points(x['score'])
    total_weight=sum(x['credits'] for x in grades)
    gpa=round(sum(x['credits']*x['grade_points'] for x in grades)/total_weight,2) if total_weight else None
    required=[x for x in rows if x['required']]
    earned=sum(x['credits'] for x in required if x['score'] is not None and x['score']>=passing)
    legacy_unknown=[x['code'] for x in rows if x['score'] is None and x['legacy_passed']==1]
    remaining=[x for x in required if x['score'] is None or x['score']<passing]
    remaining_credits=sum(x['credits'] for x in remaining)
    maximum=int(setting(c,'max_credits') or 18)
    # The project does not have a full degree-rule engine or validated transcript.
    status=('plan_missing' if not rows or not required else
            'requires_grade_verification' if legacy_unknown else
            'all_plan_courses_passed' if not remaining else
            'potential_this_term' if all(x['offered'] for x in remaining) and remaining_credits<=maximum else
            'not_currently_eligible')
    return {'plan':rows,'grades':grades,'summary':{
      'pass_score_demo':passing,'gpa_4_demo':gpa,'graded_credit_hours':total_weight,
      'required_credits':sum(x['credits'] for x in required),'earned_required_credits':earned,
      'remaining_required_credits':remaining_credits,'remaining_courses':[x['code'] for x in remaining],
      'unknown_legacy_grades':legacy_unknown,'graduation_assessment':status,
      'official_graduation_approved':False,
      'policy_note':'Demonstration only: passing score=60, GPA bands 90/80/70/60 => 4/3/2/1; not an approved university scale. All academic records need external verification.'}}

