"""Server-side validation helpers.

The backend is the security boundary — never trust the frontend.
"""

import re

from app.utils.errors import ValidationError

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[0-9+\-\s()]{7,20}$")
URL_RE = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)

MIN_PASSWORD_LENGTH = 8


def validate_email(value, field="email"):
    value = (value or "").strip().lower()
    if not value:
        raise ValidationError(f"{field} is required.")
    if len(value) > 255:
        raise ValidationError(f"{field} is too long.")
    if not EMAIL_RE.match(value):
        raise ValidationError("Please enter a valid email address.")
    return value


def validate_password(value, confirm=None, field="password"):
    value = value or ""
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f"{field} must be at least {MIN_PASSWORD_LENGTH} characters.")
    if len(value) > 128:
        raise ValidationError(f"{field} must be at most 128 characters.")
    if confirm is not None and value != confirm:
        raise ValidationError("Passwords do not match.")
    return value


def validate_required(value, field, max_length=500):
    value = (value or "").strip()
    if not value:
        raise ValidationError(f"{field} is required.")
    if len(value) > max_length:
        raise ValidationError(f"{field} must be at most {max_length} characters.")
    return value


def validate_optional_text(value, field, max_length=500):
    if value is None:
        return None
    value = str(value).strip()
    if len(value) > max_length:
        raise ValidationError(f"{field} must be at most {max_length} characters.")
    return value or None


def validate_phone(value):
    value = (value or "").strip()
    if not value:
        return None
    if not PHONE_RE.match(value):
        raise ValidationError("Please enter a valid phone number.")
    return value


def validate_url(value, field="website"):
    value = (value or "").strip()
    if not value:
        return None
    if not URL_RE.match(value):
        raise ValidationError(f"{field} must be a valid URL starting with http(s)://")
    return value


def validate_graduation_year(value):
    import datetime

    if value is None or value == "":
        return None
    try:
        year = int(value)
    except (TypeError, ValueError):
        raise ValidationError("Graduation year must be a number.")
    current = datetime.date.today().year
    if year < current - 5 or year > current + 7:
        raise ValidationError("Please enter a valid graduation year.")
    return year


def validate_in_enum(value, choices, field):
    if value not in choices:
        raise ValidationError(f"{field} must be one of: {', '.join(choices)}")
    return value


def validate_skills(value):
    """Accept a list (API) or comma-separated string (form) and return a list."""
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    else:
        items = [s.strip() for s in str(value).split(",")]
    cleaned = [s.strip()[:60] for s in items if s and s.strip()]
    return cleaned[:30]


def validate_deadline(value, field="application deadline"):
    """Validate a YYYY-MM-DD deadline; must be in the future."""
    import datetime

    try:
        deadline = datetime.date.fromisoformat(str(value))
    except ValueError:
        raise ValidationError(f"{field} must be a valid date (YYYY-MM-DD).")
    if deadline < datetime.date.today():
        raise ValidationError(f"{field} must be in the future.")
    return deadline
