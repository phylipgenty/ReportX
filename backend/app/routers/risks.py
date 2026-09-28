from fastapi import APIRouter, Depends, HTTPException, Request

from app.services.store import store
from app.services import auth, domain
from app.models.risk import Risk

router = APIRouter(tags=["risks"])


def _get(project_id: str, risk_id: str) -> Risk:
    # Hydrated read so risk_score is always Probability × Impact (README §19.1).
    risk = next((r for r in domain.get_hydrated(project_id).risks if r.id == risk_id), None)
    if not risk:
        raise HTTPException(404, "Risk not found")
    return risk


@router.post("/projects/{project_id}/risks", response_model=Risk, status_code=201, dependencies=[Depends(auth.require_project_edit)])
def add_risk(project_id: str, payload: Risk, request: Request) -> Risk:
    domain.require_project(project_id)
    payload = Risk(**domain.with_risk_defaults(payload.model_dump()))
    domain.validate_risk(payload)
    return _get(project_id, store.add_risk(project_id, payload.model_dump(), actor=domain.actor(request)))


@router.put("/projects/{project_id}/risks/{risk_id}", response_model=Risk, dependencies=[Depends(auth.require_project_edit)])
def update_risk(project_id: str, risk_id: str, payload: Risk, request: Request) -> Risk:
    domain.require_project(project_id)
    payload = Risk(**domain.with_risk_defaults(payload.model_dump()))
    domain.validate_risk(payload)
    if not store.update_risk(project_id, risk_id, payload.model_dump(), actor=domain.actor(request)):
        raise HTTPException(404, "Risk not found")
    return _get(project_id, risk_id)


@router.delete("/projects/{project_id}/risks/{risk_id}", dependencies=[Depends(auth.require_project_edit)])
def delete_risk(project_id: str, risk_id: str, request: Request):
    domain.require_project(project_id)
    if not store.delete_child("risks", project_id, risk_id, actor=domain.actor(request)):
        raise HTTPException(404, "Risk not found")
    return {"ok": True}
