"""Interviews — scheduling rules, cancellation, conflict detection, ownership."""

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
)

TODAY = datetime.date.today()
FUTURE = (TODAY + datetime.timedelta(days=10)).isoformat()


def _setup(app, client):
    register_recruiter(app, client, email="r1@test.com", approved=True)
    opp_id = create_opportunity(client)
    approve_opportunity(app, client, opp_id)
    logout(client)
    register_student(app, client, email="s1@test.edu")
    apply_as_student(client, opp_id)
    logout(client)
    login(client, "r1@test.com", "Recruiter@123")
    return opp_id


def _shortlist(app, client, opp_id):
    application_id = get_application(app, "s1@test.edu", opp_id)
    assert application_id is not None
    client.patch(
        f"/api/v1/recruiter/applications/{application_id}/status",
        json={"status": "SHORTLISTED"},
    )
    return application_id


def _schedule(client, application_id, **overrides):
    payload = {
        "scheduled_date": FUTURE,
        "scheduled_time": "10:30",
        "mode": "ONLINE",
        "location": "Remote",
        "meeting_details": "https://meet.example.com/x",
        "additional_instructions": "Keep camera on",
    }
    payload.update(overrides)
    return client.post(
        f"/api/v1/recruiter/applications/{application_id}/interviews", json=payload
    )


def _app_status(app, application_id):
    from app.models.application import Application

    with app.app_context():
        return db.session.get(Application, application_id).status


def test_schedule_interview_for_shortlisted(app, client):
    opp_id = _setup(app, client)
    application_id = _shortlist(app, client, opp_id)
    res = _schedule(client, application_id)
    assert res.status_code == 201, res.get_data(as_text=True)
    assert res.get_json()["data"]["interview"]["status"] == "SCHEDULED"
    assert _app_status(app, application_id) == "INTERVIEW_SCHEDULED"


def test_cannot_schedule_before_shortlist(app, client):
    opp_id = _setup(app, client)
    application_id = get_application(app, "s1@test.edu", opp_id)
    res = _schedule(client, application_id)
    assert res.status_code == 409
    assert res.get_json()["error"]["code"] == "NOT_SHORTLISTED"


def test_schedule_rejects_past_date(app, client):
    opp_id = _setup(app, client)
    application_id = _shortlist(app, client, opp_id)
    res = _schedule(
        client, application_id, scheduled_date=(TODAY - datetime.timedelta(days=1)).isoformat()
    )
    assert res.status_code == 409


def test_schedule_rejects_invalid_time(app, client):
    opp_id = _setup(app, client)
    application_id = _shortlist(app, client, opp_id)
    res = _schedule(client, application_id, scheduled_time="not-a-time")
    assert res.status_code == 409


def test_cancel_interview_returns_status_to_shortlisted(app, client):
    opp_id = _setup(app, client)
    application_id = _shortlist(app, client, opp_id)
    res = _schedule(client, application_id)
    interview_id = res.get_json()["data"]["interview"]["id"]

    res = client.post(f"/api/v1/recruiter/interviews/{interview_id}/cancel")
    assert res.status_code == 200
    assert _app_status(app, application_id) == "SHORTLISTED"
    from app.models.interview import Interview

    with app.app_context():
        assert db.session.get(Interview, interview_id).status == "CANCELLED"


def test_reschedule_marks_previous_cancelled(app, client):
    opp_id = _setup(app, client)
    application_id = _shortlist(app, client, opp_id)
    first = _schedule(client, application_id).get_json()["data"]["interview"]
    second = _schedule(client, application_id).get_json()["data"]["interview"]
    assert first["id"] != second["id"]
    from app.models.interview import Interview

    with app.app_context():
        assert db.session.get(Interview, first["id"]).status == "CANCELLED"
        assert db.session.get(Interview, second["id"]).status == "SCHEDULED"
    assert _app_status(app, application_id) == "INTERVIEW_SCHEDULED"


def test_recruiter_cannot_manage_other_recruiters_interview(app, client):
    opp_id = _setup(app, client)
    application_id = _shortlist(app, client, opp_id)
    res = _schedule(client, application_id)
    interview_id = res.get_json()["data"]["interview"]["id"]
    logout(client)

    register_recruiter(app, client, email="r2@test.com", approved=True)
    res = client.post(f"/api/v1/recruiter/interviews/{interview_id}/cancel")
    assert res.status_code == 404


def test_edit_interview_marks_updated(app, client):
    opp_id = _setup(app, client)
    application_id = _shortlist(app, client, opp_id)
    res = _schedule(client, application_id)
    interview_id = res.get_json()["data"]["interview"]["id"]

    res = client.put(
        f"/api/v1/recruiter/interviews/{interview_id}",
        json={
            "scheduled_date": (TODAY + datetime.timedelta(days=12)).isoformat(),
            "scheduled_time": "14:00",
            "mode": "OFFICE",
            "location": "Office HQ",
        },
    )
    assert res.status_code == 200
    assert res.get_json()["data"]["interview"]["status"] == "UPDATED"


def logout(client):
    return client.post("/api/v1/auth/logout")
