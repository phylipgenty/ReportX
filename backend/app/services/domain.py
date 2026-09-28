"""
Glue between the store, the calculation rules and the routers:
hydration (derive calculated fields), validation against the reference
data, and identifying the acting user.
"""
from __future__ import annotations
import re
from typing import List, Optional

from fastapi import HTTPException, Request

from app.config import settings
from app.models.cost import CostAssumptions
from app.models.issue import Issue
from app.models.milestone import MilestoneDefinition
from app.models.project import Project
from app.models.risk import Risk
from app.services.calc import recalc_project
from app.services.store import store

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def actor(request: Request) -> str:
    """Name of the signed-in user (set by auth.current_user), recorded in history."""
    user = getattr(request.state, "user", None)
    return user["name"] if user else settings.default_actor


def rates() -> CostAssumptions:
    return CostAssumptions(
        **store.get_cost_assumptions(),
        currency=store.setting("currency"),
        currency_symbol=store.setting("currency_symbol"),
    )


def milestone_defs() -> List[MilestoneDefinition]:
    return [MilestoneDefinition(**m) for m in store.milestone_defs()]


def complete_statuses() -> List[str]:
    """Milestone statuses that count towards completion %."""
    return [o["value"] for o in store.lookups().get("milestone_status", []) if o.get("counts_complete")]


def completed_project_statuses() -> List[str]:
    """Project statuses that mean the project is completed (README §9.1 variance rule)."""
    return [o["value"] for o in store.lookups().get("project_status", []) if o.get("is_complete")]


def hydrate(raw: dict) -> Project:
    """Project with every calculated field derived from current rules and rates."""
    return recalc_project(
        Project(**raw),
        rates=rates(),
        defs=milestone_defs(),
        complete_statuses=complete_statuses(),
        completed_project_statuses=completed_project_statuses(),
        completion_strategy=settings.completion_strategy,
    )


def get_hydrated(project_id: str) -> Project:
    raw = store.get_project(project_id)
    if not raw:
        raise HTTPException(404, "Project not found")
    return hydrate(raw)


def require_project(project_id: str) -> None:
    if not store.project_exists(project_id):
        raise HTTPException(404, "Project not found")


# ---------------------------------------------------------------------------
# Defaults (the option flagged is_default in each lookup, else the first)
# ---------------------------------------------------------------------------
def lookup_default(kind: str) -> Optional[str]:
    options = store.lookups().get(kind, [])
    chosen = next((o for o in options if o.get("is_default")), options[0] if options else None)
    return chosen["value"] if chosen else None


def with_project_defaults(data: dict) -> dict:
    """Fills unset status/RAG values and makes sure every lifecycle milestone exists."""
    data = {**data}
    ident = data["identity"] = {**data.get("identity", {})}
    ident["status"] = ident.get("status") or lookup_default("project_status")
    rag = data["rag"] = {**(data.get("rag") or {})}
    for k in ("schedule", "budget", "issues"):
        rag[k] = rag.get(k) or lookup_default("rag")
    ms_default = lookup_default("milestone_status")
    given = {m["key"]: m for m in data.get("milestones") or []}
    data["milestones"] = [
        {**given.get(d.key, {}), "key": d.key, "status": given.get(d.key, {}).get("status") or ms_default}
        for d in milestone_defs()
    ]
    data["issues"] = [with_issue_defaults(i) for i in data.get("issues") or []]
    data["risks"] = [with_risk_defaults(r) for r in data.get("risks") or []]
    return data


def with_issue_defaults(issue: dict) -> dict:
    return {**issue, "priority": issue.get("priority") or lookup_default("issue_priority")}


def with_risk_defaults(risk: dict) -> dict:
    return {
        **risk,
        "priority": risk.get("priority") or lookup_default("issue_priority"),
        "probability": risk.get("probability") or int(lookup_default("probability") or 0) or None,
        "impact": risk.get("impact") or int(lookup_default("impact") or 0) or None,
        "status": risk.get("status") or lookup_default("risk_status"),
    }


# ---------------------------------------------------------------------------
# Validation against reference data
# ---------------------------------------------------------------------------
def _check(value, allowed, field: str, errors: List[str]) -> None:
    if value is not None and value not in allowed:
        errors.append(f"{field}: '{value}' is not one of {sorted(allowed)}")


def check_date(value: Optional[str], field: str, errors: List[str], allow_placeholder: bool = False) -> None:
    if value in (None, ""):
        return
    if allow_placeholder and value in store.lookup_values("date_placeholder"):
        return
    if not ISO_DATE.match(str(value)):
        errors.append(f"{field}: '{value}' is not a YYYY-MM-DD date")


def raise_if(errors: List[str]) -> None:
    if errors:
        raise HTTPException(422, "; ".join(errors))


def validate_project_patch(patch: dict) -> List[str]:
    errors: List[str] = []
    ident = patch.get("identity") or {}
    if "name" in ident and not str(ident["name"]).strip():
        errors.append("identity.name is required")
    if "entity_id" in ident:
        _check(ident["entity_id"], {e["id"] for e in store.entities()}, "identity.entity_id", errors)
    if "division_id" in ident:
        _check(ident["division_id"], {d["id"] for d in store.divisions()}, "identity.division_id", errors)
    if "status" in ident:
        _check(ident["status"], set(store.lookup_values("project_status")), "identity.status", errors)
    rag_values = set(store.lookup_values("rag"))
    for k, v in (patch.get("rag") or {}).items():
        if not k.endswith("_comment"):
            _check(v, rag_values, f"rag.{k}", errors)
    for k, v in (patch.get("schedule") or {}).items():
        if k != "variance_days":
            check_date(v, f"schedule.{k}", errors)
    for k, v in (patch.get("resources") or {}).items():
        if isinstance(v, (int, float)) and v < 0:
            errors.append(f"resources.{k} cannot be negative")
    return errors


def validate_milestone_fields(fields: dict) -> List[str]:
    errors: List[str] = []
    if "status" in fields:
        _check(fields["status"], set(store.lookup_values("milestone_status")), "status", errors)
    for k in ("baseline_date", "expected_date", "actual_date"):
        if k in fields:
            check_date(fields[k], k, errors, allow_placeholder=True)
    return errors


def validate_issue(issue: Issue) -> None:
    errors: List[str] = []
    _check(issue.priority, set(store.lookup_values("issue_priority")), "priority", errors)
    areas = set(store.lookup_values("issue_impact_area"))
    for a in issue.impact_areas:
        _check(a, areas, "impact_areas", errors)
    if issue.milestone_key:
        _check(issue.milestone_key, {d.key for d in milestone_defs()}, "milestone_key", errors)
    raise_if(errors)


def validate_risk(risk: Risk) -> None:
    errors: List[str] = []
    _check(risk.priority, set(store.lookup_values("issue_priority")), "priority", errors)
    _check(str(risk.probability), set(store.lookup_values("probability")), "probability", errors)
    _check(str(risk.impact), set(store.lookup_values("impact")), "impact", errors)
    _check(risk.status, set(store.lookup_values("risk_status")), "status", errors)
    raise_if(errors)
