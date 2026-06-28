"""Orchestration layer.

Pure functions that take validated request params + a scenario name and call
the ``core`` engine, returning plain dicts the routers wrap in response models.
The frontend never reimplements any of this — it is all served from here.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

import numpy as np
from core import data_generator as dg
from core import forecasting as fc
from core import metrics as mx
from core import supplier as sup
from core import transportation as tp
from core import warehouse as wh
from core.scenarios import Scenario, apply_transport_costs, get_scenario

from .scenarios import describe

SEASON_LENGTH = 12
INITIAL_METHODS = ["nwc", "least_cost", "vogel"]
OPTIMALITY_METHODS = ["modi", "stepping_stone"]


@lru_cache(maxsize=1)
def _baseline() -> dict:
    """Seeded baseline network. Cached — the generator is deterministic."""
    return dg.build_all()


def _scenario_info(scenario: Scenario) -> dict:
    return describe(scenario)


# --------------------------------------------------------------------------
# Reference data
# --------------------------------------------------------------------------
def get_data(scenario_name: str) -> dict:
    scenario = get_scenario(scenario_name)
    base = _baseline()
    centers = base["centers"].copy()
    centers["lead_time_days"] = centers["lead_time_days"] + scenario.lead_time_add_days
    hubs = base["hubs"].copy()
    hubs["processing_demand_t"] = (
        hubs["processing_demand_t"] * scenario.recovered_demand_multiplier
    )
    cost = apply_transport_costs(
        base["transport_costs"].to_numpy(dtype=float), scenario
    )

    demand = base["demand"]

    # Editable transport seeds: per-center available supply and scenario-adjusted
    # per-hub demand (pre-balancing, so no dummy row/col appears in the editor).
    avail = sup.forecast_supplier_availability(
        base["supplier_history"], base["centers"]
    )
    transport_supply = np.round(sup.supply_vector(avail), 1).tolist()
    transport_demand = (
        hubs["processing_demand_t"].round(1).to_numpy(dtype=float).tolist()
    )

    return {
        "scenario": _scenario_info(scenario),
        "demand": [
            {
                "date": d.strftime("%Y-%m-%d"),
                "month": m,
                "returned_units": int(u),
            }
            for d, m, u in zip(
                demand["date"], demand["month"], demand["returned_units"]
            )
        ],
        "centers": centers.to_dict(orient="records"),
        "hubs": hubs.round(2).to_dict(orient="records"),
        "materials": base["materials"].to_dict(orient="records"),
        "transport_costs": cost.round(2).tolist(),
        "transport_supply": transport_supply,
        "transport_demand": transport_demand,
        "center_names": base["centers"]["center"].tolist(),
        "hub_names": base["hubs"]["hub"].tolist(),
    }


# --------------------------------------------------------------------------
# Demand forecasting
# --------------------------------------------------------------------------
def forecast_demand(
    scenario_name: str, alpha: float, beta: float, horizon: int
) -> dict:
    scenario = get_scenario(scenario_name)
    base = _baseline()
    demand_df = base["demand"]
    series = demand_df["returned_units"].to_numpy(dtype=float)
    months = demand_df["month"].tolist()
    n = len(series)

    aes = fc.adjusted_exponential_smoothing(series, alpha=alpha, beta=beta)
    lt = fc.linear_trend(series)
    seas = fc.seasonal_adjustment(series, season_length=SEASON_LENGTH)

    aes_fitted = aes.adjusted[:n]
    lt_fitted = lt.fitted
    seas_fitted = seas.seasonal_forecast

    # Forward forecast off the adjusted-ES trend.
    last_F, last_T = aes.forecast[-1], aes.trend[-1]
    horizon_fc = [round(float(last_F + last_T * k), 2) for k in range(1, horizon + 1)]

    mult = scenario.recovered_demand_multiplier
    return {
        "scenario": _scenario_info(scenario),
        "months": months,
        "actual": [round(float(v), 2) for v in series],
        "adjusted_es": {
            "name": "Adjusted Exponential Smoothing",
            "fitted": [round(float(v), 2) for v in aes_fitted],
            "metrics": mx.summary(series, aes_fitted),
        },
        "linear_trend": {
            "name": "Linear Trend",
            "fitted": [round(float(v), 2) for v in lt_fitted],
            "metrics": mx.summary(series, lt_fitted),
        },
        "seasonal": {
            "name": "Seasonal Adjusted",
            "fitted": [round(float(v), 2) for v in seas_fitted],
            "metrics": mx.summary(series, seas_fitted),
        },
        "seasonal_factors": [round(float(s), 3) for s in seas.seasonal_factors],
        "forecast_horizon": horizon_fc,
        "next_forecast": round(float(aes.next_forecast), 2),
        "planning_demand_next": round(float(aes.next_forecast) * mult, 2),
        "recovered_demand_multiplier": mult,
    }


# --------------------------------------------------------------------------
# Supplier forecasting
# --------------------------------------------------------------------------
def forecast_suppliers(
    scenario_name: str, alpha: float, beta: float, horizon: int
) -> dict:
    scenario = get_scenario(scenario_name)
    base = _baseline()
    centers = base["centers"].copy()
    centers["lead_time_days"] = centers["lead_time_days"] + scenario.lead_time_add_days

    avail = sup.forecast_supplier_availability(
        base["supplier_history"], centers, alpha=alpha, beta=beta, horizon=horizon
    )
    suppliers = avail.to_dict(orient="records")
    total_available = float(avail["available_t"].sum()) if len(avail) else 0.0
    avg_util = float(avail["capacity_utilization"].mean()) if len(avail) else 0.0

    return {
        "scenario": _scenario_info(scenario),
        "suppliers": suppliers,
        "total_available_t": round(total_available, 1),
        "avg_capacity_utilization": round(avg_util, 3),
        "lead_time_add_days": scenario.lead_time_add_days,
    }


# --------------------------------------------------------------------------
# Transportation optimisation
# --------------------------------------------------------------------------
def _derive_transport_inputs(
    scenario: Scenario,
    cost: Optional[List[List[float]]],
    supply: Optional[List[float]],
    demand: Optional[List[float]],
) -> tuple:
    base = _baseline()

    if cost is not None:
        cost_arr = np.array(cost, dtype=float)
    else:
        cost_arr = base["transport_costs"].to_numpy(dtype=float)
    # Always apply the scenario freight modifiers so the toggle is visible.
    cost_arr = apply_transport_costs(cost_arr, scenario)

    if supply is not None:
        supply_arr = np.array(supply, dtype=float)
    else:
        avail = sup.forecast_supplier_availability(
            base["supplier_history"], base["centers"]
        )
        supply_arr = sup.supply_vector(avail)

    if demand is not None:
        demand_arr = np.array(demand, dtype=float)
    else:
        demand_arr = (
            base["hubs"]["processing_demand_t"].to_numpy(dtype=float)
            * scenario.recovered_demand_multiplier
        )

    row_labels = base["centers"]["center"].tolist()
    col_labels = base["hubs"]["hub"].tolist()
    if cost is not None:
        row_labels = [f"S{i + 1}" for i in range(cost_arr.shape[0])]
        col_labels = [f"D{j + 1}" for j in range(cost_arr.shape[1])]
    return cost_arr, supply_arr, demand_arr, row_labels, col_labels


def optimize_transport(
    scenario_name: str,
    initial: str,
    optimize: str,
    cost: Optional[List[List[float]]] = None,
    supply: Optional[List[float]] = None,
    demand: Optional[List[float]] = None,
) -> dict:
    scenario = get_scenario(scenario_name)
    cost_arr, supply_arr, demand_arr, row_labels, col_labels = _derive_transport_inputs(
        scenario, cost, supply, demand
    )

    sol = tp.solve_transport(
        cost_arr, supply_arr, demand_arr, initial=initial, optimize=optimize
    )

    # Comparison across every initial x optimality combination.
    comparison: List[dict] = []
    totals: List[float] = []
    for init in INITIAL_METHODS:
        for opt in OPTIMALITY_METHODS:
            s = tp.solve_transport(
                cost_arr, supply_arr, demand_arr, initial=init, optimize=opt
            )
            comparison.append(
                {"initial": init, "optimize": opt, "total_cost": round(s.total_cost, 2)}
            )
            totals.append(round(s.total_cost))
    all_agree = len(set(totals)) == 1

    # Pad dummy row/col labels if balancing added one.
    rl = list(row_labels)
    cl = list(col_labels)
    if sol.dummy_added == "source" and len(rl) < sol.allocation.shape[0]:
        rl.append("Dummy (shortfall)")
    if sol.dummy_added == "destination" and len(cl) < sol.allocation.shape[1]:
        cl.append("Dummy (surplus)")

    return {
        "scenario": _scenario_info(scenario),
        "method": sol.method,
        "allocation": np.round(sol.allocation, 2).tolist(),
        "cost_matrix": np.round(sol.cost_matrix, 2).tolist(),
        "total_cost": round(sol.total_cost, 2),
        "supply": np.round(sol.supply, 2).tolist(),
        "demand": np.round(sol.demand, 2).tolist(),
        "balanced": bool(sol.balanced),
        "dummy_added": sol.dummy_added,
        "row_labels": rl,
        "col_labels": cl,
        "comparison": comparison,
        "all_methods_agree": all_agree,
    }


# --------------------------------------------------------------------------
# Warehouse policy
# --------------------------------------------------------------------------
def warehouse_policy(
    scenario_name: str, alpha: float, beta: float, service_level: float
) -> dict:
    scenario = get_scenario(scenario_name)
    base = _baseline()
    series = base["demand"]["returned_units"].to_numpy(dtype=float)

    aes = fc.adjusted_exponential_smoothing(series, alpha=alpha, beta=beta)
    forecast_demand_val = (
        float(aes.next_forecast) * scenario.recovered_demand_multiplier
    )
    demand_std = float(np.std(series))

    centers = base["centers"].copy()
    centers["lead_time_days"] = centers["lead_time_days"] + scenario.lead_time_add_days
    avg_lead = float(centers["lead_time_days"].mean())

    hubs = base["hubs"].copy()
    hubs["processing_demand_t"] = (
        hubs["processing_demand_t"] * scenario.recovered_demand_multiplier
    )
    policies_df = wh.hub_policies(
        hubs, forecast_demand_val, demand_std, avg_lead, service_level
    )
    policies = policies_df.to_dict(orient="records")
    needing = int((policies_df["status"] != "OK").sum())

    return {
        "scenario": _scenario_info(scenario),
        "policies": policies,
        "forecast_demand": round(forecast_demand_val, 1),
        "avg_lead_time_days": round(avg_lead, 1),
        "service_level": service_level,
        "hubs_needing_reorder": needing,
    }


# --------------------------------------------------------------------------
# Materials recovery
# --------------------------------------------------------------------------
def materials_recovery(scenario_name: str) -> dict:
    scenario = get_scenario(scenario_name)
    base = _baseline()

    avail = sup.forecast_supplier_availability(
        base["supplier_history"], base["centers"]
    )
    supply_total = float(sup.supply_vector(avail).sum())
    demand_total = float(
        base["hubs"]["processing_demand_t"].sum() * scenario.recovered_demand_multiplier
    )
    processed = min(supply_total, demand_total)

    mat = base["materials"]
    rows = []
    total_value = 0.0
    for _, r in mat.iterrows():
        recovered_t = r["mass_share"] * processed
        value = recovered_t * r["value_per_t_usd"]
        total_value += value
        rows.append(
            {
                "material": r["material"],
                "mass_share": float(r["mass_share"]),
                "recovered_t": round(float(recovered_t), 1),
                "value_per_t_usd": float(r["value_per_t_usd"]),
                "value_usd": round(float(value), 0),
            }
        )

    return {
        "scenario": _scenario_info(scenario),
        "processed_t": round(processed, 1),
        "materials": rows,
        "total_value_usd": round(total_value, 0),
    }


# --------------------------------------------------------------------------
# Full simulation (overview KPIs)
# --------------------------------------------------------------------------
def _kpis_for(
    scenario_name: str, alpha: float, beta: float, horizon: int, service_level: float
) -> dict:
    fcast = forecast_demand(scenario_name, alpha, beta, horizon)
    suppliers = forecast_suppliers(scenario_name, alpha, beta, horizon)
    transport = optimize_transport(scenario_name, "vogel", "modi")
    warehouse = warehouse_policy(scenario_name, alpha, beta, service_level)
    materials = materials_recovery(scenario_name)
    data = get_data(scenario_name)

    # Real (pre-balancing) totals — transport["supply"/"demand"] include any
    # dummy row/column, so they are always equal and cannot reveal imbalance.
    total_supply = float(sum(data["transport_supply"]))
    total_demand = float(sum(data["transport_demand"]))

    return {
        "kpis": {
            "next_month_demand": fcast["planning_demand_next"],
            "optimal_transport_cost": transport["total_cost"],
            "avg_supplier_utilization": suppliers["avg_capacity_utilization"],
            "recovered_material_value": materials["total_value_usd"],
            "hubs_needing_reorder": warehouse["hubs_needing_reorder"],
            "total_available_t": round(total_supply, 1),
            "total_demand_t": round(total_demand, 1),
            "balanced": bool(transport["balanced"]),
        },
        "forecast": fcast,
    }


def simulate(
    scenario_name: str, alpha: float, beta: float, horizon: int, service_level: float
) -> dict:
    scenario = get_scenario(scenario_name)
    result = _kpis_for(scenario_name, alpha, beta, horizon, service_level)
    fcast = result["forecast"]
    return {
        "scenario": _scenario_info(scenario),
        "kpis": result["kpis"],
        "months": fcast["months"],
        "actual": fcast["actual"],
        "forecast_fitted": fcast["adjusted_es"]["fitted"],
        "forecast_horizon": fcast["forecast_horizon"],
    }


def compare_scenarios(
    alpha: float, beta: float, horizon: int, service_level: float
) -> dict:
    return {
        "normal": _kpis_for("normal", alpha, beta, horizon, service_level)["kpis"],
        "hormuz_disruption": _kpis_for(
            "hormuz_disruption", alpha, beta, horizon, service_level
        )["kpis"],
    }
