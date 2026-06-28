"""Unit tests for the scenario layer (core.scenarios)."""

from __future__ import annotations

import numpy as np

from core import data_generator as dg
from core.scenarios import (
    HORMUZ_DISRUPTION,
    NORMAL,
    PROHIBITIVE_COST,
    apply_scenario,
    apply_transport_costs,
    get_scenario,
)


def test_presets_resolve():
    assert get_scenario("normal") is NORMAL
    assert get_scenario("HORMUZ_DISRUPTION") is HORMUZ_DISRUPTION


def test_unknown_scenario_raises():
    try:
        get_scenario("nope")
    except KeyError:
        return
    raise AssertionError("expected KeyError")


def test_normal_is_identity_on_costs():
    cost = np.array([[6.0, 8.0], [7.0, 11.0]])
    out = apply_transport_costs(cost, NORMAL)
    assert np.allclose(out, cost)
    # Original is untouched.
    assert np.allclose(cost, [[6.0, 8.0], [7.0, 11.0]])


def test_disruption_cost_modifiers():
    cost = np.array([[10.0, 20.0], [30.0, 40.0]])
    out = apply_transport_costs(cost, HORMUZ_DISRUPTION)
    # cell (0,0) is a disabled route -> prohibitive.
    assert out[0, 0] == PROHIBITIVE_COST
    # other cells: *1.3 + 85 surcharge.
    assert np.isclose(out[0, 1], 20.0 * 1.3 + 85.0)
    assert np.isclose(out[1, 0], 30.0 * 1.3 + 85.0)


def test_apply_scenario_is_pure():
    data = dg.build_all()
    before_lead = data["centers"]["lead_time_days"].tolist()
    before_cost = data["transport_costs"].to_numpy().copy()
    before_demand = data["hubs"]["processing_demand_t"].tolist()

    out = apply_scenario(data, HORMUZ_DISRUPTION)

    # Inputs unchanged.
    assert data["centers"]["lead_time_days"].tolist() == before_lead
    assert np.allclose(data["transport_costs"].to_numpy(), before_cost)
    assert data["hubs"]["processing_demand_t"].tolist() == before_demand

    # Outputs modified.
    assert out["centers"]["lead_time_days"].tolist() == [x + 12 for x in before_lead]
    assert out["hubs"]["processing_demand_t"].tolist() == [
        x * 1.25 for x in before_demand
    ]


def test_normal_apply_scenario_preserves_values():
    data = dg.build_all()
    out = apply_scenario(data, NORMAL)
    assert out["centers"]["lead_time_days"].tolist() == (
        data["centers"]["lead_time_days"].tolist()
    )
    assert np.allclose(
        out["transport_costs"].to_numpy(), data["transport_costs"].to_numpy()
    )
