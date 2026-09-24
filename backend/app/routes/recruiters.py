"""Recruiter routes — pages (server-rendered GET) + REST API (section 27)."""

import datetime
import io

from flask import Blueprint, g, render_template, request, send_file

from app.extensions import db
from app.middleware.permissions import recruiter_only
from app.models.application import Application
from app.models.enums import (
    ApplicationStatus,
    OpportunityStatus,
    OpportunityType,
    RecruiterApprovalStatus,
)
from app.models.interview import Interview
from app.models.opportunity import Opportunity
from app.models.recruiter import RecruiterProfile
from app.services import application_service, analytics_export, interview_service, offer_letter_service, recruiter_analytics_service
from app.services.interview_service import schedule as schedule_interview
from app.utils import validators
from app.utils.api import json_body, ok, paginate
from app.utils.errors import BusinessRuleError, NotFoundError

bp = Blueprint("recruiters", __name__)


def _current_recruiter():
    return g.current_user.recruiter_profile


def _owned_opportunity(recruiter, opportunity_id):
    opportunity = db.session.get(Opportunity, opportunity_id)
    if opportunity is None or opportunity.recruiter_id != recruiter.id:
        raise NotFoundError("Opportunity not found.", code="OPPORTUNITY_NOT_FOUND")
    return opportunity


def _require_approved(recruiter):
    if not recruiter.is_approved:
        raise BusinessRuleError(
            "Your company account has not been approved by the placement office yet.",
            code="RECRUITER_NOT_APPROVED",
        )


# ------------------------------------------------------------------ pages


@bp.get("/recruiter/dashboard")
@recruiter_only
def dashboard():
    recruiter = _current_recruiter()
    opportunities = Opportunity.query.filter_by(recruiter_id=recruiter.id).all()
    apps_query = (
        Application.query.join(Opportunity)
        .filter(Opportunity.recruiter_id == recruiter.id)
    )
    recent_applications = apps_query.order_by(Application.applied_at.desc()).limit(6).all()
    upcoming_interviews = (
        Interview.query.join(Application).join(Opportunity)
        .filter(
            Opportunity.recruiter_id == recruiter.id,
            Interview.scheduled_date >= datetime.date.today(),
            Interview.status.in_(["SCHEDULED", "UPDATED"]),
        )
        .order_by(Interview.scheduled_date, Interview.scheduled_time)
        .limit(6)
        .all()
    )
    status_counts = {s: 0 for s in OpportunityStatus.ALL}
    for opp in opportunities:
        status_counts[opp.status] = status_counts.get(opp.status, 0) + 1

    from app.models.announcement import Announcement

    announcements = (
        Announcement.query.filter_by(is_published=True)
        .filter(
            db.or_(
                Announcement.audience == "RECRUITER",
                Announcement.audience == "ALL",
            )
        )
        .order_by(Announcement.created_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "recruiter/dashboard.html",
        recruiter=recruiter,
        opportunities=opportunities,
        recent_applications=recent_applications,
        upcoming_interviews=upcoming_interviews,
        status_counts=status_counts,
        total_applications=apps_query.count(),
        announcements=announcements,
        active_tab="dashboard",
    )


def _analytics_date_params():
    """Extract start_date / end_date query params shared by analytics routes."""
    return {
        "start_date": request.args.get("start_date") or None,
        "end_date": request.args.get("end_date") or None,
    }


@bp.get("/recruiter/analytics")
@recruiter_only
def analytics_page():
    recruiter = _current_recruiter()
    params = _analytics_date_params()
    data = recruiter_analytics_service.analytics(recruiter.id, **params)
    return render_template("recruiter/analytics.html", analytics=data, active_tab="analytics")


@bp.get("/api/v1/recruiter/analytics")
@recruiter_only
def api_analytics():
    recruiter = _current_recruiter()
    params = _analytics_date_params()
    return ok({"analytics": recruiter_analytics_service.analytics(recruiter.id, **params)})


@bp.get("/recruiter/analytics/export/csv")
@recruiter_only
def export_analytics_csv():
    recruiter = _current_recruiter()
    params = _analytics_date_params()
    data = recruiter_analytics_service.analytics(recruiter.id, **params)
    buf = analytics_export.generate_csv(data)
    return (
        buf.getvalue(),
        200,
        {
            "Content-Type": "text/csv",
            "Content-Disposition": "attachment; filename=hiring-analytics.csv",
        },
    )


@bp.get("/recruiter/analytics/export/pdf")
@recruiter_only
def export_analytics_pdf():
    recruiter = _current_recruiter()
    params = _analytics_date_params()
    data = recruiter_analytics_service.analytics(recruiter.id, **params)
    pdf_bytes = analytics_export.generate_pdf(data)
    return (
        pdf_bytes,
        200,
        {
            "Content-Type": "application/pdf",
            "Content-Disposition": "attachment; filename=hiring-analytics.pdf",
        },
    )


@bp.get("/recruiter/analytics/opportunities/<int:opportunity_id>")
@recruiter_only
def opportunity_analytics_page(opportunity_id):
    recruiter = _current_recruiter()
    data = recruiter_analytics_service.opportunity_analytics(recruiter.id, opportunity_id)
    if data is None:
        raise NotFoundError("Opportunity not found.", code="OPPORTUNITY_NOT_FOUND")
    return render_template(
        "recruiter/opportunity_analytics.html", analytics=data, active_tab="analytics"
    )


@bp.get("/api/v1/recruiter/analytics/opportunities/<int:opportunity_id>")
@recruiter_only
def api_opportunity_analytics(opportunity_id):
    recruiter = _current_recruiter()
    data = recruiter_analytics_service.opportunity_analytics(recruiter.id, opportunity_id)
    if data is None:
        raise NotFoundError("Opportunity not found.", code="OPPORTUNITY_NOT_FOUND")
    return ok({"analytics": data})


@bp.post("/api/v1/recruiter/analytics/test-digest")
@recruiter_only
def api_test_digest():
    """Send a test digest email to the current recruiter."""
    from app.services.digest_service import _build_digest_body
    from app.utils.email import email_service

    recruiter = _current_recruiter()
    data = recruiter_analytics_service.analytics(recruiter.id)
    user = g.current_user
    body = _build_digest_body(data, recruiter.company_name)
    subject = f"Weekly Hiring Digest (Test) - {recruiter.company_name}"
    email_service.send(user.email, subject, body)
    return ok({}, f"Test digest sent to {user.email}. Check your inbox (or dev mailbox).")


@bp.get("/recruiter/profile")
@recruiter_only
def profile_page():
    return render_template("recruiter/profile.html", recruiter=_current_recruiter(), active_tab="profile")


@bp.get("/recruiter/opportunities")
@recruiter_only
def opportunities_page():
    recruiter = _current_recruiter()
    query = Opportunity.query.filter_by(recruiter_id=recruiter.id)
    status = request.args.get("status", "").upper()
    if status in OpportunityStatus.ALL:
        query = query.filter_by(status=status)
    items, pagination = paginate(query.order_by(Opportunity.created_at.desc()))
    return render_template(
        "recruiter/opportunities.html",
        opportunities=items,
        pagination=pagination,
        recruiter=recruiter,
        current_status=status,
        active_tab="opportunities",
    )


@bp.get("/recruiter/opportunities/new")
@recruiter_only
def opportunity_new_page():
    return render_template("recruiter/opportunity_form.html", opportunity=None, active_tab="opportunities")


@bp.get("/recruiter/opportunities/<int:opportunity_id>")
@recruiter_only
def opportunity_detail_page(opportunity_id):
    recruiter = _current_recruiter()
    opportunity = _owned_opportunity(recruiter, opportunity_id)
    applications = (
        Application.query.filter_by(opportunity_id=opportunity.id)
        .order_by(Application.applied_at.desc())
        .all()
    )
    return render_template(
        "recruiter/opportunity_detail.html",
        opportunity=opportunity,
        applications=applications,
        active_tab="opportunities",
    )


@bp.get("/recruiter/opportunities/<int:opportunity_id>/edit")
@recruiter_only
def opportunity_edit_page(opportunity_id):
    recruiter = _current_recruiter()
    opportunity = _owned_opportunity(recruiter, opportunity_id)
    return render_template("recruiter/opportunity_form.html", opportunity=opportunity, active_tab="opportunities")


@bp.get("/recruiter/opportunities/<int:opportunity_id>/applicants")
@recruiter_only
def applicants_page(opportunity_id):
    recruiter = _current_recruiter()
    opportunity = _owned_opportunity(recruiter, opportunity_id)
    items, pagination = paginate(
        Application.query.filter_by(opportunity_id=opportunity.id)
        .order_by(Application.applied_at.desc())
    )
    return render_template(
        "recruiter/applicants.html",
        opportunity=opportunity,
        applications=items,
        pagination=pagination,
        active_tab="opportunities",
    )


def _selected_applications_query(recruiter, opportunity_id=None, college=None, offer_status=None):
    """Shared query for all SELECTED applications across a recruiter's opportunities.

    Optional filters:
    - opportunity_id: filter to a specific opportunity
    - college: filter by college name (case-insensitive partial match)
    - offer_status: "sent" or "pending" — filter by offer letter status
    """
    from app.models.offer_letter import OfferLetter

    query = (
        Application.query.join(Opportunity)
        .filter(
            Opportunity.recruiter_id == recruiter.id,
            Application.status == ApplicationStatus.SELECTED,
        )
    )

    if opportunity_id:
        query = query.filter(Application.opportunity_id == opportunity_id)

    if college:
        from app.models.student import StudentProfile

        query = query.join(StudentProfile, Application.student_id == StudentProfile.id).filter(
            StudentProfile.college_id == college
        )

    if offer_status == "sent":
        query = query.join(OfferLetter, Application.id == OfferLetter.application_id).filter(
            OfferLetter.sent_at.isnot(None)
        )
    elif offer_status == "pending":
        query = query.outerjoin(OfferLetter, Application.id == OfferLetter.application_id).filter(
            db.or_(OfferLetter.id.is_(None), OfferLetter.sent_at.is_(None))
        )

    return query.order_by(Application.updated_at.desc())


@bp.get("/recruiter/selected-applicants")
@recruiter_only
def selected_applicants_page():
    recruiter = _current_recruiter()

    # Get filter values from query params
    opp_id = request.args.get("opportunity", type=int)
    college_id = request.args.get("college", type=int)
    offer = request.args.get("offer", "").lower()
    if offer not in ("sent", "pending"):
        offer = None

    # Get opportunities for filter dropdown
    opportunities = (
        Opportunity.query.filter_by(recruiter_id=recruiter.id)
        .order_by(Opportunity.title)
        .all()
    )

    # Get colleges with selected applicants for filter dropdown
    from app.models.student import StudentProfile

    colleges_q = (
        db.session.query(StudentProfile.college_id, db.func.count(Application.id))
        .join(Application, StudentProfile.id == Application.student_id)
        .join(Opportunity, Application.opportunity_id == Opportunity.id)
        .filter(
            Opportunity.recruiter_id == recruiter.id,
            Application.status == ApplicationStatus.SELECTED,
            StudentProfile.college_id.isnot(None),
        )
        .group_by(StudentProfile.college_id)
        .all()
    )
    from app.models.college import College

    college_ids = [c[0] for c in colleges_q]
    colleges = College.query.filter(College.id.in_(college_ids)).order_by(College.name).all() if college_ids else []

    query = _selected_applications_query(recruiter, opportunity_id=opp_id, college=college_id, offer_status=offer)
    items, pagination = paginate(query)

    return render_template(
        "recruiter/selected_applicants.html",
        applications=items,
        pagination=pagination,
        opportunities=opportunities,
        colleges=colleges,
        filters={"opportunity": opp_id, "college": college_id, "offer": offer},
        active_tab="selected",
    )


@bp.get("/recruiter/selected-applicants/export/csv")
@recruiter_only
def export_selected_applicants_csv():
    import csv

    recruiter = _current_recruiter()
    applications = _selected_applications_query(recruiter).all()

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Selected Applicants Export"])
    w.writerow(["Company", recruiter.company_name])
    w.writerow(["Generated", datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")])
    w.writerow(["Total selected", len(applications)])
    w.writerow([])
    w.writerow(["Student Name", "Email", "College", "Degree", "Department", "Batch",
                "Opportunity", "Type", "Location", "Selected On", "Offer Letter"])
    for app in applications:
        student = app.student
        offer_status = "Sent" if (app.offer_letter and app.offer_letter.sent_at) else "Pending"
        w.writerow([
            student.full_name,
            student.user.email,
            student.college.name if student.college else "",
            student.degree or "",
            student.department or "",
            student.graduation_year or "",
            app.opportunity.title,
            app.opportunity.type.replace("_", " ").title(),
            app.opportunity.location or "",
            app.updated_at.strftime("%d %b %Y") if app.updated_at else "",
            offer_status,
        ])

    buf.seek(0)
    return (
        buf.getvalue(),
        200,
        {
            "Content-Type": "text/csv",
            "Content-Disposition": "attachment; filename=selected-applicants.csv",
        },
    )


@bp.get("/recruiter/selected-applicants/export/pdf")
@recruiter_only
def export_selected_applicants_pdf():
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    recruiter = _current_recruiter()
    applications = _selected_applications_query(recruiter).all()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm)
    story = []
    now = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SmallGrey", fontSize=9, fontName="Helvetica",
                              textColor=colors.HexColor("#64748b")))

    # Title
    story.append(Paragraph(f"Selected Applicants — {recruiter.company_name}", styles["Title"]))
    story.append(Paragraph(f"Generated on {now} · {len(applications)} applicant(s)", styles["SmallGrey"]))
    story.append(Spacer(1, 6 * mm))

    # Table
    header = ["Student", "Email", "College", "Dept", "Batch",
              "Opportunity", "Type", "Location", "Selected On", "Offer"]
    rows = [header]
    for app in applications:
        s = app.student
        offer_status = "Sent" if (app.offer_letter and app.offer_letter.sent_at) else "Pending"
        rows.append([
            s.full_name[:22],
            s.user.email[:28],
            (s.college.name[:18] if s.college else "-")[:18],
            (s.department or "-")[:14],
            str(s.graduation_year or "-"),
            app.opportunity.title[:22],
            app.opportunity.type.replace("_", " ").title()[:10],
            (app.opportunity.location or "-")[:12],
            app.updated_at.strftime("%d %b %Y") if app.updated_at else "-",
            offer_status,
        ])

    if len(rows) == 1:
        rows.append(["—"] * len(header))

    col_widths = [42 * mm, 50 * mm, 34 * mm, 28 * mm, 16 * mm,
                  42 * mm, 22 * mm, 24 * mm, 24 * mm, 18 * mm]
    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t)

    doc.build(story)
    pdf_bytes = buf.getvalue()
    return (
        pdf_bytes,
        200,
        {
            "Content-Type": "application/pdf",
            "Content-Disposition": "attachment; filename=selected-applicants.pdf",
        },
    )


@bp.get("/recruiter/interviews")
@recruiter_only
def interviews_page():
    recruiter = _current_recruiter()
    upcoming = (
        Interview.query.join(Application).join(Opportunity)
        .filter(
            Opportunity.recruiter_id == recruiter.id,
            Interview.scheduled_date >= datetime.date.today(),
            Interview.status.in_(["SCHEDULED", "UPDATED"]),
        )
        .order_by(Interview.scheduled_date, Interview.scheduled_time)
        .all()
    )
    past = (
        Interview.query.join(Application).join(Opportunity)
        .filter(Opportunity.recruiter_id == recruiter.id)
        .filter(Interview.scheduled_date < datetime.date.today())
        .order_by(Interview.scheduled_date.desc())
        .all()
    )
    return render_template(
        "recruiter/interviews.html", upcoming=upcoming, past=past, active_tab="interviews"
    )


# ------------------------------------------------------------------ profile api


@bp.get("/api/v1/recruiter/profile")
@recruiter_only
def api_profile():
    return ok({"profile": _current_recruiter().to_dict()})


@bp.put("/api/v1/recruiter/profile")
@recruiter_only
def api_update_profile():
    recruiter = _current_recruiter()
    data = json_body()
    recruiter.company_name = validators.validate_required(data.get("company_name"), "Company name", 200)
    recruiter.company_description = validators.validate_optional_text(
        data.get("company_description"), "Company description", 2000
    )
    if data.get("company_email"):
        recruiter.company_email = validators.validate_email(data.get("company_email"), "Company email")
    recruiter.website = validators.validate_url(data.get("website"))
    recruiter.contact_person = validators.validate_optional_text(data.get("contact_person"), "Contact person", 150)
    recruiter.contact_phone = validators.validate_phone(data.get("contact_phone"))
    db.session.commit()
    return ok({"profile": recruiter.to_dict()}, "Profile updated.")


@bp.put("/api/v1/recruiter/digest-preference")
@recruiter_only
def api_update_digest_preference():
    recruiter = _current_recruiter()
    data = json_body()
    enabled = data.get("enabled")
    if not isinstance(enabled, bool):
        from app.utils.errors import ValidationError
        raise ValidationError("'enabled' must be true or false.")
    recruiter.weekly_digest_enabled = enabled
    db.session.commit()
    label = "enabled" if enabled else "disabled"
    return ok({"weekly_digest_enabled": enabled}, f"Weekly analytics digest {label}.")


# ------------------------------------------------------------------ opportunities


def _validate_opportunity_data(data, partial=False):
    fields = {}
    fields["title"] = validators.validate_required(data.get("title"), "Title", 200)
    fields["type"] = validators.validate_in_enum(
        data.get("type"), OpportunityType.ALL, "Type"
    )
    fields["description"] = validators.validate_required(data.get("description"), "Description", 10000)
    fields["responsibilities"] = validators.validate_optional_text(data.get("responsibilities"), "Responsibilities", 10000)
    fields["required_skills"] = validators.validate_required(data.get("required_skills"), "Required skills", 2000)
    fields["eligibility"] = validators.validate_required(data.get("eligibility"), "Eligibility", 2000)
    fields["location"] = validators.validate_optional_text(data.get("location"), "Location", 200)
    fields["work_mode"] = validators.validate_optional_text(data.get("work_mode"), "Work mode", 50)
    fields["salary_or_stipend"] = validators.validate_optional_text(data.get("salary_or_stipend"), "Salary / stipend", 200)
    fields["application_deadline"] = validators.validate_deadline(data.get("application_deadline"))
    return fields


@bp.get("/api/v1/recruiter/opportunities")
@recruiter_only
def api_opportunities():
    recruiter = _current_recruiter()
    items, pagination = paginate(
        Opportunity.query.filter_by(recruiter_id=recruiter.id).order_by(Opportunity.created_at.desc())
    )
    return ok({"opportunities": [o.to_dict() for o in items], "pagination": pagination})


@bp.post("/api/v1/recruiter/opportunities")
@recruiter_only
def api_create_opportunity():
    recruiter = _current_recruiter()
    _require_approved(recruiter)
    data = _validate_opportunity_data(json_body())
    opportunity = Opportunity(
        recruiter_id=recruiter.id,
        title=data["title"],
        type=data["type"],
        description=data["description"],
        responsibilities=data["responsibilities"],
        required_skills=data["required_skills"],
        eligibility=data["eligibility"],
        location=data["location"],
        work_mode=data["work_mode"],
        salary_or_stipend=data["salary_or_stipend"],
        application_deadline=data["application_deadline"],
        status=OpportunityStatus.DRAFT,
    )
    db.session.add(opportunity)
    db.session.commit()
    return ok({"opportunity": opportunity.to_dict()}, "Opportunity saved as draft.", status=201)


@bp.get("/api/v1/recruiter/opportunities/<int:opportunity_id>")
@recruiter_only
def api_opportunity_detail(opportunity_id):
    recruiter = _current_recruiter()
    opportunity = _owned_opportunity(recruiter, opportunity_id)
    return ok({"opportunity": opportunity.to_dict()})


@bp.put("/api/v1/recruiter/opportunities/<int:opportunity_id>")
@recruiter_only
def api_update_opportunity(opportunity_id):
    recruiter = _current_recruiter()
    _require_approved(recruiter)
    opportunity = _owned_opportunity(recruiter, opportunity_id)
    if opportunity.status == OpportunityStatus.CLOSED:
        raise BusinessRuleError("A closed opportunity cannot be edited.", code="OPPORTUNITY_CLOSED")

    data = _validate_opportunity_data(json_body())
    opportunity.title = data["title"]
    opportunity.type = data["type"]
    opportunity.description = data["description"]
    opportunity.responsibilities = data["responsibilities"]
    opportunity.required_skills = data["required_skills"]
    opportunity.eligibility = data["eligibility"]
    opportunity.location = data["location"]
    opportunity.work_mode = data["work_mode"]
    opportunity.salary_or_stipend = data["salary_or_stipend"]
    opportunity.application_deadline = data["application_deadline"]

    # PRD: significant changes to an approved posting return it to admin review.
    if opportunity.status == OpportunityStatus.APPROVED:
        opportunity.status = OpportunityStatus.PENDING_REVIEW
        opportunity.published_at = None
    db.session.commit()
    return ok({"opportunity": opportunity.to_dict()}, "Opportunity updated.")


@bp.post("/api/v1/recruiter/opportunities/<int:opportunity_id>/close")
@recruiter_only
def api_close_opportunity(opportunity_id):
    recruiter = _current_recruiter()
    opportunity = _owned_opportunity(recruiter, opportunity_id)
    if opportunity.status != OpportunityStatus.APPROVED:
        raise BusinessRuleError("Only live opportunities can be closed.", code="INVALID_CLOSE")
    opportunity.status = OpportunityStatus.CLOSED
    db.session.commit()
    return ok({"opportunity": opportunity.to_dict()}, "Opportunity closed to new applications.")


@bp.post("/api/v1/recruiter/opportunities/<int:opportunity_id>/reopen")
@recruiter_only
def api_reopen_opportunity(opportunity_id):
    recruiter = _current_recruiter()
    _require_approved(recruiter)
    opportunity = _owned_opportunity(recruiter, opportunity_id)
    if opportunity.status != OpportunityStatus.CLOSED:
        raise BusinessRuleError("Only closed opportunities can be reopened.", code="INVALID_REOPEN")
    # Reopening requires admin review — don't bypass approval
    opportunity.status = OpportunityStatus.PENDING_REVIEW
    opportunity.published_at = None
    db.session.commit()

    from app.models.enums import NotificationType
    from app.services.notification_service import notify_all_admins

    notify_all_admins(
        NotificationType.OPPORTUNITY_APPROVED,
        "Reopened opportunity awaiting approval",
        f"{opportunity.title} by {opportunity.company_name} was reopened and submitted for review.",
    )
    return ok({"opportunity": opportunity.to_dict()}, "Opportunity submitted for admin review.")


@bp.delete("/api/v1/recruiter/opportunities/<int:opportunity_id>")
@recruiter_only
def api_delete_opportunity(opportunity_id):
    recruiter = _current_recruiter()
    opportunity = _owned_opportunity(recruiter, opportunity_id)
    deletable = {OpportunityStatus.DRAFT, OpportunityStatus.REJECTED, OpportunityStatus.CLOSED}
    if opportunity.status not in deletable:
        raise BusinessRuleError(
            "Only draft, rejected, or closed opportunities can be deleted.",
            code="INVALID_DELETE",
        )
    db.session.delete(opportunity)
    db.session.commit()
    return ok({}, "Opportunity deleted.")


@bp.post("/api/v1/recruiter/opportunities/<int:opportunity_id>/submit")
@recruiter_only
def api_submit_opportunity(opportunity_id):
    recruiter = _current_recruiter()
    _require_approved(recruiter)
    opportunity = _owned_opportunity(recruiter, opportunity_id)
    if opportunity.status not in OpportunityStatus.SUBMITTABLE:
        raise BusinessRuleError(
            "Only draft or rejected opportunities can be submitted for review.",
            code="INVALID_SUBMISSION",
        )
    opportunity.status = OpportunityStatus.PENDING_REVIEW
    db.session.commit()

    from app.models.enums import NotificationType
    from app.services.notification_service import notify_all_admins

    notify_all_admins(
        NotificationType.OPPORTUNITY_APPROVED,
        "New opportunity awaiting approval",
        f"{opportunity.title} by {opportunity.company_name} was submitted for review.",
    )
    return ok({"opportunity": opportunity.to_dict()}, "Submitted for admin review.")


# ------------------------------------------------------------------ applicants


def _application_with_student(application):
    student = application.student
    return {
        "id": application.id,
        "student_id": student.id,
        "full_name": student.full_name,
        "college": student.college.name if student.college else None,
        "degree": student.degree,
        "department": student.department,
        "graduation_year": student.graduation_year,
        "skills": student.skills_list,
        "resume": application.resume.to_dict() if application.resume else None,
        "status": application.status,
        "applied_at": application.applied_at.isoformat() if application.applied_at else None,
        "interview": application.active_interview.to_dict() if application.active_interview else None,
    }


@bp.get("/api/v1/recruiter/opportunities/<int:opportunity_id>/applications")
@recruiter_only
def api_applications_for_opportunity(opportunity_id):
    recruiter = _current_recruiter()
    _owned_opportunity(recruiter, opportunity_id)
    items, pagination = paginate(
        Application.query.filter_by(opportunity_id=opportunity_id)
        .order_by(Application.applied_at.desc())
    )
    return ok(
        {"applications": [_application_with_student(a) for a in items], "pagination": pagination}
    )


@bp.get("/api/v1/recruiter/applications/<int:application_id>")
@recruiter_only
def api_application_detail(application_id):
    recruiter = _current_recruiter()
    application = db.session.get(Application, application_id)
    if application is None or application.opportunity.recruiter_id != recruiter.id:
        raise NotFoundError("Application not found.", code="APPLICATION_NOT_FOUND")
    return ok({"application": _application_with_student(application)})


@bp.patch("/api/v1/recruiter/applications/<int:application_id>/status")
@recruiter_only
def api_update_application_status(application_id):
    recruiter = _current_recruiter()
    data = json_body()
    status = validators.validate_in_enum(
        data.get("status"), ApplicationStatus.ALL, "Status"
    )
    application = application_service.update_status(recruiter, application_id, status)
    return ok(
        {"application": _application_with_student(application)},
        f"Application moved to '{ApplicationStatus.LABELS.get(status, status)}'.",
    )


# ------------------------------------------------------------------ interviews


@bp.post("/api/v1/recruiter/applications/<int:application_id>/interviews")
@recruiter_only
def api_schedule_interview(application_id):
    recruiter = _current_recruiter()
    interview, conflicts = schedule_interview(recruiter, application_id, json_body())
    return ok(
        {
            "interview": interview.to_dict(),
            "conflicts": [c.to_dict() for c in conflicts],
        },
        "Interview scheduled.",
        status=201,
    )


@bp.put("/api/v1/recruiter/interviews/<int:interview_id>")
@recruiter_only
def api_update_interview(interview_id):
    recruiter = _current_recruiter()
    interview, conflicts = interview_service.update(recruiter, interview_id, json_body())
    return ok(
        {"interview": interview.to_dict(), "conflicts": [c.to_dict() for c in conflicts]},
        "Interview updated.",
    )


@bp.post("/api/v1/recruiter/interviews/<int:interview_id>/cancel")
@recruiter_only
def api_cancel_interview(interview_id):
    recruiter = _current_recruiter()
    interview = interview_service.cancel(recruiter, interview_id)
    return ok({"interview": interview.to_dict()}, "Interview cancelled. The student has been notified.")


@bp.post("/api/v1/recruiter/interviews/<int:interview_id>/complete")
@recruiter_only
def api_complete_interview(interview_id):
    recruiter = _current_recruiter()
    interview = interview_service.complete(recruiter, interview_id)
    return ok({"interview": interview.to_dict()}, "Interview marked as completed.")


# ------------------------------------------------------------------ offer letters

@bp.post("/api/v1/recruiter/applications/<int:application_id>/offer-letter")
@recruiter_only
def api_send_offer_letter(application_id):
    recruiter = _current_recruiter()
    data = json_body()
    offer = offer_letter_service.send_offer_letter(recruiter, application_id, data)
    return ok({"offer_letter": offer.to_dict()}, "Offer letter sent successfully.", status=201)


@bp.get("/api/v1/recruiter/applications/<int:application_id>/offer-letter/download")
@recruiter_only
def api_download_offer_letter(application_id):
    recruiter = _current_recruiter()
    offer = offer_letter_service.get_offer_letter_for_recruiter(recruiter, application_id)
    pdf_bytes = offer_letter_service.generate_offer_letter_pdf(offer)
    student_name = offer.application.student.full_name.replace(" ", "_")
    filename = f"Offer_Letter_{student_name}.pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )
