"""OfferLetter — sent by a recruiter to a selected applicant."""

from app.extensions import db
from app.models.user import utcnow


class OfferLetter(db.Model):
    __tablename__ = "offer_letters"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(
        db.Integer, db.ForeignKey("applications.id"), nullable=False, index=True
    )
    recruiter_id = db.Column(
        db.Integer, db.ForeignKey("recruiter_profiles.id"), nullable=False, index=True
    )

    title = db.Column(db.String(200), nullable=False)
    salary_or_stipend = db.Column(db.String(200), nullable=True)
    joining_date = db.Column(db.Date, nullable=True)
    body = db.Column(db.Text, nullable=False, default="")

    sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    application = db.relationship("Application", back_populates="offer_letter")
    recruiter = db.relationship("RecruiterProfile")

    def to_dict(self):
        return {
            "id": self.id,
            "application_id": self.application_id,
            "title": self.title,
            "salary_or_stipend": self.salary_or_stipend,
            "joining_date": self.joining_date.isoformat() if self.joining_date else None,
            "body": self.body,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<OfferLetter {self.id} app={self.application_id}>"
