"""Offer letter service — create and send offer letters to selected applicants."""

import io
import datetime as _dt
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from app.extensions import db
from app.models.enums import ApplicationStatus, NotificationType
from app.models.offer_letter import OfferLetter
from app.services import notification_service
from app.utils.email import email_service
from app.utils.errors import BusinessRuleError, NotFoundError


def send_offer_letter(recruiter, application_id, data):
    """Create and send an offer letter to a selected applicant.

    Validates:
    - Application belongs to this recruiter
    - Application status is SELECTED
    - No duplicate offer letter already sent

    Returns the OfferLetter instance.
    """
    from app.models.application import Application

    application = db.session.get(Application, application_id)
    if application is None or application.opportunity.recruiter_id != recruiter.id:
        raise NotFoundError("Application not found.", code="APPLICATION_NOT_FOUND")

    if application.status != ApplicationStatus.SELECTED:
        raise BusinessRuleError(
            "Offer letters can only be sent to selected applicants.",
            code="INVALID_STATUS",
        )

    if application.offer_letter and application.offer_letter.sent_at:
        raise BusinessRuleError(
            "An offer letter has already been sent for this application.",
            code="OFFER_ALREADY_SENT",
        )

    opportunity = application.opportunity
    student = application.student
    user = student.user

    title = data.get("title", f"Offer — {opportunity.title} at {opportunity.company_name}")
    salary_or_stipend = data.get("salary_or_stipend") or opportunity.salary_or_stipend or ""
    joining_date = data.get("joining_date")  # YYYY-MM-DD string or None
    body = data.get("body", "")

    # Parse joining_date
    join_date = None
    if joining_date:
        try:
            join_date = _dt.date.fromisoformat(str(joining_date))
        except (ValueError, TypeError):
            pass

    # Create or update the offer letter
    if application.offer_letter:
        offer = application.offer_letter
        offer.title = title
        offer.salary_or_stipend = salary_or_stipend
        offer.joining_date = join_date
        offer.body = body
    else:
        offer = OfferLetter(
            application_id=application.id,
            recruiter_id=recruiter.id,
            title=title,
            salary_or_stipend=salary_or_stipend,
            joining_date=join_date,
            body=body,
        )
        db.session.add(offer)

    offer.sent_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.session.flush()

    # In-app notification
    notification_service.notify(
        user,
        NotificationType.APPLICATION_STATUS_CHANGED,
        "Offer letter received",
        f"Congratulations! You have received an offer letter for '{opportunity.title}' at {opportunity.company_name}.",
        email_subject=f"Offer Letter — {opportunity.title} at {opportunity.company_name}",
        email_body=_build_offer_email(student.full_name, opportunity, offer),
    )

    db.session.commit()
    return offer


def get_offer_letter(student, application_id):
    """Retrieve the offer letter for a student's application."""
    from app.models.application import Application

    application = db.session.get(Application, application_id)
    if application is None or application.student_id != student.id:
        raise NotFoundError("Application not found.", code="APPLICATION_NOT_FOUND")

    if application.offer_letter is None:
        raise NotFoundError("No offer letter found for this application.", code="NO_OFFER_LETTER")

    return application.offer_letter


def _build_offer_email(student_name, opportunity, offer):
    """Build a plain-text offer letter email body."""
    lines = [
        f"Dear {student_name},",
        "",
        f"Congratulations! We are pleased to extend an offer for the position of "
        f"'{opportunity.title}' at {opportunity.company_name}.",
        "",
    ]

    if offer.salary_or_stipend:
        lines.append(f"Compensation: {offer.salary_or_stipend}")
    if offer.joining_date:
        lines.append(f"Joining date: {offer.joining_date.strftime('%d %B %Y')}")
    if opportunity.location:
        lines.append(f"Location: {opportunity.location}")
    if opportunity.work_mode:
        lines.append(f"Work mode: {opportunity.work_mode.replace('_', ' ').title()}")

    lines.extend([
        "",
        "Offer details:",
        "—" * 40,
        offer.body or "(No additional details provided.)",
        "—" * 40,
        "",
        "Please log in to the Campus Placement Portal to view the full offer letter.",
        "",
        "Best regards,",
        f"{opportunity.company_name} Recruitment Team",
        "Campus Placement Portal",
    ])

    return "\n".join(lines)


# ------------------------------------------------------------------ PDF export

_OFFER_STYLES = getSampleStyleSheet()
_OFFER_STYLES.add(ParagraphStyle(
    name="OfferTitle", fontSize=18, fontName="Helvetica-Bold",
    spaceAfter=4, textColor=colors.HexColor("#1e293b"),
))
_OFFER_STYLES.add(ParagraphStyle(
    name="OfferSubtitle", fontSize=11, fontName="Helvetica",
    spaceAfter=2, textColor=colors.HexColor("#64748b"),
))
_OFFER_STYLES.add(ParagraphStyle(
    name="OfferBody", fontSize=11, fontName="Helvetica", leading=16,
    spaceAfter=6, textColor=colors.HexColor("#1e293b"),
))
_OFFER_STYLES.add(ParagraphStyle(
    name="OfferLabel", fontSize=9, fontName="Helvetica-Bold",
    textColor=colors.HexColor("#64748b"),
))
_OFFER_STYLES.add(ParagraphStyle(
    name="OfferValue", fontSize=11, fontName="Helvetica-Bold",
    textColor=colors.HexColor("#1e293b"),
))
_OFFER_STYLES.add(ParagraphStyle(
    name="OfferFooter", fontSize=9, fontName="Helvetica",
    textColor=colors.HexColor("#94a3b8"), alignment=1,
))


def generate_offer_letter_pdf(offer):
    """Generate a professional offer letter PDF and return raw bytes."""
    opp = offer.application.opportunity
    student = offer.application.student

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=25 * mm, rightMargin=25 * mm,
        topMargin=25 * mm, bottomMargin=25 * mm,
    )
    story = []

    # ── Company header ────────────────────────────────────────────────
    story.append(Paragraph(opp.company_name, _OFFER_STYLES["OfferTitle"]))
    story.append(Paragraph(opp.title, _OFFER_STYLES["OfferSubtitle"]))
    if opp.location:
        story.append(Paragraph(opp.location, _OFFER_STYLES["OfferSubtitle"]))
    story.append(Spacer(1, 6 * mm))

    # ── Horizontal rule ───────────────────────────────────────────────
    hr_table = Table([""],  colWidths=[160 * mm])
    hr_table.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(hr_table)
    story.append(Spacer(1, 6 * mm))

    # ── Date ───────────────────────────────────────────────────────────
    sent_date = offer.sent_at.strftime("%d %B %Y") if offer.sent_at else datetime.now().strftime("%d %B %Y")
    story.append(Paragraph(sent_date, _OFFER_STYLES["OfferBody"]))
    story.append(Spacer(1, 4 * mm))

    # ── Salutation ────────────────────────────────────────────────────
    story.append(Paragraph(f"Dear {student.full_name},", _OFFER_STYLES["OfferBody"]))
    story.append(Spacer(1, 3 * mm))

    # ── Offer body ────────────────────────────────────────────────────
    for para in (offer.body or "").split("\n"):
        text = para.strip()
        if text:
            story.append(Paragraph(text, _OFFER_STYLES["OfferBody"]))
        else:
            story.append(Spacer(1, 2 * mm))

    story.append(Spacer(1, 6 * mm))

    # ── Details table ──────────────────────────────────────────────────
    detail_rows = []
    if offer.salary_or_stipend:
        detail_rows.append([
            Paragraph("Compensation", _OFFER_STYLES["OfferLabel"]),
            Paragraph(offer.salary_or_stipend, _OFFER_STYLES["OfferValue"]),
        ])
    if offer.joining_date:
        detail_rows.append([
            Paragraph("Joining date", _OFFER_STYLES["OfferLabel"]),
            Paragraph(offer.joining_date.strftime("%d %B %Y"), _OFFER_STYLES["OfferValue"]),
        ])
    if opp.location:
        detail_rows.append([
            Paragraph("Location", _OFFER_STYLES["OfferLabel"]),
            Paragraph(opp.location, _OFFER_STYLES["OfferValue"]),
        ])
    if opp.work_mode:
        detail_rows.append([
            Paragraph("Work mode", _OFFER_STYLES["OfferLabel"]),
            Paragraph(opp.work_mode.replace("_", " ").title(), _OFFER_STYLES["OfferValue"]),
        ])

    if detail_rows:
        t = Table(detail_rows, colWidths=[35 * mm, 125 * mm])
        t.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (0, -1), 0),
            ("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.HexColor("#f1f5f9")),
        ]))
        story.append(t)

    story.append(Spacer(1, 12 * mm))

    # ── Signature ──────────────────────────────────────────────────────
    story.append(Paragraph("Best regards,", _OFFER_STYLES["OfferBody"]))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(f"{opp.company_name} Recruitment Team", _OFFER_STYLES["OfferBody"]))

    story.append(Spacer(1, 20 * mm))

    # ── Footer ─────────────────────────────────────────────────────────
    story.append(Paragraph(
        "This offer letter was generated via the Campus Placement Portal.",
        _OFFER_STYLES["OfferFooter"],
    ))

    doc.build(story)
    return buf.getvalue()


def get_offer_letter_for_recruiter(recruiter, application_id):
    """Retrieve the offer letter as seen by the recruiter."""
    from app.models.application import Application

    application = db.session.get(Application, application_id)
    if application is None or application.opportunity.recruiter_id != recruiter.id:
        raise NotFoundError("Application not found.", code="APPLICATION_NOT_FOUND")

    if application.offer_letter is None:
        raise NotFoundError("No offer letter found for this application.", code="NO_OFFER_LETTER")

    return application.offer_letter
