from typing import Optional

from pydantic import BaseModel


class Risk(BaseModel):
    """README §19. Probability/impact levels come from the lookup tables."""
    id: str = ""                          # system-generated on create
    priority: Optional[str] = None        # lookup defaults applied on create
    probability: Optional[int] = None
    impact: Optional[int] = None
    risk_score: int = 0                   # system-calculated: probability × impact
    description: str = ""
    impact_summary: str = ""
    response_strategy: str = ""
    status: Optional[str] = None
