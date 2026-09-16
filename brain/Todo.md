# 🚀 Campus Placement Portal — Deployment & Project Guide

> This file explains **every file and folder** in the project and gives you a
> step-by-step deployment plan for production.

---

## Table of Contents

1. [Deployment Checklist](#1-deployment-checklist)
2. [Step-by-Step Deployment](#2-step-by-step-deployment)
3. [Project Structure — Every File Explained](#3-project-structure--every-file-explained)
4. [What You Need to Change for Production](#4-what-you-need-to-change-for-production)
5. [Troubleshooting](#5-troubleshooting)

---

## 1. Deployment Checklist

Before deploying, make sure you have:

- [ ] A hosting provider (Render, Railway, Fly.io, or a VPS like DigitalOcean)
- [ ] A PostgreSQL database (Neon, Supabase, or your hosting provider's DB)
- [ ] An SMTP email service (Gmail, SendGrid, Mailgun, etc.)
- [ ] A domain name (optional but recommended)
- [ ] SSL/HTTPS enabled (required for secure cookies)

---

## 2. Step-by-Step Deployment

### Step 1: Prepare Your Code

```bash
# Make sure all tests pass before deploying
python -m pytest -q
python tests/smoke_pages.py
```

### Step 2: Create a Production `.env` File

Create a `.env` file on your server with these values:

```env
# Generate a secure secret key (run this command to get one):
# python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your-random-64-char-hex-string-here

# Use production environment
APP_ENV=default

# PostgreSQL connection string (from your database provider)
DATABASE_URL=postgresql+psycopg2://username:password@host:5432/dbname

# Real email sending
MAIL_MODE=smtp
MAIL_FROM="Campus Placement Portal <no-reply@yourdomain.com>"
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true

# File storage (local for now, can upgrade to S3 later)
STORAGE_MODE=local

# Secure cookies (required for HTTPS)
SESSION_COOKIE_SECURE=true
```

### Step 3: Set Up Your Database

**Option A — Using a managed database (recommended):**
1. Sign up for [Neon](https://neon.tech), [Supabase](https://supabase.com), or [Railway](https://railway.app)
2. Create a new PostgreSQL database
3. Copy the connection string into your `DATABASE_URL`

**Option B — Using your hosting provider's database:**
1. Create a PostgreSQL database
2. Copy the connection string into your `DATABASE_URL`

### Step 4: Deploy to a Hosting Provider

#### Option A — Render (Free tier available)

1. Push your code to GitHub/GitLab
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your repository
4. Configure:
   - **Build Command:** `pip install -r requirements.txt && flask --app run db upgrade`
   - **Start Command:** `gunicorn run:app`
5. Add environment variables from your `.env` file in the Render dashboard
6. Deploy

#### Option B — Railway

1. Push your code to GitHub/GitLab
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Railway auto-detects Python and sets up the build
4. Add a PostgreSQL database from the Railway dashboard
5. Add environment variables
6. Railway runs `flask --app run db upgrade` automatically if you add it to a start command

#### Option C — Fly.io

1. Install Fly CLI: `curl -L https://fly.io/install.sh | sh`
2. `fly launch` — answers questions about your app
3. `fly secrets set SECRET_KEY=... DATABASE_URL=... MAIL_MODE=smtp ...`
4. `fly deploy`

#### Option D — Traditional VPS (DigitalOcean, Linode, AWS EC2)

```bash
# SSH into your server
ssh root@your-server-ip

# Install Python, pip, and PostgreSQL
sudo apt update
sudo apt install python3-pip python3-venv postgresql

# Clone your repository
git clone https://github.com/yourusername/campus-placement-portal.git
cd campus-placement-portal

# Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install gunicorn psycopg2-binary

# Set up your .env file
cp .env.example .env
nano .env  # edit with your production values

# Run database migrations
flask --app run db upgrade

# Seed demo data (optional)
flask --app run seed-demo --reset

# Run with Gunicorn
gunicorn run:app --bind 0.0.0.0:8000 --workers 4
```

### Step 5: Set Up Nginx (for VPS only)

Create `/etc/nginx/sites-available/placement-portal`:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /root/campus-placement-portal/app/static/;
        expires 30d;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/placement-portal /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 6: Set Up SSL with Certbot

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### Step 7: Set Up as a System Service (VPS only)

Create `/etc/systemd/system/placement-portal.service`:

```ini
[Unit]
Description=Campus Placement Portal
After=network.target

[Service]
User=root
WorkingDirectory=/root/campus-placement-portal
ExecStart=/root/campus-placement-portal/.venv/bin/gunicorn run:app --bind 127.0.0.1:8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable placement-portal
sudo systemctl start placement-portal
```

---

## 3. Project Structure — Every File Explained

### Root Level Files

| File | Purpose |
|------|---------|
| `run.py` | **Entry point.** Creates the Flask app and runs it. Used by `python run.py` or `gunicorn run:app`. |
| `requirements.txt` | **Production dependencies.** Flask, SQLAlchemy, Flask-Migrate, python-dotenv, reportlab (for PDF exports). |
| `requirements-dev.txt` | **Development dependencies.** Includes everything in requirements.txt plus pytest for testing. |
| `pytest.ini` | **Pytest configuration.** Tells pytest to look in the `tests/` folder. |
| `.env.example` | **Environment variable template.** Copy this to `.env` and fill in your values. |
| `.gitignore` | **Git ignore rules.** Prevents `.env`, `instance/`, `__pycache__/`, and other sensitive/temporary files from being committed. |
| `README.md` | **Project documentation.** Features, quick start guide, API overview. |
| `progress.md` | **Development log.** Tracks what was built, bugs fixed, and verification results. |
| `Todo.md` | **This file.** Deployment guide and project documentation. |
| `Product Requirements Document (PRD).md` | **Original requirements.** What the product should do (features, user stories, acceptance criteria). |
| `Technical Requirements Document (TRD).md` | **Technical specs.** Architecture decisions, tech stack, database schema, API design. |
| `server.log` | **Runtime logs.** Flask server output (auto-generated, gitignored). |

---

### `app/` — Main Application Package

#### `app/__init__.py` — App Factory

The heart of the Flask application. The `create_app()` function:
- Loads configuration from `config.py`
- Initializes database (SQLAlchemy) and migrations (Flask-Migrate)
- Sets up CSRF protection middleware
- Registers all route blueprints (auth, students, recruiters, admin)
- Adds template filters (date formatting, file size display)
- Registers error handlers (API errors, HTTP errors, unexpected errors)
- Registers CLI commands (seed-demo, send-weekly-digest)

#### `app/config.py` — Configuration

All settings are driven by environment variables:
- **Core:** `SECRET_KEY`, `APP_ENV`
- **Database:** `DATABASE_URL` (SQLite for dev, PostgreSQL for prod)
- **Email:** `MAIL_MODE` (console/smtp), SMTP settings
- **Storage:** `STORAGE_MODE` (local for now)
- **Security:** `CSRF_ENABLED`, `RATE_LIMIT_*`, `SESSION_COOKIE_SECURE`
- **Limits:** `PER_PAGE` (pagination), `TOKEN_TTL_HOURS`

#### `app/extensions.py` — Flask Extensions

Initializes `db` (SQLAlchemy) and `migrate` (Flask-Migrate) so they can be imported elsewhere without circular dependencies.

#### `app/cli.py` — CLI Commands

Custom Flask commands:
- `flask seed-demo --reset` — Creates demo users, opportunities, applications, and interviews for testing
- `flask send-weekly-digest` — Sends weekly analytics emails to opted-in recruiters

---

### `app/models/` — Database Models (16 files)

Each file defines one SQLAlchemy model (database table) plus relationships.

| File | Table | Purpose |
|------|-------|---------|
| `__init__.py` | — | Imports all models so they're registered with SQLAlchemy |
| `user.py` | `users` | User accounts (email, password hash, role, is_active, is_verified). Has `set_password()` and `check_password()` methods. |
| `student.py` | `student_profiles` | Student info (name, phone, college, degree, department, graduation year, skills). Linked 1:1 to User. |
| `recruiter.py` | `recruiter_profiles` | Company info (name, description, website, contact). Includes approval status (PENDING/APPROVED/REJECTED). |
| `college.py` | `colleges` | College names for student profiles. |
| `opportunity.py` | `opportunities` | Job/internship postings (title, type, description, skills, eligibility, deadline, status). |
| `application.py` | `applications` | Student applications to opportunities. Has UNIQUE(student_id, opportunity_id) constraint. Tracks status through a state machine. |
| `interview.py` | `interviews` | Scheduled interviews (date, time, mode, location, meeting link). Linked to applications. |
| `resume.py` | `resumes` | Uploaded resume files (filename, path, size, type). Linked to students. |
| `notification.py` | `notifications` | In-app notifications (type, title, message, read status). |
| `token.py` | `auth_tokens` | Single-use tokens for email verification and password reset. Stored as hashes with expiry. |
| `audit.py` | `audit_logs` | Admin action audit trail (who did what to which entity). |
| `mailbox.py` | `dev_mailbox` | Dev-only email capture (when MAIL_MODE=console). Viewable at `/dev/mailbox`. |
| `announcement.py` | `announcements` | Admin announcements for students/recruiters. |
| `offer_letter.py` | `offer_letters` | Offer letters sent to selected students. |
| `enums.py` | — | Central enum definitions (Role, OpportunityStatus, ApplicationStatus, InterviewStatus, etc.). Used across the entire app for consistency. |

---

### `app/routes/` — HTTP Handlers (7 files)

Each file is a Flask Blueprint that handles routes for one feature area.

| File | Blueprint | Purpose |
|------|-----------|---------|
| `__init__.py` | — | Registers all blueprints with the Flask app |
| `auth.py` | `auth` | Login, logout, register (student + recruiter), email verification, forgot/reset password |
| `students.py` | `students` | Student dashboard, profile, resume upload/delete, browse opportunities, apply, track applications, view interviews |
| `recruiters.py` | `recruiters` | Recruiter dashboard, profile, create/edit/close/reopen opportunities, view applicants, update application status, schedule interviews, analytics, offer letters |
| `admin.py` | `admin` | Admin dashboard, manage students/recruiters, approve/reject opportunities, analytics, audit logs, announcements |
| `shared.py` | `shared` | Shared routes (resume preview, public announcements) accessible by multiple roles |
| `pages.py` | `pages` | Landing page, 403 error page |

---

### `app/services/` — Business Logic (11 files)

Services contain the core business rules, keeping routes clean.

| File | Purpose |
|------|---------|
| `auth_service.py` | Registration, login, email verification, password reset logic |
| `application_service.py` | Application status transitions (state machine validation), duplicate prevention |
| `interview_service.py` | Interview scheduling, rescheduling, cancellation, overlap detection |
| `notification_service.py` | Create and query notifications, unread count, notify all admins |
| `analytics_service.py` | Admin dashboard stats, selection rate, department/company breakdowns, monthly activity |
| `recruiter_analytics_service.py` | Recruiter-scoped analytics with date filtering, peer benchmarks, monthly trends |
| `analytics_export.py` | CSV and PDF export generation for analytics reports |
| `admin_service.py` | Approve/reject recruiters and opportunities, suspend users, audit logging |
| `storage_service.py` | File storage abstraction (local filesystem for now, can swap to S3) |
| `digest_service.py` | Weekly email digest generation and sending |
| `offer_letter_service.py` | Generate and send offer letter PDFs to selected students |

---

### `app/middleware/` — Request Processing (4 files)

Middleware runs before/after every request.

| File | Purpose |
|------|---------|
| `__init__.py` | Package init |
| `auth.py` | Loads the current user from the session cookie into `g.current_user` on every request |
| `permissions.py` | Decorators: `@student_only`, `@recruiter_only`, `@admin_only` — blocks unauthorized access |
| `security.py` | CSRF token generation and validation, rate limiting on auth endpoints |

---

### `app/utils/` — Utility Helpers (6 files)

| File | Purpose |
|------|---------|
| `__init__.py` | Package init |
| `errors.py` | `ApiError` base class and specific errors (`ValidationError`, `NotFoundError`, `BusinessRuleError`) |
| `validators.py` | Input validation functions (required fields, email format, phone, URL, deadlines, enums) |
| `tokens.py` | Secure token generation and hashing for verification/reset links |
| `email.py` | Email abstraction: sends to dev mailbox (console mode) or real SMTP |
| `api.py` | API response helpers (`ok()`, `json_body()`, `paginate()`) and consistent JSON envelope format |

---

### `app/templates/` — Jinja2 HTML Templates

#### Root Templates

| File | Purpose |
|------|---------|
| `base.html` | **Base layout.** Nav bar, footer, flash messages, role-aware navigation links. Extended by all pages. |
| `landing.html` | **Home page.** Public landing page with features overview and login/register links. |
| `macros.html` | **Reusable macros.** `badge()` for status pills, `opp_card()` for opportunity cards, `pagination()`, `alert()` |
| `notifications.html` | **Notifications page.** Full notification list with mark-read functionality. |

#### `templates/auth/` — Authentication Pages

| File | Purpose |
|------|---------|
| `auth_base.html` | Auth layout (centered card design, shared by all auth pages) |
| `login.html` | Login form |
| `register_student.html` | Student registration form |
| `register_recruiter.html` | Recruiter registration form (with company details) |
| `verify_email.html` | Email verification page |
| `verify_pending.html` | "Check your email" page after registration |
| `forgot_password.html` | Forgot password form |
| `reset_password.html` | Reset password form (with token) |

#### `templates/student/` — Student Pages

| File | Purpose |
|------|---------|
| `dashboard.html` | Student home: stat cards, recent applications, upcoming interviews, announcements |
| `profile.html` | Profile editing, resume upload/delete, profile completeness meter |
| `opportunities.html` | Browse/search/filter opportunities with cards |
| `opportunity_detail.html` | Single opportunity view with apply button |
| `applications.html` | Track all applications with status timeline |
| `interviews.html` | View scheduled interviews |
| `resume_preview.html` | Standalone resume preview (PDFs inline via `<object>` tag) |

#### `templates/recruiter/` — Recruiter Pages

| File | Purpose |
|------|---------|
| `dashboard.html` | Recruiter home: stat cards, recent applications, upcoming interviews, announcements |
| `profile.html` | Company profile editing, weekly digest toggle |
| `opportunities.html` | List/manage all own opportunities with status tabs |
| `opportunity_form.html` | Create/edit opportunity form |
| `opportunity_detail.html` | Single opportunity view with applicant list |
| `applicants.html` | Applicant list for an opportunity with resume downloads |
| `selected_applicants.html` | View all selected students across opportunities, with CSV/PDF export |
| `interviews.html` | Manage scheduled interviews |
| `analytics.html` | Analytics dashboard with KPI cards, charts, peer comparison |
| `opportunity_analytics.html` | Per-opportunity drill-down analytics |

#### `templates/admin/` — Admin Pages

| File | Purpose |
|------|---------|
| `dashboard.html` | Admin home: live stat cards, pending recruiter/opportunity queues, recent applications |
| `students.html` | Manage students: search, suspend/reactivate |
| `recruiters.html` | Manage recruiters: approve/reject, view status |
| `opportunities.html` | Manage all opportunities: approve/reject/close |
| `applications.html` | View all applications across the platform |
| `interviews.html` | View all interviews |
| `analytics.html` | Platform-wide analytics: charts, department/company breakdowns |
| `audit_logs.html` | Admin action audit trail |
| `announcements.html` | Manage announcements |
| `announcement_form.html` | Create/edit announcement form |

#### `templates/errors/` — Error Pages

| File | Purpose |
|------|---------|
| `error.html` | Generic error page (404, 500, etc.) |
| `403.html` | Forbidden page (role-based access denied) |

#### `templates/dev/` — Development Only

| File | Purpose |
|------|---------|
| `mailbox.html` | Dev email inbox (only works when MAIL_MODE=console) |

---

### `app/static/` — Static Assets

| File | Purpose |
|------|---------|
| `css/style.css` | **Complete design system.** CSS variables, layout grid, cards, forms, tables, badges, alerts, modals, dashboard styles, responsive breakpoints. All styling for the entire app. |
| `js/app.js` | **Vanilla JavaScript.** API helper (`window.api`), toast notifications (`window.toast`), modal handling, CSRF token injection, opportunity action buttons (close/reopen/delete), form validation. No framework — pure JS. |

---

### `migrations/` — Database Migrations

| File | Purpose |
|------|---------|
| `alembic.ini` | Alembic configuration |
| `env.py` | Migration environment setup |
| `script.py.mako` | Migration script template |
| `versions/54af6c188785_initial_schema.py` | Creates all 13 initial tables |
| `versions/5cb6c764c72e_add_weekly_digest_enabled_to_recruiter_.py` | Adds `weekly_digest_enabled` column to recruiter_profiles |

---

### `tests/` — Test Suite (72 tests)

| File | Purpose |
|------|---------|
| `conftest.py` | **Test fixtures.** Flask test client, user registration helpers, login/logout, opportunity creation helpers. |
| `test_auth.py` | Authentication tests: registration, login, logout, verification, password reset, duplicate email rejection |
| `test_permissions.py` | Role isolation: students can't reach recruiter/admin APIs, recruiters can't see other recruiters' data |
| `test_applications.py` | Application rules: duplicate prevention, deadline enforcement, eligibility checks, state machine transitions |
| `test_interviews.py` | Interview rules: scheduling, cancellation, rescheduling, overlap detection, ownership checks |
| `test_resumes.py` | Resume tests: upload validation (PDF/DOC/DOCX, size limits), download authorization |
| `test_admin.py` | Admin tests: recruiter/opportunity approval, user suspension, audit logging, analytics, reopen fix |
| `smoke_pages.py` | **Page smoke test.** Renders every page for every role to verify no template errors |

---

## 4. What You Need to Change for Production

### CRITICAL — Must Change

| What | Where | Why |
|------|-------|-----|
| `SECRET_KEY` | `.env` | The default `dev-secret-change-me` is insecure. Generate a random 64-char hex string. |
| `DATABASE_URL` | `.env` | Switch from SQLite to PostgreSQL for production. SQLite doesn't handle concurrent writes well. |
| `SESSION_COOKIE_SECURE` | `.env` | Set to `true` so session cookies are only sent over HTTPS. |
| `MAIL_MODE` | `.env` | Change from `console` to `smtp` so emails are actually sent. |
| `SMTP_*` settings | `.env` | Configure real SMTP credentials (Gmail app password, SendGrid, etc.) |
| `FLASK_DEBUG` | `.env` or environment | Make sure this is NOT `1` in production (Gunicorn doesn't use it, but be safe). |

### RECOMMENDED — Should Change

| What | Where | Why |
|------|-------|-----|
| Add `gunicorn` | `requirements.txt` | Production WSGI server. Add `gunicorn>=21.0` to requirements.txt. |
| Add `psycopg2-binary` | `requirements.txt` | PostgreSQL driver. Add `psycopg2-binary>=2.9` to requirements.txt for PostgreSQL support. |
| File storage | `app/services/storage_service.py` | Currently stores files in `instance/uploads/`. For production with multiple workers or containers, consider S3/R2/GCS. |
| Rate limiter | `app/middleware/security.py` | In-memory rate limiter resets on restart. For production, use Redis-backed rate limiting. |

### OPTIONAL — Nice to Have

| What | Where | Why |
|------|-------|-----|
| HTML email templates | `app/services/digest_service.py` | Currently sends plain-text digests. Could add HTML templates for richer emails. |
| Background scheduler | `app/cli.py` | Weekly digest is triggered manually via CLI. Could add APScheduler for auto-sending. |
| PDF.js viewer | `app/templates/student/resume_preview.html` | Currently uses `<object>` tag for PDF preview. PDF.js would add zoom/search. |
| Logging | `app/__init__.py` | Add structured logging (JSON format) for production monitoring. |

---

## 5. Troubleshooting

### "Application error" on Render/Railway
- Check build logs for missing dependencies
- Make sure `DATABASE_URL` is set correctly
- Verify `flask --app run db upgrade` runs during build

### "OperationalError: could not connect to server"
- Your `DATABASE_URL` is wrong or the database server is down
- For PostgreSQL, make sure you're using `postgresql+psycopg2://` (not `postgres://`)
- Some providers require SSL: add `?sslmode=require` to the URL

### "ProgrammingError: relation already exists"
- Migrations may have already run. This is usually fine.
- If persistent: `flask --app run db stamp head` to mark migrations as applied

### Emails not sending
- Set `MAIL_MODE=smtp` in `.env`
- For Gmail: enable 2FA, create an App Password, use that as `SMTP_PASSWORD`
- Check spam folder
- For production: use SendGrid, Mailgun, or AWS SES instead of Gmail

### Static files not loading (CSS/JS)
- Make sure Nginx is serving `/static/` directly (see Nginx config above)
- Run `flask --app run collectstatic` if using WhiteNoise

### "Secret key not set" warning
- Make sure `SECRET_KEY` is set in your `.env` file
- Generate one: `python -c "import secrets; print(secrets.token_hex(32))"`

---

## Quick Reference — Common Commands

```bash
# Development
flask --app run run                          # Start dev server
flask --app run seed-demo --reset            # Reset and seed demo data
flask --app run db upgrade                   # Apply database migrations
flask --app run db migrate -m "description"  # Generate new migration
python -m pytest -q                          # Run tests
python tests/smoke_pages.py                  # Smoke test all pages

# Production (with Gunicorn)
gunicorn run:app --bind 0.0.0.0:8000 --workers 4

# Database management
flask --app run db downgrade                 # Rollback last migration
flask --app run db history                   # View migration history
flask --app run db current                   # See current migration version
```

---

**Built with ❤️ using Flask + SQLAlchemy + Alembic + Jinja2 + Vanilla JS**
