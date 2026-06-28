"""Transportation optimisation endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from .. import service
from ..models import TransportRequest, TransportResponse

router = APIRouter(prefix="/api/optimize", tags=["transport"])


@router.post("/transport", response_model=TransportResponse)
def optimize_transport(req: TransportRequest) -> TransportResponse:
    return TransportResponse(
        **service.optimize_transport(
            req.dataset.as_dict(),
            req.scenario.value,
            req.initial.value,
            req.optimize.value,
            cost=req.cost,
            supply=req.supply,
            demand=req.demand,
            row_labels=req.row_labels,
            col_labels=req.col_labels,
        )
    )
