"""
Admin area (README §17, §43–§44): users, reference data and settings.
Each section is guarded by its own permission.
"""
import re
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.services import auth
from app.services.store import store, EDITABLE_SETTINGS

router = APIRouter(tags=["admin"])

TONES = ("positive", "warning", "danger", "info", "neutral", "muted")   # CSS badge styles
LOOKUP_FLAGS = ("is_default", "counts_complete", "is_complete", "is_not_started", "is_delayed", "needs_attention")
LOOKUP_TEXT_EXTRAS = ("range", "description")
NUMERIC_KINDS = ("probability", "impact")


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
class NewUser(BaseModel):
    email: str
    name: str
    role: str


class UserUpdate(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    active: Optional[bool] = None


def _check_role(role: str) -> None:
    if role not in {r["key"] for r in store.roles()}:
        raise HTTPException(422, f"Unknown role '{role}'")


def _guard_last_admin(user_id: str, new_role: Optional[str], new_active: Optional[bool]) -> None:
    """Never leave ReportX without an active user who can manage users."""
    target = store.get_user(user_id)
    perms_now = auth.permissions_of(target)
    if "users" not in perms_now or not target["active"]:
        return
    loses_admin = (new_active is False) or (
        new_role is not None and "users" not in auth.permissions_of({**target, "role": new_role}))
    if loses_admin and store.count_active_with_permission("users") <= 1:
        raise HTTPException(409, "This is the last active Admin — add another Admin first")


@router.get("/admin/users")
def list_users(_: dict = Depends(auth.require("users"))):
    return {"users": store.list_users(), "roles": store.roles()}


@router.post("/admin/users", status_code=201)
def create_user(payload: NewUser, _: dict = Depends(auth.require("users"))):
    if "@" not in payload.email or not payload.name.strip():
        raise HTTPException(422, "Enter a name and a valid email")
    _check_role(payload.role)
    if store.get_user_by_email(payload.email):
        raise HTTPException(409, "A user with that email already exists")
    temp = auth.temporary_password()
    user = store.create_user(payload.email, payload.name, payload.role, auth.hash_password(temp), must_change=True)
    return {"user": user, "temporary_password": temp}


@router.put("/admin/users/{user_id}")
def update_user(user_id: str, payload: UserUpdate, me: dict = Depends(auth.require("users"))):
    if not store.get_user(user_id):
        raise HTTPException(404, "User not found")
    fields = payload.model_dump(exclude_none=True)
    if "role" in fields:
        _check_role(fields["role"])
    if "email" in fields:
        other = store.get_user_by_email(fields["email"])
        if "@" not in fields["email"] or (other and other["id"] != user_id):
            raise HTTPException(422, "Email is invalid or already used")
    if fields.get("active") is False and user_id == me["id"]:
        raise HTTPException(409, "You can't deactivate your own account")
    _guard_last_admin(user_id, fields.get("role"), fields.get("active"))
    store.update_user(user_id, fields)
    return store.get_user(user_id)


@router.post("/admin/users/{user_id}/reset-password")
def reset_password(user_id: str, _: dict = Depends(auth.require("users"))):
    if not store.get_user(user_id):
        raise HTTPException(404, "User not found")
    temp = auth.temporary_password()
    store.update_user(user_id, {"password_hash": auth.hash_password(temp), "must_change_password": True})
    return {"temporary_password": temp}


@router.get("/users/directory")
def directory(_: dict = Depends(auth.current_user)):
    """Active users (id, name, role) — used to pick a project manager."""
    return [{"id": u["id"], "name": u["name"], "role": u["role"]} for u in store.list_users() if u["active"]]


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------
class RefItem(BaseModel):
    code: str
    name: str


class MilestoneLabels(BaseModel):
    label: str
    short_label: str


class LookupItem(BaseModel):
    value: Optional[str] = None           # required when adding; values are keys and can't be renamed
    label: str
    tone: str = "neutral"
    flags: Dict[str, bool] = Field(default_factory=dict)
    range: Optional[str] = None
    description: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)   # other spellings matched during Excel import


class ImportFieldUpdate(BaseModel):
    label: str
    aliases: List[str] = Field(default_factory=list)


@router.get("/admin/reference")
def reference(_: dict = Depends(auth.require("reference_data"))):
    lookups = {
        kind: [{**o, "in_use": store.lookup_usage(kind, o["value"])} for o in options]
        for kind, options in store.lookups().items()
    }
    return {
        "entities": [{**e, "in_use": store.ref_usage("entities", e["id"])} for e in store.entities()],
        "divisions": [{**d, "in_use": store.ref_usage("divisions", d["id"])} for d in store.divisions()],
        "milestone_definitions": store.milestone_defs(),
        "lookups": lookups,
        "import_fields": store.import_fields(),
        "tones": TONES,
        "flags": LOOKUP_FLAGS,
    }


def _ref_table(kind: str) -> str:
    if kind not in ("entities", "divisions"):
        raise HTTPException(404, "Unknown list")
    return kind


@router.post("/admin/reference/{kind}", status_code=201)
def add_ref(kind: str, item: RefItem, _: dict = Depends(auth.require("reference_data"))):
    table = _ref_table(kind)
    code = item.code.strip().upper()
    if not re.fullmatch(r"[A-Z0-9_-]{1,20}", code) or not item.name.strip():
        raise HTTPException(422, "Code must be 1–20 letters/digits; name is required")
    existing = store.entities() if table == "entities" else store.divisions()
    if any(r["code"] == code for r in existing):
        raise HTTPException(409, f"Code {code} already exists")
    ref_id = f"{'ent' if table == 'entities' else 'div'}_{code.lower()}"
    store.upsert_ref(table, ref_id, code, item.name.strip())
    return {"id": ref_id, "code": code, "name": item.name.strip()}


@router.put("/admin/reference/{kind}/{ref_id}")
def edit_ref(kind: str, ref_id: str, item: RefItem, _: dict = Depends(auth.require("reference_data"))):
    table = _ref_table(kind)
    existing = store.entities() if table == "entities" else store.divisions()
    if not any(r["id"] == ref_id for r in existing):
        raise HTTPException(404, "Not found")
    code = item.code.strip().upper()
    if any(r["code"] == code and r["id"] != ref_id for r in existing):
        raise HTTPException(409, f"Code {code} already exists")
    store.upsert_ref(table, ref_id, code, item.name.strip())
    return {"id": ref_id, "code": code, "name": item.name.strip()}


@router.delete("/admin/reference/{kind}/{ref_id}")
def delete_ref(kind: str, ref_id: str, _: dict = Depends(auth.require("reference_data"))):
    table = _ref_table(kind)
    used = store.ref_usage(table, ref_id)
    if used:
        raise HTTPException(409, f"In use by {used} project(s) — it can't be deleted")
    if not store.delete_ref(table, ref_id):
        raise HTTPException(404, "Not found")
    return {"ok": True}


@router.put("/admin/milestones/{key}")
def edit_milestone(key: str, item: MilestoneLabels, _: dict = Depends(auth.require("reference_data"))):
    # README §10/§52: exactly nine lifecycle milestones — labels are editable, the set is not.
    if not item.label.strip() or not item.short_label.strip():
        raise HTTPException(422, "Both labels are required")
    if not store.update_milestone_def(key, item.label.strip(), item.short_label.strip()):
        raise HTTPException(404, "Milestone not found")
    return {"ok": True}


def _lookup_extra(kind: str, item: LookupItem, value: str) -> dict:
    if item.tone not in TONES:
        raise HTTPException(422, f"Tone must be one of {TONES}")
    # Start from what's stored so details this form doesn't show (report colours,
    # codes, legend text) survive an edit; then apply what the form sent.
    existing = next((o for o in store.lookups().get(kind, []) if o["value"] == value), {})
    extra = {k: v for k, v in existing.items()
             if k not in ("value", "label", "tone", "in_use", "aliases") and k not in LOOKUP_FLAGS}
    extra.update({k: True for k, v in item.flags.items() if v and k in LOOKUP_FLAGS})
    for k in LOOKUP_TEXT_EXTRAS:
        v = getattr(item, k)
        if v is not None:            # None = not on the form; "" = cleared
            if v.strip():
                extra[k] = v.strip()
            else:
                extra.pop(k, None)
    aliases = [a.strip() for a in item.aliases if a.strip()]
    if aliases:
        extra["aliases"] = aliases
    return extra


@router.post("/admin/lookups/{kind}", status_code=201)
def add_lookup(kind: str, item: LookupItem, _: dict = Depends(auth.require("reference_data"))):
    if kind not in store.lookups():
        raise HTTPException(404, "Unknown list")
    value = (item.value or "").strip()
    if not value or not item.label.strip():
        raise HTTPException(422, "Value and label are required")
    if kind in NUMERIC_KINDS and not value.isdigit():
        raise HTTPException(422, "Probability and impact levels must be whole numbers")
    if value in store.lookup_values(kind):
        raise HTTPException(409, f"'{value}' already exists")
    store.upsert_lookup(kind, value, item.label.strip(), item.tone, _lookup_extra(kind, item, value))
    return {"ok": True}


@router.put("/admin/lookups/{kind}/{value}")
def edit_lookup(kind: str, value: str, item: LookupItem, _: dict = Depends(auth.require("reference_data"))):
    if value not in store.lookup_values(kind):
        raise HTTPException(404, "Not found")
    if not item.label.strip():
        raise HTTPException(422, "Label is required")
    store.upsert_lookup(kind, value, item.label.strip(), item.tone, _lookup_extra(kind, item, value))
    return {"ok": True}


@router.delete("/admin/lookups/{kind}/{value}")
def delete_lookup(kind: str, value: str, _: dict = Depends(auth.require("reference_data"))):
    if value not in store.lookup_values(kind):
        raise HTTPException(404, "Not found")
    used = store.lookup_usage(kind, value)
    if used:
        raise HTTPException(409, f"In use by {used} record(s) — it can't be deleted")
    if len(store.lookup_values(kind)) <= 1:
        raise HTTPException(409, "A list needs at least one option")
    store.delete_lookup(kind, value)
    return {"ok": True}


@router.put("/admin/import-fields/{key}")
def edit_import_field(key: str, item: ImportFieldUpdate, _: dict = Depends(auth.require("reference_data"))):
    aliases = [a.strip() for a in item.aliases if a.strip()]
    if not item.label.strip():
        raise HTTPException(422, "Label is required")
    if not store.update_import_field(key, item.label.strip(), aliases):
        raise HTTPException(404, "Import field not found")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
@router.get("/admin/settings")
def get_settings(_: dict = Depends(auth.require("settings"))):
    return store.all_settings()


@router.put("/admin/settings")
def put_settings(values: dict, _: dict = Depends(auth.require("settings"))):
    clean, errors = {}, []
    for k, v in values.items():
        if k not in EDITABLE_SETTINGS:
            errors.append(f"'{k}' is not an editable setting")
            continue
        try:
            v = EDITABLE_SETTINGS[k](v)
        except (TypeError, ValueError):
            errors.append(f"{k} must be a {EDITABLE_SETTINGS[k].__name__}")
            continue
        if isinstance(v, str):
            v = v.strip()
            if not v:
                errors.append(f"{k} can't be empty")
                continue
        clean[k] = v
    if "project_id_prefix" in clean and not re.fullmatch(r"[A-Za-z]{1,10}", clean["project_id_prefix"]):
        errors.append("Project ID prefix must be 1–10 letters")
    if "project_id_width" in clean and not 3 <= clean["project_id_width"] <= 8:
        errors.append("Project ID width must be between 3 and 8")
    if "upload_max_mb" in clean and not 1 <= clean["upload_max_mb"] <= 200:
        errors.append("Maximum upload size must be between 1 and 200 MB")
    if "upload_extensions" in clean:
        exts = [e.strip().lower() for e in clean["upload_extensions"].split(",") if e.strip()]
        if not exts or any(not re.fullmatch(r"\.[a-z0-9]{1,8}", e) for e in exts):
            errors.append("File types must look like .pdf,.docx")
        clean["upload_extensions"] = ",".join(exts)
    if errors:
        raise HTTPException(422, "; ".join(errors))
    store.update_settings(clean)
    return store.all_settings()
