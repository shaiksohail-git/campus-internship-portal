"""AuthToken — single-use, expiring tokens for email verification and password reset.

Only the SHA-256 hash of a token is stored, so a database leak cannot be used
to forge verification links.
"""

from app.extensions import db
from app.models.user import utcnow


class AuthToken(db.Model):
    __tablename__ = "auth_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    type = db.Column(db.String(30), nullable=False)  # EMAIL_VERIFICATION | PASSWORD_RESET
    token_hash = db.Column(db.String(64), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship("User")

    @property
    def is_expired(self):
        return utcnow() > self.expires_at

    @property
    def is_used(self):
        return self.used_at is not None

    def __repr__(self):
        return f"<AuthToken {self.id} {self.type} user={self.user_id}>"
