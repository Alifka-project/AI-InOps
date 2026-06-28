"""Reference-data, materials, and scenario-metadata endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from .. import service
from ..models import (
    DataRequest,
    DataResponse,
    MaterialsRequest,
    MaterialsResponse,
    ScenarioInfo,
)
from ..scenarios import all_descriptions

router = APIRouter(prefix="/api", tags=["data"])


@router.post("/data", response_model=DataResponse)
def get_data(req: DataRequest) -> DataResponse:
    return DataResponse(**service.get_data(req.dataset.as_dict(), req.scenario.value))


@router.post("/materials/recovery", response_model=MaterialsResponse)
def materials_recovery(req: MaterialsRequest) -> MaterialsResponse:
    return MaterialsResponse(
        **service.materials_recovery(req.dataset.as_dict(), req.scenario.value)
    )


@router.get("/scenarios", response_model=list[ScenarioInfo])
def list_scenarios() -> list[ScenarioInfo]:
    return [ScenarioInfo(**d) for d in all_descriptions()]
