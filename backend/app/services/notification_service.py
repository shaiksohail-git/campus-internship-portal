"""Notification service.

Business events create an in-app Notification (audit trail in SQL) and fire an
email through the email abstraction. Callers own the transaction/commit.
"""

from app.models.enums import Role
from app.models.notification import Notification
from app.models.user import User
from app.utils.email import email_service


def notify(user, ntype, title, message, email_subject=None, email_body=None):
    """Create an in-app notification for `user` and send an email if provided.

    Does NOT commit — the caller commits within its transaction.
    """
    notification = Notification(
        user_id=user.id, type=ntype, title=title, message=message
    )
    from app.extensions import db

    db.session.add(notification)

    if email_subject and email_body:
        email_service.send(user.email, email_subject, email_body)
    return notification


def notify_all_admins(ntype, title, message, email_subject=None, email_body=None):
    """Notify every admin user (used for pending-approval operational alerts)."""
    from app.extensions import db

    admins = User.query.filter_by(role=Role.ADMIN, is_active=True).all()
    for admin in admins:
        notification = Notification(
            user_id=admin.id, type=ntype, title=title, message=message
        )
        db.session.add(notification)
    # Emails to admins are optional/noisy — skip in V1; in-app is enough.
    return len(admins)


def unread_count(user_id):
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()
