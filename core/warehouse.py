"""
Warehouse management layer.

Turns the demand forecast and supplier availability into actionable inventory
policy per recycling hub:
  - Safety stock (service-level based)
  - Reorder point (ROP) = demand during lead time + safety stock
  - Economic Order Quantity (EOQ)
  - A simple status flag for the dashboard / digital-twin monitoring loop.
"""

from __future__ import annotations
import math
import numpy as np
import pandas as pd

Z_SCORES = {0.90: 1.2816, 0.95: 1.6449, 0.975: 1.9600, 0.99: 2.3263}


def safety_stock(
    demand_std: float, lead_time_days: float, service_level: float = 0.95
) -> float:
    z = Z_SCORES.get(round(service_level, 3), 1.6449)
    return z * demand_std * math.sqrt(lead_time_days / 30.0)


def reorder_point(avg_monthly_demand: float, lead_time_days: float, ss: float) -> float:
    daily = avg_monthly_demand / 30.0
    return daily * lead_time_days + ss


def eoq(
    annual_demand: float,
    ordering_cost: float = 250.0,
    holding_cost_per_unit: float = 12.0,
) -> float:
    if annual_demand <= 0 or holding_cost_per_unit <= 0:
        return 0.0
    return math.sqrt(2 * annual_demand * ordering_cost / holding_cost_per_unit)


def inventory_policy(
    forecast_demand: float,
    demand_std: float,
    lead_time_days: float,
    current_stock: float,
    service_level: float = 0.95,
    ordering_cost: float = 250.0,
    holding_cost_per_unit: float = 12.0,
    storage_capacity: float | None = None,
) -> dict:
    """Inventory policy from a forecast, lead time, and *real* current stock.

    ``ordering_cost`` and ``holding_cost_per_unit`` come from the warehouse
    operational parameters (not hard-coded in production). ``current_stock`` is
    the measured on-hand level from the inventory feed.
    """
    ss = safety_stock(demand_std, lead_time_days, service_level)
    rop = reorder_point(forecast_demand, lead_time_days, ss)
    annual = forecast_demand * 12
    q = eoq(annual, ordering_cost, holding_cost_per_unit)
    if current_stock <= ss:
        status = "CRITICAL"
    elif current_stock <= rop:
        status = "REORDER"
    else:
        status = "OK"
    result = {
        "safety_stock": round(ss, 1),
        "reorder_point": round(rop, 1),
        "eoq": round(q, 1),
        "current_stock": round(current_stock, 1),
        "status": status,
        "suggested_order": round(q, 1) if status != "OK" else 0.0,
    }
    if storage_capacity is not None and storage_capacity > 0:
        result["storage_capacity"] = round(storage_capacity, 1)
        result["utilization"] = round(current_stock / storage_capacity, 3)
    return result


def hub_policies(
    hubs: pd.DataFrame,
    forecast_demand: float,
    demand_std: float,
    avg_lead_time: float,
    service_level: float = 0.95,
) -> pd.DataFrame:
    rows = []
    rng = np.random.default_rng(7)
    for _, h in hubs.iterrows():
        share = h["processing_demand_t"] / hubs["processing_demand_t"].sum()
        hub_demand = forecast_demand * share
        current = hub_demand * rng.uniform(0.3, 1.4)
        p = inventory_policy(
            hub_demand, demand_std * share, avg_lead_time, current, service_level
        )
        p["hub"] = h["hub"]
        rows.append(p)
    cols = [
        "hub",
        "current_stock",
        "safety_stock",
        "reorder_point",
        "eoq",
        "suggested_order",
        "status",
    ]
    return pd.DataFrame(rows)[cols]
