"""
Supplier integration and forecasting.

Forecasts each collection center's future received tonnage from its history
(reusing the same forecasting engine used for demand), then combines the
forecast with the center's contractual attributes (lead time, capacity,
gate fee) to produce an availability picture the warehouse layer can use.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from . import forecasting as fc


def forecast_supplier_availability(supplier_history: pd.DataFrame,
                                   centers: pd.DataFrame,
                                   alpha: float = 0.4, beta: float = 0.3,
                                   horizon: int = 3) -> pd.DataFrame:
    """For each center: next-period availability forecast (adjusted ES),
    capped at contractual monthly capacity, plus a simple capacity utilization."""
    rows = []
    for _, c in centers.iterrows():
        hist = (supplier_history[supplier_history["center"] == c["center"]]
                .sort_values("period")["received_t"].to_numpy())
        if len(hist) < 2:
            continue
        aes = fc.adjusted_exponential_smoothing(hist, alpha=alpha, beta=beta)
        # project the horizon forward off the last trend
        last_F = aes.forecast[-1]
        last_T = aes.trend[-1]
        projection = [last_F + last_T * k for k in range(1, horizon + 1)]
        cap = c["monthly_capacity_t"]
        avail = float(min(projection[0], cap))
        rows.append({
            "center": c["center"],
            "lead_time_days": int(c["lead_time_days"]),
            "monthly_capacity_t": int(cap),
            "gate_fee_per_t": int(c["gate_fee_per_t"]),
            "forecast_next_t": round(float(projection[0]), 1),
            "available_t": round(avail, 1),
            "capacity_utilization": round(avail / cap, 3) if cap else 0.0,
            "horizon_forecast": [round(float(p), 1) for p in projection],
        })
    return pd.DataFrame(rows)


def supply_vector(availability: pd.DataFrame) -> np.ndarray:
    """Available tonnage per center -> supply vector for the transport model."""
    return availability["available_t"].to_numpy(dtype=float)
