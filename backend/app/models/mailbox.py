"""DevMailbox — dev-only table that captures outgoing emails so the
verification / password-reset flows can be demoed without a real provider.
"""

from app.extensions import db
from app.models.user import utcnow


class DevMailbox(db.Model):
    __tablename__ = "dev_mailbox"

    id = db.Column(db.Integer, primary_key=True)
    recipient = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def __repr__(self):
        return f"<DevMailbox {self.id} to={self.recipient}>"
