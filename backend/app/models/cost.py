"""
Resource + cost models, and the administrative CostAssumptions type.
"""
from pydantic import BaseModel


class ProjectResources(BaseModel):
    junior_days: float = 0
    intermediate_days: float = 0
    expert_days: float = 0
    other_planned_costs: float = 0
    actual_cost_to_date: float = 0

    # System-calculated
    resource_cost: float = 0
    contingency: float = 0
    planned_budget: float = 0


class CostAssumptions(BaseModel):
    junior_rate: float
    intermediate_rate: float
    expert_rate: float
    contingency_pct: float
    currency: str
    currency_symbol: str


class CostAssumptionRow(BaseModel):
    """One row of the 'Planned resource cost by project' table."""
    project_id: str
    project_name: str
    junior_days: float
    intermediate_days: float
    expert_days: float
    resource_cost: float
    contingency: float
    planned_cost: float