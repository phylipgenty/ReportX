"""
ReportX FastAPI app.

Serves:
    /               -> frontend SPA
    /css/* /js/*    -> static assets
    /api/*          -> JSON API
"""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.services.store import store
from app.services.auth import current_user
from app.routers import (
    projects, milestones, costs, issues, risks, documents, reports, imports, states, portfolio, auth, admin,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    store.init()
    yield


app = FastAPI(title="ReportX", lifespan=lifespan)

api = settings.api_prefix
app.include_router(auth.router, prefix=api)     # sign-in endpoints manage their own access
for r in (projects, portfolio, milestones, costs, issues, risks, documents, states, reports, imports, admin):
    # Every other API route needs a signed-in user; routes add finer permission checks.
    app.include_router(r.router, prefix=api, dependencies=[Depends(current_user)])


# Static frontend
_frontend = settings.frontend_dir
app.mount("/css",    StaticFiles(directory=_frontend / "css"),    name="css")
app.mount("/js",     StaticFiles(directory=_frontend / "js"),     name="js")
app.mount("/assets", StaticFiles(directory=_frontend / "assets"), name="assets")


@app.get("/")
def root() -> FileResponse:
    return FileResponse(_frontend / "index.html")


@app.get("/{full_path:path}")
def spa_fallback(full_path: str) -> FileResponse:
    # Unknown API paths are real 404s, not the SPA shell.
    if full_path.startswith(api.strip("/") + "/"):
        raise HTTPException(404, "Not found")
    return FileResponse(_frontend / "index.html")
