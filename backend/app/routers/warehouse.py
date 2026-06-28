"""Warehouse inventory-policy endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from .. import service
from ..models import WarehouseRequest, WarehouseResponse

router = APIRouter(prefix="/api/warehouse", tags=["warehouse"])


@router.post("/policy", response_model=WarehouseResponse)
def warehouse_policy(req: WarehouseRequest) -> WarehouseResponse:
    return WarehouseResponse(
        **service.warehouse_policy(
            req.scenario.value, req.alpha, req.beta, req.service_level
        )
    )
