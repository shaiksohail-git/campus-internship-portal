"""Weekly analytics digest - sends a summary email to opted-in recruiters.

Called by the ``send-weekly-digest`` CLI command or a background scheduler.
"""

import datetime
import logging

from flask import render_template

from app.extensions import db
from app.models.enums import Role
from app.models.recruiter import RecruiterProfile
from app.models.user import User
from app.services import recruiter_analytics_service
from app.utils.email import email_service

logger = logging.getLogger(__name__)


def _build_digest_body(analytics: dict, company_name: str) -> str:
    """Return a plain-text email body for the weekly digest."""
    lines = [
        f"Hi {company_name} team,",
        "",
        "Here's your weekly hiring analytics summary from Campus Placement Portal.",
        "",
        "-- Overview -----------------------------------",
        f"  Total postings:        {analytics['total_opps']}",
        f"  Live postings:         {analytics['live_opps']}",
        f"  Total applications:    {analytics['total_apps']}",
        f"  Shortlisted:           {analytics['shortlisted']}",
        f"  Selected:              {analytics['selected']}",
        f"  Rejected:              {analytics['rejected']}",
        f"  Selection rate:        {analytics['selection_rate']}%",
        f"  Avg apps per posting:  {analytics['avg_apps_per_opp']}",
        "",
    ]

    # Top opportunities
    if analytics["opp_apps"]:
        lines.append("-- Top opportunities by applications ----------")
        for opp in analytics["opp_apps"][:5]:
            lines.append(f"  * {opp['title'][:40]}  -  {opp['app_count']} apps")
        lines.append("")

    # College breakdown
    if analytics["college_breakdown"]:
        lines.append("-- Top applicant colleges --------------------")
        for item in analytics["college_breakdown"][:5]:
            lines.append(f"  * {item['name']}  -  {item['count']} applicants")
        lines.append("")

    # Department breakdown
    if analytics["dept_applications"]:
        lines.append("-- Top departments / branches ----------------")
        for dept, count in list(analytics["dept_applications"].items())[:5]:
            lines.append(f"  * {dept}  -  {count} applicants")
        lines.append("")

    # Peer comparison
    peer = analytics["peer"]
    lines.append("-- How you compare (anonymised) --------------")
    lines.append(f"  Avg apps per posting:  yours {analytics['avg_apps_per_opp']}  |  peer avg {peer['avg_apps_per_opp']}")
    lines.append(f"  Selection rate:        yours {analytics['selection_rate']}%  |  peer avg {peer['selection_rate']}%")
    lines.append("")

    lines.append("---------------------------------------------")
    lines.append("View your full analytics dashboard:")
    lines.append("  /recruiter/analytics")
    lines.append("")
    lines.append("You can disable these weekly emails from your company profile page.")

    return "\n".join(lines)


def send_weekly_digests(app=None):
    """Send digest emails to all opted-in recruiters.

    Can be called from a CLI command or a background scheduler.
    When called outside a Flask app context, pass ``app`` to push the context.
    """
    from app import create_app

    own_app = app is None
    if own_app:
        app = create_app()

    with app.app_context():
        recruiters = (
            db.session.query(RecruiterProfile, User)
            .join(User, User.id == RecruiterProfile.user_id)
            .filter(
                RecruiterProfile.weekly_digest_enabled == True,  # noqa: E712
                User.is_active == True,  # noqa: E712
                User.is_verified == True,  # noqa: E712
                RecruiterProfile.approval_status == "APPROVED",
            )
            .all()
        )

        sent = 0
        for profile, user in recruiters:
            try:
                data = recruiter_analytics_service.analytics(profile.id)
                body = _build_digest_body(data, profile.company_name)
                subject = f"Weekly Hiring Digest - {profile.company_name}"

                # Send via email service (console in dev, SMTP in production)
                email_service.send(user.email, subject, body)
                sent += 1
                logger.info("Digest sent to %s (%s)", user.email, profile.company_name)
            except Exception:
                logger.exception("Failed to send digest to %s", user.email)

        logger.info("Weekly digest sent to %d recruiters.", sent)
        return sent
