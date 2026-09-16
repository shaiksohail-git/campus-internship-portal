"""College — a normalized college record instead of repeated free-text names."""

from app.extensions import db
from app.models.user import utcnow


class College(db.Model):
    __tablename__ = "colleges"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    code = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    students = db.relationship("StudentProfile", back_populates="college")

    def __repr__(self):
        return f"<College {self.id} {self.name}>"
