-- Reference schema generated from executable SQLite startup.
-- Do not execute this file on an existing database; init_db() handles upgrades.

CREATE TABLE audit(id INTEGER PRIMARY KEY, actor_id INTEGER REFERENCES users(id), action TEXT NOT NULL, entity TEXT NOT NULL, details TEXT NOT NULL, created_at TEXT NOT NULL);

CREATE TABLE completed(user_id INTEGER REFERENCES users(id), course_id INTEGER REFERENCES courses(id), passed INTEGER NOT NULL,
        PRIMARY KEY(user_id,course_id));

CREATE TABLE course_grades (
      user_id INTEGER NOT NULL REFERENCES users(id), course_id INTEGER NOT NULL REFERENCES courses(id),
      score REAL NOT NULL CHECK(score>=0 AND score<=100),
      updated_at TEXT NOT NULL, updated_by INTEGER REFERENCES users(id),
      PRIMARY KEY(user_id,course_id));

CREATE TABLE courses(id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, name_ar TEXT NOT NULL, name_en TEXT NOT NULL,
        credits INTEGER NOT NULL CHECK(credits BETWEEN 1 AND 6), prerequisite_id INTEGER REFERENCES courses(id));

CREATE TABLE enrollments(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), section_id INTEGER NOT NULL REFERENCES sections(id),
        created_at TEXT NOT NULL, origin TEXT NOT NULL DEFAULT 'student', UNIQUE(user_id, section_id));

CREATE TABLE exceptions(user_id INTEGER PRIMARY KEY REFERENCES users(id), min_override INTEGER NOT NULL, reason TEXT NOT NULL, approved_by INTEGER REFERENCES users(id));

CREATE TABLE payments(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), request_key TEXT NOT NULL,
        reference TEXT UNIQUE NOT NULL, status TEXT NOT NULL, gateway_status TEXT NOT NULL, created_at TEXT NOT NULL,
        UNIQUE(user_id,request_key));

CREATE TABLE registration_requests(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), request_key TEXT NOT NULL,
        status TEXT NOT NULL, response_json TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(user_id,request_key));

CREATE TABLE sections(id INTEGER PRIMARY KEY, course_id INTEGER NOT NULL REFERENCES courses(id), label TEXT NOT NULL,
        capacity INTEGER NOT NULL CHECK(capacity>0), weekday INTEGER NOT NULL CHECK(weekday BETWEEN 0 AND 6),
        start_time INTEGER NOT NULL, end_time INTEGER NOT NULL, instructor TEXT NOT NULL, UNIQUE(course_id,label),
        CHECK(start_time < end_time));

CREATE TABLE sessions(token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), created_at TEXT NOT NULL);

CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE TABLE student_plan (
      user_id INTEGER NOT NULL REFERENCES users(id), course_id INTEGER NOT NULL REFERENCES courses(id),
      required INTEGER NOT NULL DEFAULT 1 CHECK(required IN (0,1)),
      assigned_at TEXT NOT NULL, PRIMARY KEY(user_id,course_id));

CREATE TABLE swap_requests(
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id),
        from_section_id INTEGER NOT NULL REFERENCES sections(id),
        to_section_id INTEGER NOT NULL REFERENCES sections(id),
        status TEXT NOT NULL DEFAULT 'pending'
            CHECK(status IN ('pending','matched','cancelled','invalid')),
        created_at TEXT NOT NULL,
        matched_request_id INTEGER REFERENCES swap_requests(id),
        processed_at TEXT,
        explanation TEXT NOT NULL DEFAULT '',
        CHECK(from_section_id <> to_section_id));

CREATE TABLE users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, name_ar TEXT NOT NULL, name_en TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('student','affairs','head','finance','admin')), password_hash TEXT NOT NULL,
        graduate INTEGER DEFAULT 0, honors INTEGER DEFAULT 0, hold INTEGER DEFAULT 0, student_number TEXT NOT NULL DEFAULT '', phone TEXT NOT NULL DEFAULT '', email TEXT NOT NULL DEFAULT '');

CREATE TABLE waitlist(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), section_id INTEGER NOT NULL REFERENCES sections(id),
        status TEXT NOT NULL DEFAULT 'waiting', joined_at TEXT NOT NULL, note TEXT NOT NULL DEFAULT '', UNIQUE(user_id,section_id));

CREATE INDEX idx_enroll_sec ON enrollments(section_id);

CREATE INDEX idx_pay_user ON payments(user_id,status);

CREATE INDEX idx_swap_match
        ON swap_requests(from_section_id,to_section_id,status,created_at,id);

CREATE UNIQUE INDEX idx_users_student_number ON users(student_number) WHERE student_number <> '';

CREATE INDEX idx_waitlist_sec ON waitlist(section_id,status,joined_at,id);

CREATE UNIQUE INDEX uq_active_swap_user
        ON swap_requests(user_id) WHERE status='pending';

CREATE TRIGGER trg_enrollment_capacity_insert
    BEFORE INSERT ON enrollments
    WHEN (SELECT COUNT(*) FROM enrollments WHERE section_id=NEW.section_id) >=
         (SELECT capacity FROM sections WHERE id=NEW.section_id)
    BEGIN SELECT RAISE(ABORT,'SECTION_FULL'); END;

CREATE TRIGGER trg_enrollment_capacity_update
    BEFORE UPDATE OF section_id ON enrollments
    WHEN NEW.section_id<>OLD.section_id AND
         (SELECT COUNT(*) FROM enrollments WHERE section_id=NEW.section_id) >=
         (SELECT capacity FROM sections WHERE id=NEW.section_id)
    BEGIN SELECT RAISE(ABORT,'SECTION_FULL'); END;

CREATE TRIGGER trg_enrollment_course_insert
    BEFORE INSERT ON enrollments
    WHEN EXISTS(
      SELECT 1 FROM enrollments e JOIN sections old ON old.id=e.section_id
      JOIN sections incoming ON incoming.id=NEW.section_id
      WHERE e.user_id=NEW.user_id AND old.course_id=incoming.course_id)
    BEGIN SELECT RAISE(ABORT,'DUPLICATE_COURSE'); END;

CREATE TRIGGER trg_enrollment_course_update
    BEFORE UPDATE OF section_id ON enrollments
    WHEN NEW.section_id<>OLD.section_id AND EXISTS(
      SELECT 1 FROM enrollments e JOIN sections old ON old.id=e.section_id
      JOIN sections incoming ON incoming.id=NEW.section_id
      WHERE e.user_id=NEW.user_id AND e.id<>OLD.id
        AND old.course_id=incoming.course_id)
    BEGIN SELECT RAISE(ABORT,'DUPLICATE_COURSE'); END;
