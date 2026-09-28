"""
SQLite-backed repository. Routers talk to this module only; it assembles
the structured tables into Project-shaped dicts (see models/project.py) and
writes changes back table by table.

Reference data (entities, divisions, milestone definitions, lookups, import
fields, cost assumptions) is seeded from app/seed/*.json only into empty
tables, so edits made later are never overwritten.
"""
from __future__ import annotations
import json
import sqlite3
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.config import settings
from app.services.db import Database
from app.services.history import now_iso, milestone_change

ACTIVITY_KINDS = ("accomplishments", "not_accomplished", "next_period")

IDENTITY_COLS = ("name", "entity_id", "division_id", "description",
                 "project_manager", "manager_user_id", "status", "status_update", "weight_pct",
                 "executive_sponsor", "delivery_organisation")
NULLABLE_IDENTITY = ("weight_pct", "manager_user_id")

# Editable at runtime from the Admin area; environment settings are the defaults.
EDITABLE_SETTINGS = {
    "app_name": str, "organisation_name": str, "currency": str, "currency_symbol": str,
    "project_id_prefix": str, "project_id_width": int, "upload_extensions": str, "upload_max_mb": int,
    "report_classification": str,
}
SCHEDULE_COLS = ("start_date", "original_baseline", "tsc_approved_date",
                 "planned_delivery", "forecast_delivery", "actual_delivery")
RESOURCE_COLS = ("junior_days", "intermediate_days", "expert_days",
                 "other_planned_costs", "actual_cost_to_date")
RAG_COLS = {"schedule": "rag_schedule", "budget": "rag_budget", "issues": "rag_issues",
            "schedule_comment": "rag_schedule_comment", "budget_comment": "rag_budget_comment",
            "issues_comment": "rag_issues_comment"}
MILESTONE_COLS = ("status", "baseline_date", "expected_date", "actual_date", "note")
ISSUE_COLS = ("priority", "description", "impact_summary", "action_steps", "milestone_key")
RISK_COLS = ("priority", "probability", "impact", "description",
             "impact_summary", "response_strategy", "status")


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


class Store:
    def __init__(self, db: Database) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------
    def init(self) -> None:
        self.db.init_schema()
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        self._seed_reference()
        self._migrate_reference()
        if settings.seed_demo_projects:
            self._seed_demo()

    def _seed_json(self, name: str) -> Any:
        return json.loads((settings.seed_dir / name).read_text(encoding="utf-8"))

    def _seed_reference(self) -> None:
        with self.db.connect() as con:
            def empty(table: str) -> bool:
                return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0

            if empty("entities"):
                con.executemany(
                    "INSERT INTO entities (id, code, name, sort_order) VALUES (?,?,?,?)",
                    [(e["id"], e["code"], e["name"], i) for i, e in enumerate(self._seed_json("entities.json"))],
                )
            if empty("divisions"):
                con.executemany(
                    "INSERT INTO divisions (id, code, name, sort_order) VALUES (?,?,?,?)",
                    [(d["id"], d["code"], d["name"], i) for i, d in enumerate(self._seed_json("divisions.json"))],
                )
            if empty("milestone_defs"):
                con.executemany(
                    "INSERT INTO milestone_defs (key, label, short_label, sort_order, weight) VALUES (?,?,?,?,?)",
                    [(m["key"], m["label"], m.get("short_label", m["label"]), m["order"], m.get("weight"))
                     for m in self._seed_json("milestone_defs.json")],
                )
            if empty("lookups"):
                con.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('reference_version', ?)",
                            (json.dumps(self.REFERENCE_VERSION),))
                rows = []
                for kind, options in self._seed_json("lookups.json").items():
                    for i, o in enumerate(options):
                        extra = {k: v for k, v in o.items() if k not in ("value", "label", "tone")}
                        rows.append((kind, o["value"], o["label"], o.get("tone", "neutral"), i, json.dumps(extra)))
                con.executemany(
                    "INSERT INTO lookups (kind, value, label, tone, sort_order, extra_json) VALUES (?,?,?,?,?,?)",
                    rows,
                )
            if empty("import_fields"):
                con.executemany(
                    "INSERT INTO import_fields (key, label, aliases_json, sort_order) VALUES (?,?,?,?)",
                    [(f["key"], f["label"], json.dumps(f.get("aliases", [])), i)
                     for i, f in enumerate(self._seed_json("import_fields.json"))],
                )
            if empty("roles"):
                con.executemany(
                    "INSERT INTO roles (key, label, permissions_json, sort_order) VALUES (?,?,?,?)",
                    [(r["key"], r["label"], json.dumps(r["permissions"]), i)
                     for i, r in enumerate(self._seed_json("roles.json"))],
                )
            if empty("cost_assumptions"):
                c = self._seed_json("cost_assumptions.json")
                con.execute(
                    "INSERT INTO cost_assumptions (id, junior_rate, intermediate_rate, expert_rate,"
                    " contingency_pct, updated_at, updated_by) VALUES (1,?,?,?,?,?,?)",
                    (c["junior_rate"], c["intermediate_rate"], c["expert_rate"],
                     c["contingency_pct"], now_iso(), settings.default_actor),
                )

    REFERENCE_VERSION = 3   # 2: April 2025 report details; 3: import aliases

    def _migrate_reference(self) -> None:
        """v2: report-format details from the April 2025 report — legend text,
        codes and colours on lookups, and the 'Not triggered' risk statuses.
        v3: spelling aliases used to match statuses and TBD/N/A during Excel import.
        Adds missing options and missing keys only, never overwriting Admin edits."""
        version = self.meta_get("reference_version") or 1
        if version >= self.REFERENCE_VERSION:
            return
        seed = self._seed_json("lookups.json")
        current = self.lookups()
        with self.db.connect() as con:
            for kind, options in seed.items():
                have = {o["value"]: o for o in current.get(kind, [])}
                for i, o in enumerate(options):
                    extra = {k: v for k, v in o.items() if k not in ("value", "label", "tone", "is_default")}
                    if o["value"] in have:
                        row = con.execute("SELECT extra_json FROM lookups WHERE kind = ? AND value = ?",
                                          (kind, o["value"])).fetchone()
                        merged = {**extra, **json.loads(row["extra_json"])}
                        con.execute("UPDATE lookups SET extra_json = ? WHERE kind = ? AND value = ?",
                                    (json.dumps(merged), kind, o["value"]))
                    else:
                        order = con.execute("SELECT COALESCE(MAX(sort_order), -1) + 1 FROM lookups WHERE kind = ?",
                                            (kind,)).fetchone()[0]
                        con.execute("INSERT INTO lookups (kind, value, label, tone, sort_order, extra_json)"
                                    " VALUES (?,?,?,?,?,?)",
                                    (kind, o["value"], o["label"], o.get("tone", "neutral"), order, json.dumps(extra)))
            # Adopt the new seed default for risk status only if the old seed default is untouched.
            row = con.execute("SELECT extra_json FROM lookups WHERE kind = 'risk_status' AND value = 'Open'").fetchone()
            if row and json.loads(row["extra_json"]).get("is_default"):
                for r in con.execute("SELECT value, extra_json FROM lookups WHERE kind = 'risk_status'").fetchall():
                    e = json.loads(r["extra_json"])
                    e.pop("is_default", None)
                    if r["value"] == "Not triggered":
                        e["is_default"] = True
                    con.execute("UPDATE lookups SET extra_json = ? WHERE kind = 'risk_status' AND value = ?",
                                (json.dumps(e), r["value"]))
        self.meta_set("reference_version", self.REFERENCE_VERSION)

    def _seed_demo(self) -> None:
        with self.db.connect() as con:
            if con.execute("SELECT COUNT(*) FROM projects").fetchone()[0]:
                return
        from app.services.domain import with_project_defaults
        for p in self._seed_json("demo_projects.json"):
            self.create_project(with_project_defaults(p))

    # ------------------------------------------------------------------
    # Reference data
    # ------------------------------------------------------------------
    def entities(self) -> List[dict]:
        with self.db.connect() as con:
            return [dict(r) for r in con.execute("SELECT id, code, name FROM entities ORDER BY sort_order")]

    def divisions(self) -> List[dict]:
        with self.db.connect() as con:
            return [dict(r) for r in con.execute("SELECT id, code, name FROM divisions ORDER BY sort_order")]

    def milestone_defs(self) -> List[dict]:
        with self.db.connect() as con:
            return [
                {"key": r["key"], "label": r["label"], "short_label": r["short_label"],
                 "order": r["sort_order"], "weight": r["weight"]}
                for r in con.execute("SELECT * FROM milestone_defs ORDER BY sort_order")
            ]

    def lookups(self) -> Dict[str, List[dict]]:
        out: Dict[str, List[dict]] = {}
        with self.db.connect() as con:
            for r in con.execute("SELECT * FROM lookups ORDER BY kind, sort_order"):
                out.setdefault(r["kind"], []).append(
                    {"value": r["value"], "label": r["label"], "tone": r["tone"], **json.loads(r["extra_json"])}
                )
        return out

    def lookup_values(self, kind: str) -> List[str]:
        return [o["value"] for o in self.lookups().get(kind, [])]

    def import_fields(self) -> List[dict]:
        with self.db.connect() as con:
            return [
                {"key": r["key"], "label": r["label"], "aliases": json.loads(r["aliases_json"])}
                for r in con.execute("SELECT * FROM import_fields ORDER BY sort_order")
            ]

    def get_cost_assumptions(self) -> dict:
        with self.db.connect() as con:
            r = con.execute(
                "SELECT junior_rate, intermediate_rate, expert_rate, contingency_pct FROM cost_assumptions WHERE id = 1"
            ).fetchone()
            return dict(r)

    def set_cost_assumptions(self, payload: dict, actor: str) -> None:
        with self.db.connect() as con:
            old = dict(con.execute("SELECT junior_rate, intermediate_rate, expert_rate, contingency_pct"
                                   " FROM cost_assumptions WHERE id = 1").fetchone())
            self._log_diff(con, None, "costs", actor, "app", None, "Cost assumptions", old,
                           {k: payload[k] for k in old})
            con.execute(
                "UPDATE cost_assumptions SET junior_rate=?, intermediate_rate=?, expert_rate=?,"
                " contingency_pct=?, updated_at=?, updated_by=? WHERE id = 1",
                (payload["junior_rate"], payload["intermediate_rate"], payload["expert_rate"],
                 payload["contingency_pct"], now_iso(), actor),
            )

    def meta_get(self, key: str) -> Optional[Any]:
        with self.db.connect() as con:
            r = con.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
            return json.loads(r["value"]) if r else None

    def meta_set(self, key: str, value: Any) -> None:
        with self.db.connect() as con:
            con.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, json.dumps(value)),
            )

    # ------------------------------------------------------------------
    # Project reads
    # ------------------------------------------------------------------
    def list_projects(self) -> List[dict]:
        with self.db.connect() as con:
            rows = con.execute("SELECT * FROM projects ORDER BY seq").fetchall()
            return self._assemble(con, rows)

    def get_project(self, project_id: str) -> Optional[dict]:
        with self.db.connect() as con:
            rows = con.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchall()
            out = self._assemble(con, rows)
            return out[0] if out else None

    def project_exists(self, project_id: str) -> bool:
        with self.db.connect() as con:
            return con.execute("SELECT 1 FROM projects WHERE id = ?", (project_id,)).fetchone() is not None

    def _assemble(self, con: sqlite3.Connection, rows: List[sqlite3.Row]) -> List[dict]:
        if not rows:
            return []
        ids = [r["id"] for r in rows]
        ph = ",".join("?" * len(ids))

        def grouped(sql: str) -> Dict[str, List[sqlite3.Row]]:
            g: Dict[str, List[sqlite3.Row]] = {}
            for r in con.execute(sql.format(ph=ph), ids):
                g.setdefault(r["project_id"], []).append(r)
            return g

        order = {r["key"]: r["sort_order"] for r in con.execute("SELECT key, sort_order FROM milestone_defs")}
        milestones = grouped("SELECT * FROM milestones WHERE project_id IN ({ph})")
        history = grouped("SELECT * FROM milestone_history WHERE project_id IN ({ph}) ORDER BY id")
        issues = grouped("SELECT * FROM issues WHERE project_id IN ({ph}) ORDER BY sort_order, rowid")
        risks = grouped("SELECT * FROM risks WHERE project_id IN ({ph}) ORDER BY sort_order, rowid")
        acts = grouped("SELECT * FROM planned_activities WHERE project_id IN ({ph}) ORDER BY sort_order, id")
        docs = grouped(
            "SELECT * FROM documents d WHERE project_id IN ({ph}) AND deleted = 0"
            " AND NOT EXISTS (SELECT 1 FROM documents n WHERE n.replaces = d.id AND n.deleted = 0)"
            " ORDER BY uploaded_at"
        )

        out = []
        for r in rows:
            pid = r["id"]
            hist_by_key: Dict[str, List[dict]] = {}
            for h in history.get(pid, []):
                hist_by_key.setdefault(h["key"], []).append({
                    "changed_at": h["changed_at"], "changed_by": h["changed_by"],
                    "from_state": json.loads(h["from_json"]), "to_state": json.loads(h["to_json"]),
                    "note": h["note"],
                })
            ms = sorted(milestones.get(pid, []), key=lambda m: order.get(m["key"], 999))
            activities = {k: [] for k in ACTIVITY_KINDS}
            for a in acts.get(pid, []):
                activities.setdefault(a["kind"], []).append(a["text"])

            out.append({
                "id": pid,
                "identity": {c: r[c] for c in IDENTITY_COLS},
                "schedule": {c: r[c] for c in SCHEDULE_COLS},
                "resources": {c: r[c] for c in RESOURCE_COLS},
                "rag": {k: r[c] for k, c in RAG_COLS.items()},
                "milestones": [
                    {"key": m["key"], **{c: m[c] for c in MILESTONE_COLS}, "history": hist_by_key.get(m["key"], [])}
                    for m in ms
                ],
                "issues": [
                    {"id": i["id"], **{c: i[c] for c in ISSUE_COLS},
                     "impact_areas": json.loads(i["impact_areas_json"])}
                    for i in issues.get(pid, [])
                ],
                "risks": [{"id": k["id"], **{c: k[c] for c in RISK_COLS}} for k in risks.get(pid, [])],
                "planned_activities": activities,
                "executive_summary": r["executive_summary"],
                "documents": [self._doc_dict(d) for d in docs.get(pid, [])],
                "is_draft": bool(r["is_draft"]),
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            })
        return out

    # ------------------------------------------------------------------
    # Change log
    # ------------------------------------------------------------------
    @staticmethod
    def _log(con: sqlite3.Connection, project_id: Optional[str], area: str, action: str, actor: str,
             source: str = "app", item_id: Optional[str] = None, item_label: str = "",
             field: Optional[str] = None, old: Any = None, new: Any = None) -> None:
        con.execute(
            "INSERT INTO change_log (project_id, area, action, item_id, item_label, field, old_json, new_json,"
            " changed_at, changed_by, source) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (project_id, area, action, item_id, item_label or "", field,
             None if old is None else json.dumps(old), None if new is None else json.dumps(new),
             now_iso(), actor or settings.default_actor, source),
        )

    def _log_diff(self, con, project_id, area, actor, source, item_id, item_label, old: dict, new: dict) -> None:
        for field, value in new.items():
            if field in old and old[field] != value and not (old[field] in (None, "") and value in (None, "")):
                self._log(con, project_id, area, "updated", actor, source, item_id, item_label, field, old[field], value)

    def change_log(self, project_id: str) -> List[dict]:
        """Project changes (incl. milestone history) plus global cost-rate changes since it was created."""
        with self.db.connect() as con:
            created = con.execute("SELECT created_at FROM projects WHERE id = ?", (project_id,)).fetchone()
            since = created["created_at"] if created else ""
            rows = [dict(r) for r in con.execute(
                "SELECT * FROM change_log WHERE project_id = ? OR (project_id IS NULL AND changed_at >= ?)",
                (project_id, since))]
            entries = [{
                "changed_at": r["changed_at"], "changed_by": r["changed_by"], "area": r["area"],
                "action": r["action"], "item_label": r["item_label"], "field": r["field"],
                "old": json.loads(r["old_json"]) if r["old_json"] is not None else None,
                "new": json.loads(r["new_json"]) if r["new_json"] is not None else None,
                "source": r["source"], "note": "",
            } for r in rows]
            labels = {r["key"]: r["label"] for r in con.execute("SELECT key, label FROM milestone_defs")}
            for h in con.execute("SELECT * FROM milestone_history WHERE project_id = ?", (project_id,)):
                old, new = json.loads(h["from_json"]), json.loads(h["to_json"])
                for field in new:
                    if old.get(field) != new.get(field):
                        entries.append({
                            "changed_at": h["changed_at"], "changed_by": h["changed_by"], "area": "milestone",
                            "action": "updated", "item_label": labels.get(h["key"], h["key"]), "field": field,
                            "old": old.get(field), "new": new.get(field), "note": h["note"],
                            "source": "import" if (h["note"] or "").startswith("Imported from") else "app",
                        })
        return sorted(entries, key=lambda e: e["changed_at"], reverse=True)

    # ------------------------------------------------------------------
    # Project writes
    # ------------------------------------------------------------------
    def create_project(self, data: dict, actor: str = "", source: str = "app") -> str:
        """Creates the project with all lifecycle milestones; returns the generated ID.
        Callers apply lookup defaults first (domain.with_project_defaults)."""
        now = now_iso()
        ident = data.get("identity", {})
        sched = data.get("schedule", {})
        res = data.get("resources", {})
        rag = data.get("rag", {})
        with self.db.connect() as con:
            seq = con.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM projects").fetchone()[0]
            pid = f"{self.setting('project_id_prefix')}-{seq:0{int(self.setting('project_id_width'))}d}"
            con.execute(
                f"INSERT INTO projects (id, seq, {', '.join(IDENTITY_COLS)}, {', '.join(SCHEDULE_COLS)},"
                f" {', '.join(RESOURCE_COLS)}, {', '.join(RAG_COLS.values())}, executive_summary,"
                f" is_draft, created_at, updated_at)"
                f" VALUES ({','.join('?' * (len(IDENTITY_COLS) + len(SCHEDULE_COLS) + len(RESOURCE_COLS) + len(RAG_COLS) + 6))})",
                (
                    pid, seq,
                    *[ident.get(c) if c in NULLABLE_IDENTITY else (ident.get(c) or "") for c in IDENTITY_COLS],
                    *[sched.get(c) for c in SCHEDULE_COLS],
                    *[res.get(c) or 0 for c in RESOURCE_COLS],
                    *[rag.get(k) if not k.endswith("_comment") else (rag.get(k) or "") for k in RAG_COLS],
                    data.get("executive_summary", ""),
                    1 if data.get("is_draft") else 0,
                    now, now,
                ),
            )
            given = {m["key"]: m for m in data.get("milestones", [])}
            for d in con.execute("SELECT key FROM milestone_defs ORDER BY sort_order"):
                m = given.get(d["key"], {})
                con.execute(
                    "INSERT INTO milestones (project_id, key, status, baseline_date, expected_date, actual_date, note)"
                    " VALUES (?,?,?,?,?,?,?)",
                    (pid, d["key"], m.get("status"), m.get("baseline_date"),
                     m.get("expected_date"), m.get("actual_date"), m.get("note") or ""),
                )
            self._write_activities(con, pid, data.get("planned_activities") or {})
            for i, issue in enumerate(data.get("issues", [])):
                self._insert_issue(con, pid, issue, i)
            for i, risk in enumerate(data.get("risks", [])):
                self._insert_risk(con, pid, risk, i)
            self._log(con, pid, "project", "created", actor, source, pid, ident.get("name", ""))
        return pid

    def update_project(self, project_id: str, patch: dict, actor: str = "", source: str = "app") -> None:
        """Partial update of scalar sections, planned activities, summary and draft flag.
        Milestones, issues, risks and documents have their own endpoints so that
        milestone history is always recorded."""
        sets: Dict[str, Any] = {}
        for section, cols in (("identity", IDENTITY_COLS), ("schedule", SCHEDULE_COLS), ("resources", RESOURCE_COLS)):
            for c in cols:
                if c in (patch.get(section) or {}):
                    sets[c] = patch[section][c]
        for k, c in RAG_COLS.items():
            if k in (patch.get("rag") or {}):
                sets[c] = patch["rag"][k]
        if "executive_summary" in patch:
            sets["executive_summary"] = patch["executive_summary"]
        if "is_draft" in patch:
            sets["is_draft"] = 1 if patch["is_draft"] else 0
        sets["updated_at"] = now_iso()

        with self.db.connect() as con:
            before = con.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
            name = before["name"] if before else project_id
            if before:
                field_of = {**{c: f"identity.{c}" for c in IDENTITY_COLS}, **{c: f"schedule.{c}" for c in SCHEDULE_COLS},
                            **{c: f"resources.{c}" for c in RESOURCE_COLS}, **{c: f"rag.{k}" for k, c in RAG_COLS.items()},
                            "executive_summary": "executive_summary", "is_draft": "is_draft"}
                old = {field_of[c]: before[c] for c in sets if c in field_of}
                new = {field_of[c]: v for c, v in sets.items() if c in field_of}
                for k in ("is_draft",):
                    if k in old:
                        old[k], new[k] = bool(old[k]), bool(new[k])
                self._log_diff(con, project_id, "project", actor, source, project_id, name, old, new)
            if "planned_activities" in patch:
                prev = {k: [] for k in ACTIVITY_KINDS}
                for a in con.execute("SELECT kind, text FROM planned_activities WHERE project_id = ? ORDER BY sort_order, id",
                                     (project_id,)):
                    prev.setdefault(a["kind"], []).append(a["text"])
            con.execute(
                f"UPDATE projects SET {', '.join(f'{c} = ?' for c in sets)} WHERE id = ?",
                (*sets.values(), project_id),
            )
            if "planned_activities" in patch:
                self._write_activities(con, project_id, patch["planned_activities"] or {})
                nxt = {k: [str(t).strip() for t in (patch["planned_activities"] or {}).get(k) or [] if str(t).strip()]
                       for k in ACTIVITY_KINDS}
                self._log_diff(con, project_id, "project", actor, source, project_id, name,
                               {f"planned_activities.{k}": v for k, v in prev.items()},
                               {f"planned_activities.{k}": v for k, v in nxt.items()})

    def _touch(self, con: sqlite3.Connection, project_id: str) -> None:
        con.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (now_iso(), project_id))

    def _write_activities(self, con: sqlite3.Connection, project_id: str, pa: dict) -> None:
        con.execute("DELETE FROM planned_activities WHERE project_id = ?", (project_id,))
        for kind in ACTIVITY_KINDS:
            for i, text in enumerate(t for t in (pa.get(kind) or []) if str(t).strip()):
                con.execute(
                    "INSERT INTO planned_activities (project_id, kind, text, sort_order) VALUES (?,?,?,?)",
                    (project_id, kind, str(text).strip(), i),
                )

    # ------------------------------------------------------------------
    # Milestones (history-aware, README §13)
    # ------------------------------------------------------------------
    def update_milestone(
        self, project_id: str, key: str, fields: dict, actor: str, note: str = ""
    ) -> Optional[dict]:
        with self.db.connect() as con:
            row = con.execute(
                "SELECT * FROM milestones WHERE project_id = ? AND key = ?", (project_id, key)
            ).fetchone()
            if not row:
                return None
            old = {c: row[c] for c in MILESTONE_COLS}
            new = {**old, **{c: fields[c] for c in MILESTONE_COLS if c in fields}}
            change = milestone_change(old, new)
            if change:
                con.execute(
                    f"UPDATE milestones SET {', '.join(f'{c} = ?' for c in MILESTONE_COLS)}"
                    " WHERE project_id = ? AND key = ?",
                    (*[new[c] for c in MILESTONE_COLS], project_id, key),
                )
                con.execute(
                    "INSERT INTO milestone_history (project_id, key, changed_at, changed_by, from_json, to_json, note)"
                    " VALUES (?,?,?,?,?,?,?)",
                    (project_id, key, now_iso(), actor, json.dumps(change[0]), json.dumps(change[1]), note or ""),
                )
                self._touch(con, project_id)
            return {"key": key, **new, "changed": bool(change)}

    # ------------------------------------------------------------------
    # Issues / risks
    # ------------------------------------------------------------------
    def _insert_issue(self, con: sqlite3.Connection, project_id: str, issue: dict, sort_order: int) -> str:
        iid = issue.get("id") or _new_id("ISS")
        con.execute(
            f"INSERT INTO issues (id, project_id, {', '.join(ISSUE_COLS)}, impact_areas_json, sort_order)"
            f" VALUES (?,?,{','.join('?' * len(ISSUE_COLS))},?,?)",
            (iid, project_id, *[issue.get(c) for c in ISSUE_COLS],
             json.dumps(issue.get("impact_areas") or []), sort_order),
        )
        return iid

    def _insert_risk(self, con: sqlite3.Connection, project_id: str, risk: dict, sort_order: int) -> str:
        rid = risk.get("id") or _new_id("RSK")
        con.execute(
            f"INSERT INTO risks (id, project_id, {', '.join(RISK_COLS)}, sort_order)"
            f" VALUES (?,?,{','.join('?' * len(RISK_COLS))},?)",
            (rid, project_id, *[risk.get(c) for c in RISK_COLS], sort_order),
        )
        return rid

    def _next_sort(self, con: sqlite3.Connection, table: str, project_id: str) -> int:
        return con.execute(
            f"SELECT COALESCE(MAX(sort_order), -1) + 1 FROM {table} WHERE project_id = ?", (project_id,)
        ).fetchone()[0]

    def add_issue(self, project_id: str, issue: dict, actor: str = "") -> str:
        with self.db.connect() as con:
            iid = self._insert_issue(con, project_id, {**issue, "id": None}, self._next_sort(con, "issues", project_id))
            self._log(con, project_id, "issue", "created", actor, item_id=iid, item_label=issue.get("description", "")[:120])
            self._touch(con, project_id)
            return iid

    def _child_fields(self, con, table: str, child_id: str) -> Optional[dict]:
        r = con.execute(f"SELECT * FROM {table} WHERE id = ?", (child_id,)).fetchone()
        if not r:
            return None
        cols = ISSUE_COLS if table == "issues" else RISK_COLS
        out = {c: r[c] for c in cols}
        if table == "issues":
            out["impact_areas"] = json.loads(r["impact_areas_json"])
        return out

    def update_issue(self, project_id: str, issue_id: str, issue: dict, actor: str = "") -> bool:
        with self.db.connect() as con:
            old = self._child_fields(con, "issues", issue_id)
            if old:
                new = {**{c: issue.get(c) for c in ISSUE_COLS}, "impact_areas": issue.get("impact_areas") or []}
                self._log_diff(con, project_id, "issue", actor, "app", issue_id,
                               (issue.get("description") or old["description"] or "")[:120], old, new)
            cur = con.execute(
                f"UPDATE issues SET {', '.join(f'{c} = ?' for c in ISSUE_COLS)}, impact_areas_json = ?"
                " WHERE id = ? AND project_id = ?",
                (*[issue.get(c) for c in ISSUE_COLS], json.dumps(issue.get("impact_areas") or []),
                 issue_id, project_id),
            )
            self._touch(con, project_id)
            return cur.rowcount > 0

    def add_risk(self, project_id: str, risk: dict, actor: str = "") -> str:
        with self.db.connect() as con:
            rid = self._insert_risk(con, project_id, {**risk, "id": None}, self._next_sort(con, "risks", project_id))
            self._log(con, project_id, "risk", "created", actor, item_id=rid, item_label=risk.get("description", "")[:120])
            self._touch(con, project_id)
            return rid

    def update_risk(self, project_id: str, risk_id: str, risk: dict, actor: str = "") -> bool:
        with self.db.connect() as con:
            old = self._child_fields(con, "risks", risk_id)
            if old:
                self._log_diff(con, project_id, "risk", actor, "app", risk_id,
                               (risk.get("description") or old["description"] or "")[:120],
                               old, {c: risk.get(c) for c in RISK_COLS})
            cur = con.execute(
                f"UPDATE risks SET {', '.join(f'{c} = ?' for c in RISK_COLS)} WHERE id = ? AND project_id = ?",
                (*[risk.get(c) for c in RISK_COLS], risk_id, project_id),
            )
            self._touch(con, project_id)
            return cur.rowcount > 0

    def delete_child(self, table: str, project_id: str, child_id: str, actor: str = "") -> bool:
        assert table in ("issues", "risks")
        with self.db.connect() as con:
            old = self._child_fields(con, table, child_id)
            if old:
                self._log(con, project_id, table[:-1], "deleted", actor, item_id=child_id,
                          item_label=(old.get("description") or "")[:120], old=old)
            cur = con.execute(f"DELETE FROM {table} WHERE id = ? AND project_id = ?", (child_id, project_id))
            self._touch(con, project_id)
            return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------
    @staticmethod
    def _doc_dict(r: sqlite3.Row) -> dict:
        return {
            "id": r["id"], "milestone_key": r["milestone_key"], "filename": r["filename"],
            "mime_type": r["mime_type"], "size_bytes": r["size_bytes"],
            "uploaded_at": r["uploaded_at"], "uploaded_by": r["uploaded_by"],
            "url": f"{settings.api_prefix}/documents/{r['id']}/raw", "replaces": r["replaces"],
        }

    def add_document(self, project_id: str, doc: dict) -> dict:
        with self.db.connect() as con:
            con.execute(
                "INSERT INTO documents (id, project_id, milestone_key, filename, stored_name, mime_type,"
                " size_bytes, uploaded_at, uploaded_by, replaces) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (doc["id"], project_id, doc.get("milestone_key"), doc["filename"], doc["stored_name"],
                 doc["mime_type"], doc["size_bytes"], doc["uploaded_at"], doc["uploaded_by"], doc.get("replaces")),
            )
            old_name = None
            if doc.get("replaces"):
                r = con.execute("SELECT filename FROM documents WHERE id = ?", (doc["replaces"],)).fetchone()
                old_name = r["filename"] if r else None
            self._log(con, project_id, "document", "replaced" if doc.get("replaces") else "uploaded", doc["uploaded_by"],
                      item_id=doc["id"], item_label=doc.get("milestone_key") or "", field="file", old=old_name, new=doc["filename"])
            self._touch(con, project_id)
            return self._doc_dict(con.execute("SELECT * FROM documents WHERE id = ?", (doc["id"],)).fetchone())

    def get_document(self, doc_id: str) -> Optional[dict]:
        with self.db.connect() as con:
            r = con.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
            return {**self._doc_dict(r), "stored_name": r["stored_name"], "project_id": r["project_id"]} if r else None

    def delete_document(self, project_id: str, doc_id: str, actor: str = "") -> bool:
        """Soft delete: the file and record stay for history."""
        with self.db.connect() as con:
            r = con.execute("SELECT filename, milestone_key FROM documents WHERE id = ? AND project_id = ?",
                            (doc_id, project_id)).fetchone()
            if r:
                self._log(con, project_id, "document", "deleted", actor, item_id=doc_id,
                          item_label=r["milestone_key"] or "", field="file", old=r["filename"])
            cur = con.execute(
                "UPDATE documents SET deleted = 1 WHERE id = ? AND project_id = ?", (doc_id, project_id)
            )
            self._touch(con, project_id)
            return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Saved states (README §39)
    # ------------------------------------------------------------------
    @staticmethod
    def _state_summary(r: sqlite3.Row) -> dict:
        return {"id": r["id"], "project_id": r["project_id"], "label": r["label"],
                "saved_at": r["saved_at"], "saved_by": r["saved_by"]}

    def save_state(self, project_id: str, label: str, actor: str, snapshot: dict) -> dict:
        with self.db.connect() as con:
            sid = _new_id("STATE")
            con.execute(
                "INSERT INTO project_states (id, project_id, label, saved_at, saved_by, snapshot_json)"
                " VALUES (?,?,?,?,?,?)",
                (sid, project_id, label, now_iso(), actor, json.dumps(snapshot)),
            )
            self._log(con, project_id, "state", "saved", actor, item_id=sid, item_label=label)
            return self._state_summary(con.execute("SELECT * FROM project_states WHERE id = ?", (sid,)).fetchone())

    def list_states(self, project_id: str) -> List[dict]:
        with self.db.connect() as con:
            return [self._state_summary(r) for r in con.execute(
                "SELECT * FROM project_states WHERE project_id = ? ORDER BY saved_at DESC", (project_id,)
            )]

    def get_state(self, state_id: str) -> Optional[dict]:
        with self.db.connect() as con:
            r = con.execute("SELECT * FROM project_states WHERE id = ?", (state_id,)).fetchone()
            return {**self._state_summary(r), "snapshot": json.loads(r["snapshot_json"])} if r else None

    def latest_state_on_or_before(self, project_id: str, iso_date: str) -> Optional[dict]:
        with self.db.connect() as con:
            r = con.execute(
                "SELECT id FROM project_states WHERE project_id = ? AND substr(saved_at, 1, 10) <= ?"
                " ORDER BY saved_at DESC LIMIT 1",
                (project_id, iso_date),
            ).fetchone()
        return self.get_state(r["id"]) if r else None


    # ------------------------------------------------------------------
    # Runtime settings (Admin > Settings)
    # ------------------------------------------------------------------
    def setting(self, key: str) -> Any:
        overrides = self.meta_get("settings") or {}
        return overrides.get(key, getattr(settings, key))

    def all_settings(self) -> Dict[str, Any]:
        return {k: self.setting(k) for k in EDITABLE_SETTINGS}

    def update_settings(self, values: Dict[str, Any]) -> None:
        overrides = self.meta_get("settings") or {}
        overrides.update({k: v for k, v in values.items() if k in EDITABLE_SETTINGS})
        self.meta_set("settings", overrides)

    # ------------------------------------------------------------------
    # Roles, users, sessions (README §43–§44)
    # ------------------------------------------------------------------
    def roles(self) -> List[dict]:
        with self.db.connect() as con:
            return [{"key": r["key"], "label": r["label"], "permissions": json.loads(r["permissions_json"])}
                    for r in con.execute("SELECT * FROM roles ORDER BY sort_order")]

    @staticmethod
    def _user(r: sqlite3.Row, with_hash: bool = False) -> dict:
        u = {"id": r["id"], "email": r["email"], "name": r["name"], "role": r["role"],
             "active": bool(r["active"]), "must_change_password": bool(r["must_change_password"]),
             "created_at": r["created_at"], "last_login_at": r["last_login_at"]}
        if with_hash:
            u["password_hash"] = r["password_hash"]
        return u

    def user_count(self) -> int:
        with self.db.connect() as con:
            return con.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def list_users(self) -> List[dict]:
        with self.db.connect() as con:
            return [self._user(r) for r in con.execute("SELECT * FROM users ORDER BY name COLLATE NOCASE")]

    def get_user(self, user_id: str, with_hash: bool = False) -> Optional[dict]:
        with self.db.connect() as con:
            r = con.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            return self._user(r, with_hash) if r else None

    def get_user_by_email(self, email: str, with_hash: bool = False) -> Optional[dict]:
        with self.db.connect() as con:
            r = con.execute("SELECT * FROM users WHERE email = ?", (email.strip(),)).fetchone()
            return self._user(r, with_hash) if r else None

    def create_user(self, email: str, name: str, role: str, password_hash: str, must_change: bool) -> dict:
        uid = _new_id("USR")
        with self.db.connect() as con:
            con.execute(
                "INSERT INTO users (id, email, name, role, password_hash, active, must_change_password, created_at)"
                " VALUES (?,?,?,?,?,1,?,?)",
                (uid, email.strip(), name.strip(), role, password_hash, 1 if must_change else 0, now_iso()),
            )
        return self.get_user(uid)

    def update_user(self, user_id: str, fields: dict) -> None:
        allowed = ("email", "name", "role", "active", "must_change_password", "password_hash")
        cols = {k: v for k, v in fields.items() if k in allowed}
        for k in ("active", "must_change_password"):
            if k in cols:
                cols[k] = 1 if cols[k] else 0
        if not cols:
            return
        with self.db.connect() as con:
            con.execute(f"UPDATE users SET {', '.join(f'{c} = ?' for c in cols)} WHERE id = ?", (*cols.values(), user_id))
            if "name" in cols:   # keep the displayed manager name in step
                con.execute("UPDATE projects SET project_manager = ? WHERE manager_user_id = ?", (cols["name"], user_id))
            if cols.get("active") == 0 or "password_hash" in cols:
                con.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))

    def count_active_with_permission(self, permission: str) -> int:
        keys = [r["key"] for r in self.roles() if permission in r["permissions"]]
        if not keys:
            return 0
        with self.db.connect() as con:
            return con.execute(
                f"SELECT COUNT(*) FROM users WHERE active = 1 AND role IN ({','.join('?' * len(keys))})", keys
            ).fetchone()[0]

    def create_session(self, token_hash: str, user_id: str, expires_at: str) -> None:
        with self.db.connect() as con:
            con.execute("DELETE FROM sessions WHERE expires_at < ?", (now_iso(),))
            con.execute("INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?,?,?,?)",
                        (token_hash, user_id, now_iso(), expires_at))
            con.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now_iso(), user_id))

    def user_for_session(self, token_hash: str) -> Optional[dict]:
        with self.db.connect() as con:
            r = con.execute(
                "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id"
                " WHERE s.token_hash = ? AND s.expires_at > ? AND u.active = 1",
                (token_hash, now_iso()),
            ).fetchone()
            return self._user(r) if r else None

    def delete_session(self, token_hash: str) -> None:
        with self.db.connect() as con:
            con.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))

    def project_manager_id(self, project_id: str) -> Optional[str]:
        with self.db.connect() as con:
            r = con.execute("SELECT manager_user_id FROM projects WHERE id = ?", (project_id,)).fetchone()
            return r["manager_user_id"] if r else None

    # ------------------------------------------------------------------
    # Reference data maintenance (Admin > Reference data)
    # ------------------------------------------------------------------
    LOOKUP_USAGE = {
        "project_status":    [("SELECT COUNT(*) FROM projects WHERE status = ?", 1)],
        "milestone_status":  [("SELECT COUNT(*) FROM milestones WHERE status = ?", 1)],
        "rag":               [("SELECT COUNT(*) FROM projects WHERE rag_schedule = ? OR rag_budget = ? OR rag_issues = ?", 3)],
        "issue_priority":    [("SELECT COUNT(*) FROM issues WHERE priority = ?", 1),
                              ("SELECT COUNT(*) FROM risks WHERE priority = ?", 1)],
        "risk_status":       [("SELECT COUNT(*) FROM risks WHERE status = ?", 1)],
        "issue_impact_area": [("SELECT COUNT(*) FROM issues WHERE instr(impact_areas_json, json_quote(?)) > 0", 1)],
        "probability":       [("SELECT COUNT(*) FROM risks WHERE probability = CAST(? AS INTEGER)", 1)],
        "impact":            [("SELECT COUNT(*) FROM risks WHERE impact = CAST(? AS INTEGER)", 1)],
        "date_placeholder":  [("SELECT COUNT(*) FROM milestones WHERE baseline_date = ? OR expected_date = ? OR actual_date = ?", 3)],
    }

    def lookup_usage(self, kind: str, value: str) -> int:
        with self.db.connect() as con:
            return sum(con.execute(sql, (value,) * n).fetchone()[0] for sql, n in self.LOOKUP_USAGE.get(kind, []))

    def ref_usage(self, table: str, ref_id: str) -> int:
        col = {"entities": "entity_id", "divisions": "division_id"}[table]
        with self.db.connect() as con:
            return con.execute(f"SELECT COUNT(*) FROM projects WHERE {col} = ?", (ref_id,)).fetchone()[0]

    def upsert_ref(self, table: str, ref_id: str, code: str, name: str) -> None:
        assert table in ("entities", "divisions")
        with self.db.connect() as con:
            if con.execute(f"SELECT 1 FROM {table} WHERE id = ?", (ref_id,)).fetchone():
                con.execute(f"UPDATE {table} SET code = ?, name = ? WHERE id = ?", (code, name, ref_id))
            else:
                order = con.execute(f"SELECT COALESCE(MAX(sort_order), -1) + 1 FROM {table}").fetchone()[0]
                con.execute(f"INSERT INTO {table} (id, code, name, sort_order) VALUES (?,?,?,?)", (ref_id, code, name, order))

    def delete_ref(self, table: str, ref_id: str) -> bool:
        assert table in ("entities", "divisions")
        with self.db.connect() as con:
            return con.execute(f"DELETE FROM {table} WHERE id = ?", (ref_id,)).rowcount > 0

    def update_milestone_def(self, key: str, label: str, short_label: str) -> bool:
        with self.db.connect() as con:
            return con.execute("UPDATE milestone_defs SET label = ?, short_label = ? WHERE key = ?",
                               (label, short_label, key)).rowcount > 0

    def upsert_lookup(self, kind: str, value: str, label: str, tone: str, extra: dict) -> None:
        with self.db.connect() as con:
            if extra.get("is_default"):
                for r in con.execute("SELECT value, extra_json FROM lookups WHERE kind = ?", (kind,)).fetchall():
                    e = json.loads(r["extra_json"])
                    e.pop("is_default", None)
                    con.execute("UPDATE lookups SET extra_json = ? WHERE kind = ? AND value = ?",
                                (json.dumps(e), kind, r["value"]))
            if con.execute("SELECT 1 FROM lookups WHERE kind = ? AND value = ?", (kind, value)).fetchone():
                con.execute("UPDATE lookups SET label = ?, tone = ?, extra_json = ? WHERE kind = ? AND value = ?",
                            (label, tone, json.dumps(extra), kind, value))
            else:
                order = con.execute("SELECT COALESCE(MAX(sort_order), -1) + 1 FROM lookups WHERE kind = ?",
                                    (kind,)).fetchone()[0]
                con.execute("INSERT INTO lookups (kind, value, label, tone, sort_order, extra_json) VALUES (?,?,?,?,?,?)",
                            (kind, value, label, tone, order, json.dumps(extra)))

    def delete_lookup(self, kind: str, value: str) -> bool:
        with self.db.connect() as con:
            return con.execute("DELETE FROM lookups WHERE kind = ? AND value = ?", (kind, value)).rowcount > 0

    def update_import_field(self, key: str, label: str, aliases: List[str]) -> bool:
        with self.db.connect() as con:
            return con.execute("UPDATE import_fields SET label = ?, aliases_json = ? WHERE key = ?",
                               (label, json.dumps(aliases), key)).rowcount > 0


store = Store(Database(settings.database_path))
