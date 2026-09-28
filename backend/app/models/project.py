"""
Project aggregate (README §50) and its identity lookups (Entity, Division).
Calculated fields are derived on every read by services/calc.py and are
never trusted from the client.
"""
from __future__ import annotations
from typing import Optional, List

from pydantic import BaseModel, Field

from app.models.cost import ProjectResources
from app.models.milestone import Milestone
from app.models.issue import Issue
from app.models.risk import Risk
from app.models.document import ProjectDocument, PlannedActivities


class Entity(BaseModel):
    id: str
    code: str
    name: str


class Division(BaseModel):
    id: str
    code: str
    name: str


class ProjectIdentity(BaseModel):
    name: str
    entity_id: str
    division_id: str
    description: str = ""
    project_manager: str = ""
    manager_user_id: Optional[str] = None   # user account that manages the project (edit rights)
    status: Optional[str] = None         # lookup default applied on create
    completion_pct: float = 0.0          # system-calculated
    status_update: str = ""
    weight_pct: Optional[float] = None   # stored as imported; unused until README §53.1 is settled
    executive_sponsor: str = ""            # shown on the status report
    delivery_organisation: str = ""        # delivery team / vendor, shown on the report cover


class ProjectSchedule(BaseModel):
    start_date: Optional[str] = None
    original_baseline: Optional[str] = None
    tsc_approved_date: Optional[str] = None
    planned_delivery: Optional[str] = None
    forecast_delivery: Optional[str] = None
    actual_delivery: Optional[str] = None
    variance_days: Optional[int] = None   # system-calculated


class ProjectRag(BaseModel):
    """Entered manually by the user (README §14). Defaults come from the rag lookup."""
    schedule: Optional[str] = None
    budget: Optional[str] = None
    issues: Optional[str] = None
    # Commentary next to each RAG in the report's Executive Summary table.
    schedule_comment: str = ""
    budget_comment: str = ""
    issues_comment: str = ""


class Project(BaseModel):
    id: str = ""                          # system-generated on create
    identity: ProjectIdentity
    schedule: ProjectSchedule = Field(default_factory=ProjectSchedule)
    resources: ProjectResources = Field(default_factory=ProjectResources)
    rag: ProjectRag = Field(default_factory=ProjectRag)
    milestones: List[Milestone] = Field(default_factory=list)
    issues: List[Issue] = Field(default_factory=list)
    risks: List[Risk] = Field(default_factory=list)
    planned_activities: PlannedActivities = Field(default_factory=PlannedActivities)
    executive_summary: str = ""
    documents: List[ProjectDocument] = Field(default_factory=list)
    is_draft: bool = False
    created_at: str = ""
    updated_at: str = ""
