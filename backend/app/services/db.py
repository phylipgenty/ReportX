"""
SQLite connection + schema. Structured tables per README §49–§50: the project
is stored as identity/schedule/resources/rag columns plus child tables, never
as one report document. Calculated values (completion, variance, costs, risk
score) are not stored — services/calc.py derives them on every read.
"""
from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Reference data (seeded from app/seed/*.json into empty tables) ----------
CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY, code TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS divisions (
    id TEXT PRIMARY KEY, code TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS milestone_defs (
    key TEXT PRIMARY KEY, label TEXT NOT NULL, short_label TEXT NOT NULL,
    sort_order INTEGER NOT NULL, weight REAL
);
CREATE TABLE IF NOT EXISTS lookups (
    kind TEXT NOT NULL, value TEXT NOT NULL, label TEXT NOT NULL,
    tone TEXT NOT NULL DEFAULT 'neutral', sort_order INTEGER NOT NULL DEFAULT 0,
    extra_json TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (kind, value)
);
CREATE TABLE IF NOT EXISTS import_fields (
    key TEXT PRIMARY KEY, label TEXT NOT NULL, aliases_json TEXT NOT NULL DEFAULT '[]',
    sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS cost_assumptions (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    junior_rate REAL NOT NULL, intermediate_rate REAL NOT NULL,
    expert_rate REAL NOT NULL, contingency_pct REAL NOT NULL,
    updated_at TEXT NOT NULL, updated_by TEXT NOT NULL
);

-- Projects ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    seq INTEGER NOT NULL UNIQUE,
    name TEXT NOT NULL,
    entity_id TEXT NOT NULL REFERENCES entities(id),
    division_id TEXT NOT NULL REFERENCES divisions(id),
    description TEXT NOT NULL DEFAULT '',
    project_manager TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    status_update TEXT NOT NULL DEFAULT '',
    weight_pct REAL,
    start_date TEXT, original_baseline TEXT, tsc_approved_date TEXT,
    planned_delivery TEXT, forecast_delivery TEXT, actual_delivery TEXT,
    junior_days REAL NOT NULL DEFAULT 0,
    intermediate_days REAL NOT NULL DEFAULT 0,
    expert_days REAL NOT NULL DEFAULT 0,
    other_planned_costs REAL NOT NULL DEFAULT 0,
    actual_cost_to_date REAL NOT NULL DEFAULT 0,
    manager_user_id TEXT REFERENCES users(id),
    executive_sponsor TEXT NOT NULL DEFAULT '',
    delivery_organisation TEXT NOT NULL DEFAULT '',
    rag_schedule TEXT NOT NULL, rag_budget TEXT NOT NULL, rag_issues TEXT NOT NULL,
    rag_schedule_comment TEXT NOT NULL DEFAULT '',
    rag_budget_comment TEXT NOT NULL DEFAULT '',
    rag_issues_comment TEXT NOT NULL DEFAULT '',
    executive_summary TEXT NOT NULL DEFAULT '',
    is_draft INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS milestones (
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    key TEXT NOT NULL REFERENCES milestone_defs(key),
    status TEXT NOT NULL,
    baseline_date TEXT, expected_date TEXT, actual_date TEXT,
    note TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (project_id, key)
);

CREATE TABLE IF NOT EXISTS milestone_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    key TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    changed_by TEXT NOT NULL,
    from_json TEXT NOT NULL,
    to_json TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS issues (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    priority TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    impact_summary TEXT NOT NULL DEFAULT '',
    impact_areas_json TEXT NOT NULL DEFAULT '[]',
    action_steps TEXT NOT NULL DEFAULT '',
    milestone_key TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS risks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    priority TEXT NOT NULL,
    probability INTEGER NOT NULL,
    impact INTEGER NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    impact_summary TEXT NOT NULL DEFAULT '',
    response_strategy TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS planned_activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,          -- accomplishments | not_accomplished | next_period
    text TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    milestone_key TEXT,
    filename TEXT NOT NULL,
    stored_name TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    uploaded_at TEXT NOT NULL,
    uploaded_by TEXT NOT NULL,
    replaces TEXT REFERENCES documents(id),
    deleted INTEGER NOT NULL DEFAULT 0
);

-- Saved states: immutable snapshots of the assembled project (README §39)
CREATE TABLE IF NOT EXISTS project_states (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    label TEXT NOT NULL DEFAULT '',
    saved_at TEXT NOT NULL,
    saved_by TEXT NOT NULL,
    snapshot_json TEXT NOT NULL
);

-- Access control (README §43–§44) --------------------------------------
CREATE TABLE IF NOT EXISTS roles (
    key TEXT PRIMARY KEY, label TEXT NOT NULL,
    permissions_json TEXT NOT NULL DEFAULT '[]',
    sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    name TEXT NOT NULL,
    role TEXT NOT NULL REFERENCES roles(key),
    password_hash TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    must_change_password INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    last_login_at TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

-- Field-level change log for everything except milestones (which keep
-- milestone_history). project_id is NULL for global changes such as cost rates.
CREATE TABLE IF NOT EXISTS change_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT,
    area TEXT NOT NULL,          -- project | issue | risk | document | state | costs
    action TEXT NOT NULL,        -- created | updated | deleted | uploaded | replaced | saved
    item_id TEXT,
    item_label TEXT NOT NULL DEFAULT '',
    field TEXT,
    old_json TEXT,
    new_json TEXT,
    changed_at TEXT NOT NULL,
    changed_by TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'app'   -- app | import
);
CREATE INDEX IF NOT EXISTS ix_change_log_project ON change_log(project_id, changed_at);

CREATE INDEX IF NOT EXISTS ix_ms_hist_project ON milestone_history(project_id, key);
CREATE INDEX IF NOT EXISTS ix_states_project ON project_states(project_id, saved_at);
"""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    def init_schema(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            con.executescript(SCHEMA)
            self._migrate(con)

    @staticmethod
    def _migrate(con: sqlite3.Connection) -> None:
        """Additive column migrations for databases created by earlier versions."""
        def columns(table: str) -> set:
            return {r["name"] for r in con.execute(f"PRAGMA table_info({table})")}

        existing = columns("projects")
        for col, ddl in (
            ("manager_user_id", "TEXT REFERENCES users(id)"),
            ("executive_sponsor", "TEXT NOT NULL DEFAULT ''"),
            ("delivery_organisation", "TEXT NOT NULL DEFAULT ''"),
            ("rag_schedule_comment", "TEXT NOT NULL DEFAULT ''"),
            ("rag_budget_comment", "TEXT NOT NULL DEFAULT ''"),
            ("rag_issues_comment", "TEXT NOT NULL DEFAULT ''"),
        ):
            if col not in existing:
                con.execute(f"ALTER TABLE projects ADD COLUMN {col} {ddl}")

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """One connection per unit of work; commits on success, rolls back on error."""
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()
