"""
Canonical dataset layer for the Digital Twin.

This module is the single source of truth for the *shape* of the data the twin
operates on. It maps the eight data-augmentation categories from the project
brief onto a normalised, JSON-serialisable structure, parses user-uploaded CSV
files into it (with flexible, case-insensitive header matching), and validates
cross-consistency between the inputs.

The eight required inputs (brief → canonical key):

    1. Historical sales data .................... sales
    2. Supplier data (lead time/capacity/price) . suppliers
    3. Transportation costs and routes .......... transport_costs
    4. External factors affecting demand ........ external
    5. Inventory data (stock/capacity/replenish). inventory  (a.k.a. warehouses)
    6. Customer order data ...................... orders
    7. Warehouse layout / operational params .... warehouse_params
    8. Historical transportation data ........... transport_history

`materials` is an optional ninth input (reference market prices for recovered
sensitive materials) used by the recovered-value lever; it is clearly labelled
as reference data, never fabricated operational data.

Nothing here is hard-coded business data. The only place synthetic values are
produced is the explicitly-labelled sample dataset (``core.data_generator``).
"""

from __future__ import annotations

import io
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

# Each input kind: canonical column -> list of accepted header synonyms.
SCHEMAS: Dict[str, Dict[str, List[str]]] = {
    "sales": {
        "period": ["period", "month", "t", "time", "index"],
        "label": ["label", "date", "month_name", "name"],
        "sales": ["sales", "demand", "units", "returned_units", "volume", "quantity"],
    },
    "suppliers": {
        "supplier": ["supplier", "center", "collection_center", "name", "source"],
        "lead_time_days": ["lead_time_days", "lead_time", "leadtime", "lead"],
        "capacity_t": [
            "capacity_t",
            "capacity",
            "monthly_capacity_t",
            "production_capacity",
        ],
        "price_per_t": [
            "price_per_t",
            "price",
            "gate_fee_per_t",
            "gate_fee",
            "cost_per_t",
        ],
    },
    "transport_costs": {
        "source": ["source", "supplier", "center", "from", "origin"],
        "destination": ["destination", "hub", "warehouse", "to", "dest"],
        "cost_per_t": ["cost_per_t", "cost", "unit_cost", "price"],
    },
    "external": {
        "period": ["period", "month", "t", "time", "index"],
        "seasonality_index": ["seasonality_index", "seasonality", "seasonal", "season"],
        "promotion": ["promotion", "promo", "promotions"],
        "market_trend": ["market_trend", "trend", "market_index", "market"],
    },
    "inventory": {
        "warehouse": ["warehouse", "hub", "location", "name", "destination"],
        "current_stock_t": ["current_stock_t", "current_stock", "stock", "on_hand"],
        "storage_capacity_t": ["storage_capacity_t", "storage_capacity", "capacity"],
        "replenishment_rate_t": [
            "replenishment_rate_t",
            "replenishment_rate",
            "replenishment",
            "demand_t",
            "processing_demand_t",
        ],
    },
    "orders": {
        "order_id": ["order_id", "id", "order"],
        "period": ["period", "month", "t", "time"],
        "size_t": ["size_t", "size", "quantity", "qty", "units"],
        "location": ["location", "region", "warehouse", "hub", "city"],
    },
    "warehouse_params": {
        "parameter": ["parameter", "param", "key", "name"],
        "value": ["value", "val", "amount"],
    },
    "transport_history": {
        "period": ["period", "month", "t", "time"],
        "source": ["source", "supplier", "center", "from", "origin"],
        "destination": ["destination", "hub", "warehouse", "to", "dest"],
        "volume_t": ["volume_t", "volume", "quantity", "qty", "shipped"],
        "cost": ["cost", "total_cost", "spend"],
    },
    "materials": {
        "material": ["material", "name"],
        "mass_share": ["mass_share", "share", "fraction"],
        "value_per_t_usd": ["value_per_t_usd", "value_per_t", "price_per_t", "value"],
    },
}

REQUIRED_INPUTS = [
    "sales",
    "suppliers",
    "transport_costs",
    "external",
    "inventory",
    "orders",
    "warehouse_params",
    "transport_history",
]
OPTIONAL_INPUTS = ["materials"]

NUMERIC_COLUMNS = {
    "sales": ["period", "sales"],
    "suppliers": ["lead_time_days", "capacity_t", "price_per_t"],
    "transport_costs": ["cost_per_t"],
    "external": ["period", "seasonality_index", "promotion", "market_trend"],
    "inventory": ["current_stock_t", "storage_capacity_t", "replenishment_rate_t"],
    "orders": ["period", "size_t"],
    "warehouse_params": ["value"],
    "transport_history": ["period", "volume_t", "cost"],
    "materials": ["mass_share", "value_per_t_usd"],
}

# Warehouse operational parameters expected as parameter/value rows.
WAREHOUSE_PARAM_KEYS = {
    "ordering_cost": ["ordering_cost", "order_cost", "setup_cost"],
    "holding_cost_per_unit": ["holding_cost_per_unit", "holding_cost", "carrying_cost"],
    "service_level": ["service_level", "service", "csl"],
}


class DatasetError(ValueError):
    """Raised when an input is missing, malformed, or inconsistent."""


def _normalise_headers(df: pd.DataFrame, kind: str) -> pd.DataFrame:
    """Rename columns to canonical names using the synonym table."""
    schema = SCHEMAS[kind]
    lower_map = {str(c).strip().lower().replace(" ", "_"): c for c in df.columns}
    rename: Dict[str, str] = {}
    for canonical, synonyms in schema.items():
        for syn in synonyms:
            if syn in lower_map:
                rename[lower_map[syn]] = canonical
                break
    df = df.rename(columns=rename)
    return df


def parse_csv(kind: str, content: str) -> pd.DataFrame:
    """Parse raw CSV ``content`` for ``kind`` into a normalised DataFrame.

    Raises ``DatasetError`` with an actionable message on any problem.
    """
    if kind not in SCHEMAS:
        raise DatasetError(f"Unknown input type {kind!r}.")
    try:
        df = pd.read_csv(io.StringIO(content))
    except Exception as exc:  # noqa: BLE001 - surface parse errors to the user
        raise DatasetError(f"{kind}: could not parse CSV ({exc}).") from exc
    if df.empty:
        raise DatasetError(f"{kind}: file contains no rows.")

    df = _normalise_headers(df, kind)

    # Required canonical columns: every schema key except those that are clearly
    # optional (label is optional for sales).
    optional = {"label"}
    required_cols = [c for c in SCHEMAS[kind] if c not in optional]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        accepted = {c: SCHEMAS[kind][c] for c in missing}
        raise DatasetError(
            f"{kind}: missing required column(s) {missing}. "
            f"Accepted header names: {accepted}."
        )

    for col in NUMERIC_COLUMNS.get(kind, []):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            if df[col].isna().any():
                bad = int(df[col].isna().sum())
                raise DatasetError(
                    f"{kind}: column '{col}' has {bad} non-numeric/empty value(s)."
                )

    return df.reset_index(drop=True)


def _series_label(row_period: int, label: Optional[str]) -> str:
    return str(label) if label is not None and str(label) != "nan" else f"P{row_period}"


def build_dataset(
    frames: Dict[str, pd.DataFrame], name: str, is_sample: bool = False
) -> dict:
    """Assemble parsed frames into the canonical, JSON-serialisable dataset.

    Validates cross-consistency: transport sources ⊆ suppliers, transport
    destinations ⊆ inventory warehouses, and aligned period coverage.
    """
    warnings: List[str] = []

    missing_inputs = [k for k in REQUIRED_INPUTS if k not in frames]
    if missing_inputs:
        raise DatasetError(
            "Missing required input(s): "
            + ", ".join(missing_inputs)
            + ". All eight data categories are required."
        )

    sales = frames["sales"].sort_values("period").reset_index(drop=True)
    suppliers = frames["suppliers"].reset_index(drop=True)
    inventory = frames["inventory"].reset_index(drop=True)
    external = frames["external"].sort_values("period").reset_index(drop=True)
    orders = frames["orders"].reset_index(drop=True)
    tc = frames["transport_costs"].reset_index(drop=True)
    th = frames["transport_history"].reset_index(drop=True)
    wp = frames["warehouse_params"].reset_index(drop=True)

    supplier_names = suppliers["supplier"].astype(str).tolist()
    warehouse_names = inventory["warehouse"].astype(str).tolist()

    # --- transport cost matrix (sources x destinations) -------------------
    tc_sources = tc["source"].astype(str)
    tc_dests = tc["destination"].astype(str)
    unknown_src = sorted(set(tc_sources) - set(supplier_names))
    unknown_dst = sorted(set(tc_dests) - set(warehouse_names))
    if unknown_src:
        raise DatasetError(
            f"transport_costs references source(s) not in suppliers: {unknown_src}."
        )
    if unknown_dst:
        raise DatasetError(
            f"transport_costs references destination(s) not in inventory "
            f"warehouses: {unknown_dst}."
        )

    matrix = np.full((len(supplier_names), len(warehouse_names)), np.nan)
    src_idx = {s: i for i, s in enumerate(supplier_names)}
    dst_idx = {d: j for j, d in enumerate(warehouse_names)}
    for _, r in tc.iterrows():
        matrix[src_idx[str(r["source"])], dst_idx[str(r["destination"])]] = r[
            "cost_per_t"
        ]
    if np.isnan(matrix).any():
        n_missing = int(np.isnan(matrix).sum())
        warnings.append(
            f"{n_missing} source→destination route(s) have no cost; treated as "
            "unavailable (prohibitive cost)."
        )

    # --- warehouse operational parameters --------------------------------
    params = _parse_warehouse_params(wp)

    # --- canonical records ------------------------------------------------
    sales_records = [
        {
            "period": int(r["period"]),
            "label": _series_label(int(r["period"]), r.get("label")),
            "sales": float(r["sales"]),
        }
        for _, r in sales.iterrows()
    ]

    suppliers_records = [
        {
            "supplier": str(r["supplier"]),
            "lead_time_days": int(round(float(r["lead_time_days"]))),
            "capacity_t": float(r["capacity_t"]),
            "price_per_t": float(r["price_per_t"]),
        }
        for _, r in suppliers.iterrows()
    ]

    inventory_records = [
        {
            "warehouse": str(r["warehouse"]),
            "current_stock_t": float(r["current_stock_t"]),
            "storage_capacity_t": float(r["storage_capacity_t"]),
            "replenishment_rate_t": float(r["replenishment_rate_t"]),
        }
        for _, r in inventory.iterrows()
    ]

    external_records = [
        {
            "period": int(r["period"]),
            "seasonality_index": float(r["seasonality_index"]),
            "promotion": float(r["promotion"]),
            "market_trend": float(r["market_trend"]),
        }
        for _, r in external.iterrows()
    ]

    orders_records = [
        {
            "order_id": str(r["order_id"]),
            "period": int(r["period"]),
            "size_t": float(r["size_t"]),
            "location": str(r["location"]),
        }
        for _, r in orders.iterrows()
    ]

    history_records = [
        {
            "period": int(r["period"]),
            "source": str(r["source"]),
            "destination": str(r["destination"]),
            "volume_t": float(r["volume_t"]),
            "cost": float(r["cost"]),
        }
        for _, r in th.iterrows()
    ]

    # Optional materials reference table.
    if "materials" in frames:
        mat = frames["materials"]
        materials_records = [
            {
                "material": str(r["material"]),
                "mass_share": float(r["mass_share"]),
                "value_per_t_usd": float(r["value_per_t_usd"]),
            }
            for _, r in mat.iterrows()
        ]
    else:
        materials_records = []
        warnings.append(
            "No materials reference table supplied; recovered-material value "
            "lever is disabled until materials prices are provided."
        )

    # Period coverage sanity check between sales and external factors.
    sales_periods = {rec["period"] for rec in sales_records}
    ext_periods = {rec["period"] for rec in external_records}
    if not sales_periods.issubset(ext_periods):
        warnings.append(
            "External factors do not cover every sales period; missing periods "
            "use a neutral factor of 1.0."
        )

    return {
        "meta": {
            "name": name,
            "is_sample": bool(is_sample),
            "n_periods": len(sales_records),
            "n_suppliers": len(suppliers_records),
            "n_warehouses": len(inventory_records),
            "n_orders": len(orders_records),
            "warnings": warnings,
        },
        "sales": sales_records,
        "suppliers": suppliers_records,
        "inventory": inventory_records,
        "external": external_records,
        "orders": orders_records,
        "transport_costs": {
            "sources": supplier_names,
            "destinations": warehouse_names,
            "matrix": [
                [None if np.isnan(v) else round(float(v), 4) for v in row]
                for row in matrix
            ],
        },
        "transport_history": history_records,
        "warehouse_params": params,
        "materials": materials_records,
    }


def _parse_warehouse_params(wp: pd.DataFrame) -> dict:
    """Extract ordering_cost, holding_cost_per_unit, service_level from rows."""
    found: Dict[str, float] = {}
    for _, r in wp.iterrows():
        key = str(r["parameter"]).strip().lower().replace(" ", "_")
        for canonical, synonyms in WAREHOUSE_PARAM_KEYS.items():
            if key in synonyms:
                found[canonical] = float(r["value"])
                break
    missing = [k for k in WAREHOUSE_PARAM_KEYS if k not in found]
    if missing:
        raise DatasetError(
            "warehouse_params missing required parameter(s): "
            + ", ".join(missing)
            + ". Provide them as parameter/value rows."
        )
    sl = found["service_level"]
    if not 0.5 < sl < 1.0:
        raise DatasetError(
            f"warehouse_params service_level must be in (0.5, 1.0); got {sl}."
        )
    if found["ordering_cost"] <= 0 or found["holding_cost_per_unit"] <= 0:
        raise DatasetError(
            "warehouse_params ordering_cost and holding_cost_per_unit must be > 0."
        )
    return found


def build_from_csv_texts(
    texts: Dict[str, str], name: str, is_sample: bool = False
) -> dict:
    """Parse a mapping of {input_kind: csv_text} and build the canonical dataset."""
    frames: Dict[str, pd.DataFrame] = {}
    for kind, content in texts.items():
        if kind in SCHEMAS and content and content.strip():
            frames[kind] = parse_csv(kind, content)
    return build_dataset(frames, name=name, is_sample=is_sample)


# --------------------------------------------------------------------------
# Accessors used by the service/compute layer
# --------------------------------------------------------------------------
def sales_series(ds: dict) -> np.ndarray:
    return np.array([r["sales"] for r in ds["sales"]], dtype=float)


def sales_labels(ds: dict) -> List[str]:
    return [r["label"] for r in ds["sales"]]


def cost_matrix(ds: dict, prohibitive: float = 1_000_000.0) -> np.ndarray:
    """Dense cost matrix with missing routes set to ``prohibitive``."""
    raw = ds["transport_costs"]["matrix"]
    out = np.array(
        [[prohibitive if v is None else float(v) for v in row] for row in raw],
        dtype=float,
    )
    return out


def supplier_capacity(ds: dict) -> np.ndarray:
    return np.array([s["capacity_t"] for s in ds["suppliers"]], dtype=float)


def warehouse_demand(ds: dict) -> np.ndarray:
    """Per-warehouse replenishment requirement = transport demand."""
    return np.array([w["replenishment_rate_t"] for w in ds["inventory"]], dtype=float)
