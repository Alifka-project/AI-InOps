"""
Synthetic data generator for the Electrolux end-of-life appliance & battery
recycling digital twin.

Everything is seeded for reproducibility so the notebook, backend, and report
all show identical numbers.

Entities
--------
- Returned-appliance demand : monthly volume of end-of-life units entering the
  network (trend + seasonality + noise) -> drives demand forecasting.
- Collection centers (suppliers) : lead times, monthly capacity, gate fee.
- Recycling hubs (destinations) : processing demand for recovered material.
- Transportation cost matrix : cost per tonne, centers -> hubs.
- Recovered materials : split of recovered mass (Li, Co, Cu, Al, steel).
"""
from __future__ import annotations
import numpy as np
import pandas as pd

RNG_SEED = 42
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
# More returns after holidays / appliance-replacement seasons -> seasonal shape
SEASONAL_SHAPE = np.array([1.25, 1.10, 0.95, 0.85, 0.80, 0.85,
                           0.95, 1.05, 1.00, 1.05, 1.15, 1.30])


def returned_demand(years: int = 3, base: float = 800, growth: float = 12,
                    noise_sd: float = 35, seed: int = RNG_SEED) -> pd.DataFrame:
    """Monthly returned-appliance volume = (base + trend) * seasonal * noise."""
    rng = np.random.default_rng(seed)
    n = years * 12
    t = np.arange(n)
    trend = base + growth * t
    seasonal = np.tile(SEASONAL_SHAPE, years)
    noise = rng.normal(0, noise_sd, n)
    volume = np.maximum(0, trend * seasonal / seasonal.mean() + noise).round()
    dates = pd.date_range("2022-01-01", periods=n, freq="MS")
    return pd.DataFrame({
        "date": dates,
        "month": [MONTHS[d.month - 1] for d in dates],
        "returned_units": volume.astype(int),
    })


def collection_centers(seed: int = RNG_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 1)
    names = ["Jebel Ali Center", "Al Quoz Center", "Sharjah Center",
             "Abu Dhabi Center"]
    return pd.DataFrame({
        "center": names,
        "lead_time_days": rng.integers(2, 8, len(names)),
        "monthly_capacity_t": rng.integers(180, 320, len(names)),
        "gate_fee_per_t": rng.integers(40, 90, len(names)),
    })


def recycling_hubs(seed: int = RNG_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 2)
    names = ["KEZAD Recycling Hub", "DIC Processing Hub", "RAK Recovery Hub"]
    return pd.DataFrame({
        "hub": names,
        "processing_demand_t": rng.integers(150, 280, len(names)),
        "recovery_yield": rng.uniform(0.82, 0.93, len(names)).round(3),
    })


def transport_costs(centers: pd.DataFrame, hubs: pd.DataFrame,
                    seed: int = RNG_SEED) -> pd.DataFrame:
    """Cost per tonne from each collection center to each recycling hub."""
    rng = np.random.default_rng(seed + 3)
    m = rng.integers(8, 26, (len(centers), len(hubs)))
    return pd.DataFrame(m, index=centers["center"], columns=hubs["hub"])


def supplier_history(centers: pd.DataFrame, months: int = 24,
                     seed: int = RNG_SEED) -> pd.DataFrame:
    """Historical monthly tonnage actually received from each center."""
    rng = np.random.default_rng(seed + 4)
    rows = []
    for _, c in centers.iterrows():
        base = c["monthly_capacity_t"] * 0.7
        for k in range(months):
            seasonal = SEASONAL_SHAPE[k % 12]
            val = base * seasonal / SEASONAL_SHAPE.mean() + rng.normal(0, 15)
            rows.append({"center": c["center"], "period": k + 1,
                         "received_t": max(0, round(val, 1))})
    return pd.DataFrame(rows)


def recovered_material_split() -> pd.DataFrame:
    """Approximate share of recovered mass by material (illustrative)."""
    return pd.DataFrame({
        "material": ["Steel", "Aluminium", "Copper", "Lithium", "Cobalt"],
        "mass_share": [0.55, 0.18, 0.12, 0.09, 0.06],
        "value_per_t_usd": [320, 1900, 8200, 21000, 33000],
    })


def build_all(seed: int = RNG_SEED) -> dict:
    centers = collection_centers(seed)
    hubs = recycling_hubs(seed)
    return {
        "demand": returned_demand(seed=seed),
        "centers": centers,
        "hubs": hubs,
        "transport_costs": transport_costs(centers, hubs, seed),
        "supplier_history": supplier_history(centers, seed=seed),
        "materials": recovered_material_split(),
    }


if __name__ == "__main__":
    data = build_all()
    for k, v in data.items():
        print(f"\n=== {k} ===")
        print(v.head() if hasattr(v, "head") else v)
