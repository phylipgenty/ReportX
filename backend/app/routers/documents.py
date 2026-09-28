"""
Optional project attachments (README §25–§27). Files are stored on disk under
settings.upload_dir; metadata lives in the documents table. Replacing keeps
the previous version on record; deleting is a soft delete.
"""
import mimetypes
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse

from app.config import settings
from app.services.store import store
from app.services import auth, domain
from app.services.history import now_iso
from app.models.document import ProjectDocument

router = APIRouter(tags=["documents"])


def _allowed_extensions() -> set:
    return {e.strip().lower() for e in store.setting("upload_extensions").split(",") if e.strip()}


@router.post("/projects/{project_id}/documents", response_model=ProjectDocument, status_code=201, dependencies=[Depends(auth.require_project_edit)])
async def upload_document(
    project_id: str,
    request: Request,
    file: UploadFile = File(...),
    milestone_key: Optional[str] = Form(default=None),
    replaces: Optional[str] = Form(default=None),
) -> ProjectDocument:
    domain.require_project(project_id)

    # Strip any client-supplied directory parts so the file stays in upload_dir.
    filename = Path(file.filename or "upload").name.replace("\\", "_") or "upload"
    ext = Path(filename).suffix.lower()
    if ext not in _allowed_extensions():
        raise HTTPException(422, f"File type '{ext or 'none'}' is not accepted. Allowed: {sorted(_allowed_extensions())}")

    if milestone_key and milestone_key not in {d.key for d in domain.milestone_defs()}:
        raise HTTPException(422, f"Unknown milestone '{milestone_key}'")

    if replaces:
        old = store.get_document(replaces)
        if not old or old["project_id"] != project_id:
            raise HTTPException(404, "Document to replace not found")
        milestone_key = milestone_key or old["milestone_key"]

    content = await file.read()
    if len(content) > int(store.setting("upload_max_mb")) * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {int(store.setting('upload_max_mb'))} MB")

    doc_id = f"DOC-{uuid4().hex[:8]}"
    stored_name = f"{doc_id}{ext}"
    (settings.upload_dir / stored_name).write_bytes(content)

    return ProjectDocument(**store.add_document(project_id, {
        "id": doc_id,
        "milestone_key": milestone_key or None,
        "filename": filename,
        "stored_name": stored_name,
        "mime_type": file.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream",
        "size_bytes": len(content),
        "uploaded_at": now_iso(),
        "uploaded_by": domain.actor(request),
        "replaces": replaces or None,
    }))


@router.get("/documents/{doc_id}/raw")
def raw_document(doc_id: str, download: bool = False):
    doc = store.get_document(doc_id)
    path = settings.upload_dir / doc["stored_name"] if doc else None
    if not path or not path.exists():
        raise HTTPException(404, "Document not found")
    # inline so PDFs open in the in-app viewer (README §26)
    return FileResponse(
        path, media_type=doc["mime_type"], filename=doc["filename"],
        content_disposition_type="attachment" if download else "inline",
    )


@router.delete("/projects/{project_id}/documents/{doc_id}", dependencies=[Depends(auth.require_project_edit)])
def delete_document(project_id: str, doc_id: str, request: Request):
    domain.require_project(project_id)
    if not store.delete_document(project_id, doc_id, actor=domain.actor(request)):
        raise HTTPException(404, "Document not found")
    return {"ok": True}
