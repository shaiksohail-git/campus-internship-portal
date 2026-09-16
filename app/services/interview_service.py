"""Interview service.

Scheduling runs inside a transaction:
  verify recruiter ownership → verify candidate shortlisted → (cancel previous
  active interview if any) → create interview → set application status →
  notify student. Any failure rolls the whole thing back.
"""

import datetime

from app.extensions import db
from app.models.application import Application
from app.models.enums import ApplicationStatus, InterviewStatus, NotificationType
from app.models.interview import Interview
from app.services import notification_service
from app.utils.errors import BusinessRuleError, NotFoundError
from app.utils.validators import validate_in_enum


def _owned_application(recruiter, application_id):
    application = db.session.get(Application, application_id)
    if application is None or application.opportunity.recruiter_id != recruiter.id:
        raise NotFoundError("Application not found.", code="APPLICATION_NOT_FOUND")
    return application


def _owned_interview(recruiter, interview_id):
    interview = db.session.get(Interview, interview_id)
    if interview is None or interview.application.opportunity.recruiter_id != recruiter.id:
        raise NotFoundError("Interview not found.", code="INTERVIEW_NOT_FOUND")
    return interview


def _validate_schedule_data(data):
    try:
        date = datetime.date.fromisoformat(str(data.get("scheduled_date")))
    except ValueError:
        raise BusinessRuleError("Interview date must be a valid date (YYYY-MM-DD).", code="INVALID_DATE")
    try:
        time = datetime.time.fromisoformat(str(data.get("scheduled_time")))
    except ValueError:
        raise BusinessRuleError("Interview time must be a valid time (HH:MM).", code="INVALID_TIME")
    if date < datetime.date.today():
        raise BusinessRuleError("Interview date must be in the future.", code="INVALID_DATE")
    mode = validate_in_enum(data.get("mode"), ("ONLINE", "OFFICE", "PHONE"), "Interview mode")
    return date, time, mode


def _student_conflicts(student_id, date, time, exclude_interview_id=None):
    """Return active interviews of the same student overlapping date+time."""
    query = (
        Interview.query.join(Application)
        .filter(
            Application.student_id == student_id,
            Interview.status.in_([InterviewStatus.SCHEDULED, InterviewStatus.UPDATED]),
            Interview.scheduled_date == date,
            Interview.scheduled_time == time,
        )
    )
    if exclude_interview_id:
        query = query.filter(Interview.id != exclude_interview_id)
    return query.all()


def schedule(recruiter, application_id, data):
    application = _owned_application(recruiter, application_id)

    if application.status not in (ApplicationStatus.SHORTLISTED, ApplicationStatus.INTERVIEW_SCHEDULED):
        raise BusinessRuleError(
            "Only shortlisted candidates can be scheduled for an interview.",
            code="NOT_SHORTLISTED",
        )

    date, time, mode = _validate_schedule_data(data)

    # Cancel any existing active interview (reschedule path)
    active = application.active_interview
    if active:
        active.status = InterviewStatus.CANCELLED

    interview = Interview(
        application_id=application.id,
        scheduled_date=date,
        scheduled_time=time,
        mode=mode,
        location=(data.get("location") or "").strip()[:255] or None,
        meeting_details=(data.get("meeting_details") or "").strip()[:500] or None,
        additional_instructions=(data.get("additional_instructions") or "").strip() or None,
        status=InterviewStatus.SCHEDULED,
    )
    db.session.add(interview)

    if application.status != ApplicationStatus.INTERVIEW_SCHEDULED:
        application.status = ApplicationStatus.INTERVIEW_SCHEDULED

    conflicts = _student_conflicts(
        application.student_id, date, time, exclude_interview_id=active.id if active else None
    )

    notification_service.notify(
        application.student.user,
        NotificationType.INTERVIEW_SCHEDULED,
        "Interview scheduled",
        (
            f"An interview for '{application.opportunity.title}' at "
            f"{application.opportunity.company_name} is scheduled for "
            f"{date.strftime('%d %b %Y')} at {time.strftime('%I:%M %p')} ({mode})."
        ),
        email_subject=f"Interview scheduled — {application.opportunity.title}",
        email_body=(
            f"Hi {application.student.full_name},\n\n"
            f"An interview has been scheduled with {application.opportunity.company_name} "
            f"for '{application.opportunity.title}'.\n\n"
            f"Date: {date.strftime('%d %b %Y')}\nTime: {time.strftime('%I:%M %p')}\n"
            f"Mode: {mode}\n"
            + (f"Location: {interview.location}\n" if interview.location else "")
            + (f"Meeting details: {interview.meeting_details}\n" if interview.meeting_details else "")
            + (f"Instructions: {interview.additional_instructions}\n" if interview.additional_instructions else "")
            + "\nGood luck!\nCampus Placement Portal"
        ),
    )
    db.session.commit()
    return interview, conflicts


def update(recruiter, interview_id, data):
    interview = _owned_interview(recruiter, interview_id)
    if interview.status == InterviewStatus.CANCELLED:
        raise BusinessRuleError("A cancelled interview cannot be edited.", code="INTERVIEW_CANCELLED")

    date, time, mode = _validate_schedule_data(data)
    interview.scheduled_date = date
    interview.scheduled_time = time
    interview.mode = mode
    interview.location = (data.get("location") or "").strip()[:255] or None
    interview.meeting_details = (data.get("meeting_details") or "").strip()[:500] or None
    interview.additional_instructions = (data.get("additional_instructions") or "").strip() or None
    interview.status = InterviewStatus.UPDATED

    conflicts = _student_conflicts(
        interview.application.student_id, date, time, exclude_interview_id=interview.id
    )

    notification_service.notify(
        interview.application.student.user,
        NotificationType.INTERVIEW_UPDATED,
        "Interview rescheduled",
        (
            f"The interview for '{interview.application.opportunity.title}' was updated to "
            f"{date.strftime('%d %b %Y')} at {time.strftime('%I:%M %p')} ({mode})."
        ),
        email_subject=f"Interview updated — {interview.application.opportunity.title}",
        email_body=(
            f"Hi {interview.application.student.full_name},\n\nYour interview for "
            f"'{interview.application.opportunity.title}' was updated.\n\n"
            f"New date: {date.strftime('%d %b %Y')}\nNew time: {time.strftime('%I:%M %p')}\nMode: {mode}\n\n"
            f"Campus Placement Portal"
        ),
    )
    db.session.commit()
    return interview, conflicts


def cancel(recruiter, interview_id):
    interview = _owned_interview(recruiter, interview_id)
    if interview.status == InterviewStatus.CANCELLED:
        raise BusinessRuleError("This interview is already cancelled.", code="INTERVIEW_CANCELLED")

    interview.status = InterviewStatus.CANCELLED
    application = interview.application
    # Application returns to shortlisted so the recruiter can reschedule
    if application.status == ApplicationStatus.INTERVIEW_SCHEDULED:
        application.status = ApplicationStatus.SHORTLISTED

    notification_service.notify(
        application.student.user,
        NotificationType.INTERVIEW_CANCELLED,
        "Interview cancelled",
        (
            f"The interview for '{application.opportunity.title}' at "
            f"{application.opportunity.company_name} was cancelled."
        ),
        email_subject=f"Interview cancelled — {application.opportunity.title}",
        email_body=(
            f"Hi {application.student.full_name},\n\nThe interview for "
            f"'{application.opportunity.title}' at {application.opportunity.company_name} "
            f"has been cancelled.\n\nCampus Placement Portal"
        ),
    )
    db.session.commit()
    return interview


def complete(recruiter, interview_id):
    interview = _owned_interview(recruiter, interview_id)
    if interview.status not in (InterviewStatus.SCHEDULED, InterviewStatus.UPDATED):
        raise BusinessRuleError("Only scheduled interviews can be completed.", code="INTERVIEW_NOT_SCHEDULED")
    interview.status = InterviewStatus.COMPLETED
    db.session.commit()
    return interview
