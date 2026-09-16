"""Admin service — approval workflows, user management and audit logging."""

from app.extensions import db
from app.models.audit import AuditLog
from app.models.enums import (
    AuditAction,
    NotificationType,
    OpportunityStatus,
    RecruiterApprovalStatus,
)
from app.models.opportunity import Opportunity
from app.models.recruiter import RecruiterProfile
from app.models.user import User, utcnow
from app.services import notification_service
from app.utils.errors import BusinessRuleError, NotFoundError


def _notify_recruiter(recruiter, ntype, title, message, email_subject, email_body):
    notification_service.notify(
        recruiter.user, ntype, title, message, email_subject=email_subject, email_body=email_body
    )


def approve_recruiter(admin, recruiter_id):
    recruiter = db.session.get(RecruiterProfile, recruiter_id)
    if recruiter is None:
        raise NotFoundError("Recruiter not found.", code="RECRUITER_NOT_FOUND")
    if recruiter.approval_status == RecruiterApprovalStatus.APPROVED:
        raise BusinessRuleError("This recruiter is already approved.", code="ALREADY_APPROVED")

    recruiter.approval_status = RecruiterApprovalStatus.APPROVED
    recruiter.approved_at = utcnow()
    recruiter.approved_by = admin.id
    AuditLog.record(admin.id, AuditAction.ADMIN_APPROVED_RECRUITER, "RecruiterProfile", recruiter.id)

    _notify_recruiter(
        recruiter,
        NotificationType.RECRUITER_APPROVED,
        "Company approved",
        f"Congratulations! {recruiter.company_name} was approved by the placement office. You can now create and publish opportunities.",
        email_subject="Your company has been approved",
        email_body=(
            f"Hi {recruiter.contact_person or recruiter.user.email},\n\n"
            f"Good news — {recruiter.company_name} has been approved by the placement office. "
            f"You can now publish internship and full-time opportunities on the portal.\n\n"
            f"Campus Placement Portal"
        ),
    )
    db.session.commit()
    return recruiter


def reject_recruiter(admin, recruiter_id):
    recruiter = db.session.get(RecruiterProfile, recruiter_id)
    if recruiter is None:
        raise NotFoundError("Recruiter not found.", code="RECRUITER_NOT_FOUND")
    if recruiter.approval_status == RecruiterApprovalStatus.REJECTED:
        raise BusinessRuleError("This recruiter is already rejected.", code="ALREADY_REJECTED")

    recruiter.approval_status = RecruiterApprovalStatus.REJECTED
    recruiter.approved_at = None
    AuditLog.record(admin.id, AuditAction.ADMIN_REJECTED_RECRUITER, "RecruiterProfile", recruiter.id)

    _notify_recruiter(
        recruiter,
        NotificationType.RECRUITER_REJECTED,
        "Company registration rejected",
        f"Unfortunately, {recruiter.company_name}'s registration was not approved. Please contact the placement office for details.",
        email_subject="Update on your company registration",
        email_body=(
            f"Hi {recruiter.contact_person or recruiter.user.email},\n\n"
            f"Your company registration for {recruiter.company_name} was not approved at this time. "
            f"Please contact the placement office if you believe this is a mistake.\n\n"
            f"Campus Placement Portal"
        ),
    )
    db.session.commit()
    return recruiter


def approve_opportunity(admin, opportunity_id):
    opportunity = db.session.get(Opportunity, opportunity_id)
    if opportunity is None:
        raise NotFoundError("Opportunity not found.", code="OPPORTUNITY_NOT_FOUND")
    if opportunity.status == OpportunityStatus.APPROVED:
        raise BusinessRuleError("This opportunity is already approved.", code="ALREADY_APPROVED")

    opportunity.status = OpportunityStatus.APPROVED
    opportunity.published_at = utcnow()
    AuditLog.record(admin.id, AuditAction.ADMIN_APPROVED_OPPORTUNITY, "Opportunity", opportunity.id)

    _notify_recruiter(
        opportunity.recruiter,
        NotificationType.OPPORTUNITY_APPROVED,
        "Opportunity approved",
        f"'{opportunity.title}' is now live and visible to students.",
        email_subject=f"Opportunity approved — {opportunity.title}",
        email_body=(
            f"Hi {opportunity.recruiter.company_name} team,\n\nYour opportunity "
            f"'{opportunity.title}' was approved and is now visible to students.\n\n"
            f"Campus Placement Portal"
        ),
    )
    db.session.commit()
    return opportunity


def reject_opportunity(admin, opportunity_id):
    opportunity = db.session.get(Opportunity, opportunity_id)
    if opportunity is None:
        raise NotFoundError("Opportunity not found.", code="OPPORTUNITY_NOT_FOUND")
    if opportunity.status == OpportunityStatus.REJECTED:
        raise BusinessRuleError("This opportunity is already rejected.", code="ALREADY_REJECTED")

    opportunity.status = OpportunityStatus.REJECTED
    AuditLog.record(admin.id, AuditAction.ADMIN_REJECTED_OPPORTUNITY, "Opportunity", opportunity.id)

    _notify_recruiter(
        opportunity.recruiter,
        NotificationType.OPPORTUNITY_REJECTED,
        "Opportunity not approved",
        f"'{opportunity.title}' was not approved. You can edit it and resubmit.",
        email_subject=f"Opportunity not approved — {opportunity.title}",
        email_body=(
            f"Hi {opportunity.recruiter.company_name} team,\n\nYour opportunity "
            f"'{opportunity.title}' was not approved. Please review the posting, make "
            f"any changes and resubmit it.\n\nCampus Placement Portal"
        ),
    )
    db.session.commit()
    return opportunity


def close_opportunity(admin, opportunity_id):
    opportunity = db.session.get(Opportunity, opportunity_id)
    if opportunity is None:
        raise NotFoundError("Opportunity not found.", code="OPPORTUNITY_NOT_FOUND")
    if opportunity.status == OpportunityStatus.CLOSED:
        raise BusinessRuleError("This opportunity is already closed.", code="ALREADY_CLOSED")
    opportunity.status = OpportunityStatus.CLOSED
    AuditLog.record(admin.id, AuditAction.ADMIN_CLOSED_OPPORTUNITY, "Opportunity", opportunity.id)
    db.session.commit()
    return opportunity


def set_user_active(admin, user_id, active):
    user = db.session.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.", code="USER_NOT_FOUND")
    if user.role == "ADMIN":
        raise BusinessRuleError("Administrator accounts cannot be suspended.", code="CANNOT_SUSPEND_ADMIN")
    user.is_active = active
    action = AuditAction.ADMIN_REACTIVATED_USER if active else AuditAction.ADMIN_SUSPENDED_USER
    AuditLog.record(admin.id, action, "User", user.id)
    db.session.commit()
    return user
