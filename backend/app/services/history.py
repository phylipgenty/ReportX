"""
History primitives shared by the store and the import pipeline.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any

MILESTONE_TRACKED = ("status", "baseline_date", "expected_date", "actual_date", "note")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def milestone_change(
    old: Dict[str, Any], new: Dict[str, Any]
) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """(from_state, to_state) when a tracked milestone field changed, else None."""
    old_state = {k: old.get(k) for k in MILESTONE_TRACKED}
    new_state = {k: new.get(k) for k in MILESTONE_TRACKED}
    return None if old_state == new_state else (old_state, new_state)
