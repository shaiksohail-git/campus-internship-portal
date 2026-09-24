"""User — the central identity table."""

from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models.enums import Role


def utcnow():
    """Naive UTC now — SQLite stores naive datetimes, so keeping everything
    naive avoids offset-aware/naive comparison errors. All timestamps are UTC."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)
    is_verified = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    student_profile = db.relationship(
        "StudentProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    recruiter_profile = db.relationship(
        "RecruiterProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        foreign_keys="RecruiterProfile.user_id",
    )
    notifications = db.relationship(
        "Notification", back_populates="user", lazy="dynamic", cascade="all, delete-orphan"
    )

    # --- Password helpers (Werkzeug — never store plain text) ---
    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    # --- Convenience ---
    @property
    def is_student(self):
        return self.role == Role.STUDENT

    @property
    def is_recruiter(self):
        return self.role == Role.RECRUITER

    @property
    def is_admin(self):
        return self.role == Role.ADMIN

    @property
    def display_name(self):
        if self.is_student and self.student_profile:
            return self.student_profile.full_name
        if self.is_recruiter and self.recruiter_profile:
            return self.recruiter_profile.company_name
        return "Administrator"

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "is_verified": self.is_verified,
            "is_active": self.is_active,
            "display_name": self.display_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<User {self.id} {self.email} {self.role}>"
