"""Resume — metadata lives in SQL, the actual file lives in storage.

Files are never exposed through predictable public URLs; downloads go through
an authenticated, authorization-checked endpoint.
"""

from app.extensions import db
from app.models.user import utcnow


class Resume(db.Model):
    __tablename__ = "resumes"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False, index=True)
    file_name = db.Column(db.String(255), nullable=False)
    storage_key = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(20), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    uploaded_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    student = db.relationship("StudentProfile", back_populates="resumes")

    def to_dict(self):
        return {
            "id": self.id,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "is_active": self.is_active,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }

    def __repr__(self):
        return f"<Resume {self.id} {self.file_name}>"
