"""Security — role isolation, ownership checks, verification gates."""

from conftest import (
    RECRUITER_PASSWORD,
    STUDENT_PASSWORD,
    apply_as_student,
    approve_opportunity,
    create_opportunity,
    login,
    make_admin,
    register_recruiter,
    register_student,
    upload_resume,
)


def test_unauthenticated_api_returns_401(app, client):
    res = client.get("/api/v1/student/applications")
    assert res.status_code == 401
    assert res.get_json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_unauthenticated_page_redirects_to_login(app, client):
    res = client.get("/student/dashboard")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]


def test_student_cannot_access_admin_api(app, client):
    register_student(app, client)
    res = client.get("/api/v1/admin/dashboard")
    assert res.status_code == 403


def test_student_cannot_access_recruiter_api(app, client):
    register_student(app, client)
    res = client.get("/api/v1/recruiter/opportunities")
    assert res.status_code == 403


def test_student_cannot_access_admin_page(app, client):
    register_student(app, client)
    res = client.get("/admin/dashboard")
    assert res.status_code == 302  # redirected to forbidden page
    follow = client.get("/admin/dashboard", follow_redirects=True)
    assert b"403" in follow.data or b"Access denied" in follow.data


def test_recruiter_cannot_access_admin_api(app, client):
    register_recruiter(app, client)
    res = client.get("/api/v1/admin/students")
    assert res.status_code == 403


def test_recruiter_cannot_access_student_api(app, client):
    register_recruiter(app, client)
    res = client.get("/api/v1/student/opportunities")
    assert res.status_code == 403


def test_unverified_student_blocked_from_protected_api(app, client):
    register_student(app, client, verify=False, with_resume=False)
    res = client.get("/api/v1/student/applications")
    assert res.status_code == 403
    assert res.get_json()["error"]["code"] == "VERIFICATION_REQUIRED"


def test_recruiter_cannot_modify_another_recruiters_opportunity(app, client):
    register_recruiter(app, client, email="r1@test.com", approved=True)
    opp_id = create_opportunity(client, title="First posting")
    logout(client)

    register_recruiter(app, client, email="r2@test.com", approved=True)
    res = client.put(
        f"/api/v1/recruiter/opportunities/{opp_id}",
        json={
            "title": "Hacked",
            "type": "FULL_TIME",
            "description": "x",
            "required_skills": "x",
            "eligibility": "x",
            "application_deadline": "2030-01-01",
        },
    )
    assert res.status_code == 404  # not 403, so data cannot be probed


def test_recruiter_cannot_view_another_recruiters_applicants(app, client):
    register_recruiter(app, client, email="r1@test.com", approved=True)
    opp_id = create_opportunity(client, title="Posting A")
    logout(client)

    register_student(app, client, email="s1@test.edu")
    apply_as_student(client, opp_id)
    logout(client)

    register_recruiter(app, client, email="r2@test.com", approved=True)
    res = client.get(f"/api/v1/recruiter/opportunities/{opp_id}/applications")
    assert res.status_code == 404


def test_unapproved_recruiter_cannot_create_opportunity(app, client):
    register_recruiter(app, client, approved=False)
    res = client.post(
        "/api/v1/recruiter/opportunities",
        json={
            "title": "x",
            "type": "INTERNSHIP",
            "description": "x",
            "required_skills": "x",
            "eligibility": "x",
            "application_deadline": "2030-01-01",
        },
    )
    assert res.status_code == 409
    assert res.get_json()["error"]["code"] == "RECRUITER_NOT_APPROVED"


def test_student_cannot_download_another_students_resume(app, client):
    register_student(app, client, email="s1@test.edu")
    resume = upload_resume(client, filename="s1.pdf")
    logout(client)

    register_student(app, client, email="s2@test.edu")
    res = client.get(f"/api/v1/resumes/{resume['id']}/download")
    assert res.status_code == 403
    assert res.get_json()["error"]["code"] == "RESUME_FORBIDDEN"


def test_opportunity_must_be_approved_to_be_visible(app, client):
    register_recruiter(app, client, email="r1@test.com", approved=True)
    # draft (never submitted)
    res = client.post(
        "/api/v1/recruiter/opportunities",
        json={
            "title": "Draft only",
            "type": "INTERNSHIP",
            "description": "x",
            "required_skills": "x",
            "eligibility": "x",
            "application_deadline": "2030-01-01",
        },
    )
    draft_id = res.get_json()["data"]["opportunity"]["id"]
    logout(client)

    register_student(app, client, email="s1@test.edu")
    res = client.get(f"/api/v1/student/opportunities/{draft_id}")
    assert res.status_code == 404


def test_approved_opportunity_visible_to_students(app, client):
    register_recruiter(app, client, email="r1@test.com", approved=True)
    opp_id = create_opportunity(client, title="Live posting")
    approve_opportunity(app, client, opp_id)
    logout(client)

    register_student(app, client, email="s1@test.edu")
    res = client.get(f"/api/v1/student/opportunities/{opp_id}")
    assert res.status_code == 200


def test_student_cannot_apply_as_recruiter(app, client):
    register_student(app, client)
    res = client.patch(
        "/api/v1/recruiter/applications/1/status", json={"status": "SELECTED"}
    )
    assert res.status_code == 403


def logout(client):
    return client.post("/api/v1/auth/logout")
