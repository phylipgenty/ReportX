from typing import List

from fastapi import APIRouter, Depends, Request

from app.services.store import store
from app.services import auth, domain
from app.models.cost import CostAssumptions, CostAssumptionRow

router = APIRouter(tags=["costs"])


@router.get("/cost-assumptions", response_model=CostAssumptions)
def get_assumptions() -> CostAssumptions:
    return domain.rates()


@router.put("/cost-assumptions", response_model=CostAssumptions, dependencies=[Depends(auth.require("costs"))])
def update_assumptions(payload: CostAssumptions, request: Request) -> CostAssumptions:
    # README §17: restricted to Admin/PMO (the "costs" permission).
    values = payload.model_dump(include={"junior_rate", "intermediate_rate", "expert_rate", "contingency_pct"})
    domain.raise_if([f"{k} cannot be negative" for k, v in values.items() if v < 0])
    store.set_cost_assumptions(values, actor=domain.actor(request))
    return domain.rates()


@router.get("/cost-assumptions/by-project", response_model=List[CostAssumptionRow])
def by_project() -> List[CostAssumptionRow]:
    rows: List[CostAssumptionRow] = []
    for raw in store.list_projects():
        p = domain.hydrate(raw)
        res = p.resources
        rows.append(CostAssumptionRow(
            project_id=p.id,
            project_name=p.identity.name,
            junior_days=res.junior_days,
            intermediate_days=res.intermediate_days,
            expert_days=res.expert_days,
            resource_cost=res.resource_cost,
            contingency=res.contingency,
            planned_cost=res.planned_budget,
        ))
    return rows
