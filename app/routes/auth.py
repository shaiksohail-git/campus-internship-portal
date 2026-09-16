"""Auth routes — pages (server-rendered GET) and REST API for auth actions."""

from flask import Blueprint, redirect, render_template, request, session, url_for

from app.middleware.auth import login_required, login_user, logout_user
from app.middleware.security import auth_rate_limit
from app.services import auth_service
from app.utils.api import json_body, ok
from app.utils.errors import NotFoundError, ValidationError
from app.utils.validators import validate_email, validate_password

bp = Blueprint("auth", __name__)

# ------------------------------------------------------------------ pages


@bp.get("/login")
def login_page():
    return render_template("auth/login.html", next_url=request.args.get("next", ""))


@bp.get("/register/student")
def register_student_page():
    from app.models.college import College

    return render_template(
        "auth/register_student.html",
        colleges=College.query.order_by(College.name).limit(50).all(),
    )


@bp.get("/register/recruiter")
def register_recruiter_page():
    return render_template("auth/register_recruiter.html")


@bp.get("/forgot-password")
def forgot_password_page():
    return render_template("auth/forgot_password.html")


@bp.get("/reset-password/<token>")
def reset_password_page(token):
    return render_template("auth/reset_password.html", token=token)


@bp.get("/verify-email")
def verify_email_page():
    token = request.args.get("token", "")
    if not token:
        return render_template("auth/verify_email.html", success=False,
                               message="Missing verification token.")
    try:
        user = auth_service.verify_email(token)
        return render_template("auth/verify_email.html", success=True, user=user)
    except Exception as exc:  # noqa: BLE001 — show friendly message
        return render_template("auth/verify_email.html", success=False, message=str(exc))


@bp.get("/verify")
@login_required
def verify_pending_page():
    from flask import g

    current_user = g.current_user
    if current_user and current_user.is_verified:
        return redirect(url_for("pages.landing"))
    return render_template("auth/verify_pending.html", email=current_user.email)


# ------------------------------------------------------------------ api

def _safe_next_url(value):
    """Only allow local relative redirect targets (open-redirect protection)."""
    if value and value.startswith("/") and not value.startswith("//"):
        return value
    return None


@bp.post("/api/v1/auth/register/student")
@auth_rate_limit("RATE_LIMIT_REGISTER")
def register_student():
    data = json_body()
    user = auth_service.register_student(data)
    login_user(user)
    return ok(
        {"user": user.to_dict(), "redirect": "/verify"},
        "Account created! Please verify your email to activate it.",
        status=201,
    )


@bp.post("/api/v1/auth/register/recruiter")
@auth_rate_limit("RATE_LIMIT_REGISTER")
def register_recruiter():
    data = json_body()
    user = auth_service.register_recruiter(data)
    login_user(user)
    return ok(
        {"user": user.to_dict(), "redirect": "/verify"},
        "Account created! Please verify your email, then an administrator will review your company.",
        status=201,
    )


@bp.post("/api/v1/auth/login")
@auth_rate_limit("RATE_LIMIT_LOGIN")
def login():
    data = json_body()
    email = validate_email(data.get("email"))
    password = data.get("password") or ""
    user = auth_service.authenticate(email, password)
    login_user(user)

    target = _safe_next_url(data.get("next") or request.args.get("next"))
    if target is None:
        target = "/verify" if not user.is_verified else auth_service.login_redirect_target(user)
    return ok(
        {"user": user.to_dict(), "redirect": target},
        "Welcome back!",
    )


@bp.post("/api/v1/auth/logout")
@login_required
def logout():
    logout_user()
    return ok({}, "You have been logged out.")


@bp.get("/api/v1/auth/me")
def me():
    from flask import g

    user = g.current_user
    if user is None:
        return ok({"user": None}, "Not logged in.")
    return ok({"user": user.to_dict()})


@bp.get("/api/v1/auth/csrf")
def csrf():
    return ok({"csrf_token": session.get("csrf_token")})


@bp.post("/api/v1/auth/resend-verification")
@auth_rate_limit("RATE_LIMIT_EMAIL")
def resend_verification():
    data = json_body()
    auth_service.resend_verification(data.get("email"))
    return ok({}, "If an unverified account exists for that email, a new verification link was sent.")


@bp.post("/api/v1/auth/forgot-password")
@auth_rate_limit("RATE_LIMIT_EMAIL")
def forgot_password():
    data = json_body()
    auth_service.forgot_password(data.get("email"))
    return ok({}, "If that email exists, a password reset link has been sent.")


@bp.post("/api/v1/auth/reset-password")
@auth_rate_limit("RATE_LIMIT_EMAIL")
def reset_password():
    data = json_body()
    auth_service.reset_password(
        data.get("token"), data.get("password"), data.get("password_confirm")
    )
    return ok({}, "Your password has been reset. You can now log in.")
