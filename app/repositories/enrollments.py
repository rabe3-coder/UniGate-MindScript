"""Persistence queries for confirmed registrations and section inventory.

No HTTP, presentation or policy decisions belong in this module. The caller
controls SQLite transactions; this repository never commits on its own.
"""
from app.infrastructure.database import one, all_rows


def schedule_for_student(c, user_id):
    return all_rows(c, '''SELECT e.id AS enrollment_id,s.id AS section_id,s.label,
        s.weekday,s.start_time,s.end_time,c.id AS course_id,c.code,c.name_ar,
        c.name_en,c.credits,e.created_at
        FROM enrollments e JOIN sections s ON s.id=e.section_id
        JOIN courses c ON c.id=s.course_id WHERE e.user_id=?
        ORDER BY s.weekday,s.start_time''',(user_id,))


def occupied_seats(c, section_id):
    row=one(c,'SELECT COUNT(*) AS n FROM enrollments WHERE section_id=?',(section_id,))
    return row['n'] if row else 0


def section_with_course(c, section_id):
    return one(c,'''SELECT s.*,c.code,c.credits,c.name_ar,c.name_en
        FROM sections s JOIN courses c ON c.id=s.course_id WHERE s.id=?''',
        (section_id,))


def section_by_id(c, section_id):
    return one(c,'SELECT * FROM sections WHERE id=?',(section_id,))


def enrollment_by_student_and_section(c, user_id, section_id):
    return one(c,'SELECT * FROM enrollments WHERE user_id=? AND section_id=?',
               (user_id,section_id))
