"""Centralized API errors.

Never let raw SQL errors, stack traces or internal paths reach the client.
"""


class ApiError(Exception):
    """Base error carrying an HTTP status, machine-readable code and message."""

    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message, code=None, status_code=None, details=None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        self.details = details or {}

    def to_dict(self):
        payload = {"code": self.code, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return payload


class ValidationError(ApiError):
    status_code = 422
    code = "VALIDATION_ERROR"


class AuthenticationError(ApiError):
    status_code = 401
    code = "AUTHENTICATION_REQUIRED"


class AuthorizationError(ApiError):
    status_code = 403
    code = "FORBIDDEN"


class NotFoundError(ApiError):
    status_code = 404
    code = "NOT_FOUND"


class ConflictError(ApiError):
    status_code = 409
    code = "CONFLICT"


class BusinessRuleError(ApiError):
    status_code = 409
    code = "BUSINESS_RULE_VIOLATION"


class RateLimitError(ApiError):
    status_code = 429
    code = "RATE_LIMITED"
