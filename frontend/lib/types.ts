// Shared types mirroring the backend pydantic models (backend/app/models.py).

export type ScenarioName = "normal" | "hormuz_disruption";
export type InitialMethod = "nwc" | "least_cost" | "vogel";
export type OptimalityMethod = "modi" | "stepping_stone";

// --------------------------------------------------------------------------
// Canonical dataset (built from the user's uploaded CSVs)
// --------------------------------------------------------------------------
export interface DatasetMeta {
  name: string;
  is_sample: boolean;
  n_periods: number;
  n_suppliers: number;
  n_warehouses: number;
  n_orders: number;
  has_scenario_data: boolean;
  warnings: string[];
}

export interface SalesRow {
  period: number;
  label: string;
  sales: number;
}
export interface SupplierRow {
  supplier: string;
  lead_time_days: number;
  capacity_t: number;
  price_per_t: number;
  lead_time_days_normal?: number | null;
  lead_time_days_disrupted?: number | null;
}
export interface InventoryRow {
  warehouse: string;
  current_stock_t: number;
  storage_capacity_t: number;
  replenishment_rate_t: number;
}
export interface ExternalRow {
  period: number;
  seasonality_index: number;
  promotion: number;
  market_trend: number;
}
export interface OrderRow {
  order_id: string;
  period: number;
  size_t: number;
  location: string;
}
export interface HistoryRow {
  period: number;
  source: string;
  destination: string;
  volume_t: number;
  cost: number;
}
export interface MaterialRefRow {
  material: string;
  mass_share: number;
  value_per_t_usd: number;
  value_per_t_normal?: number | null;
  value_per_t_disrupted?: number | null;
}
export interface TransportCostsBlock {
  sources: string[];
  destinations: string[];
  matrix: (number | null)[][];
  matrix_normal?: (number | null)[][] | null;
  matrix_disrupted?: (number | null)[][] | null;
  hormuz_routes?: number[][];
}

export interface Dataset {
  meta: DatasetMeta;
  sales: SalesRow[];
  suppliers: SupplierRow[];
  inventory: InventoryRow[];
  external: ExternalRow[];
  orders: OrderRow[];
  transport_costs: TransportCostsBlock;
  transport_history: HistoryRow[];
  warehouse_params: Record<string, number>;
  materials: MaterialRefRow[];
}

export interface ValidationResponse {
  ok: boolean;
  dataset: Dataset | null;
  errors: string[];
  warnings: string[];
}

// The eight required input categories (+ optional materials).
export const INPUT_KINDS = [
  "sales",
  "suppliers",
  "transport_costs",
  "external",
  "inventory",
  "orders",
  "warehouse_params",
  "transport_history",
] as const;
export type InputKind = (typeof INPUT_KINDS)[number];

// --------------------------------------------------------------------------
// Scenario metadata
// --------------------------------------------------------------------------
export interface ScenarioInfo {
  name: ScenarioName;
  label: string;
  is_disrupted: boolean;
  lead_time_add_days: number;
  transport_cost_multiplier: number;
  insurance_surcharge_per_t: number;
  disabled_routes: number[][];
  recovered_demand_multiplier: number;
}

// --------------------------------------------------------------------------
// Forecasting
// --------------------------------------------------------------------------
export interface Metrics {
  MAD: number;
  MSE: number;
  MAPE: number;
  Bias: number;
}
export interface Series {
  name: string;
  fitted: number[];
  metrics: Metrics | null;
}
export interface Tuning {
  alpha: number;
  beta: number;
  train_mad: number;
  validation_mad: number;
  holdout: number;
  grid_size: number;
}
export interface Validation {
  holdout: number;
  train_size: number;
  predictions: number[];
  actuals: number[];
  mad: number;
  mape: number;
}
export interface ForecastResponse {
  scenario: ScenarioInfo;
  months: string[];
  actual: number[];
  adjusted_es: Series;
  linear_trend: Series;
  seasonal: Series;
  seasonal_factors: number[];
  forecast_horizon: number[];
  next_forecast: number;
  planning_demand_next: number;
  recovered_demand_multiplier: number;
  external_factor: number;
  alpha: number;
  beta: number;
  auto_tuned: boolean;
  tuning: Tuning | null;
  validation: Validation;
}

// --------------------------------------------------------------------------
// Suppliers
// --------------------------------------------------------------------------
export interface SupplierAvailability {
  center: string;
  lead_time_days: number;
  monthly_capacity_t: number;
  gate_fee_per_t: number;
  forecast_next_t: number;
  available_t: number;
  capacity_utilization: number;
  horizon_forecast: number[];
}
export interface SupplierResponse {
  scenario: ScenarioInfo;
  suppliers: SupplierAvailability[];
  total_available_t: number;
  avg_capacity_utilization: number;
  lead_time_add_days: number;
}

// --------------------------------------------------------------------------
// Transportation
// --------------------------------------------------------------------------
export interface TransportComparisonRow {
  initial: string;
  optimize: string;
  total_cost: number;
}
export interface TransportResponse {
  scenario: ScenarioInfo;
  method: string;
  allocation: number[][];
  cost_matrix: number[][];
  total_cost: number;
  supply: number[];
  demand: number[];
  balanced: boolean;
  dummy_added: string;
  row_labels: string[];
  col_labels: string[];
  comparison: TransportComparisonRow[];
  all_methods_agree: boolean;
}

// --------------------------------------------------------------------------
// Warehouse
// --------------------------------------------------------------------------
export interface HubPolicy {
  hub: string;
  current_stock: number;
  safety_stock: number;
  reorder_point: number;
  eoq: number;
  suggested_order: number;
  status: "OK" | "REORDER" | "CRITICAL";
  storage_capacity: number | null;
  utilization: number | null;
}
export interface WarehouseResponse {
  scenario: ScenarioInfo;
  policies: HubPolicy[];
  forecast_demand: number;
  avg_lead_time_days: number;
  service_level: number;
  ordering_cost: number;
  holding_cost_per_unit: number;
  hubs_needing_reorder: number;
}

// --------------------------------------------------------------------------
// Materials
// --------------------------------------------------------------------------
export interface MaterialRecovery {
  material: string;
  mass_share: number;
  recovered_t: number;
  value_per_t_usd: number;
  value_usd: number;
}
export interface MaterialsResponse {
  scenario: ScenarioInfo;
  processed_t: number;
  materials: MaterialRecovery[];
  total_value_usd: number;
  enabled: boolean;
}

// --------------------------------------------------------------------------
// KPIs / simulate
// --------------------------------------------------------------------------
export interface Kpis {
  next_month_demand: number;
  optimal_transport_cost: number;
  avg_supplier_utilization: number;
  recovered_material_value: number;
  hubs_needing_reorder: number;
  total_available_t: number;
  total_demand_t: number;
  balanced: boolean;
}
export interface MethodologyItem {
  element: string;
  technique: string;
  result: string;
}
export interface SimulateResponse {
  scenario: ScenarioInfo;
  kpis: Kpis;
  insights: string[];
  methodology: MethodologyItem[];
  months: string[];
  actual: number[];
  forecast_fitted: number[];
  forecast_horizon: number[];
}
export interface ScenarioComparison {
  normal: Kpis;
  hormuz_disruption: Kpis;
}

// --------------------------------------------------------------------------
// Reference data view
// --------------------------------------------------------------------------
export interface DataResponse {
  scenario: ScenarioInfo;
  meta: DatasetMeta;
  demand: { date: string; month: string; returned_units: number }[];
  centers: {
    center: string;
    lead_time_days: number;
    monthly_capacity_t: number;
    gate_fee_per_t: number;
  }[];
  hubs: { hub: string; processing_demand_t: number; recovery_yield: number }[];
  materials: { material: string; mass_share: number; value_per_t_usd: number }[];
  transport_costs: number[][];
  transport_supply: number[];
  transport_demand: number[];
  center_names: string[];
  hub_names: string[];
}

// --------------------------------------------------------------------------
// Request param shapes
// --------------------------------------------------------------------------
export interface AnalysisParams {
  alpha: number;
  beta: number;
  horizon: number;
  serviceLevel: number;
  autoTune: boolean;
}
