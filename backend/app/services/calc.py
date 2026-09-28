"""
Pure calculation functions. No I/O, no side effects — trivially testable,
and easily reused from the report engine, import pipeline, and dashboard.
"""
from __future__ import annotations
from datetime import date
from typing import Optional, Tuple, List, Collection

from app.models.project import Project, ProjectSchedule
from app.models.cost import ProjectResources, CostAssumptions
from app.models.milestone import Milestone, MilestoneDefinition
from app.models.risk import Risk


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------
def _to_date(s: Optional[str]) -> Optional[date]:
    """ISO date or None (placeholders such as TBD / N/A are not dates)."""
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def schedule_variance(schedule: ProjectSchedule, is_completed: bool) -> Optional[int]:
    """
    README §9.1 — positive means later than planned:
      completed:     Actual Delivery   - TSC Approved Date
      not completed: Forecast Delivery - TSC Approved Date
    None when the date the rule needs is missing.
    """
    tsc = _to_date(schedule.tsc_approved_date)
    ref = _to_date(schedule.actual_delivery if is_completed else schedule.forecast_delivery)
    if not tsc or not ref:
        return None
    return (ref - tsc).days


# ---------------------------------------------------------------------------
# Cost
# ---------------------------------------------------------------------------
def resource_cost(res: ProjectResources, rates: CostAssumptions) -> float:
    return (
        res.junior_days * rates.junior_rate
        + res.intermediate_days * rates.intermediate_rate
        + res.expert_days * rates.expert_rate
    )


def planned_budget(
    res: ProjectResources, rates: CostAssumptions
) -> Tuple[float, float, float]:
    """Returns (resource_cost, contingency, planned_budget)."""
    rc = resource_cost(res, rates)
    contingency = rc * (rates.contingency_pct / 100.0)
    total = rc + contingency + res.other_planned_costs
    return rc, contingency, total


# ---------------------------------------------------------------------------
# Completion
# ---------------------------------------------------------------------------
def completion_pct(
    milestones: List[Milestone],
    defs: List[MilestoneDefinition],
    complete_statuses: Collection[str],
    strategy: str = "equal",
) -> float:
    """
    README §8 / §53.1 — the business rule is not final, so both the strategy
    (settings.completion_strategy) and which statuses count as complete
    (`counts_complete` on the milestone_status lookup) are configuration.
    equal:    every lifecycle milestone contributes 1/len(defs).
    weighted: MilestoneDefinition.weight.
    """
    if not defs:
        return 0.0
    by_key = {m.key: m for m in milestones}

    if strategy == "weighted":
        total_w = sum((d.weight or 0) for d in defs)
        if total_w == 0:
            return 0.0
        earned = 0.0
        for d in defs:
            m = by_key.get(d.key)
            if m and m.status in complete_statuses:
                earned += d.weight or 0
        return round(earned / total_w * 100, 2)

    # default: equal
    done = 0
    for d in defs:
        m = by_key.get(d.key)
        if m and m.status in complete_statuses:
            done += 1
    return round(done / len(defs) * 100, 2)


# ---------------------------------------------------------------------------
# Risk
# ---------------------------------------------------------------------------
def risk_score(probability: Optional[int], impact: Optional[int]) -> int:
    if probability is None or impact is None:
        return 0
    return int(probability) * int(impact)


# ---------------------------------------------------------------------------
# Aggregate recalculation — call this whenever a project is hydrated from
# the store so persisted fields never drift from their derived truth.
# ---------------------------------------------------------------------------
def recalc_project(
    p: Project,
    rates: CostAssumptions,
    defs: List[MilestoneDefinition],
    complete_statuses: Collection[str],
    completed_project_statuses: Collection[str],
    completion_strategy: str = "equal",
) -> Project:
    p.schedule.variance_days = schedule_variance(
        p.schedule, p.identity.status in completed_project_statuses
    )

    rc, cont, total = planned_budget(p.resources, rates)
    p.resources.resource_cost = rc
    p.resources.contingency = cont
    p.resources.planned_budget = total

    p.identity.completion_pct = completion_pct(p.milestones, defs, complete_statuses, completion_strategy)

    for r in p.risks:
        r.risk_score = risk_score(r.probability, r.impact)

    return p