"""
Excel import endpoints. The browser keeps the file and re-sends it with the
chosen mapping for the review (dry run) and sync steps, so nothing half-
imported is ever held on the server.
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from app.services import auth, domain, importer

router = APIRouter(tags=["imports"], dependencies=[Depends(auth.require("import"))])


@router.post("/imports/preview")
async def preview(file: UploadFile = File(...)):
    sheets = importer.read_workbook(await file.read())
    return {
        "filename": file.filename,
        "sheets": [{
            "name": s["name"],
            "headers": s["headers"],
            "sample_rows": [[("" if r[h] is None else str(r[h])) for h in s["headers"]] for r in s["rows"][:5]],
            "row_count": len(s["rows"]),
            "header_row": s.get("header_row", 1),
            "suggested_mapping": importer.suggest_mapping(s["headers"]),
        } for s in sheets],
    }


async def _plan(file: UploadFile, sheet: Optional[str], mapping: str, on_existing: str):
    if on_existing not in ("update", "create_only"):
        raise HTTPException(422, "on_existing must be 'update' or 'create_only'")
    try:
        mapping_dict = json.loads(mapping)
    except ValueError:
        raise HTTPException(422, "mapping must be JSON")
    valid = {t["key"] for t in importer.import_targets()}
    bad = [v for v in mapping_dict.values() if v and v not in valid]
    if bad:
        raise HTTPException(422, f"Unknown import targets: {bad}")
    data = importer.pick_sheet(importer.read_workbook(await file.read()), sheet)
    return importer.plan(data, mapping_dict, on_existing)


@router.post("/imports/review")
async def review(file: UploadFile = File(...), mapping: str = Form(...),
                 sheet: Optional[str] = Form(default=None), on_existing: str = Form(default="update")):
    return {"rows": importer.public(await _plan(file, sheet, mapping, on_existing))}


@router.post("/imports/commit")
async def commit(request: Request, file: UploadFile = File(...), mapping: str = Form(...),
                 sheet: Optional[str] = Form(default=None), on_existing: str = Form(default="update")):
    plans = await _plan(file, sheet, mapping, on_existing)
    return importer.commit(plans, file.filename or "upload.xlsx", domain.actor(request))
