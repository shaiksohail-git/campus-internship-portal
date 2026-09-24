"""Auth flows — registration, login, email verification, password reset."""

import datetime

from conftest import (
    ADMIN_PASSWORD,
    STUDENT_PASSWORD,
    login,
    make_admin,
    password_reset_token,
    register_recruiter,
    register_student,
    verify_user,
)


def test_register_student_creates_unverified_account(app, client):
    res = register_student(app, client, verify=False, with_resume=False)
    # register_student already asserted 201
    with app.app_context():
        from app.models.user import User

        user = User.query.filter_by(email="student1@test.edu").first()
        assert user is not None
        assert user.is_verified is False
        assert user.role == "STUDENT"
        assert user.password_hash != STUDENT_PASSWORD  # never plain text


def test_register_student_sends_verification_email(app, client):
    register_student(app, client, verify=False, with_resume=False)
    with app.app_context():
        from app.models.mailbox import DevMailbox

        mail = DevMailbox.query.filter_by(recipient="student1@test.edu").first()
        assert mail is not None
        assert "verify-email?token=" in mail.body


def test_register_duplicate_email_conflict(app, client):
    register_student(app, client, verify=False, with_resume=False)
    res = client.post(
        "/api/v1/auth/register/student",
        json={
            "full_name": "Another",
            "email": "student1@test.edu",
            "password": STUDENT_PASSWORD,
            "password_confirm": STUDENT_PASSWORD,
        },
    )
    assert res.status_code == 409
    assert res.get_json()["error"]["code"] == "EMAIL_TAKEN"


def test_register_invalid_email_rejected(app, client):
    res = client.post(
        "/api/v1/auth/register/student",
        json={
            "full_name": "Bad",
            "email": "not-an-email",
            "password": STUDENT_PASSWORD,
            "password_confirm": STUDENT_PASSWORD,
        },
    )
    assert res.status_code == 422


def test_register_weak_password_rejected(app, client):
    res = client.post(
        "/api/v1/auth/register/student",
        json={
            "full_name": "Weak",
            "email": "weak@test.edu",
            "password": "short",
            "password_confirm": "short",
        },
    )
    assert res.status_code == 422


def test_register_password_mismatch_rejected(app, client):
    res = client.post(
        "/api/v1/auth/register/student",
        json={
            "full_name": "Mismatch",
            "email": "mm@test.edu",
            "password": "LongEnough123",
            "password_confirm": "Different123",
        },
    )
    assert res.status_code == 422


def test_login_success(app, client):
    register_student(app, client)
    res = login(client, "student1@test.edu", STUDENT_PASSWORD)
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["user"]["role"] == "STUDENT"
    assert data["redirect"] == "/student/dashboard"


def test_login_wrong_password(app, client):
    register_student(app, client)
    res = login(client, "student1@test.edu", "wrong-password")
    assert res.status_code == 401


def test_login_unknown_email(app, client):
    res = login(client, "nobody@test.edu", STUDENT_PASSWORD)
    assert res.status_code == 401


def test_unverified_user_login_redirects_to_verify(app, client):
    register_student(app, client, verify=False, with_resume=False)
    res = login(client, "student1@test.edu", STUDENT_PASSWORD)
    assert res.status_code == 200
    assert res.get_json()["data"]["redirect"] == "/verify"


def test_verify_email_single_use(app, client):
    register_student(app, client, verify=False, with_resume=False)
    token = verify_user(app, client, "student1@test.edu")
    # reuse the same token — must be rejected
    res = client.get(f"/verify-email?token={token}")
    assert res.status_code == 200
    assert b"Verification failed" in res.data


def test_expired_verification_token_rejected(app, client):
    register_student(app, client, verify=False, with_resume=False)
    import re

    from app.extensions import db

    with app.app_context():
        from app.models.mailbox import DevMailbox
        from app.models.token import AuthToken

        record = AuthToken.query.first()
        record.expires_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
        db.session.commit()

        # the plaintext token is never stored — rebuild it from the mailbox link
        mail = DevMailbox.query.filter_by(recipient=record.user.email).first()
        raw = re.search(r"token=([A-Za-z0-9_-]+)", mail.body).group(1)

    res = client.get(f"/verify-email?token={raw}")
    assert b"Verification failed" in res.data


def test_resend_verification(app, client):
    register_student(app, client, verify=False, with_resume=False)
    res = client.post("/api/v1/auth/resend-verification", json={"email": "student1@test.edu"})
    assert res.status_code == 200
    with app.app_context():
        from app.models.mailbox import DevMailbox

        count = DevMailbox.query.filter_by(recipient="student1@test.edu").count()
        assert count >= 2


def test_forgot_password_always_succeeds(app, client):
    # Unknown email still returns success (no account enumeration)
    res = client.post("/api/v1/auth/forgot-password", json={"email": "ghost@test.edu"})
    assert res.status_code == 200


def test_reset_password_flow(app, client):
    register_student(app, client)
    token = password_reset_token(app, client, "student1@test.edu")
    res = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "password": "NewPass@123", "password_confirm": "NewPass@123"},
    )
    assert res.status_code == 200
    # old password no longer works, new one does
    assert login(client, "student1@test.edu", STUDENT_PASSWORD).status_code == 401
    assert login(client, "student1@test.edu", "NewPass@123").status_code == 200


def test_reset_token_single_use(app, client):
    register_student(app, client)
    token = password_reset_token(app, client, "student1@test.edu")
    payload = {"token": token, "password": "NewPass@123", "password_confirm": "NewPass@123"}
    assert client.post("/api/v1/auth/reset-password", json=payload).status_code == 200
    assert client.post("/api/v1/auth/reset-password", json=payload).status_code == 409


def test_logout_clears_session(app, client):
    register_student(app, client)
    login(client, "student1@test.edu", STUDENT_PASSWORD)
    assert client.get("/api/v1/auth/me").get_json()["data"]["user"] is not None
    res = client.post("/api/v1/auth/logout")
    assert res.status_code == 200
    assert client.get("/api/v1/auth/me").get_json()["data"]["user"] is None


def test_admin_can_login(app, client):
    make_admin(app)
    res = login(client, "admin@test.edu", ADMIN_PASSWORD)
    assert res.status_code == 200
    assert res.get_json()["data"]["redirect"] == "/admin/dashboard"


def test_recruiter_registration(app, client):
    register_recruiter(app, client, approved=False)
    with app.app_context():
        from app.models.user import User

        user = User.query.filter_by(email="recruiter1@test.com").first()
        assert user.role == "RECRUITER"
        assert user.recruiter_profile.approval_status == "PENDING"
