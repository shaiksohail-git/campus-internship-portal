"""Smoke test — render every page for every role via the test client.

Uses the real default config (seeded SQLite DB) so templates, CSRF, sessions
and role guards are all exercised. Run: python tests/smoke_pages.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

app = create_app()
client = app.test_client()


def csrf_token(page="/"):
    html = client.get(page).get_data(as_text=True)
    match = re.search(r'name="csrf-token" content="([^"]+)"', html)
    return match.group(1) if match else ""


def login(email, password):
    token = csrf_token("/login")
    res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
        headers={"X-CSRF-Token": token},
    )
    return res


def check(path, expected=200):
    res = client.get(path)
    status = "OK" if res.status_code == expected else "FAIL"
    print(f"[{status}] {res.status_code} {path}")
    if status == "FAIL":
        snippet = res.get_data(as_text=True)[:200].replace("\n", " ")
        print(f"        {snippet}")
    return res


def logout():
    token = csrf_token()
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": token})


# ---------------- landing & auth ----------------
check("/", 200)
check("/login", 200)
check("/register/student", 200)
check("/register/recruiter", 200)
check("/forgot-password", 200)

# ---------------- student ----------------
res = login("student1@college.edu", "Student@123")
print("student login:", res.status_code, res.get_json()["data"]["redirect"])
check("/student/dashboard")
check("/student/profile")
check("/student/opportunities")
check("/student/opportunities?search=Python&type=INTERNSHIP")
check("/student/opportunities/1")
check("/student/applications")
check("/student/interviews")
check("/notifications")
check("/dev/mailbox")
logout()

# ---------------- recruiter ----------------
res = login("techcorp@company.com", "Recruiter@123")
print("recruiter login:", res.status_code, res.get_json()["data"]["redirect"])
check("/recruiter/dashboard")
check("/recruiter/profile")
check("/recruiter/opportunities")
check("/recruiter/opportunities/new")
check("/recruiter/opportunities/1")
check("/recruiter/opportunities/1/edit")
check("/recruiter/opportunities/1/applicants")
check("/recruiter/interviews")
check("/recruiter/analytics")
logout()

# ---------------- admin ----------------
res = login("admin@college.edu", "Admin@123")
print("admin login:", res.status_code, res.get_json()["data"]["redirect"])
check("/admin/dashboard")
check("/admin/students")
check("/admin/recruiters")
check("/admin/opportunities")
check("/admin/applications")
check("/admin/interviews")
check("/admin/analytics")
check("/admin/audit-logs")

# ---------------- role guards ----------------
logout()
res = login("student1@college.edu", "Student@123")
print("student guards:")
check("/admin/dashboard", 302)  # redirects to forbidden
check("/recruiter/dashboard", 302)

print("\nSmoke test done.")
