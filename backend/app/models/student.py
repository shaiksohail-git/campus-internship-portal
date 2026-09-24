"""StudentProfile — one per student user."""

from app.extensions import db
from app.models.user import utcnow


class StudentProfile(db.Model):
    __tablename__ = "student_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=True)

    full_name = db.Column(db.String(150), nullable=False, default="")
    phone = db.Column(db.String(30), nullable=True)
    degree = db.Column(db.String(120), nullable=True)
    department = db.Column(db.String(120), nullable=True, index=True)
    graduation_year = db.Column(db.Integer, nullable=True, index=True)
    skills = db.Column(db.JSON, nullable=True, default=list)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user = db.relationship("User", back_populates="student_profile")
    college = db.relationship("College", back_populates="students")
    resumes = db.relationship("Resume", back_populates="student", lazy="dynamic")
    applications = db.relationship("Application", back_populates="student")

    @property
    def skills_list(self):
        return list(self.skills or [])

    def has_resume(self):
        return self.resumes.filter_by(is_active=True).first() is not None

    @property
    def completeness(self):
        """Simple profile completeness % (0-100) shown to students."""
        checks = [
            bool(self.full_name),
            bool(self.phone),
            bool(self.college_id),
            bool(self.degree),
            bool(self.department),
            bool(self.graduation_year),
            bool(self.skills_list),
            bool(self.has_resume()),
        ]
        return int(round(100 * sum(checks) / len(checks)))

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "phone": self.phone,
            "college": self.college.name if self.college else None,
            "degree": self.degree,
            "department": self.department,
            "graduation_year": self.graduation_year,
            "skills": self.skills_list,
            "completeness": self.completeness,
        }

    def __repr__(self):
        return f"<StudentProfile {self.id} {self.full_name}>"
