"""
Milestone model and milestone history entries (README §10–§13).
Dates hold an ISO date, a placeholder from the `date_placeholder` lookup
(TBD / N/A), or null.
"""
from __future__ import annotations
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class MilestoneDefinition(BaseModel):
    key: str
    label: str
    short_label: str
    order: int
    weight: Optional[float] = None


class MilestoneHistoryEntry(BaseModel):
    changed_at: str
    changed_by: str
    from_state: Dict[str, Any]
    to_state: Dict[str, Any]
    note: str = ""


class Milestone(BaseModel):
    key: str
    status: Optional[str] = None          # lookup default applied on create
    baseline_date: Optional[str] = None
    expected_date: Optional[str] = None
    actual_date: Optional[str] = None
    note: str = ""
    history: List[MilestoneHistoryEntry] = Field(default_factory=list)
