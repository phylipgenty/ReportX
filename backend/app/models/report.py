"""
Bootstrap envelope, saved project states, and the assembled Project Status
Report (README §31–§39).
"""
from __future__ import annotations
from typing import Optional, List, Dict

from pydantic import BaseModel, ConfigDict, Field

from app.models.project import Entity, Division, Project, ProjectRag
from app.models.milestone import MilestoneDefinition
from app.models.issue import Issue
from app.models.risk import Risk
from app.models.document import PlannedActivities
from app.models.cost import CostAssumptions


# ---------------------------------------------------------------------------
# Bootstrap (fetched once by the frontend)
# ---------------------------------------------------------------------------
class LookupOption(BaseModel):
    """One option of a lookup list. Extra keys (range, description,
    counts_complete...) pass through untouched."""
    model_config = ConfigDict(extra="allow")
    value: str
    label: str
    tone: str = "neutral"


class ImportField(BaseModel):
    key: str
    label: str
    aliases: List[str] = Field(default_factory=list)


class AppInfo(BaseModel):
    name: str
    organisation: str
    currency: str
    currency_symbol: str


class LastImport(BaseModel):
    filename: str
    date: str
    by: str


class BootstrapPayload(BaseModel):
    app: AppInfo
    entities: List[Entity]
    divisions: List[Division]
    milestone_definitions: List[MilestoneDefinition]
    lookups: Dict[str, List[LookupOption]]
    cost_assumptions: CostAssumptions
    import_fields: List[ImportField]
    last_import: Optional[LastImport] = None


# ---------------------------------------------------------------------------
# Saved states (README §39)
# ---------------------------------------------------------------------------
class SaveStateRequest(BaseModel):
    label: str = ""


class ProjectStateSummary(BaseModel):
    id: str
    project_id: str
    label: str
    saved_at: str
    saved_by: str


class ProjectState(ProjectStateSummary):
    snapshot: Project


# ---------------------------------------------------------------------------
# Report (README §31–§38)
# ---------------------------------------------------------------------------
class ReportRequest(BaseModel):
    start_date: str
    end_date: str
    state_id: Optional[str] = None        # explicit saved state
    use_current: bool = False             # force the live project state
    report_author: Optional[str] = None
    executive_sponsor: Optional[str] = None


class ReportingPeriod(BaseModel):
    start_date: str
    end_date: str


class ReportSource(BaseModel):
    kind: str                             # "state" | "current"
    state_id: Optional[str] = None
    label: str = ""
    saved_at: Optional[str] = None


class ReportMetadata(BaseModel):
    project_id: str
    project_title: str
    reporting_period: ReportingPeriod
    date_of_report: str
    delivery_manager: str = ""
    report_author: str = ""
    executive_sponsor: Optional[str] = None
    delivery_organisation: str = ""       # report cover line (the April 2025 report shows the delivery team)
    source: ReportSource


class MilestoneReviewRow(BaseModel):
    key: str
    label: str
    status: str
    baseline_date: Optional[str] = None
    expected_date: Optional[str] = None
    actual_date: Optional[str] = None
    has_issues: bool = False


class ProjectStatusReport(BaseModel):
    metadata: ReportMetadata
    executive_summary: str = ""
    narrative: str = ""
    rag: ProjectRag
    completion_pct: float = 0.0
    variance_days: Optional[int] = None
    milestone_status_review: List[MilestoneReviewRow] = Field(default_factory=list)
    planned_activities: PlannedActivities = Field(default_factory=PlannedActivities)
    issues: List[Issue] = Field(default_factory=list)
    risks: List[Risk] = Field(default_factory=list)
