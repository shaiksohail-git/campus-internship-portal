"""Web security helpers: CSRF protection and simple rate limiting.

CSRF: a per-session random token is rendered into every page (meta tag +
hidden form fields). All state-changing requests must echo it via the
X-CSRF-Token header or csrf_token form field.

Rate limiting: a small in-memory sliding-window limiter applied to sensitive
auth endpoints. Good enough for single-process V1 deployment.
"""

import hmac
import secrets
import time
from functools import wraps

from flask import current_app, g, jsonify, request, session

from app.utils.errors import RateLimitError


def init_csrf(app):
    @app.before_request
    def ensure_csrf_token():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)

    @app.before_request
    def protect_state_changes():
        if not current_app.config.get("CSRF_ENABLED", True):
            return None
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return None
        supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
        expected = session.get("csrf_token")
        if not expected or not supplied or not hmac.compare_digest(supplied, expected):
            if request.path.startswith("/api/"):
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": {
                                "code": "CSRF_FAILED",
                                "message": "Your session token is invalid. Refresh the page and try again.",
                            },
                        }
                    ),
                    403,
                )
            return (
                jsonify({"success": False, "error": {"code": "CSRF_FAILED", "message": "CSRF check failed."}}),
                403,
            )
        return None


class RateLimiter:
    def __init__(self):
        self._hits = {}  # key -> list of timestamps
        self._last_cleanup = time.time()

    def _prune(self, key, window):
        now = time.time()
        hits = [t for t in self._hits.get(key, []) if now - t < window]
        self._hits[key] = hits
        return hits

    def _cleanup_stale_keys(self):
        # Bound memory: drop keys with no recent hits occasionally.
        now = time.time()
        if now - self._last_cleanup < 300:
            return
        self._last_cleanup = now
        stale = [k for k, hits in self._hits.items() if not hits or now - max(hits) > 3600]
        for key in stale:
            del self._hits[key]

    def allow(self, key, limit, window):
        self._cleanup_stale_keys()
        hits = self._prune(key, window)
        if len(hits) >= limit:
            return False
        self._hits[key].append(time.time())
        return True


rate_limiter = RateLimiter()


def rate_limit(limit, per_seconds):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            key = f"{request.remote_addr}:{request.endpoint}"
            if not rate_limiter.allow(key, limit, per_seconds):
                raise RateLimitError(
                    "Too many attempts. Please wait a while and try again."
                )
            return view(*args, **kwargs)

        return wrapped

    return decorator


def auth_rate_limit(config_key):
    """Apply the configured rate limit for an auth endpoint.

    Config is read at request time (decorator is applied at import time,
    outside the application context).
    """

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            limit, window = current_app.config[config_key]
            key = f"{request.remote_addr}:{view.__name__}"
            if not rate_limiter.allow(key, limit, window):
                raise RateLimitError(
                    "Too many attempts. Please wait a while and try again."
                )
            return view(*args, **kwargs)

        return wrapped

    return decorator
