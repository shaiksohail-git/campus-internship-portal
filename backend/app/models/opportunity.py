"""Opportunity — an internship or full-time posting published by a recruiter."""

from app.extensions import db
from app.models.user import utcnow


class Opportunity(db.Model):
    __tablename__ = "opportunities"

    id = db.Column(db.Integer, primary_key=True)
    recruiter_id = db.Column(db.Integer, db.ForeignKey("recruiter_profiles.id"), nullable=False, index=True)

    title = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(20), nullable=False, index=True)  # INTERNSHIP | FULL_TIME
    description = db.Column(db.Text, nullable=False, default="")
    responsibilities = db.Column(db.Text, nullable=True)
    required_skills = db.Column(db.Text, nullable=True)
    eligibility = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(200), nullable=True, index=True)
    work_mode = db.Column(db.String(50), nullable=True)  # ON_SITE | REMOTE | HYBRID
    salary_or_stipend = db.Column(db.String(200), nullable=True)
    application_deadline = db.Column(db.Date, nullable=False, index=True)

    status = db.Column(db.String(30), nullable=False, default="DRAFT", index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    published_at = db.Column(db.DateTime, nullable=True)

    recruiter = db.relationship("RecruiterProfile", back_populates="opportunities")
    applications = db.relationship("Application", back_populates="opportunity", cascade="all, delete-orphan")

    @property
    def company_name(self):
        return self.recruiter.company_name if self.recruiter else "—"

    @property
    def is_closed(self):
        return self.status == "CLOSED"

    @property
    def is_open_for_applications(self):
        return self.status == "APPROVED" and not self.is_closed

    def to_dict(self, include_company=True):
        data = {
            "id": self.id,
            "title": self.title,
            "type": self.type,
            "description": self.description,
            "responsibilities": self.responsibilities,
            "required_skills": self.required_skills,
            "eligibility": self.eligibility,
            "location": self.location,
            "work_mode": self.work_mode,
            "salary_or_stipend": self.salary_or_stipend,
            "application_deadline": self.application_deadline.isoformat() if self.application_deadline else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_company:
            data["company_name"] = self.company_name
        return data

    def __repr__(self):
        return f"<Opportunity {self.id} {self.title}>"
