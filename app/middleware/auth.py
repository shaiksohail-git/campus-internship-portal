"""Session-based authentication middleware.

Flask's signed-cookie session stores only the user id; every request loads the
user from the database so suspensions/role changes apply immediately.
"""

from functools import wraps

from flask import g, redirect, request, session, url_for

from app.models.user import User
from app.utils.errors import AuthenticationError


def load_current_user():
    user_id = session.get("user_id")
    g.current_user = None
    if user_id:
        user = User.query.filter_by(id=user_id, is_active=True).first()
        if user:
            g.current_user = user
        else:
            session.clear()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.current_user is None:
            if request.path.startswith("/api/"):
                raise AuthenticationError(
                    "Please log in to continue.", code="AUTHENTICATION_REQUIRED"
                )
            return redirect(url_for("auth.login_page", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def login_user(user, permanent=True):
    """Create the server session. Session regeneration prevents fixation."""
    session.clear()
    session["user_id"] = user.id
    if permanent:
        session.permanent = True


def logout_user():
    session.clear()
