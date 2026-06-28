"""Endpoint tests via FastAPI TestClient — happy paths, validation, scenarios."""

from __future__ import annotations


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "docs" in r.json()


def test_scenarios_metadata(client):
    r = client.get("/api/scenarios")
    assert r.status_code == 200
    names = [s["name"] for s in r.json()]
    assert names == ["normal", "hormuz_disruption"]


def test_data_default(client):
    r = client.get("/api/data")
    assert r.status_code == 200
    body = r.json()
    assert len(body["demand"]) == 36
    assert len(body["center_names"]) == 4
    assert len(body["hub_names"]) == 3


def test_data_scenario_changes_lead_time(client):
    normal = client.get("/api/data", params={"scenario": "normal"}).json()
    disrupt = client.get("/api/data", params={"scenario": "hormuz_disruption"}).json()
    n_lead = [c["lead_time_days"] for c in normal["centers"]]
    d_lead = [c["lead_time_days"] for c in disrupt["centers"]]
    assert d_lead == [x + 12 for x in n_lead]


def test_forecast_demand_methods_and_metrics(client):
    r = client.post(
        "/api/forecast/demand",
        json={"scenario": "normal", "alpha": 0.5, "beta": 0.3, "horizon": 3},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["forecast_horizon"]) == 3
    for key in ("adjusted_es", "linear_trend", "seasonal"):
        assert set(body[key]["metrics"]) == {"MAD", "MSE", "MAPE", "Bias"}


def test_forecast_planning_demand_scales_under_disruption(client):
    base = {"alpha": 0.5, "beta": 0.3, "horizon": 3}
    n = client.post("/api/forecast/demand", json={**base, "scenario": "normal"}).json()
    d = client.post(
        "/api/forecast/demand", json={**base, "scenario": "hormuz_disruption"}
    ).json()
    assert d["planning_demand_next"] > n["planning_demand_next"]


def test_forecast_validation_alpha_out_of_range(client):
    r = client.post("/api/forecast/demand", json={"alpha": 1.5})
    assert r.status_code == 422
    assert r.json()["error"]["type"] == "validation_error"


def test_suppliers_lead_time_impact(client):
    r = client.post("/api/forecast/suppliers", json={"scenario": "hormuz_disruption"})
    assert r.status_code == 200
    body = r.json()
    assert body["lead_time_add_days"] == 12
    assert len(body["suppliers"]) == 4


def test_transport_default_balanced_normal(client):
    r = client.post("/api/optimize/transport", json={"scenario": "normal"})
    assert r.status_code == 200
    body = r.json()
    assert body["all_methods_agree"] is True
    assert len(body["comparison"]) == 6


def test_transport_known_problem_optimum_4525(client):
    payload = {
        "scenario": "normal",
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


def test_transport_unbalanced_dummy(client):
    payload = {
        "scenario": "normal",
        "cost": [[6, 8], [7, 11], [4, 5]],
        "supply": [150, 175, 275],
        "demand": [200, 100],
    }
    r = client.post("/api/optimize/transport", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["balanced"] is False
    assert body["dummy_added"] == "destination"


def test_transport_invalid_matrix_shape(client):
    payload = {"cost": [[1, 2, 3], [4, 5]]}
    r = client.post("/api/optimize/transport", json=payload)
    assert r.status_code == 422


def test_transport_negative_cost_rejected(client):
    payload = {"cost": [[1, -2], [3, 4]]}
    r = client.post("/api/optimize/transport", json=payload)
    assert r.status_code == 422


def test_warehouse_policy(client):
    r = client.post(
        "/api/warehouse/policy",
        json={"scenario": "normal", "service_level": 0.95},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["policies"]) == 3
    for p in body["policies"]:
        assert p["status"] in {"OK", "REORDER", "CRITICAL"}


def test_warehouse_service_level_validation(client):
    r = client.post("/api/warehouse/policy", json={"service_level": 1.0})
    assert r.status_code == 422


def test_materials_recovery_scales(client):
    n = client.get("/api/materials/recovery", params={"scenario": "normal"}).json()
    d = client.get(
        "/api/materials/recovery", params={"scenario": "hormuz_disruption"}
    ).json()
    assert len(n["materials"]) == 5
    assert d["total_value_usd"] >= n["total_value_usd"]


def test_simulate_payload(client):
    r = client.post("/api/simulate", json={"scenario": "normal"})
    assert r.status_code == 200
    body = r.json()
    assert set(body["kpis"]) >= {
        "next_month_demand",
        "optimal_transport_cost",
        "avg_supplier_utilization",
        "recovered_material_value",
        "hubs_needing_reorder",
    }
    assert len(body["actual"]) == 36


def test_simulate_compare(client):
    r = client.post("/api/simulate/compare", json={})
    assert r.status_code == 200
    body = r.json()
    assert "normal" in body and "hormuz_disruption" in body
    # Disruption raises transport cost.
    assert (
        body["hormuz_disruption"]["optimal_transport_cost"]
        > body["normal"]["optimal_transport_cost"]
    )
