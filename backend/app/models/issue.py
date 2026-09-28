from typing import List, Optional

from pydantic import BaseModel, Field


class Issue(BaseModel):
    """README §18 / §36."""
    id: str = ""                          # system-generated on create
    priority: Optional[str] = None        # lookup default applied on create
    description: str = ""
    impact_summary: str = ""
    impact_areas: List[str] = Field(default_factory=list)
    action_steps: str = ""
    milestone_key: Optional[str] = None   # drives "issues exist" in the milestone review
