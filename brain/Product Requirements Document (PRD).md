# Product Requirements Document (PRD)

## Campus Internship & Placement Portal — V1

**Document Version:** 1.0\
**Product Type:** Full-stack web application\
**Primary Users:** Students, Recruiters, Placement Officers/Admins\
**Frontend:** HTML, CSS, JavaScript\
**Backend:** Python\
**Database:** SQL

---

# 1. Product Overview

The Campus Internship & Placement Portal is a web application that provides a centralized platform for managing internship and full-time job opportunities across colleges.

The platform connects:

- **Students** — discover opportunities, apply for jobs/internships, track applications, and attend scheduled interviews.
- **Recruiters** — get approved by placement administrators, publish opportunities, review applicants, and schedule interviews.
- **Placement Officers/Admins** — manage students and recruiters, approve recruiters and job postings, monitor applications, and view placement activity.

The V1 goal is to replace fragmented placement processes such as spreadsheets, email communication, messaging groups, and manually maintained application records with one simple system.

---

# 2. Problem Statement

Campus recruitment and internship processes are often distributed across multiple channels.

### Current problems

**For students**

- Job and internship opportunities may be communicated through different channels.
- Students have difficulty tracking which opportunities they applied for.
- Application status is not always clear.
- Interview schedules can be difficult to track.
- Students may repeatedly submit information such as resumes and personal details.

**For recruiters**

- Recruiters need a structured way to publish opportunities to eligible students.
- Applicant information may arrive through inconsistent formats.
- Reviewing and tracking applicants manually is inefficient.
- Interview scheduling becomes difficult when applicant numbers increase.

**For placement officers**

- Student applications and recruiter activities are difficult to monitor manually.
- Recruiter verification needs to happen before recruiters can publish opportunities.
- Maintaining application and placement records through spreadsheets is error-prone.
- Generating basic placement statistics requires manual work.

### Problem to solve

Build a **single centralized portal** where verified recruiters can publish opportunities, eligible students can apply, and placement officers can control and monitor the complete process.

---

# 3. Product Goals

## Primary Goals

1. Allow students to create and manage their profiles.
2. Allow students to discover internship and full-time opportunities.
3. Allow students to apply directly through the portal.
4. Allow students to track application status.
5. Allow recruiters to create and manage job/internship postings.
6. Require admin approval before recruiters can publish opportunities.
7. Allow recruiters to review applicants.
8. Allow recruiters to schedule interviews.
9. Notify users about important application and interview events.
10. Give placement officers basic operational and placement analytics.

## V1 Success Definition

A student should be able to:

> **Register → verify email → complete profile → find an opportunity → apply → track status → receive interview notification → attend interview.**

A recruiter should be able to:

> **Register → get approved → create opportunity → receive applications → review candidates → schedule interviews → update application status.**

An admin should be able to:

> **Verify users/recruiters → control postings → monitor applications → manage the placement process → view analytics.**

---

# 4. Target Users

## 4.1 Student

### Description

College students searching for internships and full-time employment opportunities.

### Primary needs

- Create an account
- Maintain profile
- Upload resume
- Browse opportunities
- Search/filter opportunities
- View job details
- Apply
- Track applications
- View interview schedules
- Receive notifications

### Primary goal

**Find and successfully apply to relevant opportunities without losing track of applications.**

---

## 4.2 Recruiter

### Description

Companies or authorized representatives looking to recruit students for internships or full-time positions.

### Primary needs

- Create recruiter account
- Submit company information
- Get verified by admin
- Create job/internship postings
- View applicants
- Review applicant information/resumes
- Update candidate status
- Schedule interviews
- View basic recruitment activity

### Primary goal

**Find and manage suitable student candidates efficiently.**

---

## 4.3 Placement Officer / Admin

### Description

Authorized college placement staff responsible for controlling the platform and recruitment process.

### Primary needs

- Manage students
- Approve/reject recruiters
- Review job postings
- Manage applications
- Monitor interviews
- Send/trigger notifications
- View placement statistics
- Maintain platform integrity

### Primary goal

**Maintain a controlled and transparent placement process.**

---

# 5. Roles & Permissions

| Feature                   | Student | Recruiter | Admin |
| ------------------------- | ------: | --------: | ----: |
| Register                  |       ✓ |         ✓ |     — |
| Email verification        |       ✓ |         ✓ |     — |
| Manage own profile        |       ✓ |         ✓ |     ✓ |
| Browse jobs               |       ✓ |         — |     ✓ |
| Apply for jobs            |       ✓ |         — |     — |
| Track applications        |       ✓ |         — |     ✓ |
| Create job posting        |       — |         ✓ |     ✓ |
| Edit own posting          |       — |         ✓ |     ✓ |
| Approve recruiter         |       — |         — |     ✓ |
| Approve job posting       |       — |         — |     ✓ |
| View applicants           |       — |         ✓ |     ✓ |
| Update application status |       — |         ✓ |     ✓ |
| Schedule interviews       |       — |         ✓ |     ✓ |
| View analytics            | Limited |   Limited |     ✓ |
| Manage users              |       — |         — |     ✓ |

---

# 6. Core User Flows

## 6.1 Student Registration

```text
Student
   ↓
Register
   ↓
Enter basic information
   ↓
Email verification
   ↓
Account activated
   ↓
Complete profile
   ↓
Upload resume
   ↓
Student Dashboard
```

### Required student information

- Name
- Email
- Password
- College
- Course/degree
- Department
- Graduation year
- Phone number
- Skills
- Resume

---

# 7. Student Job Application Flow

```text
Student Dashboard
       ↓
Browse Opportunities
       ↓
Search / Filter
       ↓
Open Opportunity
       ↓
View Requirements
       ↓
Apply
       ↓
Application Created
       ↓
Application Status = Applied
       ↓
Recruiter Reviews
       ↓
Shortlisted / Rejected
       ↓
Interview Scheduled (if shortlisted)
       ↓
Selected / Rejected
```

### Application statuses

V1 should use a simple fixed status system:

- **Applied**
- **Under Review**
- **Shortlisted**
- **Interview Scheduled**
- **Selected**
- **Rejected**

Do not allow recruiters to create arbitrary custom statuses in V1.

---

# 8. Recruiter Flow

```text
Recruiter Registration
        ↓
Submit Company Information
        ↓
Admin Review
        ↓
Approved?
   ↙          ↘
 No            Yes
 ↓              ↓
Cannot Post    Recruiter Dashboard
                 ↓
          Create Opportunity
                 ↓
            Admin Review
                 ↓
             Published
                 ↓
           Receive Applications
                 ↓
          Review Candidates
                 ↓
         Shortlist Candidates
                 ↓
          Schedule Interviews
                 ↓
        Update Final Status
```

### Important V1 rule

A recruiter **cannot publish opportunities immediately after registration**.

The recruiter must first be approved by an administrator.

---

# 9. Admin Flow

```text
Admin Login
    ↓
Admin Dashboard
    ↓
Review Pending Recruiters
    ↓
Approve / Reject
    ↓
Review Job Postings
    ↓
Approve / Reject
    ↓
Monitor Applications
    ↓
Monitor Interviews
    ↓
View Placement Analytics
```

---

# 10. Feature Requirements

## 10.1 Authentication

### MVP

- Student registration
- Recruiter registration
- Admin login
- Login/logout
- Password hashing
- Email verification
- Role-based access
- Forgot/reset password

### Requirements

Users must only access features permitted for their role.

For example:

> A student must never be able to access recruiter or admin functionality by changing a URL manually.

---

# 11. Student Features

## 11.1 Student Profile

Students can:

- Add/edit personal information
- Add academic information
- Add skills
- Upload/update resume
- Upload multiple resumes (role-specific versions)
- Select and use a specific resume per job role or during each application
- View profile completeness

### MVP

Keep the profile simple.

Do **not** build a complete social/professional profile system.

---

## 11.2 Opportunity Listing

Students can browse:

- Internships
- Full-time jobs

Each opportunity should display:

- Job title
- Company
- Opportunity type
- Location
- Work mode
- Required skills
- Eligibility
- Application deadline
- Posted date

---

## 11.3 Search & Filtering

Students should be able to filter by:

- Internship / Full-time
- Location
- Work mode
- Skills
- Deadline

Search should primarily search:

- Job title
- Company
- Skills

---

# 12. Job / Internship Details

Each opportunity should contain:

### Basic information

- Title
- Company
- Type
- Location
- Work mode
- Salary/stipend
- Application deadline

### Description

- Job description
- Responsibilities
- Required skills
- Eligibility criteria

### Application

- Apply button
- Application deadline
- Application status

---

# 13. Application Management

Students can view:

| Opportunity       | Company | Applied Date | Status       |
| ----------------- | ------- | ------------ | ------------ |
| Python Intern     | ABC     | Aug 10       | Under Review |
| Software Engineer | XYZ     | Aug 8        | Shortlisted  |

Students should be able to see their complete application history.

### V1 restriction

A student should **not be able to apply twice to the same opportunity**.

---

# 14. Recruiter Features

## 14.1 Recruiter Profile

Recruiters provide:

- Company name
- Company description
- Company email
- Website
- Contact person
- Contact information
- Company details required for verification

---

## 14.2 Job Posting

Recruiters can create:

- Internship postings
- Full-time job postings

### Required fields

- Title
- Type
- Description
- Responsibilities
- Required skills
- Eligibility
- Location
- Work mode
- Salary/stipend
- Application deadline

### Posting lifecycle

```text
Draft
 ↓
Submitted
 ↓
Admin Review
 ↓
Approved → Published
      OR
Rejected
```

Recruiters should be able to edit rejected/draft postings and resubmit them.

---

# 15. Applicant Management

Recruiters can view applicants for their own postings.

Applicant information:

- Student name
- College
- Degree
- Department
- Graduation year
- Skills
- Resume
- Application date
- Current application status

Recruiters can:

- Review applicants
- View/download resume
- Change application status
- Shortlist applicants
- Reject applicants
- Schedule interviews

Recruiters must **not** be able to access applicants belonging to another recruiter's postings.

---

# 16. Interview Scheduling

Recruiters can schedule interviews for shortlisted students.

### Required information

- Interview date
- Interview time
- Interview mode
- Interview location or meeting information
- Additional instructions

Example:

```text
Interview
---------
Date: 18 Aug 2026
Time: 10:30 AM
Mode: Online
Details: Meeting information
```

Students can see scheduled interviews from their dashboard.

---

# 17. Notifications

V1 should support notifications for important events only.

### Student notifications

- Email verification
- Application submitted
- Application status changed
- Interview scheduled
- Interview details changed/cancelled

### Recruiter notifications

- Recruiter approved/rejected
- Job posting approved/rejected
- New application
- Interview-related updates

### Admin notifications

Only operational notifications that are necessary for pending actions.

Do not build a complex notification center in V1.

---

# 18. Admin Dashboard

The admin dashboard should provide:

### Overview

- Total students
- Total recruiters
- Pending recruiter approvals
- Active opportunities
- Total applications
- Interviews scheduled
- Selected students

### Management

- Students
- Recruiters
- Job postings
- Applications
- Interviews

### Admin actions

- Approve/reject recruiters
- Approve/reject job postings
- Suspend users where necessary
- Manage/remove inappropriate postings
- View application activity

---

# 19. Analytics

V1 analytics should focus on information useful to placement officers.

### Core metrics

- Total registered students
- Total registered recruiters
- Total internships
- Total full-time jobs
- Total applications
- Applications per opportunity
- Interviews scheduled
- Students selected
- Students rejected
- Placement/selection rate

### Basic breakdowns

- Internship vs full-time
- Department-wise applications
- Department-wise selections
- Company-wise hiring
- Monthly application activity

Do not build predictive analytics or complex dashboards in V1.

---

# 20. MVP Feature Scope

## Must Have

### Authentication

- Student registration
- Recruiter registration
- Admin login
- Email verification
- Login/logout
- Password reset
- Role-based access

### Student

- Profile
- Resume upload
- Opportunity browsing
- Search/filter
- Opportunity details
- Apply
- Application tracking
- Interview schedule
- Notifications

### Recruiter

- Company profile
- Admin approval
- Create internship/full-time postings
- Job posting approval
- Applicant management
- Resume viewing
- Application status management
- Interview scheduling

### Admin

- Dashboard
- Student management
- Recruiter approval
- Job approval
- Application monitoring
- Interview monitoring
- Basic analytics

---

# 21. Future Features

These should **not** be part of V1.

Possible future additions:

- Advanced resume screening
- AI-based job recommendations
- AI resume scoring
- Automated candidate ranking
- Chat between recruiters and students
- Advanced recruiter analytics
- Advanced student analytics
- Calendar integration
- Video interview integration
- Automated interview reminders
- Mobile application
- Multi-factor authentication
- Advanced reporting/exporting
- Automated placement prediction

These features can be evaluated after V1 usage data is available.

---

# 22. Edge Cases

## Authentication

### Case: Duplicate email

A user attempts to register with an existing email.

**Expected:** Registration rejected with a clear message.

### Case: Unverified email

A user attempts to access protected features without verifying their email.

**Expected:** Restrict access and provide a verification option.

### Case: Wrong role access

A student attempts to access an admin page.

**Expected:** Access denied.

---

## Applications

### Case: Student applies twice

**Expected:** Second application is rejected.

### Case: Deadline has passed

Student tries to apply after the deadline.

**Expected:** Apply button disabled and application rejected by backend validation.

### Case: Opportunity is closed

Recruiter/admin closes or removes an opportunity.

**Expected:** New applications are blocked while existing applications remain accessible.

### Case: Student has no resume

If resume is mandatory for the opportunity/application:

**Expected:** Student is asked to upload a resume before applying.

---

## Recruiters

### Case: Unapproved recruiter creates posting

**Expected:** Posting cannot be published.

### Case: Rejected recruiter attempts to post

**Expected:** Posting functionality remains unavailable until the recruiter is approved.

### Case: Recruiter edits approved posting

**Expected:** Significant changes should return the posting to admin review instead of silently changing the published opportunity.

---

## Interviews

### Case: Interview time changes

**Expected:** Student receives an updated notification.

### Case: Interview cancelled

**Expected:** Interview status changes to cancelled and affected students are notified.

### Case: Same student receives overlapping interviews

The system should allow the scheduling action but clearly display the conflict.

V1 does not need an advanced scheduling engine.

---

## Data

### Case: Resume upload fails

**Expected:** Application should not silently continue with a failed upload.

### Case: Invalid file

**Expected:** Reject unsupported file types and oversized files.

### Case: Recruiter attempts to access another recruiter's applicants

**Expected:** Backend authorization prevents access.

---

# 23. Non-Goals

The following are explicitly outside V1 scope:

### Not an AI platform

No:

- AI resume screening
- AI candidate ranking
- AI job recommendations
- AI chatbot
- AI interview evaluation

### Not a social network

No:

- Student connections
- Recruiter messaging feeds
- Likes/comments
- Public profiles

### Not a full HR system

No:

- Payroll
- Employee onboarding
- Attendance
- Employee performance management
- Employee database management

### Not a communication replacement

The portal should handle important recruitment notifications, but it does not need to replace email, video conferencing, or other communication platforms.

### Not a complex scheduling platform

No:

- Automated calendar optimization
- Meeting-room optimization
- Complex recruiter availability algorithms

---

# 24. Functional Requirements

## FR-01 Authentication

The system shall allow users to register, authenticate, logout, and reset passwords.

## FR-02 Role Management

The system shall enforce Student, Recruiter, and Admin permissions.

## FR-03 Email Verification

The system shall verify user email addresses before allowing full account access.

## FR-04 Recruiter Approval

The system shall require admin approval before a recruiter can publish opportunities.

## FR-05 Opportunity Management

Recruiters shall be able to create and manage internship and full-time opportunities.

## FR-06 Opportunity Approval

Administrators shall be able to approve or reject submitted opportunities.

## FR-07 Applications

Students shall be able to submit applications to active opportunities.

## FR-08 Application Tracking

Students shall be able to view their application status.

## FR-09 Applicant Management

Recruiters shall be able to view and manage applicants for their own opportunities.

## FR-10 Interview Scheduling

Recruiters shall be able to schedule interviews for applicants.

## FR-11 Notifications

The system shall notify users about important application and interview events.

## FR-12 Analytics

Administrators shall be able to view basic placement and recruitment statistics.

---

# 25. Non-Functional Requirements

## Security

- Passwords must never be stored as plain text.
- Role-based authorization must be enforced on the backend.
- Users can only access data they are authorized to access.
- Resume files must not be publicly accessible through predictable URLs.
- Input validation must be performed on the backend.

## Performance

For V1:

- Normal pages should load quickly under expected college-level usage.
- Database queries should be reasonably optimized.
- Large resume files should not unnecessarily slow down application pages.

## Reliability

- Applications should not be duplicated because of accidental repeated clicks.
- Important database operations should be handled transactionally.
- User data should persist correctly after logout/login.

## Usability

The interface should prioritize:

- Simple navigation
- Clear status labels
- Responsive design
- Mobile-friendly pages
- Minimal unnecessary UI elements

---

# 26. Core Data Entities

The initial database should contain approximately these entities:

```text
User
 ├── Student Profile
 ├── Recruiter Profile
 └── Admin

College

Opportunity
 └── Recruiter

Application
 ├── Student
 └── Opportunity

Interview
 └── Application

Notification
 └── User

Resume
 └── Student
```

The exact database schema can be designed during technical design.

---

# 27. High-Level System Workflow

```text
                    ┌───────────────┐
                    │     ADMIN     │
                    └───────┬───────┘
                            │
                 Approves Recruiters
                            │
                            ▼
┌──────────────┐     ┌───────────────┐
│   RECRUITER  │────►│  OPPORTUNITY  │
└──────┬───────┘     └───────┬───────┘
       │                      │
       │                      │
       │                 Applications
       │                      │
       │                      ▼
       │               ┌──────────────┐
       └──────────────►│   STUDENT    │
                       └──────┬───────┘
                              │
                         Application
                              │
                              ▼
                         Interview
                              │
                              ▼
                         Selection
```

---

# 28. Success Metrics

The V1 should measure whether the platform actually improves the recruitment workflow.

## Adoption

### Student registration rate

Percentage of eligible students who create accounts.

**Target:** 70%+ of participating students.

### Recruiter activation

Percentage of approved recruiters who publish at least one opportunity.

**Target:** 60%+.

---

## Engagement

### Application completion rate

Percentage of students who start an application and successfully submit it.

**Target:** 85%+.

### Application activity

Average number of applications submitted per active student.

This should be monitored rather than given an arbitrary target initially.

---

## Recruitment Efficiency

### Recruiter processing time

Time between receiving an application and making an initial status decision.

Goal: reduce manual processing time.

### Interview scheduling time

Time between shortlisting and scheduling an interview.

Goal: reduce delays caused by manual coordination.

---

## Platform Reliability

### Application failure rate

Percentage of attempted applications that fail because of system errors.

**Target:** <1%.

### Duplicate application rate

**Target:** 0%.

### Critical authorization failures

Unauthorized users accessing restricted data.

**Target:** 0.

---

## Placement Outcomes

Track:

- Total applications
- Total interviews
- Total selections
- Selection rate
- Internship selections
- Full-time selections
- Department-wise selections
- Recruiter/company-wise selections

These metrics will help determine whether the platform is actually supporting placement outcomes rather than simply generating website traffic.

---

# 29. V1 Acceptance Criteria

The product can be considered ready for initial deployment when:

### Student

- [ ] Student can register.
- [ ] Student can verify email.
- [ ] Student can complete profile.
- [ ] Student can upload resume.
- [ ] Student can browse opportunities.
- [ ] Student can filter/search opportunities.
- [ ] Student can apply.
- [ ] Student cannot apply twice.
- [ ] Student can track application status.
- [ ] Student can view interview details.
- [ ] Student receives important notifications.

### Recruiter

- [ ] Recruiter can register.
- [ ] Recruiter can submit company information.
- [ ] Admin can approve/reject recruiter.
- [ ] Approved recruiter can create opportunities.
- [ ] Admin can approve/reject opportunities.
- [ ] Recruiter can view applicants.
- [ ] Recruiter can view resumes.
- [ ] Recruiter can update application status.
- [ ] Recruiter can schedule interviews.

### Admin

- [ ] Admin can manage students.
- [ ] Admin can approve/reject recruiters.
- [ ] Admin can approve/reject opportunities.
- [ ] Admin can monitor applications.
- [ ] Admin can monitor interviews.
- [ ] Admin can view basic analytics.

---

# 30. V1 Product Boundary

The simplest useful version of the product is:

> **A controlled recruitment marketplace for colleges where verified recruiters publish opportunities, students apply and track their applications, recruiters manage candidates and interviews, and placement officers oversee the entire process.**

Anything that does not directly support this workflow should be treated as **out of scope for V1**.

The priority order should therefore be:

**Authentication → Profiles → Recruiter Approval → Opportunities → Applications → Application Status → Interviews → Notifications → Admin Analytics**

This order keeps the project buildable while still delivering the complete core placement workflow.
