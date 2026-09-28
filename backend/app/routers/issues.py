from fastapi import APIRouter, Depends, HTTPException, Request

from app.services.store import store
from app.services import auth, domain
from app.models.issue import Issue

router = APIRouter(tags=["issues"])


def _get(project_id: str, issue_id: str) -> Issue:
    issue = next((i for i in domain.get_hydrated(project_id).issues if i.id == issue_id), None)
    if not issue:
        raise HTTPException(404, "Issue not found")
    return issue


@router.post("/projects/{project_id}/issues", response_model=Issue, status_code=201, dependencies=[Depends(auth.require_project_edit)])
def add_issue(project_id: str, payload: Issue, request: Request) -> Issue:
    domain.require_project(project_id)
    payload = Issue(**domain.with_issue_defaults(payload.model_dump()))
    domain.validate_issue(payload)
    return _get(project_id, store.add_issue(project_id, payload.model_dump(), actor=domain.actor(request)))


@router.put("/projects/{project_id}/issues/{issue_id}", response_model=Issue, dependencies=[Depends(auth.require_project_edit)])
def update_issue(project_id: str, issue_id: str, payload: Issue, request: Request) -> Issue:
    domain.require_project(project_id)
    payload = Issue(**domain.with_issue_defaults(payload.model_dump()))
    domain.validate_issue(payload)
    if not store.update_issue(project_id, issue_id, payload.model_dump(), actor=domain.actor(request)):
        raise HTTPException(404, "Issue not found")
    return _get(project_id, issue_id)


@router.delete("/projects/{project_id}/issues/{issue_id}", dependencies=[Depends(auth.require_project_edit)])
def delete_issue(project_id: str, issue_id: str, request: Request):
    domain.require_project(project_id)
    if not store.delete_child("issues", project_id, issue_id, actor=domain.actor(request)):
        raise HTTPException(404, "Issue not found")
    return {"ok": True}
