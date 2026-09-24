"""Flask CLI commands — demo data seeding."""

import datetime
import os
import uuid

import click
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.application import Application
from app.models.audit import AuditLog
from app.models.college import College
from app.models.enums import (
    ApplicationStatus,
    InterviewStatus,
    OpportunityStatus,
    OpportunityType,
    RecruiterApprovalStatus,
    Role,
)
from app.models.interview import Interview
from app.models.notification import Notification
from app.models.opportunity import Opportunity
from app.models.recruiter import RecruiterProfile
from app.models.resume import Resume
from app.models.student import StudentProfile
from app.models.user import User


def _make_user(email, password, role, verified=True, active=True):
    user = User(email=email, role=role, is_verified=verified, is_active=active)
    user.password_hash = generate_password_hash(password)
    db.session.add(user)
    db.session.flush()
    return user


def _make_minimal_pdf(text):
    """Build a tiny but *valid* PDF (with a correct xref table) for demo resumes."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
    ]
    stream = b"BT /F1 18 Tf 72 720 Td (" + text.encode("ascii", "replace") + b") Tj ET"
    objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode()
    return bytes(out)


def _write_placeholder_resume(student, file_name):
    """Create a tiny valid placeholder PDF so demo resume downloads open cleanly."""
    storage_key = f"{student.id}/{uuid.uuid4().hex}.pdf"
    path = os.path.join(_upload_folder(), storage_key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    content = _make_minimal_pdf(f"Placement Resume - {student.full_name}")
    with open(path, "wb") as fh:
        fh.write(content)
    resume = Resume(
        student_id=student.id,
        file_name=file_name,
        storage_key=storage_key,
        file_type="pdf",
        file_size=os.path.getsize(path),
        is_active=True,
    )
    db.session.add(resume)
    db.session.flush()
    return resume


def _upload_folder():
    from flask import current_app

    return current_app.config["UPLOAD_FOLDER"]


def register_cli(app):
    @app.cli.command("send-weekly-digest")
    def send_weekly_digest():
        """Send weekly analytics digest emails to opted-in recruiters."""
        from app.services.digest_service import send_weekly_digests

        count = send_weekly_digests(app)
        click.echo(f"Weekly digest sent to {count} recruiter(s).")

    @app.cli.command("seed-demo")
    @click.option("--reset", is_flag=True, help="Drop all existing data first")
    def seed_demo(reset):
        """Seed the database with demo data for local development."""
        if reset:
            db.drop_all()
            db.create_all()

        if User.query.first() is not None and not reset:
            click.echo("Database already has data. Use --reset to reseed.")
            return

        db.drop_all()
        db.create_all()
        _seed(app)
        click.echo("Demo data seeded. Accounts:")
        click.echo("   Admin:     admin@college.edu / Admin@123")
        click.echo("   Student:   student1@college.edu / Student@123")
        click.echo("   Recruiter: techcorp@company.com / Recruiter@123")


def _seed(app):
    now = datetime.datetime.now(datetime.timezone.utc)
    today = datetime.date.today()

    # --- colleges ---
    colleges = [
        College(name="State Institute of Technology", code="SIT"),
        College(name="National Engineering College", code="NEC"),
        College(name="City Polytechnic University", code="CPU"),
    ]
    db.session.add_all(colleges)
    db.session.flush()
    sit = colleges[0]
    nec = colleges[1]

    # --- admin ---
    admin = _make_user("admin@college.edu", "Admin@123", Role.ADMIN)

    # --- students ---
    student_data = [
        ("student1@college.edu", "Aarav Sharma", sit, "B.Tech", "Computer Science", 2026, ["Python", "SQL", "Django", "Git"]),
        ("student2@college.edu", "Priya Patel", sit, "B.Tech", "Information Technology", 2026, ["Java", "Spring Boot", "MySQL"]),
        ("student3@college.edu", "Rohan Mehta", sit, "B.Tech", "Electronics", 2026, ["C", "Embedded Systems", "PCB Design"]),
        ("student4@college.edu", "Sneha Reddy", nec, "M.Tech", "Data Science", 2026, ["Python", "TensorFlow", "Pandas", "ML"]),
        ("student5@college.edu", "Vikram Singh", sit, "B.Tech", "Computer Science", 2027, ["Python", "React", "Node.js"]),
    ]
    students = []
    for email, name, college, degree, dept, year, skills in student_data:
        user = _make_user(email, "Student@123", Role.STUDENT)
        profile = StudentProfile(
            user_id=user.id,
            college_id=college.id,
            full_name=name,
            phone="+91 98765 43210",
            degree=degree,
            department=dept,
            graduation_year=year,
            skills=skills,
        )
        db.session.add(profile)
        db.session.flush()
        students.append(profile)

    # resumes for the first four students
    for student in students[:4]:
        _write_placeholder_resume(student, f"{student.full_name.lower().replace(' ', '_')}_resume.pdf")

    # --- recruiters ---
    recruiter_data = [
        ("techcorp@company.com", "Recruiter@123", "TechCorp Solutions", "Product engineering company", "TechCorp", "Hiring Manager", "APPROVED"),
        ("innova@company.com", "Recruiter@123", "Innova Labs", "AI & data platform startup", "Innova", "Talent Lead", "APPROVED"),
        ("greenfin@company.com", "Recruiter@123", "GreenFin Capital", "Fintech investment firm", "GreenFin", "HR Director", "PENDING"),
        ("cloudnine@company.com", "Recruiter@123", "CloudNine Infra", "Cloud infrastructure provider", "CloudNine", "Recruiter", "APPROVED"),
    ]
    recruiters = []
    for email, pwd, company, desc, company_email, contact, status in recruiter_data:
        user = _make_user(email, pwd, Role.RECRUITER)
        profile = RecruiterProfile(
            user_id=user.id,
            company_name=company,
            company_description=desc,
            company_email=company_email.lower() + "@company.com",
            website=f"https://{company_email.lower()}.com",
            contact_person=contact,
            contact_phone="+91 90000 12345",
            approval_status=status,
            approved_at=now - datetime.timedelta(days=10) if status == "APPROVED" else None,
            approved_by=admin.id if status == "APPROVED" else None,
        )
        db.session.add(profile)
        db.session.flush()
        recruiters.append(profile)

    # --- opportunities ---
    opp_data = [
        ("Software Engineering Intern", OpportunityType.INTERNSHIP, recruiters[0], "OFFICE", "Bengaluru",
         "Work on our core product platform.", "Python, SQL, Django, Git", "B.Tech CSE/IT/ECE, graduating 2026 or 2027",
         "₹30,000 / month", today + datetime.timedelta(days=20), OpportunityStatus.APPROVED),
        ("Data Analyst Trainee", OpportunityType.INTERNSHIP, recruiters[1], "HYBRID", "Hyderabad",
         "Analyse product data and build dashboards.", "Python, Pandas, SQL, Excel", "B.Tech/M.Tech, graduating 2026",
         "₹25,000 / month", today + datetime.timedelta(days=12), OpportunityStatus.APPROVED),
        ("Backend Engineer (Full-time)", OpportunityType.FULL_TIME, recruiters[0], "REMOTE", "Remote",
         "Build and scale our REST APIs.", "Python, PostgreSQL, Docker, AWS", "B.Tech, graduating 2026, CGPA 7+",
         "₹12 LPA", today + datetime.timedelta(days=30), OpportunityStatus.APPROVED),
        ("Machine Learning Intern", OpportunityType.INTERNSHIP, recruiters[1], "HYBRID", "Pune",
         "Train and evaluate models on real datasets.", "Python, TensorFlow, scikit-learn", "M.Tech, graduating 2026",
         "₹35,000 / month", today + datetime.timedelta(days=18), OpportunityStatus.APPROVED),
        ("Frontend Developer (Full-time)", OpportunityType.FULL_TIME, recruiters[3], "REMOTE", "Remote",
         "Build web applications with React.", "JavaScript, React, CSS", "B.Tech, graduating 2026 or 2027",
         "₹10 LPA", today + datetime.timedelta(days=25), OpportunityStatus.APPROVED),
        ("QA Engineer Trainee", OpportunityType.FULL_TIME, recruiters[0], "OFFICE", "Chennai",
         "Write and run test suites across products.", "Manual testing, Python, Selenium", "Any degree, graduating 2026",
         "₹6 LPA", today + datetime.timedelta(days=15), OpportunityStatus.PENDING_REVIEW),
        ("Blockchain Research Intern", OpportunityType.INTERNSHIP, recruiters[2], "REMOTE", "Remote",
         "Research DeFi protocols and write reports.", "Blockchain, Solidity, Python", "B.Tech, graduating 2026",
         "₹20,000 / month", today + datetime.timedelta(days=10), OpportunityStatus.DRAFT),
        ("Network Operations Intern", OpportunityType.INTERNSHIP, recruiters[3], "OFFICE", "Mumbai",
         "Help operate our cloud network.", "Networking, Linux, AWS", "B.Tech, graduating 2026",
         "₹22,000 / month", today + datetime.timedelta(days=22), OpportunityStatus.REJECTED),
    ]
    opportunities = []
    for title, otype, recruiter, mode, location, desc, skills, eligibility, salary, deadline, status in opp_data:
        opp = Opportunity(
            recruiter_id=recruiter.id,
            title=title,
            type=otype,
            description=desc,
            responsibilities="Collaborate with the team, deliver on assigned tasks, and document your work.",
            required_skills=skills,
            eligibility=eligibility,
            location=location,
            work_mode=mode,
            salary_or_stipend=salary,
            application_deadline=deadline,
            status=status,
            published_at=now - datetime.timedelta(days=3) if status == OpportunityStatus.APPROVED else None,
            created_at=now - datetime.timedelta(days=5),
        )
        db.session.add(opp)
        db.session.flush()
        opportunities.append(opp)

    # --- applications ---
    def _apply(student, opp, status, days_ago):
        app_row = Application(
            student_id=student.id,
            opportunity_id=opp.id,
            resume_id=student.resumes.first().id if student.resumes.first() else None,
            status=status,
            applied_at=now - datetime.timedelta(days=days_ago),
        )
        db.session.add(app_row)
        db.session.flush()
        return app_row

    a1 = _apply(students[0], opportunities[0], ApplicationStatus.SHORTLISTED, 4)
    a2 = _apply(students[1], opportunities[0], ApplicationStatus.UNDER_REVIEW, 3)
    a3 = _apply(students[2], opportunities[1], ApplicationStatus.APPLIED, 2)
    a4 = _apply(students[3], opportunities[3], ApplicationStatus.INTERVIEW_SCHEDULED, 5)
    a5 = _apply(students[0], opportunities[2], ApplicationStatus.SELECTED, 7)
    a6 = _apply(students[4], opportunities[0], ApplicationStatus.REJECTED, 6)
    a7 = _apply(students[1], opportunities[3], ApplicationStatus.APPLIED, 1)
    a8 = _apply(students[3], opportunities[2], ApplicationStatus.UNDER_REVIEW, 2)

    # --- interviews ---
    db.session.add(
        Interview(
            application_id=a1.id,
            scheduled_date=today + datetime.timedelta(days=3),
            scheduled_time=datetime.time(10, 30),
            mode="ONLINE",
            meeting_details="https://meet.example.com/techcorp-round1",
            additional_instructions="Technical round — 45 minutes. Keep your camera on.",
            status=InterviewStatus.SCHEDULED,
        )
    )
    db.session.add(
        Interview(
            application_id=a4.id,
            scheduled_date=today + datetime.timedelta(days=5),
            scheduled_time=datetime.time(14, 0),
            mode="OFFICE",
            location="Innova Labs, Pune (4th floor)",
            additional_instructions="Bring a printed copy of your resume.",
            status=InterviewStatus.SCHEDULED,
        )
    )
    db.session.add(
        Interview(
            application_id=a5.id,
            scheduled_date=today - datetime.timedelta(days=2),
            scheduled_time=datetime.time(11, 0),
            mode="ONLINE",
            meeting_details="https://meet.example.com/techcorp-final",
            status=InterviewStatus.COMPLETED,
        )
    )

    # --- notifications ---
    notifications = [
        Notification(user_id=students[0].user_id, type="APPLICATION_STATUS_CHANGED",
                     title="Application status updated",
                     message="Your application for 'Software Engineering Intern' at TechCorp Solutions is now Shortlisted.",
                     is_read=False, created_at=now - datetime.timedelta(hours=2)),
        Notification(user_id=recruiters[0].user_id, type="NEW_APPLICATION",
                     title="New application received",
                     message="Sneha Reddy applied for 'Backend Engineer (Full-time)'.",
                     is_read=False, created_at=now - datetime.timedelta(hours=1)),
        Notification(user_id=admin.id, type="OPPORTUNITY_APPROVED",
                     title="New opportunity awaiting approval",
                     message="QA Engineer Trainee by TechCorp Solutions was submitted for review.",
                     is_read=False, created_at=now - datetime.timedelta(minutes=30)),
    ]
    db.session.add_all(notifications)

    # --- audit log ---
    AuditLog.record(admin.id, "ADMIN_APPROVED_RECRUITER", "RecruiterProfile", recruiters[0].id,
                    {"company": "TechCorp Solutions"})
    db.session.commit()
