"""Declarative HTTP route map: method + path to a single application use case."""
from app.application import academics, admin, auth, basket, enrollment, labs, payments, queries, sections, students, swaps

ROUTES = {
    ('GET','/api/affairs/academic'): academics.op_affairs_academic,
    ('POST','/api/affairs/academic'): academics.op_affairs_academic,
    ('POST','/api/affairs/grade'): academics.op_affairs_grade,
    ('POST','/api/affairs/hold'): academics.op_affairs_hold,
    ('POST','/api/affairs/exception'): academics.op_affairs_exception,
    ('POST','/api/admin/settings'): admin.op_admin_settings,
    ('POST','/api/admin/reset'): admin.op_admin_reset,
    ('POST','/api/login'): auth.op_login,
    ('POST','/api/signup'): auth.op_signup,
    ('GET','/api/basket'): basket.op_basket,
    ('POST','/api/basket'): basket.op_basket,
    ('POST','/api/logout'): auth.op_logout,
    ('POST','/api/register'): enrollment.op_register,
    ('POST','/api/drop'): enrollment.op_drop,
    ('POST','/api/waitlist/join'): enrollment.op_waitlist_join,
    ('POST','/api/waitlist/leave'): enrollment.op_waitlist_leave,
    ('POST','/api/lab/run'): labs.op_lab_run,
    ('POST','/api/payment/request'): payments.op_payment_request,
    ('POST','/api/payment/reconcile'): payments.op_payment_reconcile,
    ('GET','/api/bootstrap'): queries.op_bootstrap,
    ('GET','/api/catalog'): queries.op_catalog,
    ('GET','/api/me'): queries.op_me,
    ('GET','/api/activity'): queries.op_activity,
    ('GET','/api/students'): queries.op_students,
    ('GET','/api/payments'): queries.op_payments,
    ('GET','/api/waitlist'): queries.op_waitlist,
    ('POST','/api/section/capacity'): sections.op_section_capacity,
    ('POST','/api/section/create'): sections.op_section_create,
    ('POST','/api/affairs/student/create'): students.op_affairs_student_create,
    ('GET','/api/affairs/student/profile'): students.op_affairs_student_profile,
    ('POST','/api/affairs/student/profile'): students.op_affairs_student_profile,
    ('GET','/api/swap'): swaps.op_swap,
    ('POST','/api/swap/request'): swaps.op_swap_request,
    ('POST','/api/swap/cancel'): swaps.op_swap_cancel,
}

def dispatch(method, path, c, user, body, respond, headers, request_path):
    operation = ROUTES.get((method,path))
    if operation is None:return None
    return operation(c,user,body(),respond,headers,request_path,method,path)
