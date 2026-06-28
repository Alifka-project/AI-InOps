"""Full-twin simulation and scenario-comparison endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from .. import service
from ..models import (
    ScenarioComparison,
    SimulateRequest,
    SimulateResponse,
)

router = APIRouter(prefix="/api", tags=["simulate"])


@router.post("/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest) -> SimulateResponse:
    return SimulateResponse(
        **service.simulate(
            req.dataset.as_dict(),
            req.scenario.value,
            req.alpha,
            req.beta,
            req.horizon,
            req.service_level,
            auto_tune=req.auto_tune,
        )
    )


@router.post("/simulate/compare", response_model=ScenarioComparison)
def compare(req: SimulateRequest) -> ScenarioComparison:
    return ScenarioComparison(
        **service.compare_scenarios(
            req.dataset.as_dict(),
            req.alpha,
            req.beta,
            req.horizon,
            req.service_level,
        )
    )
