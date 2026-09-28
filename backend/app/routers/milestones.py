from fastapi import APIRouter, Depends, HTTPException, Request

from app.services.store import store
from app.services import auth, domain

router = APIRouter(tags=["milestones"])


@router.patch("/projects/{project_id}/milestones/{key}", dependencies=[Depends(auth.require_project_edit)])
def update_milestone(project_id: str, key: str, payload: dict, request: Request):
    """Updates a milestone and records a history entry when anything changed (README §13).
    `note` is the milestone note; `change_note` optionally explains the change."""
    domain.require_project(project_id)
    fields = {k: payload[k] for k in ("status", "baseline_date", "expected_date", "actual_date", "note")
              if k in payload}
    fields = {k: (v or None) if k.endswith("_date") else v for k, v in fields.items()}
    domain.raise_if(domain.validate_milestone_fields(fields))

    result = store.update_milestone(
        project_id, key, fields,
        actor=domain.actor(request),
        note=payload.get("change_note") or "",
    )
    if result is None:
        raise HTTPException(404, "Milestone not found")
    return {"ok": True, "milestone": result}
