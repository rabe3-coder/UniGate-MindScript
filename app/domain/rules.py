"""Pure academic and scheduling rules, isolated from storage and HTTP."""

def conflicts(a,b):
    return a['weekday']==b['weekday'] and a['start_time']<b['end_time'] and b['start_time']<a['end_time']

def grade_points(score: float) -> float:
    """Demo GPA bands only; NOT an official university grading policy."""
    return 4.0 if score>=90 else 3.0 if score>=80 else 2.0 if score>=70 else 1.0 if score>=60 else 0.0
