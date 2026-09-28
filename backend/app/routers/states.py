"""
Saved project states (README §39–§40). Each save is an immutable snapshot of
the hydrated project, so later rate or rule changes don't rewrite history.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request

from app.services.store import store
from app.services import auth, domain
from app.models.report import SaveStateRequest, ProjectStateSummary, ProjectState

router = APIRouter(tags=["states"])


@router.post("/projects/{project_id}/states", response_model=ProjectStateSummary, status_code=201, dependencies=[Depends(auth.require_project_edit)])
def save_state(project_id: str, payload: SaveStateRequest, request: Request) -> ProjectStateSummary:
    project = domain.get_hydrated(project_id)
    return ProjectStateSummary(**store.save_state(
        project_id, payload.label.strip(), domain.actor(request), project.model_dump(),
    ))


@router.get("/projects/{project_id}/states", response_model=List[ProjectStateSummary])
def list_states(project_id: str) -> List[ProjectStateSummary]:
    domain.require_project(project_id)
    return [ProjectStateSummary(**s) for s in store.list_states(project_id)]


@router.get("/projects/{project_id}/changes")
def list_changes(project_id: str):
    """Full change history: field edits, issues, risks, documents, saved states,
    milestone changes and cost-rate changes, newest first."""
    domain.require_project(project_id)
    return store.change_log(project_id)


@router.get("/projects/{project_id}/states/{state_id}", response_model=ProjectState)
def get_state(project_id: str, state_id: str) -> ProjectState:
    state = store.get_state(state_id)
    if not state or state["project_id"] != project_id:
        raise HTTPException(404, "Saved state not found")
    return ProjectState(**state)
