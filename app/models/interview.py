"""Interview — scheduled interview tied to an application."""

from app.extensions import db
from app.models.user import utcnow


class Interview(db.Model):
    __tablename__ = "interviews"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False, index=True)

    scheduled_date = db.Column(db.Date, nullable=False, index=True)
    scheduled_time = db.Column(db.Time, nullable=False)
    mode = db.Column(db.String(30), nullable=False, default="ONLINE")  # ONLINE | OFFICE | PHONE
    location = db.Column(db.String(255), nullable=True)
    meeting_details = db.Column(db.String(500), nullable=True)
    additional_instructions = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(20), nullable=False, default="SCHEDULED")  # SCHEDULED | UPDATED | CANCELLED | COMPLETED
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    application = db.relationship("Application", back_populates="interviews")

    def to_dict(self):
        return {
            "id": self.id,
            "application_id": self.application_id,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "scheduled_time": self.scheduled_time.strftime("%H:%M") if self.scheduled_time else None,
            "mode": self.mode,
            "location": self.location,
            "meeting_details": self.meeting_details,
            "additional_instructions": self.additional_instructions,
            "status": self.status,
        }

    def __repr__(self):
        return f"<Interview {self.id} app={self.application_id} {self.scheduled_date}>"
