"""Demand and supplier forecasting endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from .. import service
from ..models import (
    ForecastRequest,
    ForecastResponse,
    SupplierRequest,
    SupplierResponse,
)

router = APIRouter(prefix="/api/forecast", tags=["forecast"])


@router.post("/demand", response_model=ForecastResponse)
def forecast_demand(req: ForecastRequest) -> ForecastResponse:
    return ForecastResponse(
        **service.forecast_demand(
            req.dataset.as_dict(),
            req.scenario.value,
            req.alpha,
            req.beta,
            req.horizon,
            auto_tune=req.auto_tune,
        )
    )


@router.post("/suppliers", response_model=SupplierResponse)
def forecast_suppliers(req: SupplierRequest) -> SupplierResponse:
    return SupplierResponse(
        **service.forecast_suppliers(
            req.dataset.as_dict(),
            req.scenario.value,
            req.alpha,
            req.beta,
            req.horizon,
        )
    )
