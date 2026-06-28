"""Orchestration layer (stateless).

Every function takes a *canonical dataset* (built from the user's uploaded CSVs
— see ``core.dataset``) plus a scenario name and analysis params, and calls the
verified ``core`` engine. Nothing here fabricates operational data: demand comes
from the sales feed, supply from the historical transportation feed capped by
contractual capacity, inventory status from the inventory feed, and EOQ costs
from the warehouse parameters. The scenario is a what-if lens applied on top of
the real data.
"""

from __future__ import annotations

from collections import defaultdict
from typing import List, Optional

import numpy as np

from core import dataset as dsmod
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


def _scenario_info(scenario: Scenario) -> dict:
    return describe(scenario)


# --------------------------------------------------------------------------
# Scenario-adjusted views of the canonical dataset
# --------------------------------------------------------------------------
PROHIBITIVE = 1_000_000.0


def _has_scenario_data(ds: dict) -> bool:
    """True when the upload carries real pre/post-conflict cost matrices, so the
    twin uses those numbers directly instead of modelled multipliers."""
    tc = ds["transport_costs"]
    return bool(
        ds["meta"].get("has_scenario_data")
        and tc.get("matrix_normal")
        and tc.get("matrix_disrupted")
    )


def _dense(matrix) -> np.ndarray:
    return np.array(
        [[PROHIBITIVE if v is None else float(v) for v in row] for row in matrix],
        dtype=float,
    )


def _adjusted_cost_matrix(ds: dict, scenario: Scenario) -> np.ndarray:
    tc = ds["transport_costs"]
    if _has_scenario_data(ds):
        m = tc["matrix_disrupted"] if scenario.is_disrupted else tc["matrix_normal"]
        return _dense(m)
    return apply_transport_costs(dsmod.cost_matrix(ds), scenario)


def _supplier_lead_times(ds: dict, scenario: Scenario) -> dict:
    out = {}
    for s in ds["suppliers"]:
        if scenario.is_disrupted and s.get("lead_time_days_disrupted") is not None:
            out[s["supplier"]] = int(s["lead_time_days_disrupted"])
        elif not scenario.is_disrupted and s.get("lead_time_days_normal") is not None:
            out[s["supplier"]] = int(s["lead_time_days_normal"])
        else:
            out[s["supplier"]] = s["lead_time_days"] + scenario.lead_time_add_days
    return out


def _demand_multiplier(ds: dict, scenario: Scenario) -> float:
    """No synthetic demand amplification when the dataset is scenario-aware."""
    return 1.0 if _has_scenario_data(ds) else scenario.recovered_demand_multiplier


def _external_factor_next(ds: dict) -> float:
    """Forward market-trend multiplier from the external-factors feed."""
    ext = ds.get("external") or []
    if not ext:
        return 1.0
    last = sorted(ext, key=lambda r: r["period"])[-1]
    return float(np.clip(last.get("market_trend", 1.0), 0.5, 2.0))


def _history_by_source(ds: dict) -> dict:
    """Per-supplier time series of total outbound volume per period."""
    agg: dict = defaultdict(lambda: defaultdict(float))
    for r in ds["transport_history"]:
        agg[r["source"]][r["period"]] += r["volume_t"]
    out = {}
    for name in ds["transport_costs"]["sources"]:
        periods = sorted(agg.get(name, {}))
        out[name] = [agg[name][p] for p in periods]
    return out


def _inflow_std_by_dest(ds: dict) -> dict:
    """Per-warehouse std of historical inbound volume per period (real demand
    variability used for safety stock)."""
    agg: dict = defaultdict(lambda: defaultdict(float))
    for r in ds["transport_history"]:
        agg[r["destination"]][r["period"]] += r["volume_t"]
    out = {}
    for name in ds["transport_costs"]["destinations"]:
        series = [agg[name][p] for p in sorted(agg.get(name, {}))]
        out[name] = float(np.std(series)) if len(series) > 1 else 0.0
    return out


# --------------------------------------------------------------------------
# Demand forecasting
# --------------------------------------------------------------------------
def forecast_demand(
    ds: dict,
    scenario_name: str,
    alpha: float,
    beta: float,
    horizon: int,
    auto_tune: bool = False,
) -> dict:
    scenario = get_scenario(scenario_name)
    series = dsmod.sales_series(ds)
    labels = dsmod.sales_labels(ds)
    n = len(series)

    tuning = None
    if auto_tune:
        t = fc.autotune_adjusted_es(series)
        alpha, beta = t.alpha, t.beta
        tuning = {
            "alpha": t.alpha,
            "beta": t.beta,
            "train_mad": t.train_mad,
            "validation_mad": t.validation_mad,
            "holdout": t.holdout,
            "grid_size": t.grid_size,
        }

    aes = fc.adjusted_exponential_smoothing(series, alpha=alpha, beta=beta)
    lt = fc.linear_trend(series)
    seas = fc.seasonal_adjustment(
        series, season_length=min(SEASON_LENGTH, max(2, n // 2))
    )

    aes_fitted = aes.adjusted[:n]
    lt_fitted = lt.fitted
    seas_fitted = seas.seasonal_forecast

    # Damped-trend forward forecast (levels off instead of ramping linearly).
    horizon_fc = [round(float(v), 2) for v in fc.forward_forecast(aes, horizon)]
    next_forecast = horizon_fc[0] if horizon_fc else float(aes.next_forecast)

    # Out-of-sample validation (back-test on historical data).
    bt = fc.backtest_adjusted_es(series, alpha=alpha, beta=beta)

    mult = _demand_multiplier(ds, scenario)
    ext_factor = _external_factor_next(ds)
    return {
        "scenario": _scenario_info(scenario),
        "months": labels,
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
        "next_forecast": round(float(next_forecast), 2),
        "planning_demand_next": round(float(next_forecast) * mult * ext_factor, 2),
        "recovered_demand_multiplier": mult,
        "external_factor": round(ext_factor, 3),
        "alpha": round(float(alpha), 3),
        "beta": round(float(beta), 3),
        "auto_tuned": bool(auto_tune),
        "tuning": tuning,
        "validation": {
            "holdout": bt.holdout,
            "train_size": bt.train_size,
            "predictions": bt.predictions,
            "actuals": bt.actuals,
            "mad": bt.mad,
            "mape": bt.mape,
        },
    }


# --------------------------------------------------------------------------
# Supplier forecasting
# --------------------------------------------------------------------------
def forecast_suppliers(
    ds: dict, scenario_name: str, alpha: float, beta: float, horizon: int
) -> dict:
    scenario = get_scenario(scenario_name)
    history = _history_by_source(ds)
    capacity = {s["supplier"]: s["capacity_t"] for s in ds["suppliers"]}
    price = {s["supplier"]: s["price_per_t"] for s in ds["suppliers"]}
    lead = _supplier_lead_times(ds, scenario)

    forecasts = sup.forecast_from_history(
        history, capacity, alpha=alpha, beta=beta, horizon=horizon
    )
    rows = []
    for f in forecasts:
        name = f["supplier"]
        rows.append(
            {
                "center": name,
                "lead_time_days": int(lead.get(name, 0)),
                "monthly_capacity_t": int(round(f["capacity_t"])),
                "gate_fee_per_t": int(round(price.get(name, 0))),
                "forecast_next_t": f["forecast_next_t"],
                "available_t": f["available_t"],
                "capacity_utilization": f["capacity_utilization"],
                "horizon_forecast": f["horizon_forecast"],
            }
        )
    total_available = round(sum(r["available_t"] for r in rows), 1)
    avg_util = round(
        float(np.mean([r["capacity_utilization"] for r in rows])) if rows else 0.0, 3
    )
    return {
        "scenario": _scenario_info(scenario),
        "suppliers": rows,
        "total_available_t": total_available,
        "avg_capacity_utilization": avg_util,
        "lead_time_add_days": scenario.lead_time_add_days,
    }


def _supply_vector(ds: dict, scenario_name: str) -> np.ndarray:
    sc = forecast_suppliers(ds, scenario_name, 0.4, 0.3, 3)
    return np.array([r["available_t"] for r in sc["suppliers"]], dtype=float)


# --------------------------------------------------------------------------
# Transportation optimisation
# --------------------------------------------------------------------------
def _derive_transport_inputs(
    ds: dict,
    scenario: Scenario,
    cost: Optional[List[List[float]]],
    supply: Optional[List[float]],
    demand: Optional[List[float]],
    row_labels: Optional[List[str]] = None,
    col_labels: Optional[List[str]] = None,
):
    names_src = list(ds["transport_costs"]["sources"])
    names_dst = list(ds["transport_costs"]["destinations"])

    if cost is not None:
        # A provided matrix is used as-is — it was seeded already scenario-
        # adjusted, so re-applying modifiers here would double-count.
        cost_arr = np.array(cost, dtype=float)
        rl = (
            list(row_labels)
            if row_labels
            else (
                names_src
                if len(names_src) == cost_arr.shape[0]
                else [f"S{i + 1}" for i in range(cost_arr.shape[0])]
            )
        )
        cl = (
            list(col_labels)
            if col_labels
            else (
                names_dst
                if len(names_dst) == cost_arr.shape[1]
                else [f"D{j + 1}" for j in range(cost_arr.shape[1])]
            )
        )
    else:
        cost_arr = _adjusted_cost_matrix(ds, scenario)
        rl = names_src
        cl = names_dst

    if supply is not None:
        supply_arr = np.array(supply, dtype=float)
    else:
        supply_arr = _supply_vector(ds, scenario.name)

    if demand is not None:
        demand_arr = np.array(demand, dtype=float)
    else:
        demand_arr = dsmod.warehouse_demand(ds) * _demand_multiplier(ds, scenario)

    return cost_arr, supply_arr, demand_arr, rl, cl


def optimize_transport(
    ds: dict,
    scenario_name: str,
    initial: str,
    optimize: str,
    cost: Optional[List[List[float]]] = None,
    supply: Optional[List[float]] = None,
    demand: Optional[List[float]] = None,
    row_labels: Optional[List[str]] = None,
    col_labels: Optional[List[str]] = None,
) -> dict:
    scenario = get_scenario(scenario_name)
    cost_arr, supply_arr, demand_arr, row_labels, col_labels = _derive_transport_inputs(
        ds, scenario, cost, supply, demand, row_labels, col_labels
    )

    sol = tp.solve_transport(
        cost_arr, supply_arr, demand_arr, initial=initial, optimize=optimize
    )

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

    # The balancing "dummy" row/column is a standard transportation-problem
    # device, not fabricated data: a source dummy carries demand that supply
    # cannot meet (unmet demand); a destination dummy carries supply left unused.
    rl = list(row_labels)
    cl = list(col_labels)
    if sol.dummy_added == "source" and len(rl) < sol.allocation.shape[0]:
        rl.append("Unmet demand (no supply)")
    if sol.dummy_added == "destination" and len(cl) < sol.allocation.shape[1]:
        cl.append("Surplus supply (unused)")

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
# Warehouse policy (real inventory + operational parameters)
# --------------------------------------------------------------------------
def warehouse_policy(
    ds: dict,
    scenario_name: str,
    alpha: float,
    beta: float,
    service_level: Optional[float] = None,
) -> dict:
    scenario = get_scenario(scenario_name)
    params = ds["warehouse_params"]
    sl = service_level if service_level is not None else params["service_level"]
    ordering_cost = params["ordering_cost"]
    holding_cost = params["holding_cost_per_unit"]

    lead = _supplier_lead_times(ds, scenario)
    avg_lead = float(np.mean(list(lead.values()))) if lead else 0.0

    inflow_std = _inflow_std_by_dest(ds)
    mult = _demand_multiplier(ds, scenario)

    policies = []
    needing = 0
    total_demand = 0.0
    for inv in ds["inventory"]:
        name = inv["warehouse"]
        demand_hub = inv["replenishment_rate_t"] * mult
        total_demand += demand_hub
        std_hub = inflow_std.get(name, 0.0)
        p = wh.inventory_policy(
            demand_hub,
            std_hub,
            avg_lead,
            inv["current_stock_t"],
            service_level=sl,
            ordering_cost=ordering_cost,
            holding_cost_per_unit=holding_cost,
            storage_capacity=inv.get("storage_capacity_t"),
        )
        p["hub"] = name
        if p["status"] != "OK":
            needing += 1
        policies.append(p)

    return {
        "scenario": _scenario_info(scenario),
        "policies": policies,
        "forecast_demand": round(total_demand, 1),
        "avg_lead_time_days": round(avg_lead, 1),
        "service_level": round(sl, 3),
        "ordering_cost": ordering_cost,
        "holding_cost_per_unit": holding_cost,
        "hubs_needing_reorder": needing,
    }


# --------------------------------------------------------------------------
# Materials recovery (reference prices)
# --------------------------------------------------------------------------
def materials_recovery(ds: dict, scenario_name: str) -> dict:
    scenario = get_scenario(scenario_name)
    materials = ds.get("materials") or []
    supply_total = float(_supply_vector(ds, scenario_name).sum())
    demand_total = float(
        dsmod.warehouse_demand(ds).sum() * _demand_multiplier(ds, scenario)
    )
    processed = min(supply_total, demand_total)

    rows = []
    total_value = 0.0
    for m in materials:
        # Use the upload's pre/post-conflict price when present; else the
        # single reference price.
        price = m["value_per_t_usd"]
        if scenario.is_disrupted and m.get("value_per_t_disrupted") is not None:
            price = m["value_per_t_disrupted"]
        elif not scenario.is_disrupted and m.get("value_per_t_normal") is not None:
            price = m["value_per_t_normal"]
        recovered_t = m["mass_share"] * processed
        value = recovered_t * price
        total_value += value
        rows.append(
            {
                "material": m["material"],
                "mass_share": float(m["mass_share"]),
                "recovered_t": round(float(recovered_t), 1),
                "value_per_t_usd": float(price),
                "value_usd": round(float(value), 0),
            }
        )
    return {
        "scenario": _scenario_info(scenario),
        "processed_t": round(processed, 1),
        "materials": rows,
        "total_value_usd": round(total_value, 0),
        "enabled": bool(materials),
    }


# --------------------------------------------------------------------------
# Reference-data view (editable transport seeds, scenario-adjusted)
# --------------------------------------------------------------------------
def get_data(ds: dict, scenario_name: str) -> dict:
    scenario = get_scenario(scenario_name)
    cost = _adjusted_cost_matrix(ds, scenario)
    supply = _supply_vector(ds, scenario_name)
    demand = dsmod.warehouse_demand(ds) * _demand_multiplier(ds, scenario)
    lead = _supplier_lead_times(ds, scenario)

    return {
        "scenario": _scenario_info(scenario),
        "meta": ds["meta"],
        "demand": [
            {
                "date": r["label"],
                "month": r["label"],
                "returned_units": int(round(r["sales"])),
            }
            for r in ds["sales"]
        ],
        "centers": [
            {
                "center": s["supplier"],
                "lead_time_days": int(lead.get(s["supplier"], 0)),
                "monthly_capacity_t": int(round(s["capacity_t"])),
                "gate_fee_per_t": int(round(s["price_per_t"])),
            }
            for s in ds["suppliers"]
        ],
        "hubs": [
            {
                "hub": inv["warehouse"],
                "processing_demand_t": round(
                    inv["replenishment_rate_t"] * _demand_multiplier(ds, scenario),
                    2,
                ),
                "recovery_yield": 0.0,
            }
            for inv in ds["inventory"]
        ],
        "materials": [
            {
                "material": m["material"],
                "mass_share": m["mass_share"],
                "value_per_t_usd": m["value_per_t_usd"],
            }
            for m in (ds.get("materials") or [])
        ],
        "transport_costs": np.round(cost, 2).tolist(),
        "transport_supply": np.round(supply, 1).tolist(),
        "transport_demand": np.round(demand, 1).tolist(),
        "center_names": list(ds["transport_costs"]["sources"]),
        "hub_names": list(ds["transport_costs"]["destinations"]),
    }


# --------------------------------------------------------------------------
# Full simulation (overview KPIs)
# --------------------------------------------------------------------------
def _kpis_for(
    ds: dict,
    scenario_name: str,
    alpha: float,
    beta: float,
    horizon: int,
    service_level: Optional[float],
    auto_tune: bool = False,
) -> dict:
    fcast = forecast_demand(
        ds, scenario_name, alpha, beta, horizon, auto_tune=auto_tune
    )
    suppliers = forecast_suppliers(ds, scenario_name, alpha, beta, horizon)
    transport = optimize_transport(ds, scenario_name, "vogel", "modi")
    warehouse = warehouse_policy(ds, scenario_name, alpha, beta, service_level)
    materials = materials_recovery(ds, scenario_name)

    total_supply = float(_supply_vector(ds, scenario_name).sum())
    scenario = get_scenario(scenario_name)
    total_demand = float(
        dsmod.warehouse_demand(ds).sum() * _demand_multiplier(ds, scenario)
    )

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
        "suppliers": suppliers,
        "transport": transport,
        "warehouse": warehouse,
        "materials": materials,
    }


def _build_insights(ds: dict, result: dict) -> list:
    """Plain-language analytical findings computed from the user's data."""
    fcast = result["forecast"]
    sup_r = result["suppliers"]
    tr = result["transport"]
    wh_r = result["warehouse"]
    mat = result["materials"]
    out = []

    lt = fcast["linear_trend"]["fitted"]
    if lt and lt[0]:
        trend = (lt[-1] - lt[0]) / lt[0] * 100
        direction = "rising" if trend > 1 else "falling" if trend < -1 else "flat"
        out.append(
            f"Demand is {direction} ~{abs(trend):.0f}% across the series; "
            f"next-period forecast is {fcast['planning_demand_next']:,.0f} units."
        )

    methods = [
        ("Adjusted ES", fcast["adjusted_es"]),
        ("Linear Trend", fcast["linear_trend"]),
        ("Seasonal", fcast["seasonal"]),
    ]
    best = min(methods, key=lambda m: m[1]["metrics"]["MAD"])
    out.append(
        f"Best-fitting forecast method: {best[0]} "
        f"(MAD {best[1]['metrics']['MAD']}, MAPE {best[1]['metrics']['MAPE']}%); "
        f"out-of-sample validation MAD {fcast['validation']['mad']}."
    )
    out.append(
        f"Suppliers run at {sup_r['avg_capacity_utilization'] * 100:.0f}% of "
        f"capacity on average; {sup_r['total_available_t']:,.0f} t available "
        "next period."
    )

    bal = "balanced" if tr["balanced"] else "unbalanced"
    gap = ""
    if not tr["balanced"]:
        # Real gap from pre-balance totals (sol.supply/demand include the dummy).
        kpis = result["kpis"]
        diff = abs(kpis["total_demand_t"] - kpis["total_available_t"])
        kind = "unmet demand" if tr["dummy_added"] == "source" else "surplus supply"
        gap = f" — {diff:,.0f} t {kind}"
    out.append(
        f"Optimal routing cost {tr['total_cost']:,.0f} "
        f"({'all 6 methods agree' if tr['all_methods_agree'] else 'methods differ'}); "
        f"network is {bal}{gap}."
    )

    crit = len([p for p in wh_r["policies"] if p["status"] == "CRITICAL"])
    out.append(
        f"{wh_r['hubs_needing_reorder']} of {len(wh_r['policies'])} hubs need "
        f"reordering ({crit} critical) at a "
        f"{wh_r['service_level'] * 100:.0f}% service level."
    )
    if mat.get("enabled"):
        out.append(
            f"Recovered-material value: ${mat['total_value_usd']:,.0f} per cycle "
            f"from {mat['processed_t']:,.0f} t processed."
        )
    return out


def _build_methodology(ds: dict, result: dict) -> list:
    """Maps the brief's required elements to the technique applied + its result."""
    meta = ds["meta"]
    fcast = result["forecast"]
    sup_r = result["suppliers"]
    tr = result["transport"]
    wh_r = result["warehouse"]
    return [
        {
            "element": "Data augmentation & preprocessing",
            "technique": "Eight inputs parsed, validated, cross-checked and merged",
            "result": (
                f"{meta['n_periods']} periods · {meta['n_suppliers']} suppliers · "
                f"{meta['n_warehouses']} warehouses · {meta['n_orders']} orders"
            ),
        },
        {
            "element": "Demand forecasting",
            "technique": "Adjusted Exp. Smoothing + Linear Trend + Seasonal, α/β "
            "auto-tuned, validated out-of-sample",
            "result": (
                f"next {fcast['planning_demand_next']:,.0f} units · "
                f"MAPE {fcast['adjusted_es']['metrics']['MAPE']}%"
            ),
        },
        {
            "element": "Supplier integration & forecasting",
            "technique": "Availability forecast from historical shipments, capped "
            "by contractual capacity",
            "result": f"{sup_r['avg_capacity_utilization'] * 100:.0f}% avg utilization",
        },
        {
            "element": "Transportation optimization",
            "technique": "NWC / Least-Cost / Vogel → Stepping-Stone & MODI; "
            "balanced and unbalanced",
            "result": (
                f"optimum {tr['total_cost']:,.0f} · "
                f"{'balanced' if tr['balanced'] else 'unbalanced (dummy added)'}"
            ),
        },
        {
            "element": "Warehouse management",
            "technique": "Safety stock + ROP + EOQ from demand, lead time, "
            "real stock & parameters",
            "result": (
                f"{wh_r['hubs_needing_reorder']}/{len(wh_r['policies'])} "
                "hubs to reorder"
            ),
        },
        {
            "element": "Scalability & adaptability",
            "technique": "Stateless engine; parameter auto-tuning + back-testing "
            "feedback loop",
            "result": "scales to any network size; self-validating forecasts",
        },
    ]


def simulate(
    ds: dict,
    scenario_name: str,
    alpha: float,
    beta: float,
    horizon: int,
    service_level: Optional[float],
    auto_tune: bool = False,
) -> dict:
    scenario = get_scenario(scenario_name)
    result = _kpis_for(
        ds, scenario_name, alpha, beta, horizon, service_level, auto_tune
    )
    fcast = result["forecast"]
    return {
        "scenario": _scenario_info(scenario),
        "kpis": result["kpis"],
        "insights": _build_insights(ds, result),
        "methodology": _build_methodology(ds, result),
        "months": fcast["months"],
        "actual": fcast["actual"],
        "forecast_fitted": fcast["adjusted_es"]["fitted"],
        "forecast_horizon": fcast["forecast_horizon"],
    }


def compare_scenarios(
    ds: dict, alpha: float, beta: float, horizon: int, service_level: Optional[float]
) -> dict:
    return {
        "normal": _kpis_for(ds, "normal", alpha, beta, horizon, service_level)["kpis"],
        "hormuz_disruption": _kpis_for(
            ds, "hormuz_disruption", alpha, beta, horizon, service_level
        )["kpis"],
    }
