# Technical Requirements Document (TRD)

## Campus Internship & Placement Portal — V1

**Document Version:** 1.0  
**Based On:** Product Requirements Document V1  
**Architecture Style:** Modular Monolith  
**Backend:** Python + Flask  
**Frontend:** HTML, CSS, JavaScript  
**Database:** PostgreSQL  
**ORM:** SQLAlchemy  
**Database Migrations:** Alembic  
**API Style:** REST

---

# 1. Technical Objectives

The technical architecture must:

1. Support the complete V1 student → application → interview workflow.
2. Enforce strict separation between Student, Recruiter, and Admin permissions.
3. Protect student information and resumes.
4. Prevent duplicate applications and invalid state changes.
5. Keep the codebase simple enough for a small development team.
6. Allow future expansion without requiring a complete rewrite.
7. Avoid infrastructure that is unnecessary for V1.

The PRD specifically requires backend authorization, backend validation, transactional database operations, secure resume handling, and prevention of duplicate applications.

---

# 2. Recommended Technology Stack

| Layer | Technology | Reason |
|---|---|---|
| Frontend | HTML | Simple, stable |
| Styling | CSS | No unnecessary UI framework |
| Client-side logic | Vanilla JavaScript | Enough for V1 |
| Backend | Python + Flask | Lightweight and modular |
| API | REST | Simple and widely supported |
| ORM | SQLAlchemy | Database abstraction and safer queries |
| Database | PostgreSQL | Reliable relational database |
| Migrations | Alembic | Controlled schema changes |
| Authentication | Flask session + secure cookies | Appropriate for browser-based application |
| Password hashing | Werkzeug | Mature Flask ecosystem |
| Email | SMTP/email provider | Verification and notifications |
| Resume storage | Object/file storage | Keeps files separate from relational data |
| Web server | Gunicorn | Production Python application server |
| Reverse proxy | Nginx | HTTPS, static files, request handling |

### Local development

For development, SQLite can optionally be used because it is simple to install.

However:

> **Production should use PostgreSQL.**

The application should not depend on SQLite-specific behavior.

---

# 3. System Architecture Overview

## 3.1 Architecture Style

Use a **modular monolithic architecture**.

Do not start with microservices.

```text
                         ┌─────────────────────┐
                         │       Browser       │
                         │ HTML/CSS/JavaScript │
                         └──────────┬──────────┘
                                    │ HTTPS
                                    ▼
                         ┌─────────────────────┐
                         │       Nginx         │
                         │ Reverse Proxy       │
                         └──────────┬──────────┘
                                    │
                                    ▼
                  ┌─────────────────────────────────┐
                  │          Flask Application      │
                  │                                 │
                  │ ┌─────────┐ ┌───────────────┐  │
                  │ │  Auth   │ │    Student    │  │
                  │ └─────────┘ └───────────────┘  │
                  │                                 │
                  │ ┌─────────┐ ┌───────────────┐  │
                  │ │Recruiter│ │     Admin     │  │
                  │ └─────────┘ └───────────────┘  │
                  │                                 │
                  │ ┌─────────────┐ ┌───────────┐  │
                  │ │Applications │ │ Interviews│  │
                  │ └─────────────┘ └───────────┘  │
                  │                                 │
                  │ ┌──────────────┐ ┌──────────┐  │
                  │ │Notifications │ │Analytics │  │
                  │ └──────────────┘ └──────────┘  │
                  └──────────────┬──────────────────┘
                                 │
                   ┌─────────────┴──────────────┐
                   │                            │
                   ▼                            ▼
          ┌─────────────────┐          ┌─────────────────┐
          │   PostgreSQL    │          │ Resume Storage  │
          │    Database     │          │ Files / Object  │
          └─────────────────┘          └─────────────────┘
                                              
                                 │
                                 ▼
                         ┌─────────────────┐
                         │ Email Provider  │
                         └─────────────────┘
```

---

# 4. Why a Modular Monolith?

The V1 has a relatively small number of core domains:

- Authentication
- Students
- Recruiters
- Opportunities
- Applications
- Interviews
- Notifications
- Analytics

These domains can live inside one Flask application while remaining logically separated.

### Benefits

- Easier development
- Easier debugging
- Simple deployment
- One database
- Lower hosting cost
- Fewer failure points
- Easier local development
- Easy database transactions

### Avoid initially

Do not introduce:

- Microservices
- Kubernetes
- Redis
- Kafka
- RabbitMQ
- Elasticsearch
- GraphQL
- Separate authentication service
- Separate analytics service

Those tools solve problems that the V1 does not currently have.

---

# 5. Backend Project Structure

Recommended structure:

```text
campus_portal/
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── student.py
│   │   ├── recruiter.py
│   │   ├── college.py
│   │   ├── opportunity.py
│   │   ├── application.py
│   │   ├── interview.py
│   │   ├── notification.py
│   │   └── resume.py
│   │
│   ├── routes/
│   │   ├── auth.py
│   │   ├── students.py
│   │   ├── recruiters.py
│   │   ├── opportunities.py
│   │   ├── applications.py
│   │   ├── interviews.py
│   │   ├── notifications.py
│   │   └── admin.py
│   │
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── application_service.py
│   │   ├── interview_service.py
│   │   ├── notification_service.py
│   │   └── analytics_service.py
│   │
│   ├── middleware/
│   │   ├── auth.py
│   │   └── permissions.py
│   │
│   ├── utils/
│   │   ├── validators.py
│   │   ├── email.py
│   │   └── storage.py
│   │
│   └── templates/
│
├── migrations/
│
├── tests/
│
├── run.py
├── requirements.txt
└── .env
```

The important architectural rule is:

> **Routes handle HTTP. Services handle business logic. Models handle database structure.**

Do not put the entire application inside route functions.

---

# 6. Frontend Responsibilities

The frontend is responsible for presentation and user interaction.

## 6.1 Authentication UI

Pages:

- Registration
- Login
- Email verification
- Forgot password
- Reset password

The frontend should never decide whether a user is actually authorized.

For example:

```text
Frontend:
"Show admin dashboard if user.role == admin"

Backend:
"Verify that the authenticated user actually has admin permission."
```

The backend is the security boundary.

---

# 7. Student Frontend

Required pages:

```text
/student/dashboard
/student/profile
/student/opportunities
/student/opportunities/<id>
/student/applications
/student/interviews
```

### Responsibilities

- Display opportunities
- Search/filter opportunities
- Display application status
- Submit applications
- Upload resumes
- Display interviews
- Display notifications
- Validate basic form input

The frontend should not be trusted for:

- Eligibility
- Application deadlines
- User permissions
- Duplicate application prevention

Those checks must happen on the backend.

---

# 8. Recruiter Frontend

Required pages:

```text
/recruiter/dashboard
/recruiter/profile
/recruiter/opportunities
/recruiter/opportunities/create
/recruiter/opportunities/<id>
/recruiter/opportunities/<id>/applicants
/recruiter/interviews
```

### Responsibilities

- Display recruiter approval status
- Create/edit postings
- Display posting status
- Display applicants
- Update application status
- Schedule interviews
- Display recruitment activity

---

# 9. Admin Frontend

Required pages:

```text
/admin/dashboard
/admin/students
/admin/recruiters
/admin/recruiters/pending
/admin/opportunities
/admin/opportunities/pending
/admin/applications
/admin/interviews
/admin/analytics
```

### Responsibilities

- Display pending approvals
- Approve/reject recruiters
- Approve/reject opportunities
- Monitor applications
- Monitor interviews
- Display analytics
- Manage users

---

# 10. Backend Responsibilities

The backend is the source of truth for:

- Authentication
- Authorization
- Business rules
- Database operations
- Application state transitions
- Recruiter approval
- Opportunity approval
- Interview scheduling
- Notification triggering
- Resume access
- Analytics calculations
- Input validation

---

# 11. Business Rules

These rules must be enforced server-side.

## BR-01 Recruiter Approval

```text
Recruiter registered
        ↓
Pending
        ↓
Admin approval
        ↓
Approved
```

Only approved recruiters can submit/publish opportunities.

This is a core V1 requirement from the PRD.

---

## BR-02 Opportunity Approval

```text
DRAFT
  ↓
SUBMITTED
  ↓
PENDING_REVIEW
  ↓
APPROVED → PUBLISHED
     ↓
  REJECTED
```

A rejected opportunity can be edited and resubmitted.

---

# 12. Application State Machine

Application status should be represented using a fixed enum.

```text
APPLIED
   ↓
UNDER_REVIEW
   ↓
SHORTLISTED
   ↓
INTERVIEW_SCHEDULED
   ↓
SELECTED
```

At appropriate points:

```text
APPLIED ───────────────► REJECTED
UNDER_REVIEW ─────────► REJECTED
SHORTLISTED ──────────► REJECTED
INTERVIEW_SCHEDULED ──► REJECTED
```

The PRD explicitly defines these fixed application statuses.

The backend should reject invalid transitions.

For example:

```text
SELECTED → APPLIED
```

should not be allowed.

---

# 13. Database Schema Proposal

Use a relational schema.

## 13.1 users

```text
users
--------------------------------
id                PK
email             UNIQUE
password_hash
role
is_verified
is_active
created_at
updated_at
```

### role

```text
STUDENT
RECRUITER
ADMIN
```

---

# 14. colleges

```text
colleges
--------------------------------
id                PK
name
code
created_at
```

A college should have its own table rather than storing the college name repeatedly in student records.

This also provides a foundation for the PRD's multi-college requirement.

---

# 15. student_profiles

```text
student_profiles
--------------------------------
id                PK
user_id           FK → users.id
college_id        FK → colleges.id
full_name
phone
degree
department
graduation_year
skills
created_at
updated_at
```

### Constraints

```text
user_id UNIQUE
```

One user should have one student profile.

---

# 16. recruiter_profiles

```text
recruiter_profiles
--------------------------------
id                PK
user_id           FK → users.id
company_name
company_description
company_email
website
contact_person
contact_phone
approval_status
approved_at
approved_by       FK → users.id
created_at
updated_at
```

### approval_status

```text
PENDING
APPROVED
REJECTED
```

---

# 17. resumes

The PRD requires resume upload and secure resume access.

Use a separate resume table:

```text
resumes
--------------------------------
id                PK
student_id        FK → student_profiles.id
file_name
storage_key
file_type
file_size
is_active
uploaded_at
```

### Important

Do **not** store the actual PDF binary inside PostgreSQL unless there is a specific reason.

Store:

- Metadata in SQL
- Actual file in file/object storage

Example:

```text
Database:
storage_key = resumes/student_123/resume_456.pdf

Storage:
actual PDF file
```

---

# 18. opportunities

```text
opportunities
--------------------------------
id                PK
recruiter_id      FK
title
type
description
responsibilities
required_skills
eligibility
location
work_mode
salary_or_stipend
application_deadline
status
created_at
updated_at
published_at
```

### type

```text
INTERNSHIP
FULL_TIME
```

### status

```text
DRAFT
PENDING_REVIEW
APPROVED
PUBLISHED
REJECTED
CLOSED
```

---

# 19. applications

This is one of the most important tables.

```text
applications
--------------------------------
id                PK
student_id        FK
opportunity_id    FK
resume_id         FK
status
applied_at
updated_at
```

### Critical constraint

```text
UNIQUE(student_id, opportunity_id)
```

This is more reliable than checking only in application code.

It guarantees that two simultaneous requests cannot create duplicate applications.

The PRD explicitly requires duplicate applications to be prevented.

---

# 20. interviews

```text
interviews
--------------------------------
id                PK
application_id    FK
scheduled_date
scheduled_time
mode
location
meeting_details
additional_instructions
status
created_at
updated_at
```

### status

```text
SCHEDULED
UPDATED
CANCELLED
COMPLETED
```

V1 does not need a complex scheduling engine, which matches the PRD's explicit scope.

---

# 21. notifications

```text
notifications
--------------------------------
id                PK
user_id           FK
type
title
message
is_read
created_at
```

Possible notification types:

```text
EMAIL_VERIFICATION
APPLICATION_SUBMITTED
APPLICATION_STATUS_CHANGED
INTERVIEW_SCHEDULED
INTERVIEW_UPDATED
INTERVIEW_CANCELLED
RECRUITER_APPROVED
RECRUITER_REJECTED
OPPORTUNITY_APPROVED
OPPORTUNITY_REJECTED
NEW_APPLICATION
```

---

# 22. Recommended Relationships

```text
User
 │
 ├────────────── StudentProfile
 │                       │
 │                       ├──── Resume
 │                       │
 │                       └──── Application
 │
 ├────────────── RecruiterProfile
 │                       │
 │                       └──── Opportunity
 │                                  │
 │                                  └──── Application
 │                                             │
 │                                             └──── Interview
 │
 └────────────── Admin
```

---

# 23. Database Indexes

Do not blindly index every column.

Initial indexes should include:

```text
users.email
users.role

student_profiles.college_id
student_profiles.department
student_profiles.graduation_year

opportunities.recruiter_id
opportunities.status
opportunities.type
opportunities.application_deadline

applications.student_id
applications.opportunity_id
applications.status

interviews.application_id
interviews.scheduled_date

notifications.user_id
notifications.is_read
```

For opportunity search, start with normal database queries.

Only introduce a dedicated search engine if real usage demonstrates that PostgreSQL search is insufficient.

---

# 24. API Structure

Use RESTful endpoints.

Base:

```text
/api/v1
```

Versioning from the beginning avoids painful API changes later.

---

# 25. Authentication APIs

```text
POST /api/v1/auth/register/student
POST /api/v1/auth/register/recruiter

POST /api/v1/auth/login
POST /api/v1/auth/logout

GET  /api/v1/auth/verify-email
POST /api/v1/auth/resend-verification

POST /api/v1/auth/forgot-password
POST /api/v1/auth/reset-password

GET /api/v1/auth/me
```

---

# 26. Student APIs

```text
GET   /api/v1/student/profile
PUT   /api/v1/student/profile

POST  /api/v1/student/resumes
GET   /api/v1/student/resumes
DELETE /api/v1/student/resumes/<id>

GET   /api/v1/student/opportunities
GET   /api/v1/student/opportunities/<id>

POST  /api/v1/student/opportunities/<id>/apply

GET   /api/v1/student/applications
GET   /api/v1/student/applications/<id>

GET   /api/v1/student/interviews
GET   /api/v1/student/notifications
```

---

# 27. Recruiter APIs

```text
GET   /api/v1/recruiter/profile
PUT   /api/v1/recruiter/profile

GET   /api/v1/recruiter/opportunities
POST  /api/v1/recruiter/opportunities

GET   /api/v1/recruiter/opportunities/<id>
PUT   /api/v1/recruiter/opportunities/<id>

POST  /api/v1/recruiter/opportunities/<id>/submit

GET   /api/v1/recruiter/opportunities/<id>/applications

GET   /api/v1/recruiter/applications/<id>

PATCH /api/v1/recruiter/applications/<id>/status

POST  /api/v1/recruiter/applications/<id>/interviews

PUT   /api/v1/recruiter/interviews/<id>
POST  /api/v1/recruiter/interviews/<id>/cancel

GET   /api/v1/recruiter/notifications
```

---

# 28. Admin APIs

```text
GET   /api/v1/admin/dashboard

GET   /api/v1/admin/students
GET   /api/v1/admin/recruiters
GET   /api/v1/admin/recruiters/pending

PATCH /api/v1/admin/recruiters/<id>/approve
PATCH /api/v1/admin/recruiters/<id>/reject

GET   /api/v1/admin/opportunities
GET   /api/v1/admin/opportunities/pending

PATCH /api/v1/admin/opportunities/<id>/approve
PATCH /api/v1/admin/opportunities/<id>/reject

GET   /api/v1/admin/applications
GET   /api/v1/admin/interviews

GET   /api/v1/admin/analytics
```

---

# 29. API Response Format

Use a consistent JSON structure.

### Success

```json
{
  "success": true,
  "data": {},
  "message": "Application submitted successfully"
}
```

### Error

```json
{
  "success": false,
  "error": {
    "code": "APPLICATION_DEADLINE_PASSED",
    "message": "The application deadline has passed."
  }
}
```

Avoid returning raw database errors to users.

---

# 30. HTTP Status Codes

Use standard status codes.

| Status | Use |
|---|---|
| 200 | Successful request |
| 201 | Resource created |
| 204 | Successful request with no response body |
| 400 | Invalid request |
| 401 | Not authenticated |
| 403 | Not authorized |
| 404 | Resource not found |
| 409 | Conflict |
| 422 | Validation failure |
| 500 | Unexpected server error |

Example:

A duplicate application should return:

```text
409 Conflict
```

rather than:

```text
500 Internal Server Error
```

---

# 31. Authentication Strategy

For this browser-based application, use **server-side sessions with secure cookies**.

Do not use JWT merely because it is popular.

## Login flow

```text
User
 ↓
POST /auth/login
 ↓
Backend validates credentials
 ↓
Session created
 ↓
Secure HTTP-only cookie
 ↓
Browser sends cookie automatically
 ↓
Backend identifies user
```

---

# 32. Password Security

Passwords must be hashed.

Never store:

```text
password = "mypassword123"
```

Store a password hash instead.

Use a mature password hashing implementation such as Werkzeug's password hashing utilities.

The PRD explicitly requires that passwords never be stored in plain text.

---

# 33. Session Security

Cookies should use:

```text
HttpOnly
Secure
SameSite=Lax
```

Where appropriate.

Additional protections:

- Session expiration
- Session regeneration after login
- Logout invalidation
- CSRF protection for state-changing browser requests

---

# 34. Authorization Strategy

Authentication answers:

> "Who are you?"

Authorization answers:

> "What are you allowed to do?"

Both are required.

Example:

```python
@require_role("ADMIN")
def approve_recruiter():
    ...
```

But role checking alone is not enough.

A recruiter request like:

```text
PUT /recruiter/opportunities/500
```

must also verify:

```text
opportunity.recruiter_id == current_user.recruiter_id
```

Otherwise a recruiter could modify another recruiter's opportunity simply by changing the ID.

This ownership check is essential because the PRD explicitly restricts recruiters to their own applicants and postings.

---

# 35. Email Verification

Registration flow:

```text
Register
   ↓
Create unverified account
   ↓
Generate verification token
   ↓
Send email
   ↓
User clicks verification link
   ↓
Backend validates token
   ↓
is_verified = true
```

Verification tokens should:

- Be random
- Expire
- Be single-use
- Not be predictable

---

# 36. Password Reset

Flow:

```text
Forgot Password
       ↓
Enter Email
       ↓
Generate Reset Token
       ↓
Send Email
       ↓
User Opens Link
       ↓
Set New Password
       ↓
Invalidate Token
```

Do not reveal whether an email exists in the system through the forgot-password response.

---

# 37. Resume Storage

Resume files are sensitive student data.

Do not expose them through:

```text
/uploads/resume123.pdf
```

with predictable public URLs.

Instead:

```text
Student
   ↓
Request Resume
   ↓
Backend Authorization
   ↓
Verify requester can access resume
   ↓
Return/download file
```

The PRD specifically requires resumes not to be publicly accessible through predictable URLs.

---

# 38. File Validation

Resume upload must validate:

- File extension
- MIME type
- File size
- Filename
- Upload success

Recommended V1:

```text
PDF
DOC
DOCX
```

The exact supported formats should be configured rather than hard-coded throughout the application.

Never trust the filename extension alone.

---

# 39. Notifications Architecture

For V1, keep notifications simple.

```text
Business Event
      ↓
Create Notification
      ↓
Send Email
```

Example:

```text
Recruiter changes application status
             ↓
      Application updated
             ↓
    Notification created
             ↓
       Email triggered
```

The database notification record provides an audit trail.

The email is the delivery mechanism.

---

# 40. Third-Party Dependencies

Keep external dependencies minimal.

## Required

### Email provider

Used for:

- Email verification
- Password reset
- Application updates
- Interview notifications
- Recruiter approval notifications

Possible implementations:

- SMTP
- Transactional email provider

The application should communicate through an internal email service abstraction:

```text
notification_service
       ↓
email_service
       ↓
SMTP / Email Provider
```

This allows the provider to be changed later without rewriting business logic.

---

# 41. Optional Storage Provider

Production resume storage can use an object-storage service.

Examples:

- Amazon S3
- Cloudflare R2
- Google Cloud Storage

Do not make the rest of the application depend directly on the provider.

Use:

```text
storage_service.upload()
storage_service.download()
storage_service.delete()
```

This keeps the application provider-independent.

For a student/development environment, local storage can be used initially.

---

# 42. Dependencies to Avoid in V1

Do not add these without a demonstrated requirement:

```text
Redis
Kafka
RabbitMQ
Elasticsearch
Kubernetes
Docker Swarm
GraphQL
Microservices
WebSockets
AI APIs
Payment gateways
Calendar APIs
Video conferencing APIs
```

The PRD explicitly excludes several of these feature areas from V1, including calendar integration, video interviews, AI functionality, and advanced analytics.

---

# 43. Scalability Strategy

The system should scale **vertically first, horizontally later**.

## Stage 1 — Initial deployment

```text
Nginx
   ↓
Flask/Gunicorn
   ↓
PostgreSQL
   ↓
File Storage
```

This is enough for initial college deployment.

---

# 44. Stage 2 — Increased Traffic

If traffic increases:

```text
                 ┌── Flask Instance 1
Nginx / LB ──────┼── Flask Instance 2
                 └── Flask Instance 3
                          │
                          ▼
                     PostgreSQL
```

The application should remain stateless at the server level so additional instances can be added later.

This is another reason not to store user session state in local server memory.

---

# 45. Database Scalability

PostgreSQL should be the central source of truth.

Initial optimization:

1. Correct relationships
2. Foreign keys
3. Unique constraints
4. Appropriate indexes
5. Pagination
6. Efficient queries
7. Avoid N+1 queries

Only consider database replication after actual traffic requires it.

---

# 46. Pagination

Do not return thousands of records in one API response.

For example:

```text
GET /api/v1/admin/applications?page=1&limit=25
```

Response:

```json
{
  "data": [],
  "pagination": {
    "page": 1,
    "limit": 25,
    "total": 250,
    "pages": 10
  }
}
```

Pagination should be used for:

- Opportunities
- Applications
- Students
- Recruiters
- Interviews
- Notifications

---

# 47. Search Strategy

V1 search should use PostgreSQL.

Search fields:

```text
Opportunity.title
Opportunity.company
Opportunity.required_skills
```

Start with:

```text
LIKE / ILIKE
```

or PostgreSQL's built-in text-search capabilities if required.

Do **not** introduce Elasticsearch initially.

If the system eventually contains millions of opportunities and search performance becomes a real problem, a dedicated search system can be introduced later.

---

# 48. Analytics Strategy

Do not create a separate analytics database for V1.

Use SQL queries against operational tables.

Examples:

```sql
SELECT COUNT(*) FROM users
WHERE role = 'STUDENT';
```

```sql
SELECT COUNT(*) FROM applications
WHERE status = 'SELECTED';
```

For more complex analytics, create optimized SQL queries or database views later.

The PRD explicitly asks only for basic analytics such as applications, interviews, selections, department-wise results, and company-wise hiring.

---

# 49. Transaction Requirements

Important operations must use database transactions.

## Application submission

```text
BEGIN TRANSACTION

1. Verify user
2. Verify opportunity
3. Verify deadline
4. Verify opportunity is open
5. Verify student eligibility
6. Verify resume
7. Create application

COMMIT
```

The database unique constraint prevents duplicate submissions.

---

# 50. Interview Scheduling Transaction

```text
BEGIN

1. Verify recruiter ownership
2. Verify application
3. Verify candidate is shortlisted
4. Create interview
5. Update application status
6. Create notification

COMMIT
```

If any critical operation fails:

```text
ROLLBACK
```

This prevents situations where an interview exists but the application status was never updated.

---

# 51. Error Handling

The backend should have centralized error handling.

Categories:

```text
ValidationError
AuthenticationError
AuthorizationError
NotFoundError
ConflictError
BusinessRuleError
DatabaseError
```

Example:

```text
Application deadline passed
        ↓
BusinessRuleError
        ↓
HTTP 409 / 422
        ↓
User-friendly message
```

Never expose:

- SQL errors
- Stack traces
- Database credentials
- Internal file paths
- Secret keys

to users.

---

# 52. Logging

Log important system events.

Examples:

```text
User registered
User logged in
Recruiter approved
Opportunity approved
Application submitted
Application status changed
Interview scheduled
Interview cancelled
```

Do not log:

- Passwords
- Session tokens
- Password reset tokens
- Private resume contents
- Sensitive authentication data

---

# 53. Auditability

Because admins control recruiter and opportunity approvals, important administrative actions should be traceable.

A lightweight audit table can be introduced:

```text
audit_logs
--------------------------------
id
user_id
action
entity_type
entity_id
metadata
created_at
```

Examples:

```text
ADMIN_APPROVED_RECRUITER
ADMIN_REJECTED_RECRUITER
ADMIN_APPROVED_OPPORTUNITY
ADMIN_REJECTED_OPPORTUNITY
ADMIN_SUSPENDED_USER
```

This is worth including because it supports the platform's administrative nature without creating a complicated event-sourcing system.

---

# 54. Security Requirements

Minimum security baseline:

### Authentication

- Secure password hashing
- Secure sessions
- Email verification
- Password reset tokens
- Session expiration

### Authorization

- Role-based authorization
- Resource ownership checks
- Admin-only operations

### Input

- Server-side validation
- Parameterized SQL through ORM
- File validation
- Request size limits

### Web security

- HTTPS
- CSRF protection
- Secure cookies
- XSS-safe template rendering
- Security headers
- Rate limiting on authentication endpoints

### File security

- Private resume storage
- File type validation
- File size limits
- Authorization before download

---

# 55. Rate Limiting

V1 does not need system-wide sophisticated rate limiting.

Apply it primarily to sensitive endpoints:

```text
/login
/register
/forgot-password
/resend-verification
```

This protects against:

- Brute-force login attempts
- Email abuse
- Automated registration
- Password reset abuse

---

# 56. Configuration Management

Secrets must not be stored in source code.

Use environment variables:

```text
DATABASE_URL
SECRET_KEY
MAIL_SERVER
MAIL_USERNAME
MAIL_PASSWORD
STORAGE_BUCKET
STORAGE_ACCESS_KEY
STORAGE_SECRET_KEY
```

Use a `.env` file locally.

Never commit `.env` to Git.

---

# 57. Database Migration Strategy

Use migrations from the beginning.

Example:

```text
Migration 001
    ↓
Create users
    ↓
Migration 002
    ↓
Create student_profiles
    ↓
Migration 003
    ↓
Create opportunities
```

Never manually modify production database tables.

Alembic should manage schema changes.

---

# 58. Testing Requirements

Testing should focus on business-critical behavior rather than chasing 100% code coverage.

## Unit tests

Test:

- Password validation
- Application status transitions
- Eligibility checks
- Deadline checks
- Permission logic

## Integration tests

Test:

- Registration
- Login
- Recruiter approval
- Opportunity approval
- Application submission
- Duplicate application prevention
- Interview scheduling

## Security tests

Test:

- Student accessing admin API
- Recruiter accessing another recruiter's opportunity
- Recruiter accessing another recruiter's applicants
- Unauthorized resume access
- Expired verification tokens

---

# 59. Critical Test Cases

The following should never fail:

```text
Student cannot apply twice
Student cannot apply after deadline
Unapproved recruiter cannot publish
Recruiter cannot modify another recruiter's opportunity
Recruiter cannot view another recruiter's applicants
Student cannot access admin APIs
Invalid application status transitions are rejected
Unauthorized users cannot download resumes
Expired tokens cannot verify accounts
```

These are more important than cosmetic features.

---

# 60. Deployment Architecture

Recommended initial production setup:

```text
                    Internet
                       │
                      HTTPS
                       │
                       ▼
                    Nginx
                       │
                       ▼
                 Gunicorn
                       │
                       ▼
                Flask Application
                  │           │
                  ▼           ▼
             PostgreSQL    File Storage
                  │
                  ▼
             Backup System
```

Email provider sits outside the application infrastructure.

---

# 61. Backup Strategy

At minimum:

### Database

- Automated daily backups
- Retain multiple backup points
- Test restoration periodically

### Resumes

- Storage redundancy
- Backup/versioning where supported

A backup that has never been restored is not a reliable backup strategy.

---

# 62. Observability

V1 needs basic observability, not a full monitoring platform.

Monitor:

- Application errors
- HTTP 5xx responses
- Database connection failures
- Disk/storage usage
- CPU/memory usage
- Request latency
- Failed email delivery
- Backup failures

Start with application logs and basic server monitoring.

Add advanced monitoring only when deployment size justifies it.

---

# 63. API Security Boundary

The most important architectural rule:

> **Never trust the frontend.**

For every protected operation:

```text
Request
 ↓
Authenticate
 ↓
Authorize role
 ↓
Check resource ownership
 ↓
Validate input
 ↓
Validate business rules
 ↓
Database transaction
 ↓
Response
```

For example:

```text
POST /student/opportunities/123/apply
```

must verify:

```text
Is user authenticated?
        ↓
Is user a student?
        ↓
Is opportunity 123 published?
        ↓
Is deadline still valid?
        ↓
Is student eligible?
        ↓
Does application already exist?
        ↓
Does required resume exist?
        ↓
Create application
```

---

# 64. Scalability Decision Rules

Do not scale infrastructure because it is theoretically possible.

Scale when there is evidence.

| Problem | First solution |
|---|---|
| Slow database query | Optimize query/index |
| Large API responses | Pagination |
| Slow page | Optimize backend/query |
| Large resume files | Object storage |
| High CPU | More application workers |
| High application traffic | Multiple Flask instances |
| Database load | Optimize queries/indexes |
| Search becomes slow | PostgreSQL text search |
| Very large search workload | Consider dedicated search later |
| Email slows requests | Introduce background processing later |

This keeps the architecture proportional to actual usage.

---

# 65. Architecture Evolution Path

### V1

```text
Flask
+
PostgreSQL
+
File/Object Storage
+
Email Provider
```

### V1.5

If required:

```text
Flask
+
PostgreSQL
+
Object Storage
+
Background Job Worker
```

The background worker would handle:

- Email sending
- Large notification batches
- Other slow non-critical tasks

### Later

Only if actual scale requires it:

```text
Load Balancer
      ↓
Multiple Flask Instances
      ↓
PostgreSQL
      +
Object Storage
      +
Background Workers
```

Microservices should only be considered after a real scaling or team-ownership problem appears.

---

# 66. Technical Non-Goals

The V1 architecture will not include:

- Microservices
- Kubernetes
- Event sourcing
- CQRS
- GraphQL
- Dedicated search infrastructure
- Dedicated analytics database
- Real-time WebSocket architecture
- AI infrastructure
- Complex distributed caching
- Multi-region deployment

These would increase operational complexity without solving a V1 requirement.

---

# 67. Recommended V1 Build Order

The backend should be developed in dependency order.

```text
1. Project setup
        ↓
2. Database + migrations
        ↓
3. User authentication
        ↓
4. Role-based authorization
        ↓
5. Student profiles + resumes
        ↓
6. Recruiter profiles + approval
        ↓
7. Opportunity management
        ↓
8. Application system
        ↓
9. Application status management
        ↓
10. Interview scheduling
        ↓
11. Notifications
        ↓
12. Admin dashboard
        ↓
13. Analytics
        ↓
14. Security hardening
        ↓
15. Testing + deployment
```

This follows the PRD's own V1 priority sequence: Authentication → Profiles → Recruiter Approval → Opportunities → Applications → Application Status → Interviews → Notifications → Admin Analytics.

---

# 68. Final Architecture Decision

## Use

```text
Frontend
HTML + CSS + JavaScript

Backend
Python + Flask

API
REST /api/v1

Database
PostgreSQL

ORM
SQLAlchemy

Migrations
Alembic

Authentication
Server-side sessions + secure cookies

Password Security
Werkzeug password hashing

File Storage
Object/local storage abstraction

Email
SMTP / transactional email provider

Production Server
Gunicorn + Nginx
```

## Do not use yet

```text
React
Node.js
Django + Flask together
Microservices
Redis
Kafka
RabbitMQ
Elasticsearch
Kubernetes
GraphQL
AI APIs
WebSockets
```

---

# 69. Architecture Principle

The system should follow one simple principle:

> **Keep the architecture boring until the product gives you a reason to make it complicated.**

The V1 is fundamentally a relational workflow:

```text
Users
  ↓
Recruiters
  ↓
Opportunities
  ↓
Applications
  ↓
Interviews
  ↓
Selections
```

A well-structured Flask monolith with PostgreSQL can handle this cleanly.

The long-term stability comes not from adding more technologies, but from getting the fundamentals right:

**clear modules + strong database constraints + server-side authorization + transactions + secure file handling + migrations + tests.**