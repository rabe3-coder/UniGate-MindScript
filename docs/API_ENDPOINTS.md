# API endpoint inventory — source-of-truth app/api/router.py

The following **34** routes are present in the current source. Operations use JSON and existing session cookies.

| Method | Path | Handler |
|---|---|---|
| `GET` | `/api/activity` | `app.application.queries.op_activity` |
| `POST` | `/api/admin/reset` | `app.application.admin.op_admin_reset` |
| `POST` | `/api/admin/settings` | `app.application.admin.op_admin_settings` |
| `GET` | `/api/affairs/academic` | `app.application.academics.op_affairs_academic` |
| `POST` | `/api/affairs/academic` | `app.application.academics.op_affairs_academic` |
| `POST` | `/api/affairs/exception` | `app.application.academics.op_affairs_exception` |
| `POST` | `/api/affairs/grade` | `app.application.academics.op_affairs_grade` |
| `POST` | `/api/affairs/hold` | `app.application.academics.op_affairs_hold` |
| `POST` | `/api/affairs/student/create` | `app.application.students.op_affairs_student_create` |
| `GET` | `/api/affairs/student/profile` | `app.application.students.op_affairs_student_profile` |
| `POST` | `/api/affairs/student/profile` | `app.application.students.op_affairs_student_profile` |
| `GET` | `/api/basket` | `app.application.basket.op_basket` |
| `POST` | `/api/basket` | `app.application.basket.op_basket` |
| `GET` | `/api/bootstrap` | `app.application.queries.op_bootstrap` |
| `GET` | `/api/catalog` | `app.application.queries.op_catalog` |
| `POST` | `/api/drop` | `app.application.enrollment.op_drop` |
| `POST` | `/api/lab/run` | `app.application.labs.op_lab_run` |
| `POST` | `/api/login` | `app.application.auth.op_login` |
| `POST` | `/api/logout` | `app.application.auth.op_logout` |
| `GET` | `/api/me` | `app.application.queries.op_me` |
| `POST` | `/api/payment/reconcile` | `app.application.payments.op_payment_reconcile` |
| `POST` | `/api/payment/request` | `app.application.payments.op_payment_request` |
| `GET` | `/api/payments` | `app.application.queries.op_payments` |
| `POST` | `/api/register` | `app.application.enrollment.op_register` |
| `POST` | `/api/section/capacity` | `app.application.sections.op_section_capacity` |
| `POST` | `/api/section/create` | `app.application.sections.op_section_create` |
| `POST` | `/api/signup` | `app.application.auth.op_signup` |
| `GET` | `/api/students` | `app.application.queries.op_students` |
| `GET` | `/api/swap` | `app.application.swaps.op_swap` |
| `POST` | `/api/swap/cancel` | `app.application.swaps.op_swap_cancel` |
| `POST` | `/api/swap/request` | `app.application.swaps.op_swap_request` |
| `GET` | `/api/waitlist` | `app.application.queries.op_waitlist` |
| `POST` | `/api/waitlist/join` | `app.application.enrollment.op_waitlist_join` |
| `POST` | `/api/waitlist/leave` | `app.application.enrollment.op_waitlist_leave` |
