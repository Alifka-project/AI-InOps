"""Reference-data, materials, and scenario-metadata endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from .. import service
from ..models import (
    DataResponse,
    MaterialsResponse,
    ScenarioInfo,
    ScenarioName,
)
from ..scenarios import all_descriptions

router = APIRouter(prefix="/api", tags=["data"])


@router.get("/data", response_model=DataResponse)
def get_data(scenario: ScenarioName = ScenarioName.normal) -> DataResponse:
    return DataResponse(**service.get_data(scenario.value))


@router.get("/materials/recovery", response_model=MaterialsResponse)
def materials_recovery(
    scenario: ScenarioName = ScenarioName.normal,
) -> MaterialsResponse:
    return MaterialsResponse(**service.materials_recovery(scenario.value))


@router.get("/scenarios", response_model=list[ScenarioInfo])
def list_scenarios() -> list[ScenarioInfo]:
    return [ScenarioInfo(**d) for d in all_descriptions()]
