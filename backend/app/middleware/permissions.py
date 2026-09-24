"""Role-based authorization.

Requirement from PRD: a student must never reach recruiter/admin functionality
by typing a URL. Role + verification checks happen here on every route.
"""

from functools import wraps

from flask import g, redirect, request, url_for

from app.utils.errors import AuthenticationError, AuthorizationError


def require_role(*roles):
    """Restrict a view to the given roles. Also requires a verified email —
    unverified users must verify before using protected functionality."""

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = g.current_user
            if user is None:
                if request.path.startswith("/api/"):
                    raise AuthenticationError(
                        "Please log in to continue.", code="AUTHENTICATION_REQUIRED"
                    )
                return redirect(url_for("auth.login_page", next=request.path))

            if user.role not in roles:
                if request.path.startswith("/api/"):
                    raise AuthorizationError(
                        "You do not have permission to perform this action.",
                        code="ROLE_FORBIDDEN",
                    )
                return redirect(url_for("pages.forbidden"))

            if not user.is_verified:
                if request.path.startswith("/api/"):
                    raise AuthorizationError(
                        "Please verify your email address first.",
                        code="VERIFICATION_REQUIRED",
                    )
                return redirect(url_for("auth.verify_pending_page"))

            return view(*args, **kwargs)

        return wrapped

    return decorator


def student_only(view):
    return require_role("STUDENT")(view)


def recruiter_only(view):
    return require_role("RECRUITER")(view)


def admin_only(view):
    return require_role("ADMIN")(view)
