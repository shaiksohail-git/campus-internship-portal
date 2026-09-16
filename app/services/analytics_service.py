"""Analytics service — basic placement statistics via SQL against operational
tables (no separate analytics database in V1)."""

import datetime

from sqlalchemy import func

from app.extensions import db
from app.models.application import Application
from app.models.enums import ApplicationStatus, OpportunityStatus, OpportunityType, RecruiterApprovalStatus, Role
from app.models.interview import Interview
from app.models.opportunity import Opportunity
from app.models.recruiter import RecruiterProfile
from app.models.student import StudentProfile
from app.models.user import User


def dashboard_stats():
    students = User.query.filter_by(role=Role.STUDENT).count()
    recruiters = User.query.filter_by(role=Role.RECRUITER).count()
    pending_recruiters = RecruiterProfile.query.filter_by(
        approval_status=RecruiterApprovalStatus.PENDING
    ).count()
    active_opportunities = Opportunity.query.filter_by(status=OpportunityStatus.APPROVED).count()
    pending_opportunities = Opportunity.query.filter_by(status=OpportunityStatus.PENDING_REVIEW).count()
    total_applications = Application.query.count()
    interviews = Interview.query.filter(Interview.status.in_(["SCHEDULED", "UPDATED"])).count()
    selected = Application.query.filter_by(status=ApplicationStatus.SELECTED).count()

    return {
        "students": students,
        "recruiters": recruiters,
        "pending_recruiters": pending_recruiters,
        "pending_opportunities": pending_opportunities,
        "active_opportunities": active_opportunities,
        "total_applications": total_applications,
        "interviews_scheduled": interviews,
        "students_selected": selected,
    }


def analytics():
    stats = dashboard_stats()
    now = datetime.datetime.now(datetime.timezone.utc)

    # Internship vs full-time applications
    by_type = dict(
        db.session.query(Opportunity.type, func.count(Application.id))
        .join(Application, Application.opportunity_id == Opportunity.id)
        .group_by(Opportunity.type)
        .all()
    )

    # Department-wise applications
    dept_applications = dict(
        db.session.query(StudentProfile.department, func.count(Application.id))
        .join(Application, Application.student_id == StudentProfile.id)
        .filter(StudentProfile.department.isnot(None))
        .group_by(StudentProfile.department)
        .order_by(func.count(Application.id).desc())
        .all()
    )
    dept_selections = dict(
        db.session.query(StudentProfile.department, func.count(Application.id))
        .join(Application, Application.student_id == StudentProfile.id)
        .filter(
            StudentProfile.department.isnot(None),
            Application.status == ApplicationStatus.SELECTED,
        )
        .group_by(StudentProfile.department)
        .all()
    )

    # Company-wise hiring (selections per company)
    # NOTE: company name lives on RecruiterProfile — query it directly.
    # Convert Rows to plain tuples so the data is JSON-serializable.
    company_hiring = [
        (row[0], row[1])
        for row in db.session.query(RecruiterProfile.company_name, func.count(Application.id))
        .join(Opportunity, Opportunity.recruiter_id == RecruiterProfile.id)
        .join(Application, Application.opportunity_id == Opportunity.id)
        .filter(Application.status == ApplicationStatus.SELECTED)
        .group_by(RecruiterProfile.company_name)
        .order_by(func.count(Application.id).desc())
        .limit(8)
        .all()
    ]

    # Monthly application activity (last 6 months)
    monthly = []
    for i in range(5, -1, -1):
        month_start = datetime.datetime(now.year, now.month, 1) - datetime.timedelta(days=30 * i)
        year, month = month_start.year, month_start.month
        count = Application.query.filter(
            func.strftime("%Y", Application.applied_at) == str(year),
            func.strftime("%m", Application.applied_at) == f"{month:02d}",
        ).count()
        monthly.append(
            {"label": month_start.strftime("%b %y"), "count": count}
        )

    # Applications per opportunity (top 5) — plain tuples for JSON-safety
    top_opportunities = [
        (row[0], row[1], row[2])
        for row in db.session.query(
            Opportunity.title, RecruiterProfile.company_name, func.count(Application.id)
        )
        .join(RecruiterProfile, Opportunity.recruiter_id == RecruiterProfile.id)
        .join(Application, Application.opportunity_id == Opportunity.id)
        .group_by(Opportunity.id)
        .order_by(func.count(Application.id).desc())
        .limit(5)
        .all()
    ]

    total_apps = max(stats["total_applications"], 1)
    return {
        "stats": stats,
        "internship_applications": by_type.get(OpportunityType.INTERNSHIP, 0),
        "fulltime_applications": by_type.get(OpportunityType.FULL_TIME, 0),
        "internship_ratio": round(100 * by_type.get(OpportunityType.INTERNSHIP, 0) / total_apps),
        "fulltime_ratio": round(100 * by_type.get(OpportunityType.FULL_TIME, 0) / total_apps),
        "dept_applications": dept_applications,
        "dept_selections": dept_selections,
        "company_hiring": company_hiring,
        "monthly_activity": monthly,
        "top_opportunities": top_opportunities,
        "selection_rate": round(100 * stats["students_selected"] / total_apps),
        "shortlisted": Application.query.filter_by(status=ApplicationStatus.SHORTLISTED).count(),
        "rejected": Application.query.filter_by(status=ApplicationStatus.REJECTED).count(),
        "interviews_scheduled": stats["interviews_scheduled"],
    }
