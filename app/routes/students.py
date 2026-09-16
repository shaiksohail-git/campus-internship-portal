"""Student routes — pages (server-rendered GET) + REST API (section 26 of TRD)."""

import datetime
import os
import uuid

from flask import Blueprint, g, render_template, request

from app.extensions import db
from app.middleware.permissions import student_only
from app.models.application import Application
from app.models.enums import ApplicationStatus, OpportunityStatus, OpportunityType, Role
from app.models.interview import Interview
from app.models.opportunity import Opportunity
from app.models.resume import Resume
from app.models.student import StudentProfile
from app.services import application_service, storage_service
from app.utils import validators
from app.utils.api import json_body, ok, paginate
from app.utils.errors import NotFoundError, ValidationError
from app.config import Config

bp = Blueprint("students", __name__)

OPPORTUNITY_FILTER_FIELDS = ("search", "type", "location", "work_mode", "skill")


def _current_student():
    return g.current_user.student_profile


# ------------------------------------------------------------------ pages


@bp.get("/student/dashboard")
@student_only
def dashboard():
    from app.models.announcement import Announcement

    student = _current_student()
    recent_opportunities = (
        Opportunity.query.filter_by(status=OpportunityStatus.APPROVED)
        .order_by(Opportunity.created_at.desc())
        .limit(4)
        .all()
    )
    my_applications = (
        Application.query.filter_by(student_id=student.id)
        .order_by(Application.applied_at.desc())
        .limit(5)
        .all()
    )
    upcoming_interviews = _upcoming_interviews(student)
    announcements = (
        Announcement.query.filter_by(is_published=True)
        .filter(
            db.or_(
                Announcement.audience == "STUDENT",
                Announcement.audience == "ALL",
            )
        )
        .order_by(Announcement.created_at.desc())
        .limit(5)
        .all()
    )
    return render_template(
        "student/dashboard.html",
        student=student,
        recent_opportunities=recent_opportunities,
        my_applications=my_applications,
        upcoming_interviews=upcoming_interviews,
        announcements=announcements,
        active_tab="dashboard",
    )


@bp.get("/student/profile")
@student_only
def profile_page():
    student = _current_student()
    from app.models.college import College

    return render_template(
        "student/profile.html",
        student=student,
        resumes=student.resumes.order_by(Resume.uploaded_at.desc()).all(),
        colleges=College.query.order_by(College.name).all(),
        active_tab="profile",
    )


@bp.get("/student/opportunities")
@student_only
def opportunities_page():
    student = _current_student()
    query = _filtered_opportunity_query()
    items, pagination = paginate(query)
    return render_template(
        "student/opportunities.html",
        opportunities=items,
        pagination=pagination,
        filters={f: request.args.get(f, "") for f in OPPORTUNITY_FILTER_FIELDS},
        applied_ids={
            app.opportunity_id
            for app in Application.query.filter_by(student_id=student.id).all()
        },
        active_tab="opportunities",
    )


@bp.get("/student/opportunities/<int:opportunity_id>")
@student_only
def opportunity_detail_page(opportunity_id):
    student = _current_student()
    opportunity = db.session.get(Opportunity, opportunity_id)
    if opportunity is None or opportunity.status not in OpportunityStatus.VISIBLE_TO_STUDENTS:
        raise NotFoundError("Opportunity not found.", code="OPPORTUNITY_NOT_FOUND")

    my_application = Application.query.filter_by(
        student_id=student.id, opportunity_id=opportunity.id
    ).first()
    issues = application_service.eligibility_issues(opportunity, student)
    deadline_passed = opportunity.application_deadline < datetime.date.today()
    return render_template(
        "student/opportunity_detail.html",
        opportunity=opportunity,
        my_application=my_application,
        eligibility_issues=issues,
        deadline_passed=deadline_passed,
        resumes=student.resumes.filter_by(is_active=True).order_by(Resume.uploaded_at.desc()).all(),
        active_tab="opportunities",
    )


@bp.get("/student/applications")
@student_only
def applications_page():
    student = _current_student()
    items, pagination = paginate(
        Application.query.filter_by(student_id=student.id).order_by(Application.applied_at.desc())
    )
    return render_template(
        "student/applications.html", applications=items, pagination=pagination, active_tab="applications"
    )


@bp.get("/student/interviews")
@student_only
def interviews_page():
    student = _current_student()
    interviews = _upcoming_interviews(student)
    past_interviews = (
        Interview.query.join(Application)
        .filter(Application.student_id == student.id)
        .filter(Interview.scheduled_date < datetime.date.today())
        .order_by(Interview.scheduled_date.desc())
        .all()
    )
    return render_template(
        "student/interviews.html",
        interviews=interviews,
        past_interviews=past_interviews,
        active_tab="interviews",
    )


def _upcoming_interviews(student):
    return (
        Interview.query.join(Application)
        .filter(
            Application.student_id == student.id,
            Interview.scheduled_date >= datetime.date.today(),
            Interview.status.in_(["SCHEDULED", "UPDATED"]),
        )
        .order_by(Interview.scheduled_date, Interview.scheduled_time)
        .all()
    )


# ------------------------------------------------------------------ profile api


def _student_query():
    return StudentProfile.query.filter_by(user_id=g.current_user.id)


@bp.get("/api/v1/student/profile")
@student_only
def api_profile():
    return ok({"profile": _current_student().to_dict()})


@bp.put("/api/v1/student/profile")
@student_only
def api_update_profile():
    student = _current_student()
    data = json_body()

    student.full_name = validators.validate_required(data.get("full_name"), "Full name", 150)
    student.phone = validators.validate_phone(data.get("phone"))
    student.degree = validators.validate_optional_text(data.get("degree"), "Degree", 120)
    student.department = validators.validate_optional_text(data.get("department"), "Department", 120)
    student.graduation_year = validators.validate_graduation_year(data.get("graduation_year"))
    student.skills = validators.validate_skills(data.get("skills"))

    college_name = (data.get("college") or "").strip()
    if college_name:
        from app.services.auth_service import find_or_create_college

        student.college = find_or_create_college(college_name)

    db.session.commit()
    return ok({"profile": student.to_dict()}, "Profile updated.")


# ------------------------------------------------------------------ resumes

ALLOWED_TYPES = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _sniffs_as_document(mime_key, head):
    """Best-effort magic-byte sniffing for the supported types."""
    if mime_key == "pdf":
        return head.startswith(b"%PDF-")
    if mime_key == "doc":
        return head.startswith((b"\xd0\xcf\x11\xe0", b"\x0f\x00\xe8\x03"))  # OLE / Word
    if mime_key == "docx":
        return head.startswith(b"PK\x03\x04")  # ZIP container
    return False


@bp.post("/api/v1/student/resumes")
@student_only
def api_upload_resume():
    student = _current_student()
    file = request.files.get("file")
    if file is None or not file.filename:
        raise ValidationError("Please choose a file to upload.")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in Config.ALLOWED_RESUME_EXTENSIONS:
        raise ValidationError("Only PDF, DOC and DOCX files are supported.")

    # Extension check + magic-byte sniffing (never trust the extension alone).
    mime_key = ext.lstrip(".")
    if mime_key not in ALLOWED_TYPES:
        raise ValidationError("Unsupported file type.")
    file.seek(0)
    head = file.read(8)
    file.seek(0)
    if not _sniffs_as_document(mime_key, head):
        raise ValidationError(
            "The file content does not match its type. Please upload a valid PDF, DOC or DOCX file."
        )

    storage = storage_service.get_storage_service()
    storage_key = f"{student.id}/{uuid.uuid4().hex}{ext}"
    stored_key, size = storage.upload(storage_key, file)
    if size > Config.MAX_RESUME_SIZE:
        storage.delete(stored_key)
        raise ValidationError("File is too large. Maximum size is 5 MB.")

    resume = Resume(
        student_id=student.id,
        file_name=file.filename,
        storage_key=stored_key,
        file_type=mime_key,
        file_size=size,
        is_active=True,
    )
    db.session.add(resume)
    db.session.commit()
    return ok({"resume": resume.to_dict()}, "Resume uploaded.", status=201)


@bp.get("/api/v1/student/resumes")
@student_only
def api_list_resumes():
    student = _current_student()
    return ok({"resumes": [r.to_dict() for r in student.resumes.order_by(Resume.uploaded_at.desc()).all()]})


@bp.delete("/api/v1/student/resumes/<int:resume_id>")
@student_only
def api_delete_resume(resume_id):
    student = _current_student()
    resume = db.session.get(Resume, resume_id)
    if resume is None or resume.student_id != student.id:
        raise NotFoundError("Resume not found.", code="RESUME_NOT_FOUND")
    storage = storage_service.get_storage_service()
    storage.delete(resume.storage_key)
    db.session.delete(resume)
    db.session.commit()
    return ok({}, "Resume deleted.")


# ------------------------------------------------------------------ opportunities


def _filtered_opportunity_query():
    from app.models.recruiter import RecruiterProfile

    query = Opportunity.query.join(RecruiterProfile).filter(
        Opportunity.status == OpportunityStatus.APPROVED
    )
    search = (request.args.get("search") or "").strip()
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                Opportunity.title.ilike(like),
                Opportunity.required_skills.ilike(like),
                RecruiterProfile.company_name.ilike(like),
            )
        )
    # company search joins recruiter profile
    otype = request.args.get("type")
    if otype in OpportunityType.ALL:
        query = query.filter(Opportunity.type == otype)
    location = (request.args.get("location") or "").strip()
    if location:
        query = query.filter(Opportunity.location.ilike(f"%{location}%"))
    work_mode = (request.args.get("work_mode") or "").strip()
    if work_mode:
        query = query.filter(Opportunity.work_mode == work_mode)
    skill = (request.args.get("skill") or "").strip()
    if skill:
        query = query.filter(Opportunity.required_skills.ilike(f"%{skill}%"))
    return query.order_by(Opportunity.created_at.desc())


@bp.get("/api/v1/student/opportunities")
@student_only
def api_opportunities():
    items, pagination = paginate(_filtered_opportunity_query())
    return ok({"opportunities": [o.to_dict() for o in items], "pagination": pagination})


@bp.get("/api/v1/student/opportunities/<int:opportunity_id>")
@student_only
def api_opportunity_detail(opportunity_id):
    opportunity = db.session.get(Opportunity, opportunity_id)
    if opportunity is None or opportunity.status not in OpportunityStatus.VISIBLE_TO_STUDENTS:
        raise NotFoundError("Opportunity not found.", code="OPPORTUNITY_NOT_FOUND")
    return ok({"opportunity": opportunity.to_dict()})


@bp.post("/api/v1/student/opportunities/<int:opportunity_id>/apply")
@student_only
def api_apply(opportunity_id):
    student = _current_student()
    data = json_body()
    application = application_service.apply(student, opportunity_id, data.get("resume_id"))
    return ok({"application": application.to_dict()}, "Application submitted!", status=201)


# ------------------------------------------------------------------ applications


@bp.get("/api/v1/student/applications")
@student_only
def api_applications():
    student = _current_student()
    items, pagination = paginate(
        Application.query.filter_by(student_id=student.id).order_by(Application.applied_at.desc())
    )
    return ok({"applications": [a.to_dict() for a in items], "pagination": pagination})


@bp.get("/api/v1/student/applications/<int:application_id>")
@student_only
def api_application_detail(application_id):
    student = _current_student()
    application = db.session.get(Application, application_id)
    if application is None or application.student_id != student.id:
        raise NotFoundError("Application not found.", code="APPLICATION_NOT_FOUND")
    return ok({"application": application.to_dict()})


# ------------------------------------------------------------------ interviews


@bp.get("/api/v1/student/interviews")
@student_only
def api_interviews():
    student = _current_student()
    interviews = (
        Interview.query.join(Application)
        .filter(Application.student_id == student.id)
        .order_by(Interview.scheduled_date.desc())
        .all()
    )
    return ok({"interviews": [i.to_dict() for i in interviews]})


# ------------------------------------------------------------------ offer letters

@bp.get("/api/v1/student/applications/<int:application_id>/offer-letter")
@student_only
def api_offer_letter(application_id):
    from app.services import offer_letter_service

    student = _current_student()
    offer = offer_letter_service.get_offer_letter(student, application_id)
    opp = offer.application.opportunity
    return ok({
        "offer_letter": offer.to_dict(),
        "opportunity_title": opp.title,
        "company_name": opp.company_name,
    })


@bp.get("/api/v1/student/applications/<int:application_id>/offer-letter/download")
@student_only
def api_download_offer_letter(application_id):
    import io
    from flask import send_file
    from app.services import offer_letter_service

    student = _current_student()
    offer = offer_letter_service.get_offer_letter(student, application_id)
    pdf_bytes = offer_letter_service.generate_offer_letter_pdf(offer)
    student_name = student.full_name.replace(" ", "_")
    filename = f"Offer_Letter_{student_name}.pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )
