"""
Sign-in endpoints. `status`, `setup` and `login` are public; the rest need a session.
The first visit to a fresh install creates the Admin account (no default password).
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from app.services import auth
from app.services.store import store

router = APIRouter(prefix="/auth", tags=["auth"])


class Credentials(BaseModel):
    email: str
    password: str


class SetupRequest(BaseModel):
    email: str
    name: str
    password: str


class ChangePassword(BaseModel):
    current_password: str
    new_password: str


def _admin_role() -> str:
    return next(r["key"] for r in store.roles() if {"users", "settings", "reference_data"} <= set(r["permissions"]))


@router.get("/status")
def status(request: Request):
    user = auth.session_user(request)
    return {
        "setup_required": store.user_count() == 0,
        "user": auth.public_user(user) if user else None,
        "app_name": store.setting("app_name"),
        "organisation": store.setting("organisation_name"),
    }


@router.post("/setup")
def setup(payload: SetupRequest, request: Request, response: Response):
    if store.user_count() > 0:
        raise HTTPException(409, "ReportX is already set up")
    if request.headers.get(auth.CSRF_HEADER) != "1":
        raise HTTPException(403, "Request rejected (missing ReportX header)")
    problems = [p for p in (
        "Enter a valid email" if "@" not in payload.email else None,
        "Enter your name" if not payload.name.strip() else None,
        auth.password_problem(payload.password),
    ) if p]
    if problems:
        raise HTTPException(422, "; ".join(problems))
    user = store.create_user(payload.email, payload.name, _admin_role(), auth.hash_password(payload.password), False)
    auth.start_session(response, user["id"])
    return {"user": auth.public_user(user)}


@router.post("/login")
def login(payload: Credentials, request: Request, response: Response):
    if request.headers.get(auth.CSRF_HEADER) != "1":
        raise HTTPException(403, "Request rejected (missing ReportX header)")
    auth.check_not_locked(payload.email)
    user = store.get_user_by_email(payload.email, with_hash=True)
    if not user or not user["active"] or not auth.verify_password(payload.password, user["password_hash"]):
        auth.record_failure(payload.email)
        raise HTTPException(401, "Email or password is incorrect")
    auth.clear_failures(payload.email)
    auth.start_session(response, user["id"])
    return {"user": auth.public_user(store.get_user(user["id"]))}


@router.post("/logout")
def logout(request: Request, response: Response):
    auth.end_session(request, response)
    return {"ok": True}


@router.get("/me")
def me(user: dict = Depends(auth.current_user)):
    return auth.public_user(user)


@router.post("/change-password")
def change_password(payload: ChangePassword, request: Request, response: Response,
                    user: dict = Depends(auth.current_user)):
    full = store.get_user(user["id"], with_hash=True)
    if not auth.verify_password(payload.current_password, full["password_hash"]):
        raise HTTPException(422, "Current password is incorrect")
    problem = auth.password_problem(payload.new_password)
    if problem:
        raise HTTPException(422, problem)
    if payload.new_password == payload.current_password:
        raise HTTPException(422, "Choose a different password")
    store.update_user(user["id"], {"password_hash": auth.hash_password(payload.new_password), "must_change_password": False})
    auth.start_session(response, user["id"])   # old sessions were revoked with the password change
    return {"user": auth.public_user(store.get_user(user["id"]))}
