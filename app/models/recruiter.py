"""RecruiterProfile — company information + admin approval status."""

from app.extensions import db
from app.models.enums import RecruiterApprovalStatus
from app.models.user import utcnow


class RecruiterProfile(db.Model):
    __tablename__ = "recruiter_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)

    company_name = db.Column(db.String(200), nullable=False, default="")
    company_description = db.Column(db.Text, nullable=True)
    company_email = db.Column(db.String(255), nullable=True)
    website = db.Column(db.String(255), nullable=True)
    contact_person = db.Column(db.String(150), nullable=True)
    contact_phone = db.Column(db.String(30), nullable=True)
    weekly_digest_enabled = db.Column(db.Boolean, nullable=False, default=True)

    approval_status = db.Column(
        db.String(20), nullable=False, default=RecruiterApprovalStatus.PENDING, index=True
    )
    approved_at = db.Column(db.DateTime, nullable=True)
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user = db.relationship("User", back_populates="recruiter_profile", foreign_keys=[user_id])
    approver = db.relationship("User", foreign_keys=[approved_by])
    opportunities = db.relationship("Opportunity", back_populates="recruiter")

    @property
    def is_approved(self):
        return self.approval_status == RecruiterApprovalStatus.APPROVED

    @property
    def is_pending(self):
        return self.approval_status == RecruiterApprovalStatus.PENDING

    def to_dict(self):
        return {
            "id": self.id,
            "company_name": self.company_name,
            "company_description": self.company_description,
            "company_email": self.company_email,
            "website": self.website,
            "contact_person": self.contact_person,
            "contact_phone": self.contact_phone,
            "approval_status": self.approval_status,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "weekly_digest_enabled": self.weekly_digest_enabled,
        }

    def __repr__(self):
        return f"<RecruiterProfile {self.id} {self.company_name}>"
