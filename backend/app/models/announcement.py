"""Announcement — admin-published posts visible to students and/or recruiters."""

from app.extensions import db
from app.models.user import utcnow


class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False, default="")
    audience = db.Column(db.String(20), nullable=False, default="ALL")  # STUDENT | RECRUITER | ALL

    is_published = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    author = db.relationship("User")

    # Audience constants
    STUDENT = "STUDENT"
    RECRUITER = "RECRUITER"
    ALL = "ALL"
    AUDIENCES = (STUDENT, RECRUITER, ALL)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "audience": self.audience,
            "is_published": self.is_published,
            "author_email": self.author.email if self.author else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Announcement {self.id} '{self.title}' [{self.audience}]>"
