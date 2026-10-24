# SQLite schema inventory — inspected from the bundled clean sample database

The bundled archive contains **0 user records**, **18 courses**, and **21 demo sections**. This inventory reflects the physical schema; the upgraded application may add any missing objects using additive migrations.

**SQLite is retained:** no conversion to PostgreSQL in this deployment path.

## Table `audit`

| Column | Type | Nullable | Key |
|---|---|---|---|
| `id` | `INTEGER` | Yes | PK |
| `actor_id` | `INTEGER` | Yes | — |
| `action` | `TEXT` | No | — |
| `entity` | `TEXT` | No | — |
| `details` | `TEXT` | No | — |
| `created_at` | `TEXT` | No | — |

Foreign keys:
- `actor_id` → `users.id` (on_delete=NO ACTION)

## Table `completed`

| Column | Type | Nullable | Key |
|---|---|---|---|
| `user_id` | `INTEGER` | Yes | PK |
| `course_id` | `INTEGER` | Yes | PK |
| `passed` | `INTEGER` | No | — |

Foreign keys:
- `course_id` → `courses.id` (on_delete=NO ACTION)
- `user_id` → `users.id` (on_delete=NO ACTION)

## Table `course_grades`

| Column | Type | Nullable | Key |
|---|---|---|---|
| `user_id` | `INTEGER` | No | PK |
| `course_id` | `INTEGER` | No | PK |
| `score` | `REAL` | No | — |
| `updated_at` | `TEXT` | No | — |
| `updated_by` | `INTEGER` | Yes | — |

Foreign keys:
- `updated_by` → `users.id` (on_delete=NO ACTION)
- `course_id` → `courses.id` (on_delete=NO ACTION)
- `user_id` → `users.id` (on_delete=NO ACTION)

## Table `courses`

| Column | Type | Nullable | Key |
|---|---|---|---|
| `id` | `INTEGER` | Yes | PK |
| `code` | `TEXT` | No | — |
| `name_ar` | `TEXT` | No | — |
| `name_en` | `TEXT` | No | — |
| `credits` | `INTEGER` | No | — |
| `prerequisite_id` | `INTEGER` | Yes | — |

Foreign keys:
- `prerequisite_id` → `courses.id` (on_delete=NO ACTION)

## Table `enrollments`

| Column | Type | Nullable | Key |
|---|---|---|---|
| `id` | `INTEGER` | Yes | PK |
| `user_id` | `INTEGER` | No | — |
| `section_id` | `INTEGER` | No | — |
| `created_at` | `TEXT` | No | — |
| `origin` | `TEXT` | No | — |

Foreign keys:
- `section_id` → `sections.id` (on_delete=NO ACTION)
- `user_id` → `users.id` (on_delete=NO ACTION)

## Table `exceptions`

| Column | Type | Nullable | Key |
|---|---|---|---|
| `user_id` | `INTEGER` | Yes | PK |
| `min_override` | `INTEGER` | No | — |
| `reason` | `TEXT` | No | — |
| `approved_by` | `INTEGER` | Yes | — |

Foreign keys:
- `approved_by` → `users.id` (on_delete=NO ACTION)
- `user_id` → `users.id` (on_delete=NO ACTION)

## Table `payments`

| Column | Type | Nullable | Key |
|---|---|---|---|
| `id` | `INTEGER` | Yes | PK |
| `user_id` | `INTEGER` | No | — |
| `request_key` | `TEXT` | No | — |
| `reference` | `TEXT` | No | — |
| `status` | `TEXT` | No | — |
| `gateway_status` | `TEXT` | No | — |
| `created_at` | `TEXT` | No | — |

Foreign keys:
- `user_id` → `users.id` (on_delete=NO ACTION)

## Table `registration_requests`

| Column | Type | Nullable | Key |
|---|---|---|---|
| `id` | `INTEGER` | Yes | PK |
| `user_id` | `INTEGER` | No | — |
| `request_key` | `TEXT` | No | — |
| `status` | `TEXT` | No | — |
| `response_json` | `TEXT` | No | — |
| `created_at` | `TEXT` | No | — |

Foreign keys:
- `user_id` → `users.id` (on_delete=NO ACTION)

## Table `sections`

| Column | Type | Nullable | Key |
|---|---|---|---|
| `id` | `INTEGER` | Yes | PK |
| `course_id` | `INTEGER` | No | — |
| `label` | `TEXT` | No | — |
| `capacity` | `INTEGER` | No | — |
| `weekday` | `INTEGER` | No | — |
| `start_time` | `INTEGER` | No | — |
| `end_time` | `INTEGER` | No | — |
| `instructor` | `TEXT` | No | — |

Foreign keys:
- `course_id` → `courses.id` (on_delete=NO ACTION)

## Table `sessions`

| Column | Type | Nullable | Key |
|---|---|---|---|
| `token_hash` | `TEXT` | Yes | PK |
| `user_id` | `INTEGER` | No | — |
| `created_at` | `TEXT` | No | — |

Foreign keys:
- `user_id` → `users.id` (on_delete=NO ACTION)

## Table `settings`

| Column | Type | Nullable | Key |
|---|---|---|---|
| `key` | `TEXT` | Yes | PK |
| `value` | `TEXT` | No | — |

Foreign keys:
- None

## Table `student_basket`

| Column | Type | Nullable | Key |
|---|---|---|---|
| `user_id` | `INTEGER` | No | PK |
| `section_id` | `INTEGER` | No | PK |
| `added_at` | `TEXT` | No | — |

Foreign keys:
- `section_id` → `sections.id` (on_delete=CASCADE)
- `user_id` → `users.id` (on_delete=CASCADE)

## Table `student_plan`

| Column | Type | Nullable | Key |
|---|---|---|---|
| `user_id` | `INTEGER` | No | PK |
| `course_id` | `INTEGER` | No | PK |
| `required` | `INTEGER` | No | — |
| `assigned_at` | `TEXT` | No | — |

Foreign keys:
- `course_id` → `courses.id` (on_delete=NO ACTION)
- `user_id` → `users.id` (on_delete=NO ACTION)

## Table `swap_requests`

| Column | Type | Nullable | Key |
|---|---|---|---|
| `id` | `INTEGER` | Yes | PK |
| `user_id` | `INTEGER` | No | — |
| `from_section_id` | `INTEGER` | No | — |
| `to_section_id` | `INTEGER` | No | — |
| `status` | `TEXT` | No | — |
| `created_at` | `TEXT` | No | — |
| `matched_request_id` | `INTEGER` | Yes | — |
| `processed_at` | `TEXT` | Yes | — |
| `explanation` | `TEXT` | No | — |

Foreign keys:
- `matched_request_id` → `swap_requests.id` (on_delete=NO ACTION)
- `to_section_id` → `sections.id` (on_delete=NO ACTION)
- `from_section_id` → `sections.id` (on_delete=NO ACTION)
- `user_id` → `users.id` (on_delete=NO ACTION)

## Table `users`

| Column | Type | Nullable | Key |
|---|---|---|---|
| `id` | `INTEGER` | Yes | PK |
| `username` | `TEXT` | No | — |
| `name_ar` | `TEXT` | No | — |
| `name_en` | `TEXT` | No | — |
| `role` | `TEXT` | No | — |
| `password_hash` | `TEXT` | No | — |
| `graduate` | `INTEGER` | Yes | — |
| `honors` | `INTEGER` | Yes | — |
| `hold` | `INTEGER` | Yes | — |
| `student_number` | `TEXT` | No | — |
| `phone` | `TEXT` | No | — |
| `email` | `TEXT` | No | — |
| `is_active` | `INTEGER` | No | — |
| `staff_slot` | `TEXT` | Yes | — |

Foreign keys:
- None

## Table `waitlist`

| Column | Type | Nullable | Key |
|---|---|---|---|
| `id` | `INTEGER` | Yes | PK |
| `user_id` | `INTEGER` | No | — |
| `section_id` | `INTEGER` | No | — |
| `status` | `TEXT` | No | — |
| `joined_at` | `TEXT` | No | — |
| `note` | `TEXT` | No | — |

Foreign keys:
- `section_id` → `sections.id` (on_delete=NO ACTION)
- `user_id` → `users.id` (on_delete=NO ACTION)

- **Index `idx_enroll_sec` on `enrollments(section_id)`**
- **Index `idx_pay_user` on `payments(user_id,status)`**
- **Index `idx_swap_match` on `swap_requests(from_section_id,to_section_id,status,created_at,id)`**
- **Index `idx_users_student_number` on `users(student_number) WHERE student_number <> ''`**
- **Index `idx_waitlist_sec` on `waitlist(section_id,status,joined_at,id)`**
- **Index `uq_active_swap_user` on `swap_requests(user_id) WHERE status='pending'`**
- **Index `uq_users_staff_slot` on `users(staff_slot) WHERE staff_slot IS NOT NULL`**
- **Index `uq_users_username_ci` on `users(username COLLATE NOCASE)`**
### Trigger `trg_enrollment_capacity_insert`

```sql
CREATE TRIGGER trg_enrollment_capacity_insert
    BEFORE INSERT ON enrollments
    WHEN (SELECT COUNT(*) FROM enrollments WHERE section_id=NEW.section_id) >=
         (SELECT capacity FROM sections WHERE id=NEW.section_id)
    BEGIN SELECT RAISE(ABORT,'SECTION_FULL'); END
```

### Trigger `trg_enrollment_capacity_update`

```sql
CREATE TRIGGER trg_enrollment_capacity_update
    BEFORE UPDATE OF section_id ON enrollments
    WHEN NEW.section_id<>OLD.section_id AND
         (SELECT COUNT(*) FROM enrollments WHERE section_id=NEW.section_id) >=
         (SELECT capacity FROM sections WHERE id=NEW.section_id)
    BEGIN SELECT RAISE(ABORT,'SECTION_FULL'); END
```

### Trigger `trg_enrollment_course_insert`

```sql
CREATE TRIGGER trg_enrollment_course_insert
    BEFORE INSERT ON enrollments
    WHEN EXISTS(
      SELECT 1 FROM enrollments e JOIN sections old ON old.id=e.section_id
      JOIN sections incoming ON incoming.id=NEW.section_id
      WHERE e.user_id=NEW.user_id AND old.course_id=incoming.course_id)
    BEGIN SELECT RAISE(ABORT,'DUPLICATE_COURSE'); END
```

### Trigger `trg_enrollment_course_update`

```sql
CREATE TRIGGER trg_enrollment_course_update
    BEFORE UPDATE OF section_id ON enrollments
    WHEN NEW.section_id<>OLD.section_id AND EXISTS(
      SELECT 1 FROM enrollments e JOIN sections old ON old.id=e.section_id
      JOIN sections incoming ON incoming.id=NEW.section_id
      WHERE e.user_id=NEW.user_id AND e.id<>OLD.id
        AND old.course_id=incoming.course_id)
    BEGIN SELECT RAISE(ABORT,'DUPLICATE_COURSE'); END
```


**Important invariants:** `PRAGMA foreign_keys=ON` is applied by the app connection factory; enrollment capacity and duplicate-course triggers protect confirmed registration; operation and payment keys are unique; session tokens are stored only as hashes.
