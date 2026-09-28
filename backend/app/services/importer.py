"""
Excel import (README §41–§42): Upload -> Map Columns -> Review Changes -> Sync.

Targets are the project-level fields in the import_fields table plus, for
every milestone definition, a date and a status target. A milestone date
column sets the milestone's expected date, and also its baseline date when
none is recorded yet.

Rows are matched on Project ID. Unknown or blank IDs create a new project
with a system-generated ID. Updates go through the same history-aware paths
as the UI: a saved state is taken before the change and milestone changes
are written to milestone history.
"""
from __future__ import annotations
import re
from datetime import date, datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from openpyxl import load_workbook
from openpyxl.utils.datetime import from_excel

from app.services import domain
from app.services.history import now_iso
from app.services.store import store

DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d-%b-%Y", "%d %B %Y", "%b %d, %Y",
                "%B %d, %Y", "%d %b, %Y", "%d %B, %Y", "%d.%m.%Y", "%d-%b-%y", "%d/%m/%y", "%Y/%m/%d")
ORDINAL = re.compile(r"(\d{1,2})(st|nd|rd|th)\b", re.I)
# "16 to 19 Dec 2025", "16-19 December 2025"
SAME_MONTH_RANGE = re.compile(r"^(\d{1,2})\s*(?:to|-|\u2013|\u2014)\s*(\d{1,2})\s+([A-Za-z]+)\.?,?\s+(\d{4})$", re.I)
RANGE_SPLIT = re.compile(r"\s+(?:to|-|\u2013|\u2014)\s+|\s*(?:\u2013|\u2014)\s*", re.I)
HEADER_SCAN_ROWS = 15
SCHEDULE_TARGETS = ("start_date", "original_baseline", "tsc_approved_date",
                    "planned_delivery", "forecast_delivery", "actual_delivery")


def _norm(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


# ---------------------------------------------------------------------------
# Targets + mapping
# ---------------------------------------------------------------------------
def import_targets() -> List[dict]:
    targets = list(store.import_fields())
    for d in domain.milestone_defs():
        names = list(dict.fromkeys([d.short_label, d.label]))
        targets.append({"key": f"ms.{d.key}.date", "label": f"{d.short_label} — date",
                        "aliases": names})
        targets.append({"key": f"ms.{d.key}.status", "label": f"{d.short_label} — status",
                        "aliases": [f"{n} Status" for n in names]})
    return targets


def suggest_mapping(headers: List[str]) -> Dict[str, str]:
    """Exact (case/space-insensitive) alias matches only — no fuzzy guessing."""
    alias_to_key = {}
    for t in import_targets():
        for a in [t["label"], *t["aliases"]]:
            alias_to_key.setdefault(_norm(a), t["key"])
    used: set = set()
    mapping = {}
    for h in headers:
        key = alias_to_key.get(_norm(h), "")
        if key in used:
            key = ""
        used.add(key)
        mapping[h] = key
    return mapping


# ---------------------------------------------------------------------------
# Workbook
# ---------------------------------------------------------------------------
def read_workbook(content: bytes) -> List[dict]:
    try:
        wb = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:
        raise HTTPException(400, f"Could not read workbook: {exc}")
    aliases = {_norm(a) for t in import_targets() for a in [t["label"], *t["aliases"]]}
    sheets = []
    for ws in wb.worksheets:
        rows = [r for r in ws.iter_rows(values_only=True)]
        if not rows:
            continue
        # Trackers often have a title or notes above the column headings: use the
        # row (within the first few) that matches the most known headings.
        scores = [sum(1 for c in r if c is not None and _norm(c) in aliases) for r in rows[:HEADER_SCAN_ROWS]]
        header_idx = max(range(len(scores)), key=lambda i: (scores[i], -i)) if max(scores, default=0) >= 2 else 0
        headers, seen = [], {}
        for i, h in enumerate(rows[header_idx]):
            name = str(h).strip() if h is not None and str(h).strip() else f"Column {i + 1}"
            seen[name] = seen.get(name, 0) + 1
            headers.append(name if seen[name] == 1 else f"{name} ({seen[name]})")
        data = []
        for r in rows[header_idx + 1:]:
            if all(c is None or str(c).strip() == "" for c in r):
                continue
            data.append({headers[i]: r[i] if i < len(r) else None for i in range(len(headers))})
        sheets.append({"name": ws.title, "headers": headers, "rows": data, "header_row": header_idx + 1})
    if not sheets:
        raise HTTPException(400, "The workbook has no data")
    return sheets


def pick_sheet(sheets: List[dict], name: Optional[str]) -> dict:
    if not name:
        return sheets[0]
    sheet = next((s for s in sheets if s["name"] == name), None)
    if not sheet:
        raise HTTPException(400, f"Sheet '{name}' not found")
    return sheet


# ---------------------------------------------------------------------------
# Value conversion
# ---------------------------------------------------------------------------
def _parse_one(s: str) -> Optional[str]:
    s = ORDINAL.sub(r"\1", s.strip().rstrip("."))
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _to_dates(v: Any, allow_placeholder: bool) -> tuple:
    """(start, end, warning). A single date gives start == end; a range such as
    '16 to 19 Dec 2025' gives both ends."""
    if v is None or str(v).strip() == "":
        return None, None, None
    if isinstance(v, datetime):
        return (v.date().isoformat(),) * 2 + (None,)
    if isinstance(v, date):
        return (v.isoformat(),) * 2 + (None,)
    if isinstance(v, (int, float)) and 20000 < v < 80000:   # Excel serial date stored as a number
        d = from_excel(v)
        d = d.date() if isinstance(d, datetime) else d
        return (d.isoformat(),) * 2 + (None,)
    s = re.sub(r"\s+", " ", str(v)).strip()
    if allow_placeholder:
        for p in store.lookups().get("date_placeholder", []):
            if _norm(s) in (_norm(p["value"]), _norm(p["label"]), *(_norm(a) for a in p.get("aliases", []))):
                return p["value"], p["value"], None
    one = _parse_one(s)
    if one:
        return one, one, None
    m = SAME_MONTH_RANGE.match(ORDINAL.sub(r"\1", s))
    if m:
        a, b = _parse_one(f"{m[1]} {m[3]} {m[4]}"), _parse_one(f"{m[2]} {m[3]} {m[4]}")
        if a and b:
            return a, b, None
    parts = [p for p in RANGE_SPLIT.split(s) if p]
    if len(parts) == 2:
        a, b = _parse_one(parts[0]), _parse_one(parts[1])
        if a and b:
            return a, b, None
    return None, None, f"'{s}' is not a recognised date"


def _to_date(v: Any, allow_placeholder: bool) -> tuple:
    """(value, warning) — the end of a range for single-date fields."""
    start, end, warning = _to_dates(v, allow_placeholder)
    if warning:
        return None, warning
    return end, (f"range '{v}' — using {end}" if start != end else None)


def _match(v: Any, options: List[dict]) -> Optional[str]:
    """Matches a lookup value, label or one of its aliases (Admin > Reference data)."""
    n = _norm(v)
    return next((o["value"] for o in options
                 if n in (_norm(o["value"]), _norm(o["label"]), *(_norm(a) for a in o.get("aliases", [])))), None)


def _match_ref(v: Any, rows: List[dict]) -> Optional[str]:
    n = _norm(v)
    return next((r["id"] for r in rows if n in (_norm(r["code"]), _norm(r["name"]), _norm(r["id"]))), None)


# ---------------------------------------------------------------------------
# Plan (dry run) + commit
# ---------------------------------------------------------------------------
def plan(sheet: dict, mapping: Dict[str, str], on_existing: str) -> List[dict]:
    lookups = store.lookups()
    entities, divisions = store.entities(), store.divisions()
    ms_labels = {d.key: d.short_label for d in domain.milestone_defs()}
    field_labels = {t["key"]: t["label"] for t in import_targets()}
    existing = {p["id"]: p for p in store.list_projects()}

    plans = []
    for idx, row in enumerate(sheet["rows"], start=2):   # Excel row number (header is row 1)
        errors: List[str] = []
        warnings: List[str] = []
        ident: Dict[str, Any] = {}
        sched: Dict[str, Any] = {}
        milestones: Dict[str, Dict[str, Any]] = {}
        pid = ""

        for header, target in mapping.items():
            if not target or header not in row:
                continue
            v = row[header]
            blank = v is None or str(v).strip() == ""
            label = field_labels.get(target, target)
            if target == "project_id":
                pid = "" if blank else str(v).strip()
            elif blank:
                continue
            elif target in ("name", "description", "project_manager"):
                ident[target] = str(v).strip()
            elif target == "entity":
                ident["entity_id"] = _match_ref(v, entities) or errors.append(f"{label}: unknown '{v}'")
            elif target == "division":
                ident["division_id"] = _match_ref(v, divisions) or errors.append(f"{label}: unknown '{v}'")
            elif target == "status":
                ident["status"] = _match(v, lookups.get("project_status", [])) or errors.append(f"{label}: unknown '{v}'")
            elif target == "weight_pct":
                try:
                    ident["weight_pct"] = float(str(v).replace("%", "").strip())
                except ValueError:
                    warnings.append(f"{label}: '{v}' is not a number — skipped")
            elif target in SCHEDULE_TARGETS:
                d, w = _to_date(v, allow_placeholder=False)
                if d:
                    sched[target] = d
                if w:
                    warnings.append(f"{label}: {w}" if d else f"{label}: {w} — skipped")
            elif target.startswith("ms."):
                _, key, part = target.split(".")
                if part == "date":
                    start, end, w = _to_dates(v, allow_placeholder=True)
                    if w:
                        warnings.append(f"{label}: {w} — skipped")
                    else:
                        ms = milestones.setdefault(key, {})
                        ms["expected_date"] = end
                        if start != end:          # "16 to 19 Dec 2025": baseline -> expected
                            ms["baseline_date"] = start
                else:
                    s = _match(v, lookups.get("milestone_status", []))
                    if s:
                        milestones.setdefault(key, {})["status"] = s
                    else:
                        errors.append(f"{label}: unknown status '{v}'")
        ident = {k: v for k, v in ident.items() if v is not None}

        current = existing.get(pid) if pid else None
        entry = {"row": idx, "project_id": pid or None, "name": ident.get("name") or (current or {}).get("identity", {}).get("name", ""),
                 "action": "", "changes": [], "warnings": warnings, "errors": errors}

        if current:
            if on_existing == "create_only":
                entry["action"] = "skip"
                plans.append(entry)
                continue
            entry["action"] = "update"
            for k, v in ident.items():
                if current["identity"].get(k) != v:
                    entry["changes"].append({"field": field_labels.get(k.replace("_id", ""), k), "from": current["identity"].get(k), "to": v})
            for k, v in sched.items():
                if current["schedule"].get(k) != v:
                    entry["changes"].append({"field": field_labels.get(k, k), "from": current["schedule"].get(k), "to": v})
            cur_ms = {m["key"]: m for m in current["milestones"]}
            for key, fields in milestones.items():
                old = cur_ms.get(key, {})
                if "expected_date" in fields and "baseline_date" not in fields and not old.get("baseline_date"):
                    fields["baseline_date"] = fields["expected_date"]
                for f, v in fields.items():
                    if old.get(f) != v:
                        entry["changes"].append({"field": f"{ms_labels.get(key, key)} {f.replace('_', ' ')}", "from": old.get(f), "to": v})
            if not entry["changes"] and not errors:
                entry["action"] = "unchanged"
        else:
            entry["action"] = "create"
            if pid:
                warnings.append(f"Project ID '{pid}' not found — a new ID will be generated")
            for req, lbl in (("name", "Project name"), ("entity_id", "Entity"), ("division_id", "Division")):
                if not ident.get(req):
                    errors.append(f"{lbl} is required to create a project")
            for key, fields in milestones.items():
                if "expected_date" in fields and "baseline_date" not in fields:
                    fields["baseline_date"] = fields["expected_date"]
            entry["changes"] = [{"field": "New project", "from": None, "to": ident.get("name")}]

        if errors:
            entry["action"] = "error"
        entry["_data"] = {"identity": ident, "schedule": sched, "milestones": milestones}
        plans.append(entry)
    return plans


def public(plans: List[dict]) -> List[dict]:
    return [{k: v for k, v in p.items() if not k.startswith("_")} for p in plans]


def commit(plans: List[dict], filename: str, actor: str) -> dict:
    created, updated, skipped, failed = [], [], 0, 0
    for p in plans:
        data = p.get("_data", {})
        if p["action"] == "create":
            payload = domain.with_project_defaults({
                "identity": data["identity"],
                "schedule": data["schedule"],
                "milestones": [{"key": k, **v} for k, v in data["milestones"].items()],
            })
            created.append(store.create_project(payload, actor=actor, source="import"))
        elif p["action"] == "update":
            pid = p["project_id"]
            store.save_state(pid, f"Before import of {filename}", actor, domain.get_hydrated(pid).model_dump())
            patch = {k: data[k] for k in ("identity", "schedule") if data[k]}
            if patch:
                store.update_project(pid, patch, actor=actor, source="import")
            for key, fields in data["milestones"].items():
                store.update_milestone(pid, key, fields, actor=actor, note=f"Imported from {filename}")
            updated.append(pid)
        elif p["action"] == "error":
            failed += 1
        else:
            skipped += 1

    store.meta_set("last_import", {"filename": filename, "date": now_iso()[:10], "by": actor})
    return {"created": len(created), "updated": len(updated), "skipped": skipped, "failed": failed,
            "total": len(plans), "created_ids": created, "updated_ids": updated}
