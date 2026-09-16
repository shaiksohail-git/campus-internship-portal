"""Application — links a student to an opportunity.

The UNIQUE(student_id, opportunity_id) constraint is the hard guarantee against
duplicate applications, even for two simultaneous requests.
"""

from app.extensions import db
from app.models.user import utcnow


class Application(db.Model):
    __tablename__ = "applications"
    __table_args__ = (
        db.UniqueConstraint("student_id", "opportunity_id", name="uq_student_opportunity"),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False, index=True)
    opportunity_id = db.Column(db.Integer, db.ForeignKey("opportunities.id"), nullable=False, index=True)
    resume_id = db.Column(db.Integer, db.ForeignKey("resumes.id"), nullable=True)

    status = db.Column(db.String(30), nullable=False, default="APPLIED", index=True)
    applied_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    student = db.relationship("StudentProfile", back_populates="applications")
    opportunity = db.relationship("Opportunity", back_populates="applications")
    resume = db.relationship("Resume", lazy="joined")
    interviews = db.relationship(
        "Interview",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="desc(Interview.created_at)",
    )
    offer_letter = db.relationship(
        "OfferLetter", back_populates="application", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def active_interview(self):
        for interview in self.interviews:
            if interview.status in ("SCHEDULED", "UPDATED"):
                return interview
        return None

    def to_dict(self):
        return {
            "id": self.id,
            "opportunity_id": self.opportunity_id,
            "opportunity_title": self.opportunity.title if self.opportunity else None,
            "company_name": self.opportunity.company_name if self.opportunity else None,
            "status": self.status,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
        }

    def __repr__(self):
        return f"<Application {self.id} opp={self.opportunity_id} status={self.status}>"
