"""Pydantic v2 request/response schemas.

The typed contract between the FastAPI backend and the Next.js client, mirrored
in ``frontend/lib/types.ts``. Every compute request carries the canonical
dataset (built from the user's uploaded CSVs), so the backend is stateless.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

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


class Aggregate(str, Enum):
    none = "none"
    weekly = "weekly"
    monthly = "monthly"


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
# Canonical dataset (mirrors core.dataset output)
# --------------------------------------------------------------------------
class DatasetMeta(BaseModel):
    name: str
    is_sample: bool = False
    n_periods: int = 0
    n_suppliers: int = 0
    n_warehouses: int = 0
    n_orders: int = 0
    has_scenario_data: bool = False
    warnings: List[str] = Field(default_factory=list)


class SalesRow(BaseModel):
    period: int
    label: str
    sales: float


class SupplierRow(BaseModel):
    supplier: str
    lead_time_days: int
    capacity_t: float
    price_per_t: float
    lead_time_days_normal: Optional[int] = None
    lead_time_days_disrupted: Optional[int] = None


class InventoryRow(BaseModel):
    warehouse: str
    current_stock_t: float
    storage_capacity_t: float
    replenishment_rate_t: float


class ExternalRow(BaseModel):
    period: int
    seasonality_index: float
    promotion: float
    market_trend: float


class OrderRow(BaseModel):
    order_id: str
    period: int
    size_t: float
    location: str


class HistoryRow(BaseModel):
    period: int
    source: str
    destination: str
    volume_t: float
    cost: float


class MaterialRefRow(BaseModel):
    material: str
    mass_share: float
    value_per_t_usd: float
    value_per_t_normal: Optional[float] = None
    value_per_t_disrupted: Optional[float] = None


class TransportCosts(BaseModel):
    sources: List[str]
    destinations: List[str]
    matrix: List[List[Optional[float]]]
    matrix_normal: Optional[List[List[Optional[float]]]] = None
    matrix_disrupted: Optional[List[List[Optional[float]]]] = None
    hormuz_routes: List[List[int]] = Field(default_factory=list)


class Dataset(BaseModel):
    meta: DatasetMeta
    sales: List[SalesRow]
    suppliers: List[SupplierRow]
    inventory: List[InventoryRow]
    external: List[ExternalRow]
    orders: List[OrderRow]
    transport_costs: TransportCosts
    transport_history: List[HistoryRow]
    warehouse_params: Dict[str, float]
    materials: List[MaterialRefRow] = Field(default_factory=list)

    def as_dict(self) -> dict:
        return self.model_dump()


class ValidationResponse(BaseModel):
    ok: bool
    dataset: Optional[Dataset] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Forecasting — demand
# --------------------------------------------------------------------------
class ForecastRequest(BaseModel):
    dataset: Dataset
    scenario: ScenarioName = ScenarioName.normal
    alpha: float = Field(0.5, gt=0.0, le=1.0)
    beta: float = Field(0.3, ge=0.0, le=1.0)
    horizon: int = Field(6, ge=1, le=24)
    auto_tune: bool = False
    aggregate: Aggregate = Aggregate.none


class MetricsModel(BaseModel):
    MAD: float
    MSE: float
    MAPE: float
    Bias: float


class SeriesModel(BaseModel):
    name: str
    fitted: List[float]
    metrics: Optional[MetricsModel] = None


class TuningModel(BaseModel):
    alpha: float
    beta: float
    train_mad: float
    validation_mad: float
    holdout: int
    grid_size: int


class ValidationModel(BaseModel):
    holdout: int
    train_size: int
    predictions: List[float]
    actuals: List[float]
    mad: float
    mape: float


class ForecastResponse(BaseModel):
    scenario: ScenarioInfo
    months: List[str]
    actual: List[float]
    adjusted_es: SeriesModel
    linear_trend: SeriesModel
    seasonal: SeriesModel
    seasonal_factors: List[float]
    forecast_horizon: List[float]
    forecast_labels: List[str] = Field(default_factory=list)
    next_forecast: float
    planning_demand_next: float
    recovered_demand_multiplier: float
    external_factor: float
    alpha: float
    beta: float
    auto_tuned: bool
    tuning: Optional[TuningModel] = None
    validation: ValidationModel


# --------------------------------------------------------------------------
# Forecasting — suppliers
# --------------------------------------------------------------------------
class SupplierRequest(BaseModel):
    dataset: Dataset
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
    dataset: Dataset
    scenario: ScenarioName = ScenarioName.normal
    initial: InitialMethod = InitialMethod.vogel
    optimize: OptimalityMethod = OptimalityMethod.modi
    cost: Optional[List[List[float]]] = None
    supply: Optional[List[float]] = None
    demand: Optional[List[float]] = None
    row_labels: Optional[List[str]] = None
    col_labels: Optional[List[str]] = None

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


class InitialCostRow(BaseModel):
    initial: str
    cost: float


class TransportResponse(BaseModel):
    scenario: ScenarioInfo
    method: str
    allocation: List[List[float]]
    initial_allocation: List[List[float]]
    cost_matrix: List[List[float]]
    total_cost: float
    initial_cost: float
    supply: List[float]
    demand: List[float]
    balanced: bool
    balancing_added: str
    row_labels: List[str]
    col_labels: List[str]
    comparison: List[TransportComparisonRow]
    initial_costs: List[InitialCostRow]
    all_methods_agree: bool


# --------------------------------------------------------------------------
# Warehouse
# --------------------------------------------------------------------------
class WarehouseRequest(BaseModel):
    dataset: Dataset
    scenario: ScenarioName = ScenarioName.normal
    alpha: float = Field(0.4, gt=0.0, le=1.0)
    beta: float = Field(0.3, ge=0.0, le=1.0)
    service_level: Optional[float] = Field(None, gt=0.5, lt=1.0)


class HubPolicy(BaseModel):
    hub: str
    current_stock: float
    safety_stock: float
    reorder_point: float
    eoq: float
    suggested_order: float
    status: str
    storage_capacity: Optional[float] = None
    utilization: Optional[float] = None


class WarehouseResponse(BaseModel):
    scenario: ScenarioInfo
    policies: List[HubPolicy]
    forecast_demand: float
    avg_lead_time_days: float
    service_level: float
    ordering_cost: float
    holding_cost_per_unit: float
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


class MaterialsRequest(BaseModel):
    dataset: Dataset
    scenario: ScenarioName = ScenarioName.normal


class MaterialsResponse(BaseModel):
    scenario: ScenarioInfo
    processed_t: float
    materials: List[MaterialRecovery]
    total_value_usd: float
    enabled: bool


# --------------------------------------------------------------------------
# Reference data view
# --------------------------------------------------------------------------
class DataRequest(BaseModel):
    dataset: Dataset
    scenario: ScenarioName = ScenarioName.normal


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
    meta: DatasetMeta
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
# Simulate
# --------------------------------------------------------------------------
class SimulateRequest(BaseModel):
    dataset: Dataset
    scenario: ScenarioName = ScenarioName.normal
    alpha: float = Field(0.4, gt=0.0, le=1.0)
    beta: float = Field(0.3, ge=0.0, le=1.0)
    horizon: int = Field(6, ge=1, le=24)
    service_level: Optional[float] = Field(None, gt=0.5, lt=1.0)
    auto_tune: bool = False


class KpiSet(BaseModel):
    next_month_demand: float
    optimal_transport_cost: float
    avg_supplier_utilization: float
    recovered_material_value: float
    hubs_needing_reorder: int
    total_available_t: float
    total_demand_t: float
    balanced: bool


class MethodologyItem(BaseModel):
    element: str
    technique: str
    result: str


class SimulateResponse(BaseModel):
    scenario: ScenarioInfo
    kpis: KpiSet
    insights: List[str] = Field(default_factory=list)
    methodology: List[MethodologyItem] = Field(default_factory=list)
    months: List[str]
    actual: List[float]
    forecast_fitted: List[float]
    forecast_horizon: List[float]
    forecast_labels: List[str] = Field(default_factory=list)


class ScenarioComparison(BaseModel):
    normal: KpiSet
    hormuz_disruption: KpiSet


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------
class ReportRequest(BaseModel):
    dataset: Dataset
    scenario: ScenarioName = ScenarioName.normal
    alpha: float = Field(0.5, gt=0.0, le=1.0)
    beta: float = Field(0.3, ge=0.0, le=1.0)
    horizon: int = Field(6, ge=1, le=24)
    service_level: Optional[float] = Field(None, gt=0.5, lt=1.0)
    auto_tune: bool = True


# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------
class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
