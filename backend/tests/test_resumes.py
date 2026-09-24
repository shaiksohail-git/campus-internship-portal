"""Resumes — upload validation, secure downloads, cross-role authorization."""

import io

from conftest import (
    apply_as_student,
    approve_opportunity,
    create_opportunity,
    get_application,
    login,
    register_recruiter,
    register_student,
    upload_resume,
)


def test_upload_valid_pdf(app, client):
    register_student(app, client, with_resume=False)
    resume = upload_resume(client, filename="my_resume.pdf")
    assert resume["file_type"] == "pdf"
    assert resume["file_name"] == "my_resume.pdf"


def test_upload_rejects_unsupported_type(app, client):
    register_student(app, client, with_resume=False)
    data = {"file": (io.BytesIO(b"MZ executable"), "virus.exe")}
    res = client.post("/api/v1/student/resumes", data=data, content_type="multipart/form-data")
    assert res.status_code == 422


def test_upload_rejects_missing_file(app, client):
    register_student(app, client, with_resume=False)
    res = client.post("/api/v1/student/resumes", data={}, content_type="multipart/form-data")
    assert res.status_code == 422


def test_upload_rejects_oversized_file(app, client):
    register_student(app, client, with_resume=False)
    big = b"x" * (6 * 1024 * 1024)  # 6 MB > 5 MB limit
    data = {"file": (io.BytesIO(big), "big.pdf")}
    res = client.post("/api/v1/student/resumes", data=data, content_type="multipart/form-data")
    assert res.status_code == 422


def test_student_downloads_own_resume(app, client):
    register_student(app, client, with_resume=False)
    resume = upload_resume(client)
    res = client.get(f"/api/v1/resumes/{resume['id']}/download")
    assert res.status_code == 200
    assert res.data == b"%PDF-1.4 fake resume"


def test_resume_download_requires_auth(app, client):
    register_student(app, client, with_resume=False)
    resume = upload_resume(client)
    logout(client)
    res = client.get(f"/api/v1/resumes/{resume['id']}/download")
    assert res.status_code == 401


def test_recruiter_can_download_applicants_resume(app, client):
    register_recruiter(app, client, email="r1@test.com", approved=True)
    opp_id = create_opportunity(client)
    approve_opportunity(app, client, opp_id)
    logout(client)

    register_student(app, client, email="s1@test.edu", with_resume=False)
    resume = upload_resume(client)
    apply_as_student(client, opp_id, resume_id=resume["id"])
    logout(client)

    login(client, "r1@test.com", "Recruiter@123")
    res = client.get(f"/api/v1/resumes/{resume['id']}/download")
    assert res.status_code == 200


def test_recruiter_cannot_download_unrelated_resume(app, client):
    register_recruiter(app, client, email="r1@test.com", approved=True)
    opp_id = create_opportunity(client)
    logout(client)

    register_student(app, client, email="s1@test.edu", with_resume=False)
    resume = upload_resume(client)  # student never applied to r1's opportunity
    logout(client)

    login(client, "r1@test.com", "Recruiter@123")
    res = client.get(f"/api/v1/resumes/{resume['id']}/download")
    assert res.status_code == 403


def test_student_cannot_delete_other_resume(app, client):
    register_student(app, client, email="s1@test.edu", with_resume=False)
    resume = upload_resume(client, filename="s1.pdf")
    logout(client)

    register_student(app, client, email="s2@test.edu", with_resume=False)
    res = client.delete(f"/api/v1/student/resumes/{resume['id']}")
    assert res.status_code == 404


def test_admin_can_download_any_resume(app, client):
    register_student(app, client, with_resume=False)
    resume = upload_resume(client)
    logout(client)

    from conftest import ADMIN_PASSWORD, make_admin

    make_admin(app)
    login(client, "admin@test.edu", ADMIN_PASSWORD)
    res = client.get(f"/api/v1/resumes/{resume['id']}/download")
    assert res.status_code == 200


def logout(client):
    return client.post("/api/v1/auth/logout")
