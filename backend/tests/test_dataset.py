"""Unit tests for the canonical dataset layer and accuracy helpers."""

from __future__ import annotations

import numpy as np
import pytest

from core import data_generator as dg
from core import dataset as ds
from core import forecasting as fc


def test_sample_dataset_has_all_inputs():
    d = dg.sample_dataset()
    assert d["meta"]["is_sample"] is True
    for key in (
        "sales",
        "suppliers",
        "inventory",
        "external",
        "orders",
        "transport_costs",
        "transport_history",
        "warehouse_params",
        "materials",
    ):
        assert key in d and d[key]
    assert set(d["warehouse_params"]) == {
        "ordering_cost",
        "holding_cost_per_unit",
        "service_level",
    }


def test_flexible_headers_and_synonyms():
    csv = "month,units\n1,100\n2,110\n3,130\n"
    frame = ds.parse_csv("sales", csv)
    assert list(frame.columns)[:2] == ["period", "sales"]
    assert frame["sales"].tolist() == [100, 110, 130]


def test_missing_column_raises_actionable_error():
    with pytest.raises(ds.DatasetError) as exc:
        ds.parse_csv("suppliers", "supplier,lead_time_days\nA,3\n")
    assert "capacity_t" in str(exc.value)


def test_non_numeric_value_rejected():
    with pytest.raises(ds.DatasetError):
        ds.parse_csv("sales", "period,sales\n1,abc\n")


def test_build_rejects_unknown_transport_source():
    texts = dg.sample_csv_texts()
    texts["transport_costs"] = (
        "source,destination,cost_per_t\nGHOST,KEZAD Recycling Hub,10\n"
    )
    with pytest.raises(ds.DatasetError) as exc:
        ds.build_from_csv_texts(texts, name="x")
    assert "not in suppliers" in str(exc.value)


def test_missing_route_becomes_prohibitive():
    texts = dg.sample_csv_texts()
    # Drop one route line entirely.
    lines = texts["transport_costs"].splitlines()
    texts["transport_costs"] = "\n".join([lines[0]] + lines[2:])
    d = ds.build_from_csv_texts(texts, name="x")
    m = ds.cost_matrix(d)
    assert (m >= 1_000_000.0).any()


def test_warehouse_params_validation():
    texts = dg.sample_csv_texts()
    texts["warehouse_params"] = (
        "parameter,value\nordering_cost,250\nholding_cost_per_unit,12\n"
        "service_level,1.4\n"
    )
    with pytest.raises(ds.DatasetError) as exc:
        ds.build_from_csv_texts(texts, name="x")
    assert "service_level" in str(exc.value)


def test_autotune_minimises_validation_error():
    series = [37, 40, 41, 37, 45, 50, 52, 49, 55, 60, 58, 63]
    t = fc.autotune_adjusted_es(series)
    assert 0 < t.alpha <= 0.95
    assert 0 <= t.beta <= 0.9
    # Tuned params should not be worse than a fixed mediocre baseline.
    base = fc.backtest_adjusted_es(series, alpha=0.1, beta=0.9, holdout=t.holdout or 3)
    tuned = fc.backtest_adjusted_es(
        series, alpha=t.alpha, beta=t.beta, holdout=t.holdout or 3
    )
    assert tuned.mad <= base.mad + 1e-6


def test_backtest_is_out_of_sample():
    series = list(range(1, 25))
    bt = fc.backtest_adjusted_es(series, alpha=0.5, beta=0.3, holdout=4)
    assert bt.holdout == 4
    assert bt.train_size == 20
    assert len(bt.predictions) == 4


def test_match_kind_real_world_names():
    cases = {
        "Sales (Demand)": "sales",
        "Suppliers": "suppliers",
        "Transport Costs": "transport_costs",
        "Transport Costs & Routes": "transport_costs",
        "External Factors": "external",
        "Inventory": "inventory",
        "Orders": "orders",
        "Warehouse Params": "warehouse_params",
        "Transport History": "transport_history",
        "Materials": "materials",
        "Summary": None,
        "historical_sales.csv": "sales",
        "Vendor List": "suppliers",
    }
    for name, expected in cases.items():
        assert ds.match_kind(name) == expected, (name, ds.match_kind(name))


def test_build_from_excel_with_descriptive_sheet_names_and_extra_columns():
    import io

    import pandas as pd

    frames = dg.sample_frames()
    rename = {
        "sales": "Sales (Demand)",
        "suppliers": "Suppliers",
        "transport_costs": "Transport Costs",
        "external": "External Factors",
        "inventory": "Inventory",
        "orders": "Orders",
        "warehouse_params": "Warehouse Params",
        "transport_history": "Transport History",
        "materials": "Materials",
    }
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        pd.DataFrame({"note": ["ignore me"]}).to_excel(
            w, sheet_name="Summary", index=False
        )
        for kind, df in frames.items():
            extra = df.copy()
            extra["extra_unused_column"] = 1  # rich real-world workbooks have extras
            extra.to_excel(w, sheet_name=rename[kind][:31], index=False)
    buf.seek(0)
    built = ds.build_from_excel(buf.read(), name="Descriptive")
    assert built["meta"]["n_periods"] == 36
    assert built["meta"]["n_suppliers"] == 4


def test_accessors():
    d = dg.sample_dataset()
    assert len(ds.sales_series(d)) == 36
    assert ds.cost_matrix(d).shape == (4, 3)
    assert np.all(ds.warehouse_demand(d) > 0)
