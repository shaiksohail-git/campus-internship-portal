"""Applications — apply flow, duplicate prevention, deadlines, eligibility,
and the status state machine."""

import datetime

from app.extensions import db
from conftest import (
    apply_as_student,
    approve_opportunity,
    create_opportunity,
    get_application,
    login,
    register_recruiter,
    register_student,
    set_opportunity_deadline,
)


def _recruiter_with_live_job(app, client, **overrides):
    """Approved recruiter with a live (admin-approved) opportunity."""
    opp_id = create_opportunity(client, **overrides)
    approve_opportunity(app, client, opp_id)
    return opp_id


def test_student_applies_successfully(app, client):
    register_recruiter(app, client, email="r1@test.com", approved=True)
    opp_id = _recruiter_with_live_job(app, client)
    logout(client)

    register_student(app, client, email="s1@test.edu")
    res = apply_as_student(client, opp_id)
    assert res.status_code == 201
    assert res.get_json()["data"]["application"]["status"] == "APPLIED"

    application_id = get_application(app, "s1@test.edu", opp_id)
    assert application_id is not None

    # auto-picked active resume + student notification created
    from app.models.application import Application
    from app.models.notification import Notification

    with app.app_context():
        application = db.session.get(Application, application_id)
        assert application.resume is not None
        student_notifs = Notification.query.filter_by(
            user_id=application.student.user_id
        ).all()
        assert any(n.type == "APPLICATION_SUBMITTED" for n in student_notifs)


def test_duplicate_application_rejected(app, client):
    register_recruiter(app, client, email="r1@test.com", approved=True)
    opp_id = _recruiter_with_live_job(app, client)
    logout(client)

    register_student(app, client, email="s1@test.edu")
    assert apply_as_student(client, opp_id).status_code == 201
    res = apply_as_student(client, opp_id)
    assert res.status_code == 409
    assert res.get_json()["error"]["code"] == "DUPLICATE_APPLICATION"


def test_apply_after_deadline_rejected(app, client):
    register_recruiter(app, client, email="r1@test.com", approved=True)
    opp_id = _recruiter_with_live_job(app, client)
    set_opportunity_deadline(app, opp_id, days_ago=1)
    logout(client)

    register_student(app, client, email="s1@test.edu")
    res = apply_as_student(client, opp_id)
    assert res.status_code == 409
    assert res.get_json()["error"]["code"] == "APPLICATION_DEADLINE_PASSED"


def test_apply_without_resume_rejected(app, client):
    register_recruiter(app, client, email="r1@test.com", approved=True)
    opp_id = _recruiter_with_live_job(app, client)
    logout(client)

    register_student(app, client, email="s1@test.edu", with_resume=False)
    res = apply_as_student(client, opp_id)
    assert res.status_code == 409
    assert res.get_json()["error"]["code"] == "RESUME_REQUIRED"


def test_apply_to_unpublished_opportunity_rejected(app, client):
    register_recruiter(app, client, email="r1@test.com", approved=True)
    opp_id = create_opportunity(client)  # submitted but NOT admin-approved
    logout(client)

    register_student(app, client, email="s1@test.edu")
    res = apply_as_student(client, opp_id)
    assert res.status_code == 409
    assert res.get_json()["error"]["code"] == "OPPORTUNITY_CLOSED"


def test_apply_not_eligible_rejected(app, client):
    register_recruiter(app, client, email="r1@test.com", approved=True)
    opp_id = _recruiter_with_live_job(app, client, eligibility="B.Tech, graduating 2027 only")
    logout(client)

    # student graduating 2026
    register_student(app, client, email="s1@test.edu", graduation_year=2026)
    res = apply_as_student(client, opp_id)
    assert res.status_code == 409
    assert res.get_json()["error"]["code"] == "NOT_ELIGIBLE"


def test_valid_status_transition(app, client):
    register_recruiter(app, client, email="r1@test.com", approved=True)
    opp_id = _recruiter_with_live_job(app, client)
    logout(client)
    register_student(app, client, email="s1@test.edu")
    apply_as_student(client, opp_id)
    logout(client)

    login(client, "r1@test.com", "Recruiter@123")
    application_id = get_application(app, "s1@test.edu", opp_id)
    assert application_id is not None
    res = client.patch(
        f"/api/v1/recruiter/applications/{application_id}/status",
        json={"status": "UNDER_REVIEW"},
    )
    assert res.status_code == 200
    assert res.get_json()["data"]["application"]["status"] == "UNDER_REVIEW"


def test_invalid_status_transition_rejected(app, client):
    register_recruiter(app, client, email="r1@test.com", approved=True)
    opp_id = _recruiter_with_live_job(app, client)
    logout(client)
    register_student(app, client, email="s1@test.edu")
    apply_as_student(client, opp_id)
    logout(client)

    login(client, "r1@test.com", "Recruiter@123")
    application_id = get_application(app, "s1@test.edu", opp_id)
    assert application_id is not None
    # APPLIED -> SELECTED is not allowed by the state machine
    res = client.patch(
        f"/api/v1/recruiter/applications/{application_id}/status",
        json={"status": "SELECTED"},
    )
    assert res.status_code == 409
    assert res.get_json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_full_pipeline_to_selected(app, client):
    register_recruiter(app, client, email="r1@test.com", approved=True)
    opp_id = _recruiter_with_live_job(app, client)
    logout(client)
    register_student(app, client, email="s1@test.edu")
    apply_as_student(client, opp_id)
    logout(client)

    login(client, "r1@test.com", "Recruiter@123")
    application_id = get_application(app, "s1@test.edu", opp_id)
    assert application_id is not None
    # status steps up to shortlisted via PATCH…
    for status in ("UNDER_REVIEW", "SHORTLISTED"):
        res = client.patch(
            f"/api/v1/recruiter/applications/{application_id}/status",
            json={"status": status},
        )
        assert res.status_code == 200, res.get_data(as_text=True)
    # …INTERVIEW_SCHEDULED is owned by the interview scheduling transaction…
    future = (datetime.date.today() + datetime.timedelta(days=10)).isoformat()
    res = client.post(
        f"/api/v1/recruiter/applications/{application_id}/interviews",
        json={"scheduled_date": future, "scheduled_time": "10:30", "mode": "ONLINE"},
    )
    assert res.status_code == 201, res.get_data(as_text=True)
    # …then the final decision.
    res = client.patch(
        f"/api/v1/recruiter/applications/{application_id}/status",
        json={"status": "SELECTED"},
    )
    assert res.status_code == 200, res.get_data(as_text=True)
    with app.app_context():
        from app.models.application import Application

        assert db.session.get(Application, application_id).status == "SELECTED"


def test_student_sees_own_applications(app, client):
    register_recruiter(app, client, email="r1@test.com", approved=True)
    opp_id = _recruiter_with_live_job(app, client)
    logout(client)
    register_student(app, client, email="s1@test.edu")
    apply_as_student(client, opp_id)
    res = client.get("/api/v1/student/applications")
    assert res.status_code == 200
    apps = res.get_json()["data"]["applications"]
    assert len(apps) == 1
    assert apps[0]["opportunity_title"] == "Software Engineer"


def logout(client):
    return client.post("/api/v1/auth/logout")
