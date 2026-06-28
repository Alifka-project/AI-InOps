"""API-facing adapter over ``core.scenarios``.

The algorithmic scenario modifiers live in the verified ``core`` engine. This
thin module maps API scenario names to those presets and exposes a small,
JSON-friendly description used by the ``/api/scenarios`` metadata endpoint.
"""

from __future__ import annotations

from typing import Dict, List

from core import scenarios as core_scenarios
from core.scenarios import Scenario, apply_scenario, get_scenario  # re-export

ScenarioName = str


def describe(scenario: Scenario) -> Dict[str, object]:
    """A serialisable summary of a scenario's modifiers."""
    return {
        "name": scenario.name,
        "label": scenario.label,
        "is_disrupted": scenario.is_disrupted,
        "lead_time_add_days": scenario.lead_time_add_days,
        "transport_cost_multiplier": scenario.transport_cost_multiplier,
        "insurance_surcharge_per_t": scenario.insurance_surcharge_per_t,
        "disabled_routes": [list(r) for r in scenario.disabled_routes],
        "recovered_demand_multiplier": scenario.recovered_demand_multiplier,
    }


def all_descriptions() -> List[Dict[str, object]]:
    return [describe(s) for s in core_scenarios.list_scenarios()]


__all__ = [
    "Scenario",
    "ScenarioName",
    "apply_scenario",
    "get_scenario",
    "describe",
    "all_descriptions",
]
