"""AuditLog — lightweight trace of important administrative actions."""

from app.extensions import db
from app.models.user import utcnow


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(80), nullable=False, index=True)
    entity_type = db.Column(db.String(80), nullable=True)
    entity_id = db.Column(db.Integer, nullable=True)
    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)

    actor = db.relationship("User", foreign_keys=[user_id])

    @staticmethod
    def record(user_id, action, entity_type=None, entity_id=None, metadata=None):
        import json

        log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        db.session.add(log)
        return log

    def __repr__(self):
        return f"<AuditLog {self.id} {self.action}>"
