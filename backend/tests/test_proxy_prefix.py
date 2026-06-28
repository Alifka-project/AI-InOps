"""The backend must answer whether or not the platform strips the proxy prefix."""

from __future__ import annotations


def test_health_without_prefix(client):
    assert client.get("/health").status_code == 200


def test_health_with_proxy_prefix(client):
    # Simulates a platform that forwards the full "/_/backend/..." path.
    r = client.get("/_/backend/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_api_with_proxy_prefix(client):
    r = client.get("/_/backend/api/scenarios")
    assert r.status_code == 200
    assert [s["name"] for s in r.json()] == ["normal", "hormuz_disruption"]


def test_prefixed_post_with_query_preserved(client, sample):
    r = client.post("/_/backend/api/simulate", json={"dataset": sample})
    assert r.status_code == 200
    assert len(r.json()["actual"]) == 36
