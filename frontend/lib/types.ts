// Shared types mirroring the backend pydantic models (backend/app/models.py).

export type ScenarioName = "normal" | "hormuz_disruption";
export type InitialMethod = "nwc" | "least_cost" | "vogel";
export type OptimalityMethod = "modi" | "stepping_stone";

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
}

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

export interface HubPolicy {
  hub: string;
  current_stock: number;
  safety_stock: number;
  reorder_point: number;
  eoq: number;
  suggested_order: number;
  status: "OK" | "REORDER" | "CRITICAL";
}

export interface WarehouseResponse {
  scenario: ScenarioInfo;
  policies: HubPolicy[];
  forecast_demand: number;
  avg_lead_time_days: number;
  service_level: number;
  hubs_needing_reorder: number;
}

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
}

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

export interface SimulateResponse {
  scenario: ScenarioInfo;
  kpis: Kpis;
  months: string[];
  actual: number[];
  forecast_fitted: number[];
  forecast_horizon: number[];
}

export interface ScenarioComparison {
  normal: Kpis;
  hormuz_disruption: Kpis;
}

export interface DemandPoint {
  date: string;
  month: string;
  returned_units: number;
}

export interface DataResponse {
  scenario: ScenarioInfo;
  demand: DemandPoint[];
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

// Request param shapes.
export interface ForecastParams {
  scenario: ScenarioName;
  alpha: number;
  beta: number;
  horizon: number;
}

export interface TransportRequest {
  scenario: ScenarioName;
  initial: InitialMethod;
  optimize: OptimalityMethod;
  cost?: number[][];
  supply?: number[];
  demand?: number[];
}

export interface WarehouseRequest {
  scenario: ScenarioName;
  alpha: number;
  beta: number;
  service_level: number;
}

export interface SimulateRequest {
  scenario: ScenarioName;
  alpha: number;
  beta: number;
  horizon: number;
  service_level: number;
}
