"""
Bootstrap (reference data for the frontend) and project CRUD.
"""
from __future__ import annotations
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request

from app.services.store import store
from app.services import auth, domain, importer
from app.models.project import Project, Entity, Division
from app.models.report import BootstrapPayload, AppInfo, ImportField, LookupOption, LastImport

router = APIRouter(tags=["projects"])


@router.get("/bootstrap", response_model=BootstrapPayload)
def get_bootstrap() -> BootstrapPayload:
    last = store.meta_get("last_import")
    return BootstrapPayload(
        app=AppInfo(
            name=store.setting("app_name"),
            organisation=store.setting("organisation_name"),
            currency=store.setting("currency"),
            currency_symbol=store.setting("currency_symbol"),
        ),
        entities=[Entity(**e) for e in store.entities()],
        divisions=[Division(**d) for d in store.divisions()],
        milestone_definitions=domain.milestone_defs(),
        lookups={k: [LookupOption(**o) for o in v] for k, v in store.lookups().items()},
        cost_assumptions=domain.rates(),
        import_fields=[ImportField(**f) for f in importer.import_targets()],
        last_import=LastImport(**last) if last else None,
    )


@router.get("/projects", response_model=List[Project])
def list_projects() -> List[Project]:
    return [domain.hydrate(p) for p in store.list_projects()]


@router.get("/projects/{project_id}", response_model=Project)
def get_project(project_id: str) -> Project:
    return domain.get_hydrated(project_id)


def _apply_manager(data: dict, user: dict, current_manager: str = None) -> None:
    """Links the project to a user account (edit rights, README §44).
    current_manager is None when creating. Project Managers (edit_own) always
    manage what they create and can't hand a project to someone else."""
    ident = data.setdefault("identity", {})
    can_assign = "project.edit_all" in auth.permissions_of(user)
    creating = current_manager is None
    wanted = ident.get("manager_user_id") or None
    if not can_assign:
        allowed = user["id"] if creating else (current_manager or None)
        # Creating: an unset manager defaults to the creator. Updating: must stay unchanged.
        if wanted != allowed and (wanted or not creating):
            raise HTTPException(403, "Only PMO or Admin can change a project's manager")
        wanted = allowed
    ident["manager_user_id"] = wanted
    if wanted:
        manager = store.get_user(wanted)
        if not manager or not manager["active"]:
            raise HTTPException(422, "Project manager must be an active user")
        ident["project_manager"] = manager["name"]


@router.post("/projects", response_model=Project, status_code=201)
def create_project(payload: Project, user: dict = Depends(auth.require("project.create"))) -> Project:
    """Project ID and timestamps are always system-generated (README §4.2)."""
    data = payload.model_dump()
    _apply_manager(data, user)
    data = domain.with_project_defaults(data)
    errors = domain.validate_project_patch(data)
    for m in data["milestones"]:
        errors += [f"milestones.{m['key']}.{e}" for e in domain.validate_milestone_fields(m)]
    domain.raise_if(errors)
    return domain.get_hydrated(store.create_project(data, actor=user["name"]))


@router.patch("/projects/{project_id}", response_model=Project)
def update_project(project_id: str, payload: dict, user: dict = Depends(auth.require_project_edit)) -> Project:
    """Identity, schedule, resources, RAG, planned activities, executive summary
    and draft flag. Milestones/issues/risks/documents use their own endpoints."""
    if "manager_user_id" in (payload.get("identity") or {}):
        _apply_manager(payload, user, current_manager=store.project_manager_id(project_id) or "")
    domain.raise_if(domain.validate_project_patch(payload))
    store.update_project(project_id, payload, actor=user["name"])
    return domain.get_hydrated(project_id)
