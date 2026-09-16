"""Recruiter analytics — statistics scoped to one recruiter's opportunities,
with anonymised peer benchmarks so companies can gauge their hiring reach.

Accepts optional ``start_date`` / ``end_date`` (``datetime.date`` or ``None``)
to restrict application-based metrics to a window.  When ``None`` the query is
unbounded (i.e. all time).  Opportunity-level counts (total postings, live
postings) are always shown for the full history so the recruiter retains
context.
"""

import datetime

from sqlalchemy import func

from app.extensions import db
from app.models.application import Application
from app.models.enums import ApplicationStatus, OpportunityStatus
from app.models.opportunity import Opportunity
from app.models.recruiter import RecruiterProfile
from app.models.student import StudentProfile


def _parse_date(value):
    """Try to parse a YYYY-MM-DD string into a date, or return None."""
    if not value:
        return None
    try:
        return datetime.date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def analytics(recruiter_id: int, start_date=None, end_date=None) -> dict:
    """Return a dict consumed by the recruiter analytics template.

    Parameters
    ----------
    recruiter_id : int
    start_date : datetime.date or None
        When set, only applications with ``applied_at >= start_date`` are counted.
    end_date : datetime.date or None
        When set, only applications with ``applied_at <= end_date`` are counted.
    """

    # ── resolve date boundaries ────────────────────────────────────────
    sd = _parse_date(start_date)
    ed = _parse_date(end_date)

    # ── base queries scoped to this recruiter ──────────────────────────
    my_opps = Opportunity.query.filter_by(recruiter_id=recruiter_id)
    my_opp_ids = [o.id for o in my_opps.all()]

    # Application base query (always scoped to this recruiter's opps)
    my_apps = Application.query.filter(Application.opportunity_id.in_(my_opp_ids)) if my_opp_ids else Application.query.filter(False)

    # Apply date filter to application queries
    if sd:
        my_apps = my_apps.filter(Application.applied_at >= datetime.datetime.combine(sd, datetime.time.min))
    if ed:
        my_apps = my_apps.filter(Application.applied_at <= datetime.datetime.combine(ed, datetime.time.max))

    # ── stat cards ─────────────────────────────────────────────────────
    total_opps = my_opps.count()
    live_opps = my_opps.filter_by(status=OpportunityStatus.APPROVED).count()
    total_apps = my_apps.count()
    shortlisted = my_apps.filter_by(status=ApplicationStatus.SHORTLISTED).count()
    interviewed = my_apps.filter(
        Application.status.in_([ApplicationStatus.SHORTLISTED, ApplicationStatus.SELECTED])
    ).count()
    selected = my_apps.filter_by(status=ApplicationStatus.SELECTED).count()
    rejected = my_apps.filter_by(status=ApplicationStatus.REJECTED).count()
    selection_rate = round(100 * selected / total_apps) if total_apps else 0
    # Avg apps per posting uses *all-time* postings count for context
    avg_apps_per_opp = round(total_apps / total_opps, 1) if total_opps else 0

    # ── applications per opportunity (date-filtered) ───────────────────
    opp_app_q = (
        db.session.query(
            Opportunity.id,
            Opportunity.title,
            Opportunity.type,
            Opportunity.status,
            func.count(Application.id).label("app_count"),
        )
        .outerjoin(Application, Application.opportunity_id == Opportunity.id)
        .filter(Opportunity.recruiter_id == recruiter_id)
    )
    if sd:
        opp_app_q = opp_app_q.filter(Application.applied_at >= datetime.datetime.combine(sd, datetime.time.min))
    if ed:
        opp_app_q = opp_app_q.filter(Application.applied_at <= datetime.datetime.combine(ed, datetime.time.max))

    opp_apps = opp_app_q.group_by(Opportunity.id).order_by(func.count(Application.id).desc()).all()

    # ── department breakdown (date-filtered) ───────────────────────────
    dept_q = (
        db.session.query(
            func.coalesce(StudentProfile.department, "Unknown"),
            func.count(Application.id),
        )
        .join(Application, Application.student_id == StudentProfile.id)
        .filter(Application.opportunity_id.in_(my_opp_ids) if my_opp_ids else False)
    )
    if sd:
        dept_q = dept_q.filter(Application.applied_at >= datetime.datetime.combine(sd, datetime.time.min))
    if ed:
        dept_q = dept_q.filter(Application.applied_at <= datetime.datetime.combine(ed, datetime.time.max))
    college_counts = dict(
        dept_q.group_by(StudentProfile.department)
        .order_by(func.count(Application.id).desc())
        .all()
    )

    # ── college-wise application counts (date-filtered) ────────────────
    from app.models.college import College

    coll_q = (
        db.session.query(
            College.name,
            func.count(Application.id),
        )
        .join(StudentProfile, StudentProfile.college_id == College.id)
        .join(Application, Application.student_id == StudentProfile.id)
        .filter(Application.opportunity_id.in_(my_opp_ids) if my_opp_ids else False)
    )
    if sd:
        coll_q = coll_q.filter(Application.applied_at >= datetime.datetime.combine(sd, datetime.time.min))
    if ed:
        coll_q = coll_q.filter(Application.applied_at <= datetime.datetime.combine(ed, datetime.time.max))
    college_breakdown = (
        coll_q.group_by(College.name)
        .order_by(func.count(Application.id).desc())
        .limit(10)
        .all()
    )

    # ── application status funnel (date-filtered) ──────────────────────
    funnel_q = Application.query.filter(
        Application.opportunity_id.in_(my_opp_ids) if my_opp_ids else False
    )
    if sd:
        funnel_q = funnel_q.filter(Application.applied_at >= datetime.datetime.combine(sd, datetime.time.min))
    if ed:
        funnel_q = funnel_q.filter(Application.applied_at <= datetime.datetime.combine(ed, datetime.time.max))
    status_funnel = dict(
        funnel_q.with_entities(Application.status, func.count(Application.id))
        .group_by(Application.status)
        .all()
    )

    # ── peer benchmarks (anonymised, always all-time) ─────────────────
    opp_counts_subq = (
        db.session.query(func.count(Application.id).label("cnt"))
        .join(Opportunity, Opportunity.id == Application.opportunity_id)
        .filter(Opportunity.status == OpportunityStatus.APPROVED)
        .group_by(Opportunity.id)
        .subquery()
    )
    peer_stats = db.session.query(func.avg(opp_counts_subq.c.cnt)).scalar()
    peer_avg_apps = round(float(peer_stats or 0), 1)

    peer_total_apps = Application.query.count()
    peer_total_selected = Application.query.filter_by(status=ApplicationStatus.SELECTED).count()
    peer_selection_rate = round(100 * peer_total_selected / peer_total_apps) if peer_total_apps else 0

    peer_live_opps = Opportunity.query.filter_by(status=OpportunityStatus.APPROVED).count()
    peer_recruiters = RecruiterProfile.query.filter_by(is_approved=True).count()
    peer_avg_opps = round(peer_live_opps / peer_recruiters, 1) if peer_recruiters else 0

    # ── human-readable date range label ────────────────────────────────
    if sd and ed:
        range_label = f"{sd.strftime('%d %b %Y')} – {ed.strftime('%d %b %Y')}"
    elif sd:
        range_label = f"From {sd.strftime('%d %b %Y')}"
    elif ed:
        range_label = f"Until {ed.strftime('%d %b %Y')}"
    else:
        range_label = "All time"

    return {
        "total_opps": total_opps,
        "live_opps": live_opps,
        "total_apps": total_apps,
        "shortlisted": shortlisted,
        "interviewed": interviewed,
        "selected": selected,
        "rejected": rejected,
        "selection_rate": selection_rate,
        "avg_apps_per_opp": avg_apps_per_opp,
        "opp_apps": [
            {
                "id": row.id,
                "title": row.title,
                "type": row.type,
                "status": row.status,
                "app_count": row.app_count,
            }
            for row in opp_apps
        ],
        "dept_applications": college_counts,
        "college_breakdown": [{"name": name, "count": count} for name, count in college_breakdown],
        "status_funnel": status_funnel,
        "peer": {
            "avg_apps_per_opp": peer_avg_apps,
            "selection_rate": peer_selection_rate,
            "avg_opps": peer_avg_opps,
        },
        "range_label": range_label,
        "start_date": sd.isoformat() if sd else "",
        "end_date": ed.isoformat() if ed else "",
        # ── monthly trend (last 6 months) ─────────────────────────────
        "monthly_trend": _monthly_trend(my_opp_ids, sd, ed),
        # ── period-over-period deltas ─────────────────────────────────
        "trends": _period_trends(my_opp_ids, sd, ed),
    }


def _monthly_trend(opp_ids, sd, ed):
    """Applications per month for the last 6 months."""
    now = datetime.datetime.now(datetime.timezone.utc)
    months = []
    for i in range(5, -1, -1):
        month_start = datetime.datetime(now.year, now.month, 1) - datetime.timedelta(days=30 * i)
        year, month = month_start.year, month_start.month
        q = Application.query.filter(
            Application.opportunity_id.in_(opp_ids) if opp_ids else False,
            func.strftime("%Y", Application.applied_at) == str(year),
            func.strftime("%m", Application.applied_at) == f"{month:02d}",
        )
        if sd:
            q = q.filter(Application.applied_at >= datetime.datetime.combine(sd, datetime.time.min))
        if ed:
            q = q.filter(Application.applied_at <= datetime.datetime.combine(ed, datetime.time.max))
        months.append({"label": month_start.strftime("%b"), "count": q.count()})
    return months


def _period_trends(opp_ids, sd, ed):
    """Compare current period to the previous period of equal length."""
    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.date()

    # Default: compare last 30 days vs the 30 days before that
    if sd and ed:
        length = (ed - sd).days or 30
        curr_start = sd
        curr_end = ed
        prev_start = sd - datetime.timedelta(days=length)
        prev_end = sd - datetime.timedelta(days=1)
    else:
        length = 30
        curr_start = today - datetime.timedelta(days=length)
        curr_end = today
        prev_start = today - datetime.timedelta(days=length * 2)
        prev_end = today - datetime.timedelta(days=length)

    def _count(start, end):
        q = Application.query.filter(
            Application.opportunity_id.in_(opp_ids) if opp_ids else False,
            Application.applied_at >= datetime.datetime.combine(start, datetime.time.min),
            Application.applied_at <= datetime.datetime.combine(end, datetime.time.max),
        )
        return q.count()

    def _selected(start, end):
        q = Application.query.filter(
            Application.opportunity_id.in_(opp_ids) if opp_ids else False,
            Application.applied_at >= datetime.datetime.combine(start, datetime.time.min),
            Application.applied_at <= datetime.datetime.combine(end, datetime.time.max),
            Application.status == ApplicationStatus.SELECTED,
        )
        return q.count()

    curr_apps = _count(curr_start, curr_end)
    prev_apps = _count(prev_start, prev_end)
    curr_sel = _selected(curr_start, curr_end)
    prev_sel = _selected(prev_start, prev_end)

    def _delta(curr, prev):
        if prev == 0:
            return 0 if curr == 0 else 100
        return round(100 * (curr - prev) / prev)

    curr_rate = round(100 * curr_sel / curr_apps) if curr_apps else 0
    prev_rate = round(100 * prev_sel / prev_apps) if prev_apps else 0

    return {
        "applications": _delta(curr_apps, prev_apps),
        "selected": _delta(curr_sel, prev_sel),
        "selection_rate": curr_rate - prev_rate,
    }


def opportunity_analytics(recruiter_id: int, opportunity_id: int) -> dict:
    """Detailed analytics for a single opportunity."""
    from app.models.college import College

    opp = Opportunity.query.filter_by(id=opportunity_id, recruiter_id=recruiter_id).first()
    if opp is None:
        return None

    apps = Application.query.filter_by(opportunity_id=opp.id)

    total = apps.count()
    shortlisted = apps.filter_by(status=ApplicationStatus.SHORTLISTED).count()
    interviewed = apps.filter(
        Application.status.in_([ApplicationStatus.SHORTLISTED, ApplicationStatus.SELECTED])
    ).count()
    selected = apps.filter_by(status=ApplicationStatus.SELECTED).count()
    rejected = apps.filter_by(status=ApplicationStatus.REJECTED).count()
    selection_rate = round(100 * selected / total) if total else 0

    # Status funnel
    status_funnel = dict(
        apps.with_entities(Application.status, func.count(Application.id))
        .group_by(Application.status)
        .all()
    )

    # Department breakdown
    dept_breakdown = dict(
        db.session.query(
            func.coalesce(StudentProfile.department, "Unknown"),
            func.count(Application.id),
        )
        .join(Application, Application.student_id == StudentProfile.id)
        .filter(Application.opportunity_id == opp.id)
        .group_by(StudentProfile.department)
        .order_by(func.count(Application.id).desc())
        .all()
    )

    # College breakdown
    college_breakdown = [
        {"name": name, "count": count}
        for name, count in db.session.query(
            College.name,
            func.count(Application.id),
        )
        .join(StudentProfile, StudentProfile.college_id == College.id)
        .join(Application, Application.student_id == StudentProfile.id)
        .filter(Application.opportunity_id == opp.id)
        .group_by(College.name)
        .order_by(func.count(Application.id).desc())
        .limit(10)
        .all()
    ]

    # Recent applicants (last 20)
    recent_applicants = (
        db.session.query(Application)
        .filter_by(opportunity_id=opp.id)
        .order_by(Application.applied_at.desc())
        .limit(20)
        .all()
    )
    applicants_list = []
    for app in recent_applicants:
        s = app.student
        applicants_list.append({
            "id": app.id,
            "name": s.full_name,
            "college": s.college.name if s.college else "—",
            "department": s.department or "—",
            "graduation_year": s.graduation_year or "—",
            "status": app.status,
            "applied_at": app.applied_at.strftime("%d %b %Y") if app.applied_at else "—",
        })

    # Graduation year distribution
    year_dist = dict(
        db.session.query(StudentProfile.graduation_year, func.count(Application.id))
        .join(Application, Application.student_id == StudentProfile.id)
        .filter(
            Application.opportunity_id == opp.id,
            StudentProfile.graduation_year.isnot(None),
        )
        .group_by(StudentProfile.graduation_year)
        .order_by(StudentProfile.graduation_year)
        .all()
    )

    return {
        "opportunity": {
            "id": opp.id,
            "title": opp.title,
            "type": opp.type,
            "status": opp.status,
            "location": opp.location,
            "work_mode": opp.work_mode,
            "application_deadline": opp.application_deadline,
            "company_name": opp.company_name,
        },
        "total": total,
        "shortlisted": shortlisted,
        "interviewed": interviewed,
        "selected": selected,
        "rejected": rejected,
        "selection_rate": selection_rate,
        "status_funnel": status_funnel,
        "dept_breakdown": dept_breakdown,
        "college_breakdown": college_breakdown,
        "recent_applicants": applicants_list,
        "year_distribution": {str(k): v for k, v in year_dist.items()},
    }
