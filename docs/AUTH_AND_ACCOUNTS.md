# Security and account decisions — UniGate / eng.rabe3

## Story and design

### Student self-signup (FR-A1)
`POST /api/signup`, anonymously accessible, accepts only `name`, `student_number`, `password`. Server ignores any attempted role assignment and inserts **role='student'**, `graduate=0`, `honors=0`, `hold=0`, `is_active=1`. The university number is unique and used as the initial `username`. `name_en` initially mirrors `name_ar` because transliteration must not be fabricated. An authorized student affairs employee can update it later.

### Login (FR-A2)
`POST /api/login` accepts student university number or staff username and password, checks salted PBKDF2 hash and `is_active=1`, issues an HttpOnly SameSite Strict session cookie. `GET /api/bootstrap` is authenticated. The actual data are keyed by database user IDs, not mutable names or browser session storage.

### Private staff provisioning (FR-A3)
`python manage_staff.py setup` prompts locally for the administrator and three student affairs officers. Exactly one admin and three affairs users are set active. Existing accounts of those roles not assigned a slot are disabled and their sessions revoked. A unique `staff_slot` allows rotating logins while keeping previous account IDs/history. Optional `set-role` covers historical head/finance roles. This is **not exposed through HTTP**.

### Persistent draft basket (FR-A4)
`GET/POST /api/basket` operates on `student_basket(user_id,section_id,added_at)` with an authenticated student. It does not reserve seats or override confirmation-time constraints. It is user-specific even when multiple students sign in to the same machine. Existing confirmed enrollments, payments and waitlists keep their original persistence.

### Migration (NFR-M1)
`init_db()` adds `is_active`, `staff_slot`, and `student_basket` without deleting prior rows. First normal migration deactivates legacy *privileged* users with known demo passwords (administrators, affairs, finance, heads), preserves user IDs, and revokes their old sessions. This requires local staff setup before employees can login. Old student rows and enrollment history remain untouched. The full clean database starts with sample courses but no accounts.

### Protection and limitations (NFR-S1)
- Anonymous signup cannot assign elevated roles; role is a constant in SQL.
- Unique indexes plus immediate SQLite transactions prevent duplicate sign-up races.
- Student sessions are scoped by `user_id`; deactivated staff sessions fail authorization.
- A simple in-memory auth-attempt limit reduces local brute force; it is insufficient for public distributed hosting.
- No password recovery/email verification/university identity validation exists yet. A person knowing another student's unused number could impersonate them on self-registration. Production needs official identity verification, HTTPS, recovery flows, central rate limiting, logging, and database/backups with access controls.
- Do not use the old shared `Demo123!` student credentials beyond local demonstration.
- No web endpoint is allowed to delete registered account data in non-test mode.

## Test traceability

| Check | Test |
|---|---|
| Anonymous student signup and forced student role | `test_accounts.py` |
| Duplicate IDs, wrong-password rejection | `test_accounts.py` |
| Different users see different draft baskets | `test_accounts.py` |
| Draft basket survives logout, browser changes, server restarts | `test_accounts.py` |
| Only local provisioning creates 1 admin and 3 affairs | `test_accounts.py` |
| Staff powers remain separate from students | `test_accounts.py` |
| Existing student profiles survive migration and historical staff access is blocked | `test_accounts.py` |
| Seat capacity and enrollment idempotency | `test_concurrency.py`, `test_layered_workflows.py` |
