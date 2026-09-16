"""Admin routes — pages (server-rendered GET) + REST API (section 28 of TRD)."""

import datetime
from flask import Blueprint, g, render_template, request

from app.extensions import db
from app.middleware.permissions import admin_only
from app.models.audit import AuditLog
from app.models.enums import ApplicationStatus, OpportunityStatus, RecruiterApprovalStatus
from app.models.opportunity import Opportunity
from app.models.recruiter import RecruiterProfile
from app.models.student import StudentProfile
from app.models.user import User
from app.services import admin_service, analytics_service
from app.utils import validators
from app.utils.api import json_body, ok, paginate
from app.utils.errors import NotFoundError

bp = Blueprint("admin", __name__)


def _student_rows():
    query = (
        db.session.query(User, StudentProfile)
        .join(StudentProfile, StudentProfile.user_id == User.id)
    )
    search = (request.args.get("search") or "").strip()
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                User.email.ilike(like),
                StudentProfile.full_name.ilike(like),
                StudentProfile.department.ilike(like),
            )
        )
    return query.order_by(User.created_at.desc())


def _application_counts():
    """One grouped query instead of a lazy count per student row."""
    from app.models.application import Application

    counts = (
        db.session.query(Application.student_id, db.func.count(Application.id))
        .group_by(Application.student_id)
        .all()
    )
    return {student_id: count for student_id, count in counts}


# ------------------------------------------------------------------ pages


@bp.get("/admin/dashboard")
@admin_only
def dashboard():
    stats = analytics_service.dashboard_stats()
    pending_recruiters = (
        RecruiterProfile.query.filter_by(approval_status=RecruiterApprovalStatus.PENDING)
        .order_by(RecruiterProfile.created_at.asc())
        .limit(5)
        .all()
    )
    pending_opportunities = (
        Opportunity.query.filter_by(status=OpportunityStatus.PENDING_REVIEW)
        .order_by(Opportunity.created_at.asc())
        .limit(5)
        .all()
    )
    from app.models.application import Application

    recent_applications = Application.query.order_by(Application.applied_at.desc()).limit(6).all()
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        pending_recruiters=pending_recruiters,
        pending_opportunities=pending_opportunities,
        recent_applications=recent_applications,
        active_tab="dashboard",
    )


@bp.get("/admin/students")
@admin_only
def students_page():
    items, pagination = paginate(_student_rows())
    return render_template(
        "admin/students.html",
        rows=items,
        pagination=pagination,
        app_counts=_application_counts(),
        active_tab="students",
    )


@bp.get("/admin/recruiters")
@admin_only
def recruiters_page():
    status = request.args.get("status", "").upper()
    query = RecruiterProfile.query
    if status in RecruiterApprovalStatus.ALL:
        query = query.filter_by(approval_status=status)
    items, pagination = paginate(query.order_by(RecruiterProfile.created_at.desc()))
    return render_template(
        "admin/recruiters.html",
        recruiters=items,
        pagination=pagination,
        current_status=status,
        active_tab="recruiters",
    )


@bp.get("/admin/opportunities")
@admin_only
def opportunities_page():
    status = request.args.get("status", "").upper()
    query = Opportunity.query
    if status in OpportunityStatus.ALL:
        query = query.filter_by(status=status)
    items, pagination = paginate(query.order_by(Opportunity.created_at.desc()))
    return render_template(
        "admin/opportunities.html",
        opportunities=items,
        pagination=pagination,
        current_status=status,
        active_tab="opportunities",
    )


@bp.get("/admin/applications")
@admin_only
def applications_page():
    from app.models.application import Application

    query = Application.query
    status = request.args.get("status", "").upper()
    if status in ApplicationStatus.ALL:
        query = query.filter_by(status=status)
    items, pagination = paginate(query.order_by(Application.applied_at.desc()))
    return render_template(
        "admin/applications.html",
        applications=items,
        pagination=pagination,
        current_status=status,
        active_tab="applications",
    )


@bp.get("/admin/interviews")
@admin_only
def interviews_page():
    from app.models.interview import Interview

    items, pagination = paginate(Interview.query.order_by(Interview.scheduled_date.desc()))
    return render_template(
        "admin/interviews.html", interviews=items, pagination=pagination, active_tab="interviews"
    )


@bp.get("/admin/analytics")
@admin_only
def analytics_page():
    return render_template(
        "admin/analytics.html", analytics=analytics_service.analytics(), active_tab="analytics"
    )


@bp.get("/admin/analytics/export/csv")
@admin_only
def export_analytics_csv():
    import csv
    import io

    data = analytics_service.analytics()
    stats = data["stats"]

    buf = io.StringIO()
    w = csv.writer(buf)

    # Overview
    w.writerow(["Placement Analytics Report"])
    w.writerow(["Generated", datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")])
    w.writerow([])
    w.writerow(["Metric", "Value"])
    w.writerow(["Registered students", stats["students"]])
    w.writerow(["Registered companies", stats["recruiters"]])
    w.writerow(["Total applications", stats["total_applications"]])
    w.writerow(["Students selected", stats["students_selected"]])
    w.writerow(["Interviews scheduled", stats["interviews_scheduled"]])
    w.writerow(["Rejected", data["rejected"]])
    w.writerow(["Shortlisted", data["shortlisted"]])
    w.writerow(["Selection rate", f"{data['selection_rate']}%"])
    w.writerow([])

    # Applications by type
    w.writerow(["Applications by Type"])
    w.writerow(["Type", "Count", "Percentage"])
    total = max(stats["total_applications"], 1)
    w.writerow(["Internship", data["internship_applications"], f"{data['internship_ratio']}%"])
    w.writerow(["Full-time", data["fulltime_applications"], f"{data['fulltime_ratio']}%"])
    w.writerow([])

    # Monthly activity
    w.writerow(["Monthly Application Activity"])
    w.writerow(["Month", "Applications"])
    for m in data["monthly_activity"]:
        w.writerow([m["label"], m["count"]])
    w.writerow([])

    # Department-wise
    w.writerow(["Department-wise Applications"])
    w.writerow(["Department", "Applications", "Selected"])
    for dept, count in data["dept_applications"].items():
        w.writerow([dept, count, data["dept_selections"].get(dept, 0)])
    w.writerow([])

    # Company-wise selections
    w.writerow(["Company-wise Selections"])
    w.writerow(["Company", "Selected"])
    for name, count in data["company_hiring"]:
        w.writerow([name, count])
    w.writerow([])

    # Top opportunities
    w.writerow(["Most Popular Opportunities"])
    w.writerow(["Opportunity", "Company", "Applications"])
    for title, company, count in data["top_opportunities"]:
        w.writerow([title, company, count])

    buf.seek(0)
    return (
        buf.getvalue(),
        200,
        {
            "Content-Type": "text/csv",
            "Content-Disposition": "attachment; filename=admin-analytics.csv",
        },
    )


@bp.get("/admin/audit-logs")
@admin_only
def audit_logs_page():
    items, pagination = paginate(AuditLog.query.order_by(AuditLog.created_at.desc()))
    return render_template(
        "admin/audit_logs.html", logs=items, pagination=pagination, active_tab="audit-logs"
    )


# ------------------------------------------------------------------ announcements pages


@bp.get("/admin/announcements")
@admin_only
def announcements_page():
    from app.models.announcement import Announcement

    items, pagination = paginate(
        Announcement.query.order_by(Announcement.created_at.desc())
    )
    return render_template(
        "admin/announcements.html",
        announcements=items,
        pagination=pagination,
        active_tab="announcements",
    )


@bp.get("/admin/announcements/new")
@admin_only
def announcement_new_page():
    return render_template(
        "admin/announcement_form.html", announcement=None, active_tab="announcements"
    )


@bp.get("/admin/announcements/<int:announcement_id>/edit")
@admin_only
def announcement_edit_page(announcement_id):
    from app.models.announcement import Announcement

    announcement = db.session.get(Announcement, announcement_id)
    if announcement is None:
        raise NotFoundError("Announcement not found.", code="ANNOUNCEMENT_NOT_FOUND")
    return render_template(
        "admin/announcement_form.html",
        announcement=announcement,
        active_tab="announcements",
    )


# ------------------------------------------------------------------ api


@bp.get("/api/v1/admin/dashboard")
@admin_only
def api_dashboard():
    return ok({"stats": analytics_service.dashboard_stats()})


@bp.get("/api/v1/admin/students")
@admin_only
def api_students():
    items, pagination = paginate(_student_rows())
    return ok(
        {
            "students": [
                {
                    **user.to_dict(),
                    "profile": profile.to_dict(),
                }
                for user, profile in items
            ],
            "pagination": pagination,
        }
    )


@bp.get("/api/v1/admin/recruiters")
@admin_only
def api_recruiters():
    status = request.args.get("status", "").upper()
    query = RecruiterProfile.query
    if status in RecruiterApprovalStatus.ALL:
        query = query.filter_by(approval_status=status)
    items, pagination = paginate(query.order_by(RecruiterProfile.created_at.desc()))
    return ok({"recruiters": [r.to_dict() for r in items], "pagination": pagination})


@bp.get("/api/v1/admin/recruiters/pending")
@admin_only
def api_recruiters_pending():
    items = (
        RecruiterProfile.query.filter_by(approval_status=RecruiterApprovalStatus.PENDING)
        .order_by(RecruiterProfile.created_at.asc())
        .all()
    )
    return ok({"recruiters": [r.to_dict() for r in items]})


@bp.patch("/api/v1/admin/recruiters/<int:recruiter_id>/approve")
@admin_only
def api_approve_recruiter(recruiter_id):
    from flask import g

    recruiter = admin_service.approve_recruiter(g.current_user, recruiter_id)
    return ok({"recruiter": recruiter.to_dict()}, f"{recruiter.company_name} approved.")


@bp.patch("/api/v1/admin/recruiters/<int:recruiter_id>/reject")
@admin_only
def api_reject_recruiter(recruiter_id):
    from flask import g

    recruiter = admin_service.reject_recruiter(g.current_user, recruiter_id)
    return ok({"recruiter": recruiter.to_dict()}, f"{recruiter.company_name} rejected.")


@bp.get("/api/v1/admin/opportunities")
@admin_only
def api_opportunities():
    status = request.args.get("status", "").upper()
    query = Opportunity.query
    if status in OpportunityStatus.ALL:
        query = query.filter_by(status=status)
    items, pagination = paginate(query.order_by(Opportunity.created_at.desc()))
    return ok({"opportunities": [o.to_dict() for o in items], "pagination": pagination})


@bp.get("/api/v1/admin/opportunities/pending")
@admin_only
def api_opportunities_pending():
    items = (
        Opportunity.query.filter_by(status=OpportunityStatus.PENDING_REVIEW)
        .order_by(Opportunity.created_at.asc())
        .all()
    )
    return ok({"opportunities": [o.to_dict() for o in items]})


@bp.patch("/api/v1/admin/opportunities/<int:opportunity_id>/approve")
@admin_only
def api_approve_opportunity(opportunity_id):
    from flask import g

    opportunity = admin_service.approve_opportunity(g.current_user, opportunity_id)
    return ok({"opportunity": opportunity.to_dict()}, "Opportunity approved and published.")


@bp.patch("/api/v1/admin/opportunities/<int:opportunity_id>/reject")
@admin_only
def api_reject_opportunity(opportunity_id):
    from flask import g

    opportunity = admin_service.reject_opportunity(g.current_user, opportunity_id)
    return ok({"opportunity": opportunity.to_dict()}, "Opportunity rejected.")


@bp.patch("/api/v1/admin/opportunities/<int:opportunity_id>/close")
@admin_only
def api_close_opportunity(opportunity_id):
    from flask import g

    opportunity = admin_service.close_opportunity(g.current_user, opportunity_id)
    return ok({"opportunity": opportunity.to_dict()}, "Opportunity closed.")


@bp.get("/api/v1/admin/applications")
@admin_only
def api_applications():
    from app.models.application import Application

    status = request.args.get("status", "").upper()
    query = Application.query
    if status in ApplicationStatus.ALL:
        query = query.filter_by(status=status)
    items, pagination = paginate(query.order_by(Application.applied_at.desc()))
    return ok({"applications": [a.to_dict() for a in items], "pagination": pagination})


@bp.get("/api/v1/admin/interviews")
@admin_only
def api_interviews():
    from app.models.interview import Interview

    items, pagination = paginate(Interview.query.order_by(Interview.scheduled_date.desc()))
    return ok({"interviews": [i.to_dict() for i in items], "pagination": pagination})


@bp.get("/api/v1/admin/analytics")
@admin_only
def api_analytics():
    return ok({"analytics": analytics_service.analytics()})


@bp.patch("/api/v1/admin/users/<int:user_id>/suspend")
@admin_only
def api_suspend_user(user_id):
    from flask import g

    admin_service.set_user_active(g.current_user, user_id, False)
    return ok({}, "User suspended.")


@bp.patch("/api/v1/admin/users/<int:user_id>/reactivate")
@admin_only
def api_reactivate_user(user_id):
    from flask import g

    admin_service.set_user_active(g.current_user, user_id, True)
    return ok({}, "User reactivated.")


@bp.get("/api/v1/admin/audit-logs")
@admin_only
def api_audit_logs():
    items, pagination = paginate(AuditLog.query.order_by(AuditLog.created_at.desc()))
    return ok({"logs": [{"id": l.id, "action": l.action, "actor": l.actor.email if l.actor else None,
                          "entity_type": l.entity_type, "entity_id": l.entity_id,
                          "created_at": l.created_at.isoformat() if l.created_at else None} for l in items],
                "pagination": pagination})


# ------------------------------------------------------------------ announcements api


@bp.get("/api/v1/admin/announcements")
@admin_only
def api_announcements():
    from app.models.announcement import Announcement

    items, pagination = paginate(
        Announcement.query.order_by(Announcement.created_at.desc())
    )
    return ok({"announcements": [a.to_dict() for a in items], "pagination": pagination})


@bp.post("/api/v1/admin/announcements")
@admin_only
def api_create_announcement():
    from app.models.announcement import Announcement

    data = json_body()
    title = validators.validate_required(data.get("title"), "Title", 200)
    body = data.get("body", "")
    audience = validators.validate_in_enum(
        data.get("audience", "ALL"), Announcement.AUDIENCES, "Audience"
    )
    is_published = data.get("is_published", True)

    announcement = Announcement(
        author_id=g.current_user.id,
        title=title,
        body=body,
        audience=audience,
        is_published=bool(is_published),
    )
    db.session.add(announcement)
    db.session.commit()
    return ok({"announcement": announcement.to_dict()}, "Announcement published.", status=201)


@bp.put("/api/v1/admin/announcements/<int:announcement_id>")
@admin_only
def api_update_announcement(announcement_id):
    from app.models.announcement import Announcement

    announcement = db.session.get(Announcement, announcement_id)
    if announcement is None:
        raise NotFoundError("Announcement not found.", code="ANNOUNCEMENT_NOT_FOUND")

    data = json_body()
    announcement.title = validators.validate_required(data.get("title"), "Title", 200)
    announcement.body = data.get("body", "")
    announcement.audience = validators.validate_in_enum(
        data.get("audience", "ALL"), Announcement.AUDIENCES, "Audience"
    )
    announcement.is_published = bool(data.get("is_published", True))
    db.session.commit()
    return ok({"announcement": announcement.to_dict()}, "Announcement updated.")


@bp.delete("/api/v1/admin/announcements/<int:announcement_id>")
@admin_only
def api_delete_announcement(announcement_id):
    from app.models.announcement import Announcement

    announcement = db.session.get(Announcement, announcement_id)
    if announcement is None:
        raise NotFoundError("Announcement not found.", code="ANNOUNCEMENT_NOT_FOUND")
    db.session.delete(announcement)
    db.session.commit()
    return ok({}, "Announcement deleted.")


@bp.get("/api/v1/announcements")
def api_public_announcements():
    """Public endpoint — returns published announcements filtered by audience.
    Used by student and recruiter dashboards."""
    from app.models.announcement import Announcement

    audience = request.args.get("audience", "").upper()
    query = Announcement.query.filter_by(is_published=True)
    if audience in (Announcement.STUDENT, Announcement.RECRUITER):
        query = query.filter(
            db.or_(
                Announcement.audience == audience,
                Announcement.audience == Announcement.ALL,
            )
        )
    announcements = query.order_by(Announcement.created_at.desc()).limit(10).all()
    return ok({"announcements": [a.to_dict() for a in announcements]})
