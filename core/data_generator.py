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
MONTHS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]
# More returns after holidays / appliance-replacement seasons -> seasonal shape
SEASONAL_SHAPE = np.array(
    [1.25, 1.10, 0.95, 0.85, 0.80, 0.85, 0.95, 1.05, 1.00, 1.05, 1.15, 1.30]
)


def returned_demand(
    years: int = 3,
    base: float = 800,
    growth: float = 12,
    noise_sd: float = 35,
    seed: int = RNG_SEED,
) -> pd.DataFrame:
    """Monthly returned-appliance volume = (base + trend) * seasonal * noise."""
    rng = np.random.default_rng(seed)
    n = years * 12
    t = np.arange(n)
    trend = base + growth * t
    seasonal = np.tile(SEASONAL_SHAPE, years)
    noise = rng.normal(0, noise_sd, n)
    volume = np.maximum(0, trend * seasonal / seasonal.mean() + noise).round()
    dates = pd.date_range("2022-01-01", periods=n, freq="MS")
    return pd.DataFrame(
        {
            "date": dates,
            "month": [MONTHS[d.month - 1] for d in dates],
            "returned_units": volume.astype(int),
        }
    )


def collection_centers(seed: int = RNG_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 1)
    names = ["Jebel Ali Center", "Al Quoz Center", "Sharjah Center", "Abu Dhabi Center"]
    return pd.DataFrame(
        {
            "center": names,
            "lead_time_days": rng.integers(2, 8, len(names)),
            "monthly_capacity_t": rng.integers(180, 320, len(names)),
            "gate_fee_per_t": rng.integers(40, 90, len(names)),
        }
    )


def recycling_hubs(seed: int = RNG_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 2)
    names = ["KEZAD Recycling Hub", "DIC Processing Hub", "RAK Recovery Hub"]
    return pd.DataFrame(
        {
            "hub": names,
            "processing_demand_t": rng.integers(150, 280, len(names)),
            "recovery_yield": rng.uniform(0.82, 0.93, len(names)).round(3),
        }
    )


def transport_costs(
    centers: pd.DataFrame, hubs: pd.DataFrame, seed: int = RNG_SEED
) -> pd.DataFrame:
    """Cost per tonne from each collection center to each recycling hub."""
    rng = np.random.default_rng(seed + 3)
    m = rng.integers(8, 26, (len(centers), len(hubs)))
    return pd.DataFrame(m, index=centers["center"], columns=hubs["hub"])


def supplier_history(
    centers: pd.DataFrame, months: int = 24, seed: int = RNG_SEED
) -> pd.DataFrame:
    """Historical monthly tonnage actually received from each center."""
    rng = np.random.default_rng(seed + 4)
    rows = []
    for _, c in centers.iterrows():
        base = c["monthly_capacity_t"] * 0.7
        for k in range(months):
            seasonal = SEASONAL_SHAPE[k % 12]
            val = base * seasonal / SEASONAL_SHAPE.mean() + rng.normal(0, 15)
            rows.append(
                {
                    "center": c["center"],
                    "period": k + 1,
                    "received_t": max(0, round(val, 1)),
                }
            )
    return pd.DataFrame(rows)


def recovered_material_split() -> pd.DataFrame:
    """Approximate share of recovered mass by material (illustrative)."""
    return pd.DataFrame(
        {
            "material": ["Steel", "Aluminium", "Copper", "Lithium", "Cobalt"],
            "mass_share": [0.55, 0.18, 0.12, 0.09, 0.06],
            "value_per_t_usd": [320, 1900, 8200, 21000, 33000],
        }
    )


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


# --------------------------------------------------------------------------
# Sample (synthetic) dataset in the canonical 8-input shape
# --------------------------------------------------------------------------
# This is the ONLY place synthetic / random values are produced. It exists so
# the app can be demonstrated and tested without real uploads. Every dataset it
# produces is flagged ``is_sample=True`` and labelled "SAMPLE" in the UI/report.
def sample_frames(seed: int = RNG_SEED) -> dict:
    """Build pandas frames for all eight inputs (+ materials) of the canonical
    dataset, themed on Electrolux UAE sensitive-material recovery."""

    rng = np.random.default_rng(seed)
    centers = collection_centers(seed)
    hubs = recycling_hubs(seed)
    demand = returned_demand(seed=seed)
    costs = transport_costs(centers, hubs, seed)
    history = supplier_history(centers, seed=seed)
    materials = recovered_material_split()

    n = len(demand)
    supplier_names = centers["center"].tolist()
    hub_names = hubs["hub"].tolist()

    # 1. sales
    sales = pd.DataFrame(
        {
            "period": range(1, n + 1),
            "label": demand["month"].tolist(),
            "sales": demand["returned_units"].to_numpy(),
        }
    )

    # 2. suppliers (lead time / capacity / pricing contract)
    suppliers = pd.DataFrame(
        {
            "supplier": supplier_names,
            "lead_time_days": centers["lead_time_days"].to_numpy(),
            "capacity_t": centers["monthly_capacity_t"].to_numpy(),
            "price_per_t": centers["gate_fee_per_t"].to_numpy(),
        }
    )

    # 3. transport costs and routes (long format)
    rows = []
    for ci, c in enumerate(supplier_names):
        for hi, h in enumerate(hub_names):
            rows.append(
                {"source": c, "destination": h, "cost_per_t": float(costs.iloc[ci, hi])}
            )
    transport_costs_long = pd.DataFrame(rows)

    # 4. external factors affecting demand
    seasonal = np.tile(SEASONAL_SHAPE, (n // 12) + 1)[:n]
    external = pd.DataFrame(
        {
            "period": range(1, n + 1),
            "seasonality_index": np.round(seasonal, 3),
            "promotion": rng.integers(0, 2, n),
            "market_trend": np.round(
                1.0 + np.linspace(0, 0.15, n) + rng.normal(0, 0.02, n), 3
            ),
        }
    )

    # 5. inventory (stock / capacity / replenishment)
    processing = hubs["processing_demand_t"].to_numpy(dtype=float)
    inventory = pd.DataFrame(
        {
            "warehouse": hub_names,
            "current_stock_t": np.round(
                processing * rng.uniform(0.4, 1.3, len(hub_names)), 1
            ),
            "storage_capacity_t": np.round(processing * 2.5, 1),
            "replenishment_rate_t": np.round(processing, 1),
        }
    )

    # 6. customer orders (frequency / size / location)
    order_rows = []
    oid = 1
    for p in range(1, n + 1):
        k = int(rng.integers(3, 8))
        for _ in range(k):
            order_rows.append(
                {
                    "order_id": f"SO-{oid:04d}",
                    "period": p,
                    "size_t": round(float(rng.uniform(5, 60)), 1),
                    "location": str(rng.choice(hub_names)),
                }
            )
            oid += 1
    orders = pd.DataFrame(order_rows)

    # 7. warehouse operational parameters
    warehouse_params = pd.DataFrame(
        {
            "parameter": ["ordering_cost", "holding_cost_per_unit", "service_level"],
            "value": [250.0, 12.0, 0.95],
        }
    )

    # 8. historical transportation data
    hist_rows = []
    months_hist = 24
    for p in range(1, months_hist + 1):
        for ci, c in enumerate(supplier_names):
            # spread each center's received tonnage across hubs
            received = (
                float(
                    history[(history["center"] == c) & (history["period"] == p)][
                        "received_t"
                    ].iloc[0]
                )
                if not history[
                    (history["center"] == c) & (history["period"] == p)
                ].empty
                else 0.0
            )
            weights = rng.dirichlet(np.ones(len(hub_names)))
            for hi, h in enumerate(hub_names):
                vol = received * weights[hi]
                hist_rows.append(
                    {
                        "period": p,
                        "source": c,
                        "destination": h,
                        "volume_t": round(vol, 1),
                        "cost": round(vol * float(costs.iloc[ci, hi]), 1),
                    }
                )
    transport_history = pd.DataFrame(hist_rows)

    # materials (reference prices)
    materials_df = pd.DataFrame(
        {
            "material": materials["material"].tolist(),
            "mass_share": materials["mass_share"].tolist(),
            "value_per_t_usd": materials["value_per_t_usd"].tolist(),
        }
    )

    return {
        "sales": sales,
        "suppliers": suppliers,
        "transport_costs": transport_costs_long,
        "external": external,
        "inventory": inventory,
        "orders": orders,
        "warehouse_params": warehouse_params,
        "transport_history": transport_history,
        "materials": materials_df,
    }


def sample_dataset(seed: int = RNG_SEED) -> dict:
    """Return the canonical, validated SAMPLE dataset (flagged is_sample)."""
    from . import dataset as ds

    frames = sample_frames(seed)
    return ds.build_dataset(
        frames, name="SAMPLE — Electrolux UAE (synthetic)", is_sample=True
    )


def sample_csv_texts(seed: int = RNG_SEED) -> dict:
    """Return {input_kind: csv_text} for the sample dataset (for templates/tests)."""
    frames = sample_frames(seed)
    return {k: v.to_csv(index=False) for k, v in frames.items()}


if __name__ == "__main__":
    data = build_all()
    for k, v in data.items():
        print(f"\n=== {k} ===")
        print(v.head() if hasattr(v, "head") else v)
