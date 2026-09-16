# 📈 Development Progress — Campus Internship & Placement Portal (V1)

> Live project log tracking what was decided, built, fixed and verified.
> Companion to `README.md` (how to run) — this file documents *how the build went*.

**Status:** ✅ MVP complete · 71/71 tests passing · all pages rendering · server running on `http://127.0.0.1:5000`

---

## 1. Requirements (from PRD + TRD)

The project implements the **Campus Internship & Placement Portal V1**:

- **PRD** — a controlled recruitment marketplace: students discover/apply/track
  opportunities, recruiters get approved and publish/manage them, placement
  officers approve, monitor and analyze the process. Fixed application statuses,
  no duplicate applications, strict role isolation.
- **TRD** — Python + Flask modular monolith, SQLAlchemy + Alembic, REST API at
  `/api/v1`, server-side sessions, Werkzeug password hashing, abstracted email
  and file storage, security-first backend.

**Decisions confirmed with the user before building:**
| Question | Chosen option |
|---|---|
| Email in development | **Dev mailbox + SMTP support** (in-app `/dev/mailbox` in dev, real SMTP in prod) |
| Database | **SQLite** for local dev (PostgreSQL-ready via SQLAlchemy) |
| Frontend | **Vanilla per TRD** (Jinja2 server-rendered pages + REST API for actions) |

---

## 2. Tech Stack (implemented)

| Layer | Technology |
|---|---|
| Backend | Python 3.13 + Flask 3.0.3 |
| ORM / DB | SQLAlchemy 2.0 · SQLite (dev) / PostgreSQL (prod via `DATABASE_URL`) |
| Migrations | Alembic via Flask-Migrate |
| Auth | Server-side sessions (signed cookies, `HttpOnly`, `SameSite=Lax`) |
| Password hashing | Werkzeug (`generate_password_hash`) |
| Email | Abstraction: dev mailbox (`MAIL_MODE=console`) ↔ SMTP (`MAIL_MODE=smtp`) |
| File storage | Abstraction: local filesystem (swap for S3/R2/GCS later) |
| PDF export | ReportLab 4.0+ |
| Frontend | Jinja2 templates + custom CSS design system + vanilla JS (no framework) |

---

## 3. Database Schema (13 tables, all migrated)

`users` · `colleges` · `student_profiles` · `recruiter_profiles` · `resumes` ·
`opportunities` · `applications` · `interviews` · `notifications` ·
`auth_tokens` (single-use verification/reset tokens) ·
`audit_logs` (admin action trace) · `dev_mailbox` (dev-only email capture) ·
`recruiter_profiles.weekly_digest_enabled` (added in this session)

Key constraints & rules enforced at the DB level:
- `applications`: `UNIQUE(student_id, opportunity_id)` → duplicate applications are impossible even under race conditions
- `auth_tokens`: hashed tokens, expiry, single-use (atomic `UPDATE … WHERE used_at IS NULL`)
- `student_profiles.user_id` / `recruiter_profiles.user_id`: unique (one profile per user)
- `recruiter_profiles.weekly_digest_enabled`: Boolean, default True (added via migration `5cb6c764c72e`)

---

## 4. Project Structure

```
campus-placement-portal/
├── app/
│   ├── __init__.py          # App factory, error handlers, template globals, CLI
│   ├── config.py            # Env-driven config (SQLite/Postgres, mail, storage, CSRF, rate limits)
│   ├── cli.py               # `flask seed-demo` + `flask send-weekly-digest`
│   ├── models/              # 13 models + central enums (roles, statuses, state machine)
│   ├── routes/              # Blueprints: auth, students, recruiters, admin, shared (pages + REST API)
│   ├── services/            # auth, application, interview, notification, analytics,
│   │                        #   analytics_export, recruiter_analytics, digest, admin, storage
│   ├── middleware/          # session auth, role permissions (+verification gate), CSRF, rate limiting
│   ├── utils/               # ApiError hierarchy, validators, token hashing, email abstraction, API envelope
│   ├── templates/           # 35+ Jinja2 pages + macros
│   └── static/              # style.css (design system + dashboard) + app.js (vanilla JS)
├── migrations/              # Alembic — 2 migrations (initial schema + weekly_digest_enabled)
├── tests/                   # 71 pytest tests + smoke_pages.py
├── run.py                   # Entry point
├── requirements.txt / requirements-dev.txt
├── .env.example / .gitignore
├── dashboard.png            # Design reference image
└── README.md / progress.md
```

**Architecture rule (from TRD):** *Routes handle HTTP · Services handle business
logic · Models handle database structure.*

---

## 5. Feature Status vs PRD Acceptance Criteria

### Student ✅
- [x] Register + email verification (token link, single-use, expires in 24h)
- [x] Complete profile (name, phone, college, degree, department, batch, skills) + profile-completeness meter
- [x] Upload/delete multiple resumes (PDF/DOC/DOCX, ≤5 MB, magic-byte check)
- [x] **Resume preview** — dedicated preview page renders PDFs inline via `<object>` tag; DOC/DOCX shows download fallback
- [x] Browse + search/filter opportunities (title/company/skills, type, work mode, location, skill)
- [x] Apply with a chosen resume; **cannot apply twice** (409), **cannot apply after deadline**, without resume, or to unapproved postings; batch-year eligibility check
- [x] Apply modal shows **Resume preview button** so students can review before attaching
- [x] Track applications (Applied → Under Review → Shortlisted → Interview Scheduled → Selected/Rejected)
- [x] View interview details (date/time/mode/location/meeting details)
- [x] Notifications (bell dropdown + full page + mark read/all)

### Recruiter ✅
- [x] Register + company profile + email verification
- [x] **Admin approval required** before any posting is allowed (PENDING → APPROVED/REJECTED)
- [x] Create/edit internship & full-time postings (draft → submit → admin review)
- [x] **Editing an approved posting returns it to admin review** (PRD edge case)
- [x] View applicants (name, college, degree, dept, batch, skills, resume, status) + download resumes
- [x] Update application status via **validated state machine** (invalid transitions → 409)
- [x] Schedule / reschedule / cancel / complete interviews; **overlap warning** shown to recruiter, student notified
- [x] Close own live postings
- [x] **Analytics dashboard** — UX Planet-inspired redesign with sidebar, KPI cards, area/donut charts, bar charts, data tables
- [x] **Date-range filtering** — presets (All time, This month, This semester, This year) + custom date range
- [x] **CSV/PDF export** — downloadable reports with all analytics data, respects date range
- [x] **Per-opportunity drill-down** — click any opportunity to see applicant breakdown by college, department, graduation year, status funnel, and applicant table
- [x] **Weekly email digest** — opt-in/opt-out toggle, plain-text email with stats summary, peer comparison, sent via CLI or test button
- [x] **Test digest** — "Send test digest" button on analytics page to preview the email

### Admin ✅
- [x] Dashboard with live stat cards + pending recruiter/posting queues
- [x] Approve/reject recruiters & postings (notifies the recruiter, writes audit log)
- [x] Manage students/recruiters: search, suspend/reactivate (suspension blocks login instantly)
- [x] Monitor all applications & interviews
- [x] Analytics: totals, selection rate donut, internship vs full-time, department-wise apps/selections, company-wise hiring, monthly activity chart, top opportunities
- [x] Audit log page

### Security (all tested) ✅
- Student can never reach recruiter/admin APIs (403) or admin pages (redirect to 403 page)
- Recruiters get **404** (not 403) when touching another recruiter's postings/applicants/interviews — no data probing
- Unverified accounts blocked from all protected surfaces (API 403 `VERIFICATION_REQUIRED`, pages redirect to `/verify`)
- Resumes not public — downloads require ownership/recruiter-of-application/admin
- CSRF on every state-changing request · rate-limited login/register/forgot/resend
- No plain-text passwords; suspended users rejected at login and on active sessions

---

## 6. Build Milestones (chronological)

### Phase 1 — Core MVP (original build)
1. **Setup** — venv, Flask/SQLAlchemy/Flask-Migrate/pytest installed.
2. **Core scaffold** — config, extensions, app factory, error handling.
3. **Models + enums** — full schema incl. `auth_tokens` + application state machine.
4. **Utils & services** — errors, validators, tokens, email abstraction, storage;
   auth/applications/interviews/notifications/analytics/admin services.
5. **Middleware** — session auth, `require_role` (role + verification), CSRF, rate limiting.
6. **Routes** — all pages + full REST API (`/api/v1`), ~90 routes.
7. **Alembic** — initial migration generated & applied (12 tables).
8. **Frontend** — design system CSS, vanilla JS, 30+ templates across all roles.
9. **Seed data** — 10 users, 8 opportunities, 8 applications, 3 interviews; demo accounts.
10. **Tests** — 71 tests; iterated to 100% green.
11. **Smoke test** — every page for every role renders (32/32 OK).
12. **Code review + hardening** — state machine fix, atomic tokens, N+1 fix, magic-byte validation, etc.

### Phase 2 — Resume Preview & Bug Fixes (this session)
13. **Resume preview** — dedicated preview page with `<object>` tag for PDFs, download fallback for DOC/DOCX.
14. **Preview endpoint** — `GET /api/v1/resumes/<id>/preview` (serves file inline, not as attachment).
15. **Preview buttons** — added to profile page resume list + apply modal.
16. **Opportunity publishing bug fix** — `api()` and `toast()` were scoped inside IIFE in `app.js`, invisible to inline scripts; exposed on `window`.

### Phase 3 — Recruiter Analytics Dashboard
17. **Analytics service** — `recruiter_analytics_service.py` with date-range filtering, peer benchmarks.
18. **Analytics routes** — page + API + CSV export + PDF export.
19. **Analytics template** — initial version with stat cards, bar charts, donut, funnel, peer comparison.
20. **CSV export** — `analytics_export.py` with multi-section CSV generation.
21. **PDF export** — ReportLab-based PDF with styled tables, section headers, date range.
22. **Date-range filtering** — service accepts `start_date`/`end_date` params; template has preset buttons + custom date inputs.
23. **Per-opportunity drill-down** — `opportunity_analytics()` service function; dedicated page with applicant breakdown by college, department, graduation year, status funnel, applicant table.
24. **Analytics nav link** — added "Analytics" tab to recruiter navbar.

### Phase 4 — Weekly Email Digest
25. **Digest service** — `digest_service.py` builds plain-text email with stats, top opportunities, college/department breakdown, peer comparison.
26. **CLI command** — `flask send-weekly-digest` sends to all opted-in recruiters.
27. **Digest preference** — `weekly_digest_enabled` column on `recruiter_profiles` (migration `5cb6c764c72e`).
28. **Toggle UI** — switch on recruiter profile page with real-time API update.
29. **Test digest** — button on analytics page sends a preview email.
30. **Unicode fix** — removed em-dash/emoji characters that broke cp1252 encoding on Windows.

### Phase 5 — Dashboard Redesign
31. **CSV export fix** — export `<a>` buttons had no `href`; added server-side `url_for` so they work without JS.
32. **UX Planet redesign** — complete rewrite of analytics template with:
    - Dark sidebar navigation with icons
    - KPI cards with trend indicators (period-over-period deltas)
    - SVG area chart for monthly application trend
    - SVG donut chart for selection rate
    - Horizontal bar charts for opportunity, college, department breakdowns
    - Application status funnel visualization
    - Side-by-side peer comparison cards
    - Responsive layout (sidebar hidden on mobile)
33. **Monthly trend data** — `_monthly_trend()` in analytics service (last 6 months).
34. **Period-over-period trends** — `_period_trends()` computes deltas for KPI cards.

---

## 7. Bugs Found & Fixed

| # | Issue | Fix |
|---|---|---|
| 1 | `auth_rate_limit` read config at import time (outside app context) → crash | Defer config lookup to request time |
| 2 | Ambiguous FK on `RecruiterProfile` (user_id + approved_by) | Explicit `foreign_keys` on relationships |
| 3 | `click.echo` with emoji crashed Windows console (cp1252) | Removed emojis from CLI output |
| 4 | Timezone-aware vs naive datetime comparison on token expiry (SQLite) | `utcnow()` returns naive UTC consistently |
| 5 | Resume upload rejected every file (`.pdf` vs `pdf` key mismatch) | Normalize extension key |
| 6 | `re.findall` with capturing group returned `19`/`20` instead of years → false "not eligible" | Non-capturing group in year regex |
| 7 | Test helpers passed ORM instances across app contexts → `DetachedInstanceError` | Helpers return ids; re-query in context |
| 8 | Analytics JSON failed on SQLAlchemy `Row` objects | Convert to plain tuples |
| 9 | Jinja macros couldn't see globals (`status_label` undefined) | Import macros `with context` (20 templates) |
| 10 | Analytics template unpacked tuples incorrectly | Fixed unpacking |
| 11 | Navbar brand link went to `/` for recruiters/admins | Role-aware dashboard links |
| 12 | Recruiter opportunity tabs didn't filter | Added status filter to the page route |
| 13 | **Modal overlay couldn't be closed** (CSS `display:flex` overrode the `hidden` attribute) | `[hidden] { display:none !important; }` |
| 14 | Recruiters could PATCH an application straight to `INTERVIEW_SCHEDULED` with no interview | Removed from recruiter transitions — only the interview transaction sets it |
| 15 | Token single-use had a TOCTOU race | Atomic `UPDATE … WHERE used_at IS NULL` |
| 16 | Unverified users could read `/notifications` | Gate shared routes on verification too |
| 17 | N+1 on admin students page (lazy count per row) | Single grouped count query |
| 18 | Rate limiter memory growth | Periodic stale-key cleanup |
| 19 | Uploads only checked extension, not content | Magic-byte sniffing (%PDF, OLE, ZIP) |
| 20 | Seed resumes were fake text files with `.pdf` | Generate a minimal *valid* PDF with a correct xref table |
| 21 | **`api()` and `toast()` not accessible from inline scripts** — opportunity form couldn't save | Exposed `window.api` and `window.toast` from `app.js` IIFE |
| 22 | **Resume preview showed "preview failed"** — iframe approach had MIME/security issues | Replaced with dedicated preview page using `<object>` tag |
| 23 | **CSV export button not working** — `<a>` tags had no `href`, JS `setAttribute` unreliable | Added server-side `url_for` in template |
| 24 | **Analytics template Jinja error** — `comparisons` tuple had string values that couldn't be divided | Separated display values from numeric values |
| 25 | **SQLAlchemy warning** — implicit scalar subquery coercion | Used `.label()` + `.c.cnt` for proper column reference |
| 26 | **Digest email UnicodeEncodeError** — em-dash/emoji broke cp1252 on Windows | Replaced with ASCII-safe characters |
| 27 | **SQLite migration error** — NOT NULL column without server_default | Added `server_default=sa.text('1')` |

---

## 8. New Files Added (this session)

| File | Purpose |
|---|---|
| `app/templates/student/resume_preview.html` | Standalone resume preview page (PDF inline, DOC/DOCX fallback) |
| `app/routes/shared.py` | Added `GET /api/v1/resumes/<id>/preview` + `GET /resumes/<id>/preview` |
| `app/services/recruiter_analytics_service.py` | Recruiter-scoped analytics with date filtering, peer benchmarks, monthly trends, period deltas |
| `app/services/analytics_export.py` | CSV + PDF generation for analytics reports |
| `app/templates/recruiter/analytics.html` | UX Planet-inspired analytics dashboard (rewritten) |
| `app/templates/recruiter/opportunity_analytics.html` | Per-opportunity drill-down analytics page |
| `app/services/digest_service.py` | Weekly email digest generation + sending |
| `app/templates/student/resume_preview.html` | Resume preview page |
| `migrations/versions/5cb6c764c72e_*.py` | Migration for `weekly_digest_enabled` column |

---

## 9. Verification Summary

- **71/71 pytest tests pass** — auth, permissions/role isolation, applications
  (duplicates, deadlines, eligibility, state machine), interviews (rules,
  cancellation, conflicts, ownership), resumes (upload validation + download
  authorization), admin (approvals, suspensions, audit, analytics).
- **32/32 page smoke checks** — every page of every role returns 200 (with
  correct CSRF + session handling); role guards return the expected 302/403.
- **Export verification** — CSV (200, text/csv, valid content) and PDF (200, application/pdf, %PDF- header) both confirmed.
- **Digest verification** — toggle (200), test digest email sent to dev mailbox with correct content.
- **Date-range verification** — analytics page, CSV export, PDF export all respect `start_date`/`end_date` params.
- **Drill-down verification** — `GET /recruiter/analytics/opportunities/1` returns 200 with full applicant breakdown.
- Test commands:
  ```bash
  .venv/Scripts/python -m pytest -q
  .venv/Scripts/python tests/smoke_pages.py
  ```

---

## 10. How to Run (short version)

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt
.venv/Scripts/flask --app run db upgrade
.venv/Scripts/flask --app run seed-demo --reset   # optional demo data
.venv/Scripts/flask --app run run                 # → http://127.0.0.1:5000
```

**Demo accounts** (after seeding):
- Admin: `admin@college.edu` / `Admin@123`
- Student: `student1@college.edu` / `Student@123`
- Recruiter: `techcorp@company.com` / `Recruiter@123`

Verification/password-reset emails land in the **Dev Mailbox** at `/dev/mailbox`
while `MAIL_MODE=console`.

**Send weekly digest manually:**
```bash
.venv/Scripts/flask --app run send-weekly-digest
```

---

## 11. Known Limitations / Out of V1 Scope

- Eligibility check is a pragmatic heuristic (batch-year comparison) — free-text
  criteria beyond years are not machine-evaluated.
- In-memory rate limiter is per-process (fine for single-instance V1).
- MIME sniffing is best-effort (magic bytes), not a full document parser.
- Browser automation (browser-use agent) was unreliable in this environment, so
  visual QA was done via scripted page rendering rather than a live browser.
- Per PRD: no AI features, chat, calendar/video integration, payroll, complex
  scheduling engine, or mobile app — all deferred to future versions.
- DOC/DOCX files cannot be previewed inline in browsers — only PDFs render natively.
- Weekly digest uses plain-text email (no HTML template yet).
- No background scheduler thread — digest is triggered via CLI command (cron or manual).

## 12. Suggested Next Steps

1. Run the full demo flow as each role (student applies → recruiter shortlists
   → schedules interview → selects).
2. Add PostgreSQL + SMTP config and deploy with Gunicorn/Nginx.
3. Extend tests (e.g., analytics edge cases, CSRF failure paths, rate-limit
   enforcement).
4. Optional UX additions: interview reminders, resume default selection,
   export/print of placement reports.
5. **From this session:**
   - Add HTML email templates for richer digest emails.
   - Add background scheduler thread for auto-sending digests.
   - Add PDF.js viewer for richer PDF preview with zoom/search.
   - Add date-range filtering to admin analytics page.
   - Add per-opportunity CSV/PDF export from the drill-down page.
