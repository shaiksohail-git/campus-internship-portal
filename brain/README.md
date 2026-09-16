# 🎓 Campus Internship & Placement Portal

A full-stack **Campus Placement Portal** (V1) built from the PRD & TRD documents in
this repository. One centralized portal where **verified recruiters** publish
internships & full-time roles, **students** apply and track their applications,
and **placement officers** approve, monitor and analyze the whole process.

**Stack (per the TRD):** Python + Flask · SQLAlchemy · Alembic migrations ·
REST API (`/api/v1`) · server-side sessions · Werkzeug password hashing ·
vanilla HTML/CSS/JS frontend · SQLite locally (PostgreSQL in production).

---

## ✨ Features

| Role | Capabilities |
|---|---|
| **Student** | Register → verify email → complete profile → upload resumes → browse/search/filter opportunities → apply (with a chosen resume) → track fixed status flow → view scheduled interviews → in-app notifications |
| **Recruiter** | Register → get approved by admin → create internship/full-time postings → submit for approval → review applicants → download resumes → update application status (state machine) → schedule/reschedule/cancel interviews |
| **Admin** | Dashboard with live stats → approve/reject recruiters → approve/reject postings → close postings → manage/suspend users → monitor applications & interviews → placement analytics (type split, departments, companies, monthly activity, selection rate) → audit log |

**Security highlights:** role-based authorization on every route, ownership
checks (404 on foreign data), backend-only business rules, duplicate-application
prevention via a DB unique constraint, single-use expiring tokens (stored as
hashes), CSRF protection, rate-limited auth endpoints, private resume storage
with authorized downloads and magic-byte validation, audit logging for admin
actions.

---

## 🚀 Quick start

```bash
# 1. Create a virtual environment and install dependencies
python -m venv .venv
.venv/Scripts/activate            # Windows (Git Bash: .venv/Scripts/activate)
pip install -r requirements-dev.txt

# 2. Apply database migrations
flask --app run db upgrade

# 3. (Optional) seed the database with demo data
flask --app run seed-demo --reset

# 4. Run the app
flask --app run run
```

Open **http://127.0.0.1:5000**.

### Demo accounts (after seeding)

| Role | Email | Password |
|---|---|---|
| Admin | `admin@college.edu` | `Admin@123` |
| Student | `student1@college.edu` | `Student@123` |
| Recruiter | `techcorp@company.com` | `Recruiter@123` |

> 🧪 **Dev mailbox:** emails (verification, password reset, notifications) are
> captured in the app at **`/dev/mailbox`** when `MAIL_MODE=console` (the
> default). Register a fresh account and grab the verification link there.
> Set SMTP credentials in `.env` to send real emails (`MAIL_MODE=smtp`).

---

## 🗂 Project structure

```
├── app/
│   ├── __init__.py        # App factory, error handlers, CLI, template globals
│   ├── config.py          # Environment-driven configuration
│   ├── cli.py             # `flask seed-demo` command
│   ├── models/            # SQLAlchemy models + central enums
│   ├── routes/            # Blueprints: auth, students, recruiters, admin, shared
│   ├── services/          # Business logic: auth, applications, interviews,
│   │                      #   notifications, analytics, admin, storage
│   ├── middleware/        # Session auth, role permissions, CSRF, rate limiting
│   ├── utils/             # Errors, validators, tokens, email, API helpers
│   ├── templates/         # Jinja2 pages (landing, auth, role dashboards)
│   └── static/            # style.css design system + vanilla JS
├── migrations/            # Alembic migrations
├── tests/                 # pytest suite + page smoke test
├── run.py                 # Entry point
└── requirements.txt
```

**Architecture rule (from the TRD):** *Routes handle HTTP, services handle
business logic, models handle database structure.*

---

## 🔐 Configuration

Copy `.env.example` → `.env` for:

- `SECRET_KEY` — set a long random value in production
- `DATABASE_URL` — `sqlite:///portal.db` (default) or PostgreSQL, e.g.
  `postgresql+psycopg2://user:pass@localhost:5432/campus_portal`
- `MAIL_MODE` — `console` (dev mailbox) or `smtp` + `SMTP_HOST/PORT/USERNAME/PASSWORD`
- `STORAGE_MODE` — `local` (default; files under `instance/uploads/resumes`)
- `SESSION_COOKIE_SECURE` — `true` behind HTTPS

Never commit `.env` (already gitignored).

---

## 🧪 Testing

```bash
.venv/Scripts/python -m pytest -q        # 71 tests: auth, permissions,
                                         # applications, interviews, resumes, admin
.venv/Scripts/python tests/smoke_pages.py  # renders every page for every role
```

The critical PRD/TRD guarantees are covered by tests:

- Student cannot apply twice (409, DB constraint)
- Cannot apply after the deadline / without a resume / to unpublished postings
- Unapproved recruiters cannot publish
- Invalid application status transitions are rejected
- Recruiters cannot see or modify another recruiter's data (404)
- Students cannot reach recruiter/admin APIs (403) or other students' resumes
- Verification tokens are single-use and expire; password reset flows work
- Suspended users are blocked immediately

---

## 📡 API overview (REST, `/api/v1`)

- **Auth:** `register/student`, `register/recruiter`, `login`, `logout`,
  `verify-email`, `resend-verification`, `forgot-password`, `reset-password`, `me`
- **Student:** profile, resumes (upload/list/delete), opportunities (list/filter,
  detail, apply), applications, interviews
- **Recruiter:** profile, opportunities (CRUD + submit + close), applicants,
  application status, interviews (schedule/update/cancel/complete)
- **Admin:** dashboard, students, recruiters (+approve/reject), opportunities
  (+approve/reject/close), applications, interviews, analytics, audit-logs

Responses use a consistent envelope:
`{"success": true, "data": ..., "message": ...}` /
`{"success": false, "error": {"code": "...", "message": "..."}}`.

---

## 🗄 Database

Migrations are managed with **Alembic** (via Flask-Migrate). Schema: `users`,
`colleges`, `student_profiles`, `recruiter_profiles`, `resumes`, `opportunities`,
`applications` (unique student+opportunity), `interviews`, `notifications`,
`auth_tokens`, `audit_logs`, `dev_mailbox`.

```bash
flask --app run db migrate -m "description"   # after model changes
flask --app run db upgrade
```

---

## ☁️ Production notes

- Run with **Gunicorn** behind **Nginx** (HTTPS), use **PostgreSQL**, enable
  `MAIL_MODE=smtp`, and set `SESSION_COOKIE_SECURE=true`.
- The in-memory rate limiter is per-process — acceptable for single-instance V1.
- `MAIL_MODE=console` and `/dev/mailbox` are development-only.

---

Built to the V1 scope: **Authentication → Profiles → Recruiter Approval →
Opportunities → Applications → Status → Interviews → Notifications → Admin Analytics**.
