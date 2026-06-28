"""
Transportation problem optimization.

Minimize total shipping cost moving recovered material from collection
centers (sources, with supply) to recycling hubs (destinations, with demand).

Initial basic feasible solutions:
  - Northwest Corner Method (NWC)
  - Least / Minimum Cell Cost Method (LCM)
  - Vogel's Approximation Method (VAM)

Optimality tests / improvement:
  - Stepping Stone Method
  - MODI (Modified Distribution) Method

Handles both balanced (sum supply == sum demand) and unbalanced problems
(a dummy source or destination with zero cost is added automatically).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

EPS = 1e-9


@dataclass
class TransportSolution:
    allocation: np.ndarray  # m x n shipment quantities
    cost_matrix: np.ndarray  # m x n unit costs (after balancing)
    total_cost: float
    supply: np.ndarray
    demand: np.ndarray
    balanced: bool  # was the ORIGINAL problem balanced?
    dummy_added: str  # "", "source", or "destination"
    method: str


# --------------------------------------------------------------------------
# Balancing
# --------------------------------------------------------------------------
def balance(cost, supply, demand):
    """Return (cost, supply, demand, balanced, dummy_added) with a zero-cost
    dummy row/column added if total supply != total demand."""
    cost = np.array(cost, dtype=float)
    supply = np.array(supply, dtype=float)
    demand = np.array(demand, dtype=float)
    s, d = supply.sum(), demand.sum()
    if abs(s - d) < EPS:
        return cost, supply, demand, True, ""
    if s < d:  # need a dummy SOURCE that supplies the shortfall at zero cost
        dummy_row = np.zeros((1, cost.shape[1]))
        cost = np.vstack([cost, dummy_row])
        supply = np.append(supply, d - s)
        return cost, supply, demand, False, "source"
    else:  # need a dummy DESTINATION that absorbs the surplus
        dummy_col = np.zeros((cost.shape[0], 1))
        cost = np.hstack([cost, dummy_col])
        demand = np.append(demand, s - d)
        return cost, supply, demand, False, "destination"


def total_cost(allocation, cost) -> float:
    return float(np.sum(np.asarray(allocation) * np.asarray(cost)))


# --------------------------------------------------------------------------
# Initial solutions
# --------------------------------------------------------------------------
def northwest_corner(supply, demand):
    s = np.array(supply, dtype=float).copy()
    d = np.array(demand, dtype=float).copy()
    m, n = len(s), len(d)
    alloc = np.zeros((m, n))
    i = j = 0
    while i < m and j < n:
        q = min(s[i], d[j])
        alloc[i, j] = q
        s[i] -= q
        d[j] -= q
        if s[i] < EPS and i < m - 1:
            i += 1
        elif d[j] < EPS and j < n - 1:
            j += 1
        elif s[i] < EPS:
            i += 1
        else:
            j += 1
    return alloc


def least_cost(cost, supply, demand):
    c = np.array(cost, dtype=float)
    s = np.array(supply, dtype=float).copy()
    d = np.array(demand, dtype=float).copy()
    m, n = c.shape
    alloc = np.zeros((m, n))
    done = np.zeros((m, n), dtype=bool)
    while (s.sum() > EPS) and (d.sum() > EPS):
        masked = np.where(done, np.inf, c)
        # only consider cells with remaining supply and demand
        for r in range(m):
            if s[r] < EPS:
                masked[r, :] = np.inf
        for col in range(n):
            if d[col] < EPS:
                masked[:, col] = np.inf
        if not np.isfinite(masked).any():
            break
        i, j = np.unravel_index(np.argmin(masked), masked.shape)
        q = min(s[i], d[j])
        alloc[i, j] = q
        s[i] -= q
        d[j] -= q
        done[i, j] = True
    return alloc


def vogel(cost, supply, demand):
    c = np.array(cost, dtype=float)
    s = np.array(supply, dtype=float).copy()
    d = np.array(demand, dtype=float).copy()
    m, n = c.shape
    alloc = np.zeros((m, n))
    row_active = np.ones(m, dtype=bool)
    col_active = np.ones(n, dtype=bool)

    def penalty(values):
        vals = np.sort(values)
        return (vals[1] - vals[0]) if len(vals) >= 2 else vals[0]

    while row_active.any() and col_active.any():
        if s[row_active].sum() < EPS or d[col_active].sum() < EPS:
            break
        best_pen, best_is_row, best_idx = -1, True, -1
        # row penalties
        for r in np.where(row_active)[0]:
            costs = c[r, col_active]
            if len(costs) == 0:
                continue
            p = penalty(costs)
            if p > best_pen:
                best_pen, best_is_row, best_idx = p, True, r
        # column penalties
        for col in np.where(col_active)[0]:
            costs = c[row_active, col]
            if len(costs) == 0:
                continue
            p = penalty(costs)
            if p > best_pen:
                best_pen, best_is_row, best_idx = p, False, col

        if best_is_row:
            r = best_idx
            cols = np.where(col_active)[0]
            j = cols[np.argmin(c[r, cols])]
            i = r
        else:
            col = best_idx
            rows = np.where(row_active)[0]
            i = rows[np.argmin(c[rows, col])]
            j = col

        q = min(s[i], d[j])
        alloc[i, j] = q
        s[i] -= q
        d[j] -= q
        if s[i] < EPS:
            row_active[i] = False
        if d[j] < EPS:
            col_active[j] = False
    return alloc


# --------------------------------------------------------------------------
# Loop finding (shared by Stepping Stone and MODI pivoting)
# --------------------------------------------------------------------------
def _basic_cells(alloc):
    return [
        (i, j)
        for i in range(alloc.shape[0])
        for j in range(alloc.shape[1])
        if alloc[i, j] > EPS
    ]


def _find_loop(start, basic):
    """Find a closed loop starting/ending at `start` using only `basic` cells
    as the other corners. Returns the ordered list of cells in the loop, or None.
    Alternates horizontal and vertical moves."""
    nodes = [start] + [c for c in basic if c != start]

    def search(path, horizontal):
        last = path[-1]
        if len(path) > 3 and last[0] == start[0] and last[1] == start[1]:
            return path[:-1]
        candidates = []
        for cell in nodes:
            if cell in path[1:]:
                continue
            if horizontal and cell[0] == last[0] and cell[1] != last[1]:
                candidates.append(cell)
            elif (not horizontal) and cell[1] == last[1] and cell[0] != last[0]:
                candidates.append(cell)
        # allow returning to start to close the loop
        if start not in candidates:
            if horizontal and start[0] == last[0] and start != last:
                candidates.append(start)
            elif (not horizontal) and start[1] == last[1] and start != last:
                candidates.append(start)
        for cell in candidates:
            res = search(path + [cell], not horizontal)
            if res:
                return res
        return None

    # first move can be horizontal or vertical
    for horiz in (True, False):
        res = search([start], horiz)
        if res and len(res) >= 4 and len(res) % 2 == 0:
            return res
    return None


# --------------------------------------------------------------------------
# MODI (Modified Distribution) optimality test + improvement
# --------------------------------------------------------------------------
def _ensure_nondegenerate(alloc, basic):
    """If basic cells < m+n-1, add zero-quantity basic cells to break
    degeneracy so u/v can be solved."""
    m, n = alloc.shape
    needed = m + n - 1
    if len(basic) >= needed:
        return basic
    basic = list(basic)
    bset = set(basic)
    # add independent zero cells
    for i in range(m):
        for j in range(n):
            if len(basic) >= needed:
                break
            if (i, j) in bset:
                continue
            trial = basic + [(i, j)]
            if _find_loop((i, j), trial) is None:  # keeps it acyclic
                basic.append((i, j))
                bset.add((i, j))
    return basic


def _compute_uv(cost, basic, m, n):
    u = [None] * m
    v = [None] * n
    u[0] = 0.0
    changed = True
    while changed:
        changed = False
        for i, j in basic:
            if u[i] is not None and v[j] is None:
                v[j] = cost[i, j] - u[i]
                changed = True
            elif v[j] is not None and u[i] is None:
                u[i] = cost[i, j] - v[j]
                changed = True
    u = [0.0 if x is None else x for x in u]
    v = [0.0 if x is None else x for x in v]
    return u, v


def modi(cost, alloc, max_iter: int = 200):
    """Optimize an initial allocation to minimum cost via MODI."""
    cost = np.array(cost, dtype=float)
    alloc = np.array(alloc, dtype=float).copy()
    m, n = cost.shape
    for _ in range(max_iter):
        basic = _basic_cells(alloc)
        basic = _ensure_nondegenerate(alloc, basic)
        u, v = _compute_uv(cost, basic, m, n)
        # reduced cost for every non-basic cell
        best_cell, best_delta = None, -EPS
        bset = set(basic)
        for i in range(m):
            for j in range(n):
                if (i, j) in bset:
                    continue
                delta = cost[i, j] - u[i] - v[j]
                if delta < best_delta:
                    best_delta, best_cell = delta, (i, j)
        if best_cell is None:  # all reduced costs >= 0 -> optimal
            break
        loop = _find_loop(best_cell, basic)
        if loop is None:
            break
        # plus positions are even indices, minus positions odd indices
        minus = loop[1::2]
        theta = min(alloc[c] for c in minus)
        for k, c in enumerate(loop):
            if k % 2 == 0:
                alloc[c] += theta
            else:
                alloc[c] -= theta
        alloc[np.abs(alloc) < EPS] = 0.0
    return alloc


def stepping_stone(cost, alloc, max_iter: int = 200):
    """Optimize via the Stepping Stone method (loop evaluation per empty cell)."""
    cost = np.array(cost, dtype=float)
    alloc = np.array(alloc, dtype=float).copy()
    m, n = cost.shape
    for _ in range(max_iter):
        basic = _basic_cells(alloc)
        basic = _ensure_nondegenerate(alloc, basic)
        bset = set(basic)
        best_cell, best_delta, best_loop = None, -EPS, None
        for i in range(m):
            for j in range(n):
                if (i, j) in bset:
                    continue
                loop = _find_loop((i, j), basic)
                if loop is None:
                    continue
                delta = sum((-1) ** k * cost[c] for k, c in enumerate(loop))
                if delta < best_delta:
                    best_delta, best_cell, best_loop = delta, (i, j), loop
        if best_cell is None:
            break
        minus = best_loop[1::2]
        theta = min(alloc[c] for c in minus)
        for k, c in enumerate(best_loop):
            alloc[c] += theta if k % 2 == 0 else -theta
        alloc[np.abs(alloc) < EPS] = 0.0
    return alloc


# --------------------------------------------------------------------------
# High-level driver
# --------------------------------------------------------------------------
def solve_transport(cost, supply, demand, initial="vogel", optimize="modi"):
    """End-to-end: balance -> initial solution -> optimality improvement."""
    c, s, d, balanced, dummy = balance(cost, supply, demand)
    init_fn = {"nwc": northwest_corner, "least_cost": least_cost, "vogel": vogel}
    if initial == "nwc":
        alloc = northwest_corner(s, d)
    else:
        alloc = init_fn[initial](c, s, d)
    if optimize == "modi":
        alloc = modi(c, alloc)
    elif optimize == "stepping_stone":
        alloc = stepping_stone(c, alloc)
    return TransportSolution(
        allocation=alloc,
        cost_matrix=c,
        total_cost=total_cost(alloc, c),
        supply=s,
        demand=d,
        balanced=balanced,
        dummy_added=dummy,
        method=f"{initial}+{optimize}",
    )
