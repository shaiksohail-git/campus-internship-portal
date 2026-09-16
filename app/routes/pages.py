"""Public pages — landing and generic error helpers."""

from flask import Blueprint, render_template

bp = Blueprint("pages", __name__)


@bp.get("/")
def landing():
    from app.models.enums import OpportunityStatus
    from app.models.opportunity import Opportunity

    live_opportunities = Opportunity.query.filter_by(status=OpportunityStatus.APPROVED).count()
    return render_template("landing.html", live_opportunities=live_opportunities)


@bp.get("/forbidden")
def forbidden():
    return render_template("errors/403.html"), 403
