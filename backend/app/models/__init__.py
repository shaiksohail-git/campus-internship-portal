"""Model registry — importing this module registers every table on db.Model."""

from app.models.user import User
from app.models.college import College
from app.models.student import StudentProfile
from app.models.recruiter import RecruiterProfile
from app.models.resume import Resume
from app.models.opportunity import Opportunity
from app.models.application import Application
from app.models.interview import Interview
from app.models.notification import Notification
from app.models.audit import AuditLog
from app.models.token import AuthToken
from app.models.mailbox import DevMailbox
from app.models.offer_letter import OfferLetter
from app.models.announcement import Announcement

__all__ = [
    "User",
    "College",
    "StudentProfile",
    "RecruiterProfile",
    "Resume",
    "Opportunity",
    "Application",
    "Interview",
    "Notification",
    "AuditLog",
    "AuthToken",
    "DevMailbox",
    "OfferLetter",
    "Announcement",
]
