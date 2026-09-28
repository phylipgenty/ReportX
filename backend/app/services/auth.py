"""
Authentication and authorisation (README §17, §43–§44).

- Passwords: salted scrypt (stdlib), never stored or logged in clear.
- Sessions: random token in an HttpOnly cookie; only its SHA-256 is stored.
- Permissions: each user has one role; roles map to permission keys
  (seed/roles.json -> roles table). Every API route checks on the server.
- CSRF: state-changing requests must carry the X-ReportX header, which a
  cross-site form cannot set.
"""
from __future__ import annotations
import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Deque, Dict, Optional, Set

from fastapi import Depends, HTTPException, Request, Response

from app.config import settings
from app.services.store import store

SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1, "dklen": 32}
CSRF_HEADER = "X-ReportX"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
# Endpoints a user who must change their password may still call.
PASSWORD_CHANGE_ALLOWED = ("/auth/me", "/auth/logout", "/auth/change-password", "/bootstrap")


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, digest = stored.split("$")
        calc = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), **SCRYPT)
        return hmac.compare_digest(calc.hex(), digest)
    except (ValueError, TypeError):
        return False


def password_problem(password: str) -> Optional[str]:
    if len(password or "") < settings.min_password_length:
        return f"Password must be at least {settings.min_password_length} characters"
    return None


def temporary_password() -> str:
    return secrets.token_urlsafe(9)


# ---------------------------------------------------------------------------
# Login throttling (per email, in memory)
# ---------------------------------------------------------------------------
_failures: Dict[str, Deque[float]] = defaultdict(deque)


def _recent_failures(email: str) -> Deque[float]:
    q = _failures[email.lower()]
    cutoff = time.time() - settings.login_lockout_minutes * 60
    while q and q[0] < cutoff:
        q.popleft()
    return q


def check_not_locked(email: str) -> None:
    if len(_recent_failures(email)) >= settings.login_max_attempts:
        raise HTTPException(429, f"Too many failed sign-in attempts. Try again in {settings.login_lockout_minutes} minutes.")


def record_failure(email: str) -> None:
    _recent_failures(email).append(time.time())


def clear_failures(email: str) -> None:
    _failures.pop(email.lower(), None)


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------
def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def start_session(response: Response, user_id: str) -> None:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.session_hours)
    store.create_session(_hash_token(token), user_id, expires.isoformat())
    response.set_cookie(
        settings.session_cookie_name, token,
        max_age=settings.session_hours * 3600, httponly=True, samesite="lax",
        secure=settings.session_cookie_secure, path="/",
    )


def end_session(request: Request, response: Response) -> None:
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        store.delete_session(_hash_token(token))
    response.delete_cookie(settings.session_cookie_name, path="/")


def session_user(request: Request) -> Optional[dict]:
    token = request.cookies.get(settings.session_cookie_name)
    return store.user_for_session(_hash_token(token)) if token else None


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------
def permissions_of(user: dict) -> Set[str]:
    role = next((r for r in store.roles() if r["key"] == user["role"]), None)
    return set(role["permissions"]) if role else set()


def public_user(user: dict) -> dict:
    role = next((r for r in store.roles() if r["key"] == user["role"]), {})
    return {
        "id": user["id"], "email": user["email"], "name": user["name"],
        "role": user["role"], "role_label": role.get("label", user["role"]),
        "permissions": sorted(permissions_of(user)),
        "must_change_password": user["must_change_password"],
    }


def can_edit_project(user: dict, project_id: str) -> bool:
    perms = permissions_of(user)
    if "project.edit_all" in perms:
        return True
    return "project.edit_own" in perms and store.project_manager_id(project_id) == user["id"]


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------
def current_user(request: Request) -> dict:
    user = session_user(request)
    if not user:
        raise HTTPException(401, "Please sign in")
    if request.method not in SAFE_METHODS and request.headers.get(CSRF_HEADER) != "1":
        raise HTTPException(403, "Request rejected (missing ReportX header)")
    path = request.url.path[len(settings.api_prefix):]
    if user["must_change_password"] and not path.startswith(PASSWORD_CHANGE_ALLOWED):
        raise HTTPException(403, "Please change your password before continuing")
    request.state.user = user
    return user


def require(*perms: str):
    """Dependency: the user must hold at least one of `perms`."""
    def dependency(user: dict = Depends(current_user)) -> dict:
        if not permissions_of(user) & set(perms):
            raise HTTPException(403, "You don't have permission to do that")
        return user
    return dependency


def require_project_edit(project_id: str, user: dict = Depends(current_user)) -> dict:
    """Dependency for /projects/{project_id}/... writes: PMO/Admin, or the project's own manager."""
    if not store.project_exists(project_id):
        raise HTTPException(404, "Project not found")
    if not can_edit_project(user, project_id):
        raise HTTPException(403, "Only this project's manager, PMO or Admin can change it")
    return user
