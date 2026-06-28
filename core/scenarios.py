"""
Scenario layer for the Electrolux UAE supply-chain digital twin.

A *scenario* is a set of modifiers applied to the baseline synthetic network to
model operating conditions. Two presets are provided:

- ``NORMAL`` — business-as-usual: no modifiers (identity transform).
- ``HORMUZ_DISRUPTION`` — the 2026 Strait of Hormuz closure: longer lead times,
  higher transport cost plus a per-tonne war-risk insurance surcharge, selected
  direct routes disabled (forced to a prohibitive cost so the optimizer avoids
  them and reroutes via the Gulf of Oman), and elevated recovered-material
  demand as import substitution becomes a resilience lever.

``apply_scenario`` is a *pure* function: it never mutates its inputs. It returns
a brand-new ``data`` dict with deep copies of the affected frames so the same
baseline can be replayed under any scenario.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import List, Tuple

import numpy as np
import pandas as pd

# A cost high enough that any optimizer will avoid a disabled route, but finite
# so totals stay numeric (never inf/NaN) and the LP/heuristics remain stable.
PROHIBITIVE_COST = 1_000_000.0


@dataclass(frozen=True)
class Scenario:
    """Immutable description of an operating scenario.

    Attributes
    ----------
    name:
        Stable identifier, e.g. ``"normal"`` or ``"hormuz_disruption"``.
    label:
        Human-friendly display name.
    lead_time_add_days:
        Days added to every supplier/center lead time.
    transport_cost_multiplier:
        Multiplicative factor applied to every transport unit cost.
    insurance_surcharge_per_t:
        Flat per-tonne war-risk insurance surcharge added to every (non-dummy)
        transport cell after the multiplier.
    disabled_routes:
        ``(center_index, hub_index)`` pairs forced to ``PROHIBITIVE_COST`` to
        model direct routes closed by the disruption.
    recovered_demand_multiplier:
        Factor applied to recovered-material demand at the recycling hubs.
    """

    name: str
    label: str
    lead_time_add_days: int = 0
    transport_cost_multiplier: float = 1.0
    insurance_surcharge_per_t: float = 0.0
    disabled_routes: Tuple[Tuple[int, int], ...] = field(default_factory=tuple)
    recovered_demand_multiplier: float = 1.0

    @property
    def is_disrupted(self) -> bool:
        return self.name != NORMAL.name


# --------------------------------------------------------------------------
# Presets
# --------------------------------------------------------------------------
NORMAL = Scenario(
    name="normal",
    label="Normal Operations",
)

HORMUZ_DISRUPTION = Scenario(
    name="hormuz_disruption",
    label="Strait of Hormuz Disruption",
    lead_time_add_days=12,  # 10–14 day Cape-of-Good-Hope reroute
    transport_cost_multiplier=1.3,  # +30% freight under war risk
    insurance_surcharge_per_t=85.0,  # per-tonne war-risk insurance
    disabled_routes=((0, 0),),  # Jebel Ali -> KEZAD direct route closed
    recovered_demand_multiplier=1.25,  # import substitution lifts demand
)

PRESETS = {NORMAL.name: NORMAL, HORMUZ_DISRUPTION.name: HORMUZ_DISRUPTION}


def get_scenario(name: str) -> Scenario:
    """Resolve a scenario by name. Raises ``KeyError`` for unknown names."""
    key = (name or "").strip().lower()
    if key not in PRESETS:
        raise KeyError(f"Unknown scenario {name!r}. Valid options: {sorted(PRESETS)}")
    return PRESETS[key]


def list_scenarios() -> List[Scenario]:
    return [NORMAL, HORMUZ_DISRUPTION]


# --------------------------------------------------------------------------
# Application
# --------------------------------------------------------------------------
def apply_transport_costs(cost: np.ndarray, scenario: Scenario) -> np.ndarray:
    """Return a new cost matrix with the scenario's freight modifiers applied.

    Order of operations: multiplier, then per-tonne insurance surcharge, then
    disabled routes overwritten with ``PROHIBITIVE_COST``. The input is never
    mutated.
    """
    c = np.array(cost, dtype=float)
    c = c * scenario.transport_cost_multiplier + scenario.insurance_surcharge_per_t
    rows, cols = c.shape
    for i, j in scenario.disabled_routes:
        if 0 <= i < rows and 0 <= j < cols:
            c[i, j] = PROHIBITIVE_COST
    return c


def apply_scenario(data: dict, scenario: Scenario) -> dict:
    """Apply ``scenario`` to a baseline ``data`` dict (from ``build_all``).

    Returns a new dict with deep copies of every affected frame. The original
    ``data`` and all of its frames are left untouched.

    Modifies:
      - ``centers.lead_time_days`` += ``lead_time_add_days``
      - ``transport_costs`` via :func:`apply_transport_costs`
      - ``hubs.processing_demand_t`` *= ``recovered_demand_multiplier``
      - ``supplier_history`` is copied unchanged (identity, but isolated)
    """
    out = dict(data)  # shallow copy of the container

    centers = data["centers"].copy(deep=True)
    centers["lead_time_days"] = centers["lead_time_days"] + scenario.lead_time_add_days
    out["centers"] = centers

    tc = data["transport_costs"]
    new_costs = apply_transport_costs(tc.to_numpy(dtype=float), scenario)
    out["transport_costs"] = pd.DataFrame(
        new_costs, index=tc.index.copy(), columns=tc.columns.copy()
    )

    hubs = data["hubs"].copy(deep=True)
    hubs["processing_demand_t"] = (
        hubs["processing_demand_t"] * scenario.recovered_demand_multiplier
    )
    out["hubs"] = hubs

    # Copy the remaining frames so callers can never alias the baseline.
    out["demand"] = data["demand"].copy(deep=True)
    out["supplier_history"] = data["supplier_history"].copy(deep=True)
    out["materials"] = data["materials"].copy(deep=True)

    return out


__all__ = [
    "Scenario",
    "NORMAL",
    "HORMUZ_DISRUPTION",
    "PRESETS",
    "PROHIBITIVE_COST",
    "get_scenario",
    "list_scenarios",
    "apply_transport_costs",
    "apply_scenario",
    "replace",
]
