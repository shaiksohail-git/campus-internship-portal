"""Analytics export — generate CSV and PDF reports for recruiter analytics."""

import csv
import io
import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)


# ── CSV ────────────────────────────────────────────────────────────────


def generate_csv(data: dict) -> io.StringIO:
    """Build a multi-section CSV report from analytics data."""
    buf = io.StringIO()
    w = csv.writer(buf)

    # Section 1 — Overview
    w.writerow(["Hiring Analytics Report"])
    w.writerow(["Generated", datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")])
    w.writerow(["Date range", data.get("range_label", "All time")])
    w.writerow([])
    w.writerow(["Metric", "Value"])
    w.writerow(["Total postings", data["total_opps"]])
    w.writerow(["Live postings", data["live_opps"]])
    w.writerow(["Total applications", data["total_apps"]])
    w.writerow(["Shortlisted", data["shortlisted"]])
    w.writerow(["Interviewed / shortlisted", data["interviewed"]])
    w.writerow(["Selected", data["selected"]])
    w.writerow(["Rejected", data["rejected"]])
    w.writerow(["Selection rate", f"{data['selection_rate']}%"])
    w.writerow(["Avg. applications per posting", data["avg_apps_per_opp"]])
    w.writerow([])

    # Section 2 — Applications per opportunity
    w.writerow(["Applications per Opportunity"])
    w.writerow(["Opportunity", "Type", "Status", "Applications"])
    for opp in data["opp_apps"]:
        w.writerow([opp["title"], opp["type"], opp["status"], opp["app_count"]])
    w.writerow([])

    # Section 3 — College breakdown
    w.writerow(["College Breakdown"])
    w.writerow(["College", "Applications"])
    for item in data["college_breakdown"]:
        w.writerow([item["name"], item["count"]])
    w.writerow([])

    # Section 4 — Department breakdown
    w.writerow(["Department / Branch Breakdown"])
    w.writerow(["Department", "Applications"])
    for dept, count in data["dept_applications"].items():
        w.writerow([dept, count])
    w.writerow([])

    # Section 5 — Status funnel
    status_labels = {
        "APPLIED": "Applied",
        "SHORTLISTED": "Shortlisted",
        "INTERVIEW_SCHEDULED": "Interview Scheduled",
        "SELECTED": "Selected",
        "REJECTED": "Rejected",
    }
    w.writerow(["Application Status Funnel"])
    w.writerow(["Status", "Count"])
    for status in ["APPLIED", "SHORTLISTED", "INTERVIEW_SCHEDULED", "SELECTED", "REJECTED"]:
        w.writerow([status_labels.get(status, status), data["status_funnel"].get(status, 0)])
    w.writerow([])

    # Section 6 — Peer comparison
    w.writerow(["Peer Comparison (Anonymised)"])
    w.writerow(["Metric", "You", "Peer Average"])
    w.writerow(["Avg. applications per posting", data["avg_apps_per_opp"], data["peer"]["avg_apps_per_opp"]])
    w.writerow(["Selection rate", f"{data['selection_rate']}%", f"{data['peer']['selection_rate']}%"])
    w.writerow(["Live postings", data["live_opps"], data["peer"]["avg_opps"]])

    buf.seek(0)
    return buf


# ── PDF ────────────────────────────────────────────────────────────────

STYLES = getSampleStyleSheet()
STYLES.add(ParagraphStyle(name="SectionTitle", fontSize=13, fontName="Helvetica-Bold",
                           spaceAfter=6, spaceBefore=14, textColor=colors.HexColor("#1e293b")))
STYLES.add(ParagraphStyle(name="Small", fontSize=9, fontName="Helvetica",
                           textColor=colors.HexColor("#64748b")))
STYLES.add(ParagraphStyle(name="Cell", fontSize=8.5, fontName="Helvetica"))
STYLES.add(ParagraphStyle(name="CellBold", fontSize=8.5, fontName="Helvetica-Bold"))


def _status_color(status):
    return {
        "APPLIED": colors.HexColor("#6366f1"),
        "SHORTLISTED": colors.HexColor("#f59e0b"),
        "INTERVIEW_SCHEDULED": colors.HexColor("#06b6d4"),
        "SELECTED": colors.HexColor("#10b981"),
        "REJECTED": colors.HexColor("#ef4444"),
    }.get(status, colors.grey)


def generate_pdf(data: dict) -> bytes:
    """Build a styled PDF report from analytics data."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=18 * mm, bottomMargin=18 * mm)
    story = []
    now = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")

    # Title
    story.append(Paragraph("Hiring Analytics Report", STYLES["Title"]))
    story.append(Paragraph(f"Generated on {now}", STYLES["Small"]))
    story.append(Paragraph(f"Date range: {data.get('range_label', 'All time')}", STYLES["Small"]))
    story.append(Spacer(1, 8 * mm))

    # ── Overview stats table ───────────────────────────────────────────
    story.append(Paragraph("Overview", STYLES["SectionTitle"]))
    stats = [
        ["Metric", "Value"],
        ["Total postings", str(data["total_opps"])],
        ["Live postings", str(data["live_opps"])],
        ["Total applications", str(data["total_apps"])],
        ["Shortlisted", str(data["shortlisted"])],
        ["Interviewed / shortlisted", str(data["interviewed"])],
        ["Selected", str(data["selected"])],
        ["Rejected", str(data["rejected"])],
        ["Selection rate", f"{data['selection_rate']}%"],
        ["Avg. apps per posting", str(data["avg_apps_per_opp"])],
    ]
    t = Table(stats, colWidths=[120 * mm, 45 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)

    # ── Applications per opportunity ───────────────────────────────────
    story.append(Paragraph("Applications per Opportunity", STYLES["SectionTitle"]))
    opp_rows = [["Opportunity", "Type", "Status", "Apps"]]
    for opp in data["opp_apps"]:
        title = opp["title"][:35] + ("…" if len(opp["title"]) > 35 else "")
        opp_rows.append([title, opp["type"].replace("_", " ").title(), opp["status"], str(opp["app_count"])])
    if len(opp_rows) == 1:
        opp_rows.append(["—", "—", "—", "—"])
    t2 = Table(opp_rows, colWidths=[72 * mm, 32 * mm, 38 * mm, 20 * mm])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t2)

    # ── College breakdown ──────────────────────────────────────────────
    story.append(Paragraph("Top Colleges", STYLES["SectionTitle"]))
    c_rows = [["College", "Applications"]]
    for item in data["college_breakdown"]:
        c_rows.append([item["name"][:40], str(item["count"])])
    if len(c_rows) == 1:
        c_rows.append(["—", "—"])
    t3 = Table(c_rows, colWidths=[120 * mm, 45 * mm])
    t3.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t3)

    # ── Department breakdown ───────────────────────────────────────────
    story.append(Paragraph("Departments / Branches", STYLES["SectionTitle"]))
    d_rows = [["Department", "Applications"]]
    for dept, count in data["dept_applications"].items():
        d_rows.append([dept[:40], str(count)])
    if len(d_rows) == 1:
        d_rows.append(["—", "—"])
    t4 = Table(d_rows, colWidths=[120 * mm, 45 * mm])
    t4.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t4)

    # ── Status funnel ──────────────────────────────────────────────────
    story.append(Paragraph("Application Status Funnel", STYLES["SectionTitle"]))
    status_labels = {
        "APPLIED": "Applied", "SHORTLISTED": "Shortlisted",
        "INTERVIEW_SCHEDULED": "Interview Scheduled",
        "SELECTED": "Selected", "REJECTED": "Rejected",
    }
    f_rows = [["Status", "Count"]]
    for s in ["APPLIED", "SHORTLISTED", "INTERVIEW_SCHEDULED", "SELECTED", "REJECTED"]:
        f_rows.append([status_labels.get(s, s), str(data["status_funnel"].get(s, 0))])
    t5 = Table(f_rows, colWidths=[100 * mm, 65 * mm])
    t5.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t5)

    # ── Peer comparison ────────────────────────────────────────────────
    story.append(Paragraph("Peer Comparison (Anonymised)", STYLES["SectionTitle"]))
    p_rows = [
        ["Metric", "You", "Peer Average"],
        ["Avg. apps per posting", str(data["avg_apps_per_opp"]), str(data["peer"]["avg_apps_per_opp"])],
        ["Selection rate", f"{data['selection_rate']}%", f"{data['peer']['selection_rate']}%"],
        ["Live postings", str(data["live_opps"]), str(data["peer"]["avg_opps"])],
    ]
    t6 = Table(p_rows, colWidths=[72 * mm, 46 * mm, 46 * mm])
    t6.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t6)

    doc.build(story)
    return buf.getvalue()
