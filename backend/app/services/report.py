"""
Assembles the formal Project Status Report (README §31–§38).

Which project state is reported (README §38 "Load Project State"):
  1. an explicit saved state (state_id), else
  2. the live project when use_current is set, else
  3. the latest saved state taken on or before the period end date, else
  4. the live project.
The chosen source is recorded in the report metadata.
"""
from __future__ import annotations
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import HTTPException

from app.models.project import Project
from app.models.report import (
    ReportRequest, ReportingPeriod, ReportMetadata, ReportSource,
    MilestoneReviewRow, ProjectStatusReport,
)
from app.services import domain
from app.services.store import store


def _parse(d: str, field: str) -> date:
    try:
        return date.fromisoformat(d)
    except (TypeError, ValueError):
        raise HTTPException(422, f"{field} must be a YYYY-MM-DD date")


def build_report(project_id: str, req: ReportRequest, default_author: str = "") -> ProjectStatusReport:
    """default_author: the signed-in user, used when no report author is given."""
    if _parse(req.start_date, "start_date") > _parse(req.end_date, "end_date"):
        raise HTTPException(422, "start_date must be on or before end_date")
    domain.require_project(project_id)

    state: Optional[dict] = None
    if req.state_id:
        state = store.get_state(req.state_id)
        if not state or state["project_id"] != project_id:
            raise HTTPException(404, "Saved state not found")
    elif not req.use_current:
        state = store.latest_state_on_or_before(project_id, req.end_date)

    if state:
        project = Project(**state["snapshot"])
        source = ReportSource(kind="state", state_id=state["id"], label=state["label"], saved_at=state["saved_at"])
    else:
        project = domain.get_hydrated(project_id)
        source = ReportSource(kind="current", label="Current project data")

    labels = {d.key: d.label for d in domain.milestone_defs()}
    with_issues = {i.milestone_key for i in project.issues if i.milestone_key}

    return ProjectStatusReport(
        metadata=ReportMetadata(
            project_id=project.id,
            project_title=project.identity.name,
            reporting_period=ReportingPeriod(start_date=req.start_date, end_date=req.end_date),
            date_of_report=datetime.now(timezone.utc).date().isoformat(),
            delivery_manager=project.identity.project_manager,
            report_author=(req.report_author or "").strip() or default_author or project.identity.project_manager,
            executive_sponsor=(req.executive_sponsor or "").strip() or project.identity.executive_sponsor or None,
            delivery_organisation=project.identity.delivery_organisation or store.setting("organisation_name"),
            source=source,
        ),
        executive_summary=project.executive_summary,
        narrative=project.identity.status_update,
        rag=project.rag,
        completion_pct=project.identity.completion_pct,
        variance_days=project.schedule.variance_days,
        milestone_status_review=[
            MilestoneReviewRow(
                key=m.key, label=labels.get(m.key, m.key), status=m.status,
                baseline_date=m.baseline_date, expected_date=m.expected_date,
                actual_date=m.actual_date, has_issues=m.key in with_issues,
            )
            for m in project.milestones
        ],
        planned_activities=project.planned_activities,
        issues=project.issues,
        risks=project.risks,
    )
