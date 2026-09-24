"""Application service.

apply() runs the PRD's transactional flow:
  verify student → verify opportunity open → verify deadline → eligibility →
  verify resume → create application (unique constraint blocks duplicates).
"""

import datetime
import re

from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.application import Application
from app.models.enums import (
    ApplicationStatus,
    NotificationType,
    OpportunityStatus,
)
from app.models.opportunity import Opportunity
from app.models.resume import Resume
from app.services import notification_service
from app.utils.errors import (
    AuthorizationError,
    BusinessRuleError,
    ConflictError,
    NotFoundError,
)


# ---------------------------------------------------------------- eligibility

_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")  # non-capturing — findall must return full years


def eligibility_issues(opportunity, student):
    """Return a list of human-readable eligibility problems (empty = eligible).

    V1 uses a pragmatic heuristic: batch years mentioned in the eligibility text
    are compared with the student's graduation year. Free-text criteria that
    cannot be machine-checked are ignored.
    """
    issues = []
    if not opportunity.eligibility:
        return issues

    years = {int(y) for y in _YEAR_RE.findall(opportunity.eligibility)}
    if years and student.graduation_year not in years:
        issues.append(
            f"This opportunity is open to the {', '.join(sorted(str(y) for y in years))} batch, "
            f"but your graduation year is {student.graduation_year}."
        )
    return issues


# ---------------------------------------------------------------- apply

def apply(student, opportunity_id, resume_id=None):
    opportunity = db.session.get(Opportunity, opportunity_id)
    if opportunity is None:
        raise NotFoundError("Opportunity not found.", code="OPPORTUNITY_NOT_FOUND")

    if opportunity.status != OpportunityStatus.APPROVED or opportunity.is_closed:
        raise BusinessRuleError(
            "This opportunity is not accepting applications right now.",
            code="OPPORTUNITY_CLOSED",
        )
    if opportunity.application_deadline < datetime.date.today():
        raise BusinessRuleError(
            "The application deadline has passed.",
            code="APPLICATION_DEADLINE_PASSED",
        )

    issues = eligibility_issues(opportunity, student)
    if issues:
        raise BusinessRuleError(issues[0], code="NOT_ELIGIBLE")

    resume = _select_resume(student, resume_id)
    if resume is None:
        raise BusinessRuleError(
            "Please upload a resume before applying.",
            code="RESUME_REQUIRED",
        )

    application = Application(
        student_id=student.id,
        opportunity_id=opportunity.id,
        resume_id=resume.id,
        status=ApplicationStatus.APPLIED,
    )
    db.session.add(application)

    try:
        db.session.flush()  # triggers unique constraint
    except IntegrityError:
        db.session.rollback()
        raise ConflictError(
            "You have already applied to this opportunity.",
            code="DUPLICATE_APPLICATION",
        )

    # Notifications (same transaction as the application)
    notification_service.notify(
        student.user,
        NotificationType.APPLICATION_SUBMITTED,
        "Application submitted",
        f"Your application for '{opportunity.title}' at {opportunity.company_name} was submitted successfully.",
        email_subject=f"Application submitted — {opportunity.title}",
        email_body=(
            f"Hi {student.full_name},\n\nYour application for "
            f"'{opportunity.title}' at {opportunity.company_name} has been submitted "
            f"and is now under review.\n\nAll the best!\nCampus Placement Portal"
        ),
    )
    notification_service.notify(
        opportunity.recruiter.user,
        NotificationType.NEW_APPLICATION,
        "New application received",
        f"{student.full_name} applied for '{opportunity.title}'.",
        email_subject=f"New application — {opportunity.title}",
        email_body=(
            f"{student.full_name} ({student.department or '—'}, "
            f"{student.graduation_year or '—'}) just applied for "
            f"'{opportunity.title}'. Review their application in the portal."
        ),
    )
    db.session.commit()
    return application


def _select_resume(student, resume_id):
    """Choose the resume for this application — explicit selection or newest active."""
    if resume_id:
        resume = db.session.get(Resume, resume_id)
        if resume is None or resume.student_id != student.id or not resume.is_active:
            raise AuthorizationError(
                "You can only use your own active resumes.", code="RESUME_NOT_YOURS"
            )
        return resume
    return (
        Resume.query.filter_by(student_id=student.id, is_active=True)
        .order_by(Resume.uploaded_at.desc())
        .first()
    )


# ---------------------------------------------------------------- status

def update_status(recruiter, application_id, new_status):
    """Recruiter updates an application status — validates the state machine."""
    application = _owned_application(recruiter, application_id)

    allowed = ApplicationStatus.TRANSITIONS.get(application.status, set())
    if new_status not in allowed:
        raise BusinessRuleError(
            f"Cannot move an application from '{ApplicationStatus.LABELS.get(application.status, application.status)}' "
            f"to '{ApplicationStatus.LABELS.get(new_status, new_status)}'.",
            code="INVALID_STATUS_TRANSITION",
        )

    old_status = application.status
    application.status = new_status
    application.updated_at = datetime.datetime.now(datetime.timezone.utc)

    notification_service.notify(
        application.student.user,
        NotificationType.APPLICATION_STATUS_CHANGED,
        "Application status updated",
        (
            f"Your application for '{application.opportunity.title}' at "
            f"{application.opportunity.company_name} is now "
            f"'{ApplicationStatus.LABELS.get(new_status, new_status)}'."
        ),
        email_subject=f"Application status: {ApplicationStatus.LABELS.get(new_status, new_status)}",
        email_body=(
            f"Hi {application.student.full_name},\n\nYour application for "
            f"'{application.opportunity.title}' at {application.opportunity.company_name} "
            f"was updated from '{ApplicationStatus.LABELS.get(old_status, old_status)}' "
            f"to '{ApplicationStatus.LABELS.get(new_status, new_status)}'.\n\n"
            f"Campus Placement Portal"
        ),
    )
    db.session.commit()
    return application


def _owned_application(recruiter, application_id):
    application = db.session.get(Application, application_id)
    if application is None or application.opportunity.recruiter_id != recruiter.id:
        # 404 rather than 403 so recruiters cannot probe other recruiters' data
        raise NotFoundError("Application not found.", code="APPLICATION_NOT_FOUND")
    return application
