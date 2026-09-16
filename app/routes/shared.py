"""Routes shared across roles — notifications, secure resume download, and the
dev-only mailbox page."""

from flask import Blueprint, current_app, g, render_template, send_file

from app.extensions import db
from app.middleware.permissions import require_role
from app.models.application import Application
from app.models.enums import Role
from app.models.notification import Notification
from app.models.resume import Resume
from app.services import storage_service
from app.utils.api import json_body, ok, paginate
from app.utils.errors import AuthorizationError, NotFoundError

# All shared routes require a verified, active account of any role.
verified_any_role = require_role(Role.STUDENT, Role.RECRUITER, Role.ADMIN)

bp = Blueprint("shared", __name__)


# ------------------------------------------------------------------ notifications


@bp.get("/notifications")
@verified_any_role
def notifications_page():
    items, pagination = paginate(
        Notification.query.filter_by(user_id=g.current_user.id)
        .order_by(Notification.created_at.desc())
    )
    return render_template("notifications.html", notifications=items, pagination=pagination)


@bp.get("/api/v1/notifications")
@verified_any_role
def api_notifications():
    items, pagination = paginate(
        Notification.query.filter_by(user_id=g.current_user.id)
        .order_by(Notification.created_at.desc())
    )
    return ok({"notifications": [n.to_dict() for n in items], "pagination": pagination})


@bp.post("/api/v1/notifications/<int:notification_id>/read")
@verified_any_role
def api_mark_read(notification_id):
    notification = db.session.get(Notification, notification_id)
    if notification is None or notification.user_id != g.current_user.id:
        raise NotFoundError("Notification not found.", code="NOTIFICATION_NOT_FOUND")
    notification.is_read = True
    db.session.commit()
    return ok({"notification": notification.to_dict()}, "Marked as read.")


@bp.post("/api/v1/notifications/read-all")
@verified_any_role
def api_mark_all_read():
    Notification.query.filter_by(user_id=g.current_user.id, is_read=False).update(
        {"is_read": True}
    )
    db.session.commit()
    return ok({}, "All notifications marked as read.")# ------------------------------------------------------------------ resume preview

def _can_access_resume(user, resume):
    """PRD: resumes must not be publicly accessible — authorization is required."""
    if user.is_student:
        return user.student_profile and resume.student_id == user.student_profile.id
    if user.is_recruiter:
        # Recruiter may download resumes of applicants to their own opportunities.
        return (
            Application.query.join(Application.opportunity)
            .filter(
                Application.resume_id == resume.id,
                Application.opportunity.has(recruiter_id=user.recruiter_profile.id),
            )
            .first()
            is not None
        )
    return True  # admin


@bp.get("/resumes/<int:resume_id>/preview")
@verified_any_role
def resume_preview_page(resume_id):
    """Server-rendered resume preview page."""
    resume = db.session.get(Resume, resume_id)
    if resume is None:
        raise NotFoundError("Resume not found.", code="RESUME_NOT_FOUND")
    if not _can_access_resume(g.current_user, resume):
        raise AuthorizationError(
            "You are not allowed to access this resume.", code="RESUME_FORBIDDEN"
        )
    return render_template(
        "student/resume_preview.html",
        resume=resume,
    )


@bp.get("/api/v1/resumes/<int:resume_id>/download")
@verified_any_role
def api_download_resume(resume_id):
    resume = db.session.get(Resume, resume_id)
    if resume is None:
        raise NotFoundError("Resume not found.", code="RESUME_NOT_FOUND")
    if not _can_access_resume(g.current_user, resume):
        raise AuthorizationError(
            "You are not allowed to access this resume.", code="RESUME_FORBIDDEN"
        )
    storage = storage_service.get_storage_service()
    try:
        path = storage.download(resume.storage_key)
    except FileNotFoundError:
        raise NotFoundError("Resume file is missing.", code="RESUME_FILE_MISSING")
    return send_file(
        path,
        as_attachment=True,
        download_name=resume.file_name,
        mimetype=resume.file_type or "application/octet-stream",
    )


@bp.get("/api/v1/resumes/<int:resume_id>/preview")
@verified_any_role
def api_preview_resume(resume_id):
    """Serve the resume file inline for in-browser preview."""
    resume = db.session.get(Resume, resume_id)
    if resume is None:
        raise NotFoundError("Resume not found.", code="RESUME_NOT_FOUND")
    if not _can_access_resume(g.current_user, resume):
        raise AuthorizationError(
            "You are not allowed to access this resume.", code="RESUME_FORBIDDEN"
        )
    storage = storage_service.get_storage_service()
    try:
        path = storage.download(resume.storage_key)
    except FileNotFoundError:
        raise NotFoundError("Resume file is missing.", code="RESUME_FILE_MISSING")
    return send_file(
        path,
        as_attachment=False,
        mimetype=resume.file_type or "application/octet-stream",
    )


# ------------------------------------------------------------------ dev mailbox


@bp.get("/dev/mailbox")
@verified_any_role
def dev_mailbox_page():
    """Only available when emails are in console (dev) mode."""
    if current_app.config["MAIL_MODE"] != "console":
        raise NotFoundError("Not found.", code="NOT_FOUND")
    from app.models.mailbox import DevMailbox

    mails = DevMailbox.query.order_by(DevMailbox.created_at.desc()).limit(50).all()
    return render_template("dev/mailbox.html", mails=mails)
