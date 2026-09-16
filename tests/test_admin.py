"""Admin — approvals, user management, analytics, audit trail."""

from conftest import (
    ADMIN_PASSWORD,
    RECRUITER_PASSWORD,
    login,
    make_admin,
    register_recruiter,
    register_student,
)


def _admin_client(app, client):
    make_admin(app)
    login(client, "admin@test.edu", ADMIN_PASSWORD)
    return client


def test_admin_dashboard_stats(app, client):
    register_student(app, client, email="s1@test.edu")
    _admin_client(app, client)
    res = client.get("/api/v1/admin/dashboard")
    assert res.status_code == 200
    stats = res.get_json()["data"]["stats"]
    assert stats["students"] == 1
    assert stats["active_opportunities"] == 0


def test_admin_approves_recruiter(app, client):
    register_recruiter(app, client, email="r1@test.com", approved=False)
    _admin_client(app, client)

    from app.models.user import User

    with app.app_context():
        recruiter_id = User.query.filter_by(email="r1@test.com").first().recruiter_profile.id

    res = client.patch(f"/api/v1/admin/recruiters/{recruiter_id}/approve")
    assert res.status_code == 200

    with app.app_context():
        from app.extensions import db
        from app.models.recruiter import RecruiterProfile

        profile = db.session.get(RecruiterProfile, recruiter_id)
        assert profile.approval_status == "APPROVED"
        assert profile.approved_by is not None

    # recruiter received a notification
    from app.models.notification import Notification

    with app.app_context():
        user = User.query.filter_by(email="r1@test.com").first()
        assert any(n.type == "RECRUITER_APPROVED" for n in Notification.query.filter_by(user_id=user.id).all())


def test_admin_rejects_recruiter(app, client):
    register_recruiter(app, client, email="r1@test.com", approved=False)
    _admin_client(app, client)

    from app.models.user import User

    with app.app_context():
        recruiter_id = User.query.filter_by(email="r1@test.com").first().recruiter_profile.id

    res = client.patch(f"/api/v1/admin/recruiters/{recruiter_id}/reject")
    assert res.status_code == 200
    with app.app_context():
        from app.models.recruiter import RecruiterProfile

        assert RecruiterProfile.query.get(recruiter_id).approval_status == "REJECTED"


def test_admin_approves_opportunity(app, client):
    register_recruiter(app, client, email="r1@test.com", approved=True)
    res = client.post(
        "/api/v1/recruiter/opportunities",
        json={
            "title": "Pending role",
            "type": "INTERNSHIP",
            "description": "x",
            "required_skills": "x",
            "eligibility": "x",
            "application_deadline": "2030-01-01",
        },
    )
    opp_id = res.get_json()["data"]["opportunity"]["id"]
    client.post(f"/api/v1/recruiter/opportunities/{opp_id}/submit")
    logout(client)

    _admin_client(app, client)
    res = client.patch(f"/api/v1/admin/opportunities/{opp_id}/approve")
    assert res.status_code == 200

    from app.models.opportunity import Opportunity

    with app.app_context():
        from app.extensions import db

        opp = db.session.get(Opportunity, opp_id)
        assert opp.status == "APPROVED"
        assert opp.published_at is not None


def test_edit_approved_opportunity_returns_to_review(app, client):
    """PRD: significant changes to an approved posting return it to admin review."""
    register_recruiter(app, client, email="r1@test.com", approved=True)
    res = client.post(
        "/api/v1/recruiter/opportunities",
        json={
            "title": "Live role",
            "type": "INTERNSHIP",
            "description": "x",
            "required_skills": "x",
            "eligibility": "x",
            "application_deadline": "2030-01-01",
        },
    )
    opp_id = res.get_json()["data"]["opportunity"]["id"]
    client.post(f"/api/v1/recruiter/opportunities/{opp_id}/submit")
    logout(client)
    _admin_client(app, client)
    client.patch(f"/api/v1/admin/opportunities/{opp_id}/approve")
    logout(client)

    login(client, "r1@test.com", RECRUITER_PASSWORD)
    res = client.put(
        f"/api/v1/recruiter/opportunities/{opp_id}",
        json={
            "title": "Live role (updated)",
            "type": "INTERNSHIP",
            "description": "changed",
            "required_skills": "x",
            "eligibility": "x",
            "application_deadline": "2030-02-01",
        },
    )
    assert res.status_code == 200
    from app.models.opportunity import Opportunity

    with app.app_context():
        from app.extensions import db

        assert db.session.get(Opportunity, opp_id).status == "PENDING_REVIEW"


def test_suspended_user_cannot_login(app, client):
    register_student(app, client, email="s1@test.edu")
    logout(client)
    _admin_client(app, client)

    from app.models.user import User

    with app.app_context():
        user_id = User.query.filter_by(email="s1@test.edu").first().id

    res = client.patch(f"/api/v1/admin/users/{user_id}/suspend")
    assert res.status_code == 200
    logout(client)

    res = login(client, "s1@test.edu", "Student@123")
    assert res.status_code == 401


def test_admin_cannot_suspend_admin(app, client):
    _admin_client(app, client)
    from app.models.user import User

    with app.app_context():
        admin_id = User.query.filter_by(email="admin@test.edu").first().id
    res = client.patch(f"/api/v1/admin/users/{admin_id}/suspend")
    assert res.status_code == 409


def test_audit_log_records_approvals(app, client):
    register_recruiter(app, client, email="r1@test.com", approved=False)
    _admin_client(app, client)

    from app.models.user import User

    with app.app_context():
        recruiter_id = User.query.filter_by(email="r1@test.com").first().recruiter_profile.id
    client.patch(f"/api/v1/admin/recruiters/{recruiter_id}/approve")

    res = client.get("/api/v1/admin/audit-logs")
    assert res.status_code == 200
    actions = [log["action"] for log in res.get_json()["data"]["logs"]]
    assert "ADMIN_APPROVED_RECRUITER" in actions


def test_admin_analytics(app, client):
    register_recruiter(app, client, email="r1@test.com", approved=True)
    res = client.post(
        "/api/v1/recruiter/opportunities",
        json={
            "title": "Analytics role",
            "type": "INTERNSHIP",
            "description": "x",
            "required_skills": "x",
            "eligibility": "B.Tech, graduating 2026",
            "application_deadline": "2030-01-01",
        },
    )
    opp_id = res.get_json()["data"]["opportunity"]["id"]
    client.post(f"/api/v1/recruiter/opportunities/{opp_id}/submit")
    logout(client)
    register_student(app, client, email="s1@test.edu")
    _admin_client(app, client)
    client.patch(f"/api/v1/admin/opportunities/{opp_id}/approve")
    logout(client)

    login(client, "s1@test.edu", "Student@123")
    res = client.post(f"/api/v1/student/opportunities/{opp_id}/apply", json={})
    assert res.status_code == 201, res.get_data(as_text=True)
    logout(client)

    _admin_client(app, client)
    res = client.get("/api/v1/admin/analytics")
    assert res.status_code == 200
    analytics = res.get_json()["data"]["analytics"]
    assert analytics["stats"]["total_applications"] == 1
    assert analytics["internship_applications"] == 1


def test_reopen_opportunity_requires_admin_review(app, client):
    """Reopening a closed opportunity should go to PENDING_REVIEW, not APPROVED."""
    register_recruiter(app, client, email="r1@test.com", approved=True)
    res = client.post(
        "/api/v1/recruiter/opportunities",
        json={
            "title": "Reopen test",
            "type": "INTERNSHIP",
            "description": "x",
            "required_skills": "x",
            "eligibility": "x",
            "application_deadline": "2030-01-01",
        },
    )
    opp_id = res.get_json()["data"]["opportunity"]["id"]
    client.post(f"/api/v1/recruiter/opportunities/{opp_id}/submit")
    logout(client)
    _admin_client(app, client)
    client.patch(f"/api/v1/admin/opportunities/{opp_id}/approve")
    logout(client)

    # Close the opportunity
    login(client, "r1@test.com", RECRUITER_PASSWORD)
    client.post(f"/api/v1/recruiter/opportunities/{opp_id}/close")

    # Reopen it
    res = client.post(f"/api/v1/recruiter/opportunities/{opp_id}/reopen")
    assert res.status_code == 200

    from app.models.opportunity import Opportunity

    with app.app_context():
        from app.extensions import db

        opp = db.session.get(Opportunity, opp_id)
        assert opp.status == "PENDING_REVIEW", f"Expected PENDING_REVIEW, got {opp.status}"
        assert opp.published_at is None


def logout(client):
    return client.post("/api/v1/auth/logout")
