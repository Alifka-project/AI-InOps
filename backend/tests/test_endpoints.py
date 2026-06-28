"""Endpoint tests via TestClient — stateless dataset-driven API."""

from __future__ import annotations

import json

from core import data_generator as dg


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_parse_combined_excel(client):
    xlsx = dg.sample_excel_bytes()
    files = {
        "file": (
            "network.xlsx",
            xlsx,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }
    r = client.post("/api/datasets/parse-combined", data={"name": "Combo"}, files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["dataset"]["meta"]["name"] == "Combo"
    assert body["dataset"]["meta"]["n_periods"] == 36
    assert body["dataset"]["meta"]["is_sample"] is False


def test_parse_combined_zip(client):
    z = dg.sample_zip_bytes()
    files = {"file": ("network.zip", z, "application/zip")}
    r = client.post("/api/datasets/parse-combined", files=files)
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_parse_combined_json_roundtrip(client):
    ds = client.get("/api/datasets/sample").json()
    blob = json.dumps(ds).encode()
    files = {"file": ("network.json", blob, "application/json")}
    r = client.post("/api/datasets/parse-combined", files=files)
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_parse_combined_bad_excel_returns_structured_error(client):
    files = {"file": ("bad.xlsx", b"not really an excel file", "application/octet-stream")}
    r = client.post("/api/datasets/parse-combined", files=files)
    assert r.status_code == 200
    assert r.json()["ok"] is False
    assert r.json()["errors"]


def test_template_combined_xlsx(client):
    r = client.get("/api/datasets/template-combined")
    assert r.status_code == 200
    assert "spreadsheetml" in r.headers["content-type"]
    assert r.content[:2] == b"PK"  # xlsx is a zip container


def test_template_combined_zip(client):
    r = client.get("/api/datasets/template-combined", params={"format": "zip"})
    assert r.status_code == 200
    assert r.content[:2] == b"PK"


def test_scenarios_metadata(client):
    r = client.get("/api/scenarios")
    assert r.status_code == 200
    assert [s["name"] for s in r.json()] == ["normal", "hormuz_disruption"]


def test_sample_dataset_is_flagged(client):
    r = client.get("/api/datasets/sample")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["is_sample"] is True
    assert body["meta"]["n_periods"] == 36
    assert len(body["suppliers"]) == 4
    assert len(body["inventory"]) == 3


def test_parse_upload_round_trip(client, sample_csvs):
    files = {k: (f"{k}.csv", v, "text/csv") for k, v in sample_csvs.items()}
    r = client.post("/api/datasets/parse", data={"name": "Acme"}, files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["dataset"]["meta"]["is_sample"] is False
    assert body["dataset"]["meta"]["name"] == "Acme"


def test_parse_upload_missing_required_input(client, sample_csvs):
    partial = {k: v for k, v in sample_csvs.items() if k != "inventory"}
    files = {k: (f"{k}.csv", v, "text/csv") for k, v in partial.items()}
    r = client.post("/api/datasets/parse", files=files)
    # inventory is a required File(...) -> 422 from FastAPI
    assert r.status_code == 422


def test_parse_upload_bad_csv_returns_structured_error(client, sample_csvs):
    bad = dict(sample_csvs)
    bad["sales"] = "wrong,header\n1,2\n"
    files = {k: (f"{k}.csv", v, "text/csv") for k, v in bad.items()}
    r = client.post("/api/datasets/parse", files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert any("sales" in e for e in body["errors"])


def test_forecast_demand(client, sample):
    r = client.post(
        "/api/forecast/demand",
        json={"dataset": sample, "alpha": 0.5, "beta": 0.3, "horizon": 4},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["forecast_horizon"]) == 4
    for key in ("adjusted_es", "linear_trend", "seasonal"):
        assert set(body[key]["metrics"]) == {"MAD", "MSE", "MAPE", "Bias"}
    assert "validation" in body and body["validation"]["holdout"] >= 1


def test_forecast_autotune_sets_params(client, sample):
    r = client.post(
        "/api/forecast/demand",
        json={"dataset": sample, "auto_tune": True, "horizon": 3},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["auto_tuned"] is True
    assert body["tuning"] is not None
    assert 0 < body["alpha"] <= 1


def test_forecast_planning_demand_scales_under_disruption(client, sample):
    base = {"dataset": sample, "alpha": 0.5, "beta": 0.3, "horizon": 3}
    n = client.post("/api/forecast/demand", json={**base, "scenario": "normal"}).json()
    d = client.post(
        "/api/forecast/demand", json={**base, "scenario": "hormuz_disruption"}
    ).json()
    assert d["planning_demand_next"] > n["planning_demand_next"]


def test_forecast_validation_alpha_out_of_range(client, sample):
    r = client.post("/api/forecast/demand", json={"dataset": sample, "alpha": 1.5})
    assert r.status_code == 422


def test_suppliers_lead_time_impact(client, sample):
    r = client.post(
        "/api/forecast/suppliers",
        json={"dataset": sample, "scenario": "hormuz_disruption"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["lead_time_add_days"] == 12
    assert len(body["suppliers"]) == 4


def test_transport_default_agrees(client, sample):
    r = client.post("/api/optimize/transport", json={"dataset": sample})
    assert r.status_code == 200
    body = r.json()
    assert body["all_methods_agree"] is True
    assert len(body["comparison"]) == 6


def test_transport_known_optimum_4525(client, sample):
    payload = {
        "dataset": sample,
        "initial": "vogel",
        "optimize": "modi",
        "cost": [[6, 8, 10], [7, 11, 11], [4, 5, 12]],
        "supply": [150, 175, 275],
        "demand": [200, 100, 300],
    }
    r = client.post("/api/optimize/transport", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert round(body["total_cost"]) == 4525
    assert body["all_methods_agree"] is True
    assert body["balanced"] is True


def test_transport_invalid_matrix_shape(client, sample):
    r = client.post(
        "/api/optimize/transport",
        json={"dataset": sample, "cost": [[1, 2, 3], [4, 5]]},
    )
    assert r.status_code == 422


def test_warehouse_uses_real_stock_and_params(client, sample):
    r = client.post("/api/warehouse/policy", json={"dataset": sample})
    assert r.status_code == 200
    body = r.json()
    assert len(body["policies"]) == 3
    assert body["ordering_cost"] == 250.0
    assert body["holding_cost_per_unit"] == 12.0
    # current stock must equal the inventory feed (no randomisation)
    inv = {i["warehouse"]: i["current_stock_t"] for i in sample["inventory"]}
    for p in body["policies"]:
        assert abs(p["current_stock"] - inv[p["hub"]]) < 0.05
        assert p["status"] in {"OK", "REORDER", "CRITICAL"}


def test_materials_recovery_scales(client, sample):
    n = client.post(
        "/api/materials/recovery", json={"dataset": sample, "scenario": "normal"}
    ).json()
    d = client.post(
        "/api/materials/recovery",
        json={"dataset": sample, "scenario": "hormuz_disruption"},
    ).json()
    assert n["enabled"] is True
    assert len(n["materials"]) == 5
    assert d["total_value_usd"] >= n["total_value_usd"]


def test_simulate_and_compare(client, sample):
    r = client.post("/api/simulate", json={"dataset": sample})
    assert r.status_code == 200
    assert len(r.json()["actual"]) == 36

    c = client.post("/api/simulate/compare", json={"dataset": sample})
    assert c.status_code == 200
    body = c.json()
    assert (
        body["hormuz_disruption"]["optimal_transport_cost"]
        > body["normal"]["optimal_transport_cost"]
    )


def test_report_returns_pdf(client, sample):
    r = client.post(
        "/api/report",
        json={"dataset": sample, "scenario": "hormuz_disruption", "auto_tune": False},
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 2000
