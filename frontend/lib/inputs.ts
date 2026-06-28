// The nine dataset inputs: eight required data-augmentation categories from the
// project brief plus optional materials reference prices. Used to drive the
// upload UI, column hints, and template downloads.

export interface InputDef {
  kind: string;
  title: string;
  brief: string; // the brief's data-augmentation wording
  columns: string[];
  required: boolean;
}

export const INPUT_DEFS: InputDef[] = [
  {
    kind: "sales",
    title: "Historical Sales",
    brief: "Historical sales data for demand forecasting",
    columns: ["period", "label", "sales"],
    required: true,
  },
  {
    kind: "suppliers",
    title: "Supplier Data",
    brief: "Lead times, production capacities, and pricing contracts",
    columns: ["supplier", "lead_time_days", "capacity_t", "price_per_t"],
    required: true,
  },
  {
    kind: "transport_costs",
    title: "Transportation Costs & Routes",
    brief: "Cost per tonne for each source → destination route",
    columns: ["source", "destination", "cost_per_t"],
    required: true,
  },
  {
    kind: "external",
    title: "External Factors",
    brief: "Seasonality, promotions, and market trends affecting demand",
    columns: ["period", "seasonality_index", "promotion", "market_trend"],
    required: true,
  },
  {
    kind: "inventory",
    title: "Inventory Data",
    brief: "Stock levels, storage capacities, and replenishment rates",
    columns: [
      "warehouse",
      "current_stock_t",
      "storage_capacity_t",
      "replenishment_rate_t",
    ],
    required: true,
  },
  {
    kind: "orders",
    title: "Customer Orders",
    brief: "Order frequency, size, and location",
    columns: ["order_id", "period", "size_t", "location"],
    required: true,
  },
  {
    kind: "warehouse_params",
    title: "Warehouse Parameters",
    brief: "Operational parameters (ordering cost, holding cost, service level)",
    columns: ["parameter", "value"],
    required: true,
  },
  {
    kind: "transport_history",
    title: "Transport History",
    brief: "Historical data for transportation optimization methods",
    columns: ["period", "source", "destination", "volume_t", "cost"],
    required: true,
  },
  {
    kind: "materials",
    title: "Materials (reference)",
    brief: "Recovered sensitive-material reference prices (optional)",
    columns: ["material", "mass_share", "value_per_t_usd"],
    required: false,
  },
];
