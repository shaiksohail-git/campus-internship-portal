"""Authentication service — registration, login, email verification,
password reset. All security rules live here (or in middleware), never in views.
"""

from datetime import timedelta

from flask import current_app, url_for

from app.extensions import db
from app.models.college import College
from app.models.enums import (
    NotificationType,
    RecruiterApprovalStatus,
    Role,
)
from app.models.recruiter import RecruiterProfile
from app.models.student import StudentProfile
from app.models.token import AuthToken
from app.models.user import User, utcnow
from app.services import notification_service
from app.utils import validators
from app.utils.errors import (
    AuthenticationError,
    BusinessRuleError,
    ConflictError,
    NotFoundError,
)
from app.utils.tokens import generate_token, hash_token


# ---------------------------------------------------------------- register

def register_student(data):
    email = validators.validate_email(data.get("email"))
    password = validators.validate_password(
        data.get("password"), data.get("password_confirm")
    )
    full_name = validators.validate_required(data.get("full_name"), "Full name", 150)

    _ensure_email_available(email)

    college = find_or_create_college(data.get("college"))

    user = User(email=email, role=Role.STUDENT, is_verified=False)
    user.set_password(password)
    profile = StudentProfile(
        full_name=full_name,
        phone=validators.validate_phone(data.get("phone")),
        college=college,
        degree=validators.validate_optional_text(data.get("degree"), "Degree", 120),
        department=validators.validate_optional_text(data.get("department"), "Department", 120),
        graduation_year=validators.validate_graduation_year(data.get("graduation_year")),
        skills=validators.validate_skills(data.get("skills")),
    )
    profile.user = user
    db.session.add(user)
    db.session.flush()  # get user.id before generating token

    token = _issue_token(user, "EMAIL_VERIFICATION")
    _send_verification_email(user, token)
    db.session.commit()
    return user


def register_recruiter(data):
    email = validators.validate_email(data.get("email"))
    password = validators.validate_password(
        data.get("password"), data.get("password_confirm")
    )
    company_name = validators.validate_required(data.get("company_name"), "Company name", 200)

    _ensure_email_available(email)

    user = User(email=email, role=Role.RECRUITER, is_verified=False)
    user.set_password(password)
    profile = RecruiterProfile(
        company_name=company_name,
        company_description=validators.validate_optional_text(
            data.get("company_description"), "Company description", 2000
        ),
        company_email=(
            validators.validate_email(data.get("company_email"))
            if data.get("company_email")
            else email
        ),
        website=validators.validate_url(data.get("website")),
        contact_person=validators.validate_optional_text(data.get("contact_person"), "Contact person", 150),
        contact_phone=validators.validate_phone(data.get("contact_phone")),
        approval_status=RecruiterApprovalStatus.PENDING,
    )
    profile.user = user
    db.session.add(user)
    db.session.flush()

    token = _issue_token(user, "EMAIL_VERIFICATION")
    _send_verification_email(user, token)

    notification_service.notify_all_admins(
        NotificationType.RECRUITER_PENDING,
        "New recruiter pending approval",
        f"{company_name} ({email}) registered and is awaiting verification/approval.",
    )
    db.session.commit()
    return user


def _ensure_email_available(email):
    if User.query.filter_by(email=email).first():
        raise ConflictError(
            "An account with this email already exists.", code="EMAIL_TAKEN"
        )


def find_or_create_college(name):
    """Normalize + reuse colleges instead of storing free-text names."""
    if not name:
        return None
    name = name.strip()
    if not name:
        return None
    college = College.query.filter_by(name=name).first()
    if college:
        return college
    college = College(name=name)
    db.session.add(college)
    db.session.flush()
    return college


# ---------------------------------------------------------------- login

def authenticate(email, password):
    email = validators.validate_email(email)
    user = User.query.filter_by(email=email).first()
    if user is None or not user.is_active:
        raise AuthenticationError("Invalid email or password.", code="INVALID_CREDENTIALS")
    if not user.check_password(password):
        raise AuthenticationError("Invalid email or password.", code="INVALID_CREDENTIALS")
    return user


def login_redirect_target(user):
    if user.is_student:
        return "/student/dashboard"
    if user.is_recruiter:
        return "/recruiter/dashboard"
    return "/admin/dashboard"


# ---------------------------------------------------------------- tokens

def _issue_token(user, token_type, ttl_hours=None):
    ttl_hours = ttl_hours or current_app.config["TOKEN_TTL_HOURS"]
    raw = generate_token()
    record = AuthToken(
        user_id=user.id,
        type=token_type,
        token_hash=hash_token(raw),
        expires_at=utcnow() + timedelta(hours=ttl_hours),
    )
    db.session.add(record)
    db.session.flush()
    return raw


def _consume_token(raw_token, token_type, user=None):
    """Validate + consume (single-use) a token. Returns the AuthToken.

    Consumption uses an atomic UPDATE ... WHERE used_at IS NULL so two
    concurrent requests cannot both use the same token (TOCTOU-safe).
    """
    if not raw_token:
        raise BusinessRuleError("A valid token is required.", code="INVALID_TOKEN")
    record = AuthToken.query.filter_by(
        token_hash=hash_token(raw_token), type=token_type
    ).first()
    if record is None:
        raise BusinessRuleError("This link is invalid or has already been used.", code="INVALID_TOKEN")
    if record.is_expired:
        raise BusinessRuleError("This link has expired. Please request a new one.", code="TOKEN_EXPIRED")
    if user is not None and record.user_id != user.id:
        raise BusinessRuleError("This link does not belong to your account.", code="INVALID_TOKEN")

    from sqlalchemy import update

    claimed = db.session.execute(
        update(AuthToken)
        .where(AuthToken.id == record.id, AuthToken.used_at.is_(None))
        .values(used_at=utcnow())
    )
    if claimed.rowcount == 0:
        raise BusinessRuleError("This link has already been used.", code="INVALID_TOKEN")
    db.session.flush()
    record.used_at = utcnow()
    return record


# ---------------------------------------------------------------- email

def _send_verification_email(user, token):
    link = url_for("auth.verify_email_page", token=token, _external=True)
    subject = "Verify your Campus Placement Portal account"
    body = (
        f"Hi {user.display_name},\n\n"
        f"Welcome to the Campus Placement Portal. Please verify your email address "
        f"by clicking the link below:\n\n{link}\n\n"
        f"This link expires in {current_app.config['TOKEN_TTL_HOURS']} hours.\n\n"
        f"If you did not create this account, you can ignore this email."
    )
    notification_service.notify(
        user,
        NotificationType.EMAIL_VERIFICATION,
        "Verify your email",
        "We sent a verification link to your email address. Please verify to activate your account.",
        email_subject=subject,
        email_body=body,
    )


# ---------------------------------------------------------------- verification

def verify_email(raw_token):
    record = _consume_token(raw_token, "EMAIL_VERIFICATION")
    user = record.user
    if not user.is_active:
        raise BusinessRuleError("This account has been deactivated.", code="ACCOUNT_INACTIVE")
    user.is_verified = True
    db.session.commit()
    return user


def resend_verification(email):
    email = validators.validate_email(email)
    user = User.query.filter_by(email=email).first()
    if user and user.is_active and not user.is_verified:
        token = _issue_token(user, "EMAIL_VERIFICATION")
        _send_verification_email(user, token)
    db.session.commit()
    # Same response whether or not the account exists (don't leak accounts).
    return True


# ---------------------------------------------------------------- password reset

def forgot_password(email):
    email = validators.validate_email(email)
    user = User.query.filter_by(email=email, is_active=True).first()
    if user:
        token = _issue_token(user, "PASSWORD_RESET")
        link = url_for("auth.reset_password_page", token=token, _external=True)
        subject = "Reset your Campus Placement Portal password"
        body = (
            f"Hi {user.display_name},\n\n"
            f"We received a request to reset your password. Click the link below to "
            f"choose a new one:\n\n{link}\n\n"
            f"This link expires in {current_app.config['TOKEN_TTL_HOURS']} hours. "
            f"If you didn't request this, you can safely ignore this email."
        )
        notification_service.notify(
            user,
            NotificationType.EMAIL_VERIFICATION,  # reuse channel, not shown as critical
            "Password reset requested",
            "We sent a password reset link to your email address.",
            email_subject=subject,
            email_body=body,
        )
    db.session.commit()
    # Always succeed — do not reveal whether the email exists.
    return True


def reset_password(raw_token, new_password, password_confirm=None):
    password = validators.validate_password(new_password, password_confirm)
    record = _consume_token(raw_token, "PASSWORD_RESET")
    user = record.user
    if not user.is_active:
        raise BusinessRuleError("This account has been deactivated.", code="ACCOUNT_INACTIVE")
    user.set_password(password)
    db.session.commit()
    return user


def get_user_by_id(user_id):
    return db.session.get(User, user_id)
