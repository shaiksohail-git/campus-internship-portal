"""Shared pytest fixtures and factories."""

import datetime
import io
import re

import pytest

from app import create_app
from app.extensions import db
from app.models.enums import RecruiterApprovalStatus, Role
from app.models.opportunity import Opportunity
from app.models.user import User

STUDENT_PASSWORD = "Student@123"
RECRUITER_PASSWORD = "Recruiter@123"
ADMIN_PASSWORD = "Admin@123"

TOKEN_RE = re.compile(r"token=([A-Za-z0-9_-]+)")


@pytest.fixture()
def app():
    app = create_app("test")
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


# ------------------------------------------------------------------ factories


def register_student(app, client, email="student1@test.edu", verify=True, with_resume=True, **overrides):
    data = {
        "full_name": "Test Student",
        "email": email,
        "phone": "+91 98765 43210",
        "college": "Test College",
        "degree": "B.Tech",
        "department": "Computer Science",
        "graduation_year": 2026,
        "skills": ["Python", "SQL"],
        "password": STUDENT_PASSWORD,
        "password_confirm": STUDENT_PASSWORD,
    }
    data.update(overrides)
    res = client.post("/api/v1/auth/register/student", json=data)
    assert res.status_code == 201, res.get_data(as_text=True)
    if verify:
        verify_user(app, client, email)
    if with_resume:
        upload_resume(client)
    return client


def register_recruiter(app, client, email="recruiter1@test.com", verify=True, approved=False, **overrides):
    data = {
        "company_name": "TestCorp",
        "company_description": "A test company",
        "company_email": "hr@testcorp.com",
        "website": "https://testcorp.com",
        "contact_person": "HR Lead",
        "contact_phone": "+91 90000 12345",
        "email": email,
        "password": RECRUITER_PASSWORD,
        "password_confirm": RECRUITER_PASSWORD,
    }
    data.update(overrides)
    res = client.post("/api/v1/auth/register/recruiter", json=data)
    assert res.status_code == 201, res.get_data(as_text=True)
    if verify:
        verify_user(app, client, email)
    if approved:
        set_recruiter_status(app, email, RecruiterApprovalStatus.APPROVED)
    return client


def set_recruiter_status(app, email, status):
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        user.recruiter_profile.approval_status = status
        db.session.commit()


def make_admin(app, email="admin@test.edu"):
    """Idempotent admin factory."""
    with app.app_context():
        existing = User.query.filter_by(email=email).first()
        if existing:
            return existing.id
        admin = User(email=email, role=Role.ADMIN, is_verified=True)
        admin.set_password(ADMIN_PASSWORD)
        db.session.add(admin)
        db.session.commit()
        return admin.id


def login(client, email, password):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def verify_user(app, client, email):
    """Extract the verification token from the dev mailbox and verify the user."""
    with app.app_context():
        from app.models.mailbox import DevMailbox

        mail = (
            DevMailbox.query.filter_by(recipient=email)
            .order_by(DevMailbox.created_at.desc())
            .first()
        )
        assert mail, f"No verification email found for {email}"
        match = TOKEN_RE.search(mail.body)
        assert match, f"No token in email body: {mail.body}"
        token = match.group(1)
    res = client.get(f"/verify-email?token={token}")
    assert res.status_code == 200
    assert b"Email verified" in res.data
    return token


RESET_TOKEN_RE = re.compile(r"/reset-password/([A-Za-z0-9_-]+)")


def password_reset_token(app, client, email):
    client.post("/api/v1/auth/forgot-password", json={"email": email})
    with app.app_context():
        from app.models.mailbox import DevMailbox

        mail = (
            DevMailbox.query.filter_by(
                recipient=email, subject="Reset your Campus Placement Portal password"
            )
            .order_by(DevMailbox.created_at.desc())
            .first()
        )
        assert mail, "No reset email found"
        match = RESET_TOKEN_RE.search(mail.body)
        assert match, f"No reset link in email body: {mail.body[:300]}"
        return match.group(1)


def upload_resume(client, filename="resume.pdf", content=b"%PDF-1.4 fake resume"):
    data = {"file": (io.BytesIO(content), filename)}
    res = client.post(
        "/api/v1/student/resumes", data=data, content_type="multipart/form-data"
    )
    assert res.status_code == 201, res.get_data(as_text=True)
    return res.get_json()["data"]["resume"]


def create_opportunity(client, title="Software Engineer", deadline_offset_days=30, **overrides):
    """Create + submit an opportunity for the logged-in recruiter. Returns opp id."""
    data = {
        "title": title,
        "type": "FULL_TIME",
        "description": "Great role",
        "responsibilities": "Build stuff",
        "required_skills": "Python, SQL",
        "eligibility": "B.Tech, graduating 2026",
        "location": "Bengaluru",
        "work_mode": "ON_SITE",
        "salary_or_stipend": "12 LPA",
        "application_deadline": (
            datetime.date.today() + datetime.timedelta(days=deadline_offset_days)
        ).isoformat(),
    }
    data.update(overrides)
    res = client.post("/api/v1/recruiter/opportunities", json=data)
    assert res.status_code == 201, res.get_data(as_text=True)
    opp_id = res.get_json()["data"]["opportunity"]["id"]
    res = client.post(f"/api/v1/recruiter/opportunities/{opp_id}/submit")
    assert res.status_code == 200, res.get_data(as_text=True)
    return opp_id


def approve_opportunity(app, client, opportunity_id):
    """Approve an opportunity through the real admin API (end-to-end)."""
    with app.app_context():
        from app.models.user import User

        admin = User.query.filter_by(email="tmp-admin@test.edu").first()
        if admin is None:
            admin = User(email="tmp-admin@test.edu", role=Role.ADMIN, is_verified=True)
            admin.set_password(ADMIN_PASSWORD)
            db.session.add(admin)
            db.session.commit()
    login(client, "tmp-admin@test.edu", ADMIN_PASSWORD)
    res = client.patch(f"/api/v1/admin/opportunities/{opportunity_id}/approve")
    assert res.status_code == 200, res.get_data(as_text=True)
    logout(client)
    return res


def logout(client):
    return client.post("/api/v1/auth/logout")


def apply_as_student(client, opportunity_id, resume_id=None):
    payload = {"resume_id": resume_id} if resume_id else {}
    return client.post(f"/api/v1/student/opportunities/{opportunity_id}/apply", json=payload)


def get_application(app, student_email, opportunity_id):
    """Return the application id (or None). ORM instances do not survive app
    context teardown, so callers re-query inside their own app context."""
    from app.models.application import Application
    from app.models.student import StudentProfile

    with app.app_context():
        row = (
            Application.query.join(StudentProfile, Application.student_id == StudentProfile.id)
            .join(User, StudentProfile.user_id == User.id)
            .filter(User.email == student_email, Application.opportunity_id == opportunity_id)
            .first()
        )
        return row.id if row else None


def set_opportunity_deadline(app, opportunity_id, days_ago):
    with app.app_context():
        opp = db.session.get(Opportunity, opportunity_id)
        opp.application_deadline = datetime.date.today() - datetime.timedelta(days=days_ago)
        db.session.commit()


def student_user(app, email):
    with app.app_context():
        return User.query.filter_by(email=email).first()
