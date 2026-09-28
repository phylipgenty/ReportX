"""
Document attachments (README §25–§27) and the PlannedActivities block (§23).
"""
from __future__ import annotations
from typing import Optional, List

from pydantic import BaseModel, Field


class ProjectDocument(BaseModel):
    id: str
    milestone_key: Optional[str] = None
    filename: str
    mime_type: str
    size_bytes: int
    uploaded_at: str
    uploaded_by: str
    url: str
    replaces: Optional[str] = None        # id of the attachment this one replaced


class PlannedActivities(BaseModel):
    accomplishments: List[str] = Field(default_factory=list)
    not_accomplished: List[str] = Field(default_factory=list)
    next_period: List[str] = Field(default_factory=list)
