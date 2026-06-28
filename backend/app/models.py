"""Pydantic v2 request/response schemas for every endpoint.

These models are the single typed contract between the FastAPI backend and the
Next.js client (mirrored in ``frontend/lib/types.ts``). Validation lives here:
parameter ranges, non-negativity, and matrix-shape consistency.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# --------------------------------------------------------------------------
# Shared enums
# --------------------------------------------------------------------------
class ScenarioName(str, Enum):
    normal = "normal"
    hormuz_disruption = "hormuz_disruption"


class InitialMethod(str, Enum):
    nwc = "nwc"
    least_cost = "least_cost"
    vogel = "vogel"


class OptimalityMethod(str, Enum):
    modi = "modi"
    stepping_stone = "stepping_stone"


# --------------------------------------------------------------------------
# Health / metadata
# --------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str = "ok"
    app_env: str
    version: str


class ScenarioInfo(BaseModel):
    name: str
    label: str
    is_disrupted: bool
    lead_time_add_days: int
    transport_cost_multiplier: float
    insurance_surcharge_per_t: float
    disabled_routes: List[List[int]]
    recovered_demand_multiplier: float


# --------------------------------------------------------------------------
# Reference data
# --------------------------------------------------------------------------
class CenterModel(BaseModel):
    center: str
    lead_time_days: int
    monthly_capacity_t: int
    gate_fee_per_t: int


class HubModel(BaseModel):
    hub: str
    processing_demand_t: float
    recovery_yield: float


class MaterialModel(BaseModel):
    material: str
    mass_share: float
    value_per_t_usd: float


class DemandPoint(BaseModel):
    date: str
    month: str
    returned_units: int


class DataResponse(BaseModel):
    scenario: ScenarioInfo
    demand: List[DemandPoint]
    centers: List[CenterModel]
    hubs: List[HubModel]
    materials: List[MaterialModel]
    transport_costs: List[List[float]]
    transport_supply: List[float]
    transport_demand: List[float]
    center_names: List[str]
    hub_names: List[str]


# --------------------------------------------------------------------------
# Forecasting — demand
# --------------------------------------------------------------------------
class ForecastRequest(BaseModel):
    scenario: ScenarioName = ScenarioName.normal
    alpha: float = Field(0.5, gt=0.0, le=1.0, description="Smoothing constant (0,1].")
    beta: float = Field(0.3, ge=0.0, le=1.0, description="Trend smoothing [0,1].")
    horizon: int = Field(3, ge=1, le=24, description="Periods to forecast ahead.")


class MetricsModel(BaseModel):
    MAD: float
    MSE: float
    MAPE: float
    Bias: float


class SeriesModel(BaseModel):
    name: str
    fitted: List[float]
    metrics: Optional[MetricsModel] = None


class ForecastResponse(BaseModel):
    scenario: ScenarioInfo
    months: List[str]
    actual: List[float]
    adjusted_es: SeriesModel
    linear_trend: SeriesModel
    seasonal: SeriesModel
    seasonal_factors: List[float]
    forecast_horizon: List[float]
    next_forecast: float
    planning_demand_next: float
    recovered_demand_multiplier: float


# --------------------------------------------------------------------------
# Forecasting — suppliers
# --------------------------------------------------------------------------
class SupplierRequest(BaseModel):
    scenario: ScenarioName = ScenarioName.normal
    alpha: float = Field(0.4, gt=0.0, le=1.0)
    beta: float = Field(0.3, ge=0.0, le=1.0)
    horizon: int = Field(3, ge=1, le=24)


class SupplierAvailability(BaseModel):
    center: str
    lead_time_days: int
    monthly_capacity_t: int
    gate_fee_per_t: int
    forecast_next_t: float
    available_t: float
    capacity_utilization: float
    horizon_forecast: List[float]


class SupplierResponse(BaseModel):
    scenario: ScenarioInfo
    suppliers: List[SupplierAvailability]
    total_available_t: float
    avg_capacity_utilization: float
    lead_time_add_days: int


# --------------------------------------------------------------------------
# Transportation
# --------------------------------------------------------------------------
class TransportRequest(BaseModel):
    scenario: ScenarioName = ScenarioName.normal
    initial: InitialMethod = InitialMethod.vogel
    optimize: OptimalityMethod = OptimalityMethod.modi
    cost: Optional[List[List[float]]] = Field(
        None, description="Custom unit-cost matrix (centers x hubs)."
    )
    supply: Optional[List[float]] = Field(None, description="Custom supply per source.")
    demand: Optional[List[float]] = Field(
        None, description="Custom demand per destination."
    )

    @model_validator(mode="after")
    def _check_shapes(self) -> "TransportRequest":
        if self.cost is not None:
            if len(self.cost) == 0 or any(len(r) == 0 for r in self.cost):
                raise ValueError("cost matrix must be non-empty")
            width = len(self.cost[0])
            if any(len(r) != width for r in self.cost):
                raise ValueError("cost matrix rows must all have the same length")
            if any(v < 0 for row in self.cost for v in row):
                raise ValueError("cost values must be non-negative")
            if self.supply is not None and len(self.supply) != len(self.cost):
                raise ValueError("supply length must match number of cost rows")
            if self.demand is not None and len(self.demand) != width:
                raise ValueError("demand length must match number of cost columns")
        if self.supply is not None and any(v < 0 for v in self.supply):
            raise ValueError("supply values must be non-negative")
        if self.demand is not None and any(v < 0 for v in self.demand):
            raise ValueError("demand values must be non-negative")
        return self


class TransportComparisonRow(BaseModel):
    initial: str
    optimize: str
    total_cost: float


class TransportResponse(BaseModel):
    scenario: ScenarioInfo
    method: str
    allocation: List[List[float]]
    cost_matrix: List[List[float]]
    total_cost: float
    supply: List[float]
    demand: List[float]
    balanced: bool
    dummy_added: str
    row_labels: List[str]
    col_labels: List[str]
    comparison: List[TransportComparisonRow]
    all_methods_agree: bool


# --------------------------------------------------------------------------
# Warehouse
# --------------------------------------------------------------------------
class WarehouseRequest(BaseModel):
    scenario: ScenarioName = ScenarioName.normal
    alpha: float = Field(0.4, gt=0.0, le=1.0)
    beta: float = Field(0.3, ge=0.0, le=1.0)
    service_level: float = Field(0.95, gt=0.5, lt=1.0)


class HubPolicy(BaseModel):
    hub: str
    current_stock: float
    safety_stock: float
    reorder_point: float
    eoq: float
    suggested_order: float
    status: str


class WarehouseResponse(BaseModel):
    scenario: ScenarioInfo
    policies: List[HubPolicy]
    forecast_demand: float
    avg_lead_time_days: float
    service_level: float
    hubs_needing_reorder: int


# --------------------------------------------------------------------------
# Materials recovery
# --------------------------------------------------------------------------
class MaterialRecovery(BaseModel):
    material: str
    mass_share: float
    recovered_t: float
    value_per_t_usd: float
    value_usd: float


class MaterialsResponse(BaseModel):
    scenario: ScenarioInfo
    processed_t: float
    materials: List[MaterialRecovery]
    total_value_usd: float


# --------------------------------------------------------------------------
# Simulate (full twin payload powering the overview)
# --------------------------------------------------------------------------
class SimulateRequest(BaseModel):
    scenario: ScenarioName = ScenarioName.normal
    alpha: float = Field(0.4, gt=0.0, le=1.0)
    beta: float = Field(0.3, ge=0.0, le=1.0)
    horizon: int = Field(3, ge=1, le=24)
    service_level: float = Field(0.95, gt=0.5, lt=1.0)


class KpiSet(BaseModel):
    next_month_demand: float
    optimal_transport_cost: float
    avg_supplier_utilization: float
    recovered_material_value: float
    hubs_needing_reorder: int
    total_available_t: float
    total_demand_t: float
    balanced: bool


class SimulateResponse(BaseModel):
    scenario: ScenarioInfo
    kpis: KpiSet
    months: List[str]
    actual: List[float]
    forecast_fitted: List[float]
    forecast_horizon: List[float]


class ScenarioComparison(BaseModel):
    normal: KpiSet
    hormuz_disruption: KpiSet


# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------
class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
