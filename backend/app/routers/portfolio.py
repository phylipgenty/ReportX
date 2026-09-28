"""
Portfolio KPIs (README §28 / §45). Definitions are driven by flags on the
lookup data, not by literal status names:
  completed        project_status.is_complete
  not started      project_status.is_not_started
  needs attention  any RAG whose value has rag.needs_attention
  at risk/delayed  not complete AND (schedule variance > 0 OR any milestone
                   whose status has milestone_status.is_delayed)
Draft projects are excluded from the KPIs and counted separately.
"""
from typing import Optional

from fastapi import APIRouter

from app.services.store import store
from app.services import domain

router = APIRouter(tags=["portfolio"])


def _flagged(lookups: dict, kind: str, flag: str) -> set:
    return {o["value"] for o in lookups.get(kind, []) if o.get(flag)}


@router.get("/portfolio/summary")
def summary(entity_id: Optional[str] = None):
    lookups = store.lookups()
    complete = _flagged(lookups, "project_status", "is_complete")
    not_started = _flagged(lookups, "project_status", "is_not_started")
    attention = _flagged(lookups, "rag", "needs_attention")
    delayed_ms = _flagged(lookups, "milestone_status", "is_delayed")

    projects = [domain.hydrate(p) for p in store.list_projects()]
    if entity_id and entity_id != "all":
        projects = [p for p in projects if p.identity.entity_id == entity_id]
    drafts = [p for p in projects if p.is_draft]
    live = [p for p in projects if not p.is_draft]

    def at_risk(p) -> bool:
        if p.identity.status in complete:
            return False
        late = (p.schedule.variance_days or 0) > 0
        return late or any(m.status in delayed_ms for m in p.milestones)

    budget = sum(p.resources.planned_budget for p in live)
    actual = sum(p.resources.actual_cost_to_date for p in live)
    return {
        "projects": len(live),
        "drafts": len(drafts),
        "completed": sum(p.identity.status in complete for p in live),
        "not_started": sum(p.identity.status in not_started for p in live),
        "average_completion": round(sum(p.identity.completion_pct for p in live) / len(live), 1) if live else 0,
        "needs_attention": sum(
            any(v in attention for v in (p.rag.schedule, p.rag.budget, p.rag.issues)) for p in live
        ),
        "at_risk_delayed": sum(at_risk(p) for p in live),
        "total_budget": budget,
        "total_actual": actual,
        "spend_pct": round(actual / budget * 100, 1) if budget else 0,
    }
