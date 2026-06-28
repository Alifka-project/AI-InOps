"use client";

import { useCallback, useEffect, useState } from "react";
import type { Dataset, InitialMethod, OptimalityMethod, TransportResponse } from "@/lib/types";
import { useScenarioStore } from "@/store/useScenarioStore";
import { api, ApiError } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { fmtNum, fmtUsdCompact } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import { Panel } from "@/components/Panel";
import { MatrixEditor } from "@/components/MatrixEditor";
import { AsyncBoundary } from "@/components/AsyncBoundary";
import { CardSkeleton } from "@/components/Skeleton";
import { RequireDataset } from "@/components/RequireDataset";

const INITIAL_METHODS: { value: InitialMethod; label: string }[] = [
  { value: "nwc", label: "Northwest Corner" },
  { value: "least_cost", label: "Least Cost" },
  { value: "vogel", label: "Vogel (VAM)" },
];
const OPT_METHODS: { value: OptimalityMethod; label: string }[] = [
  { value: "modi", label: "MODI" },
  { value: "stepping_stone", label: "Stepping Stone" },
];

interface Matrix {
  cost: number[][];
  supply: number[];
  demand: number[];
  rowLabels: string[];
  colLabels: string[];
}

export default function TransportationPage() {
  return (
    <RequireDataset>
      <TransportationBody />
    </RequireDataset>
  );
}

function TransportationBody() {
  const dataset = useScenarioStore((s) => s.dataset) as Dataset;
  const scenario = useScenarioStore((s) => s.scenario);

  const data = useApi(() => api.getData(dataset, scenario), [dataset.meta.name, scenario]);
  const [matrix, setMatrix] = useState<Matrix | null>(null);
  const [initial, setInitial] = useState<InitialMethod>("vogel");
  const [optimize, setOptimize] = useState<OptimalityMethod>("modi");

  const [result, setResult] = useState<TransportResponse | null>(null);
  const [solving, setSolving] = useState(false);
  const [solveError, setSolveError] = useState<string | null>(null);

  const seed = useCallback(() => {
    if (!data.data) return;
    setMatrix({
      cost: data.data.transport_costs.map((r) => [...r]),
      supply: [...data.data.transport_supply],
      demand: [...data.data.transport_demand],
      rowLabels: data.data.center_names,
      colLabels: data.data.hub_names,
    });
  }, [data.data]);

  useEffect(() => {
    seed();
  }, [seed]);

  const runOptimize = useCallback(
    async (m: Matrix, init: InitialMethod, opt: OptimalityMethod) => {
      setSolving(true);
      setSolveError(null);
      try {
        const res = await api.optimizeTransport(dataset, scenario, {
          initial: init,
          optimize: opt,
          cost: m.cost,
          supply: m.supply,
          demand: m.demand,
          row_labels: m.rowLabels,
          col_labels: m.colLabels,
        });
        setResult(res);
      } catch (err) {
        setSolveError(err instanceof ApiError ? err.message : "Optimization failed");
      } finally {
        setSolving(false);
      }
    },
    [dataset, scenario],
  );

  useEffect(() => {
    if (matrix) runOptimize(matrix, initial, optimize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [matrix, initial, optimize]);

  const updateMatrix = (patch: (m: Matrix) => Matrix) =>
    setMatrix((m) => (m ? patch(m) : m));

  const dataDriven = dataset.meta.has_scenario_data;

  // Real shortfall/surplus tonnage = the balancing row/column's allocation total.
  let shortfall = 0;
  if (result) {
    if (result.dummy_added === "source") {
      const last = result.allocation[result.allocation.length - 1] ?? [];
      shortfall = last.reduce((a, b) => a + b, 0);
    } else if (result.dummy_added === "destination") {
      shortfall = result.allocation.reduce(
        (s, row) => s + (row[row.length - 1] ?? 0),
        0,
      );
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Transportation Optimization"
        description="Minimize shipping cost from your suppliers to your warehouses. Edit the matrix and compare methods."
      />

      <div
        className={`card card-pad text-sm ${
          dataDriven
            ? "ring-1 ring-inset ring-emerald-500/30 text-emerald-200"
            : "ring-1 ring-inset ring-amber-500/30 text-amber-200"
        }`}
      >
        {dataDriven ? (
          <>
            <span className="font-semibold">Data-driven scenario:</span> Normal vs
            Hormuz use the <strong>pre/post-conflict costs and lead times from your
            file</strong> — no modelled multipliers. Toggle the scenario to compare.
          </>
        ) : (
          <>
            <span className="font-semibold">Modelled scenario:</span> this dataset
            has no pre/post-conflict columns, so Hormuz applies documented
            assumptions (×1.3 freight + $85/t insurance, +12-day lead time). Upload
            a file with <code>cost_per_t_preconflict/postconflict</code> columns to
            make it fully data-driven.
          </>
        )}
      </div>

      <AsyncBoundary loading={data.loading} error={data.error} onRetry={data.reload} skeleton={<CardSkeleton />}>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
          <Panel
            title="Cost / Supply / Demand"
            description="Unit cost per tonne. Edit any cell, supply, or demand."
            className="lg:col-span-3"
          >
            {matrix && (
              <MatrixEditor
                cost={matrix.cost}
                supply={matrix.supply}
                demand={matrix.demand}
                rowLabels={matrix.rowLabels}
                colLabels={matrix.colLabels}
                onCostChange={(i, j, v) =>
                  updateMatrix((m) => {
                    const cost = m.cost.map((r) => [...r]);
                    cost[i][j] = v;
                    return { ...m, cost };
                  })
                }
                onSupplyChange={(i, v) =>
                  updateMatrix((m) => {
                    const supply = [...m.supply];
                    supply[i] = v;
                    return { ...m, supply };
                  })
                }
                onDemandChange={(j, v) =>
                  updateMatrix((m) => {
                    const demand = [...m.demand];
                    demand[j] = v;
                    return { ...m, demand };
                  })
                }
              />
            )}
            <div className="mt-4 flex flex-wrap gap-3">
              <button className="btn-ghost" onClick={seed}>
                Reset to scenario defaults
              </button>
              <button
                className="btn-primary"
                disabled={solving || !matrix}
                onClick={() => matrix && runOptimize(matrix, initial, optimize)}
              >
                {solving ? "Solving…" : "Re-optimize"}
              </button>
            </div>
          </Panel>

          <Panel title="Method" className="lg:col-span-2">
            <div className="space-y-4">
              <div>
                <p className="label mb-2">Initial solution</p>
                <div className="flex flex-wrap gap-2">
                  {INITIAL_METHODS.map((m) => (
                    <button
                      key={m.value}
                      onClick={() => setInitial(m.value)}
                      className={`btn ${initial === m.value ? "btn-primary" : "btn-ghost"}`}
                    >
                      {m.label}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <p className="label mb-2">Optimality test</p>
                <div className="flex flex-wrap gap-2">
                  {OPT_METHODS.map((m) => (
                    <button
                      key={m.value}
                      onClick={() => setOptimize(m.value)}
                      className={`btn ${optimize === m.value ? "btn-primary" : "btn-ghost"}`}
                    >
                      {m.label}
                    </button>
                  ))}
                </div>
              </div>

              {result && (
                <div className="mt-2 space-y-3 rounded-lg border border-white/10 bg-ink/40 p-4">
                  <div>
                    <p className="label">Optimal total cost</p>
                    <p className="text-2xl font-semibold text-accent">
                      {result.total_cost.toLocaleString("en-US", { maximumFractionDigits: 0 })}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <span
                      className={`chip ${
                        result.balanced
                          ? "bg-emerald-500/15 text-emerald-300"
                          : "bg-amber-500/15 text-amber-300"
                      }`}
                    >
                      {result.balanced ? "Balanced" : "Unbalanced"}
                    </span>
                    {result.dummy_added === "source" && (
                      <span className="chip bg-rose-500/15 text-rose-300">
                        {fmtNum(shortfall)} t unmet demand
                      </span>
                    )}
                    {result.dummy_added === "destination" && (
                      <span className="chip bg-electric/15 text-electric">
                        {fmtNum(shortfall)} t surplus supply
                      </span>
                    )}
                  </div>
                </div>
              )}
              {solveError && <p className="text-sm text-rose-300">{solveError}</p>}
            </div>
          </Panel>
        </div>
      </AsyncBoundary>

      {result && (
        <Panel
          title="Optimal Allocation"
          description={`Shipment quantities (t) — ${result.method}. An "Unmet demand" / "Surplus supply" row balances the problem at zero real cost.`}
        >
          <div className="overflow-x-auto">
            <table className="border-separate border-spacing-1 text-sm">
              <thead>
                <tr>
                  <th className="px-3 py-1.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                    From \ To
                  </th>
                  {result.col_labels.map((c, j) => (
                    <th key={j} className="px-3 py-1.5 text-center text-xs font-semibold text-electric">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.allocation.map((row, i) => (
                  <tr key={i}>
                    <td className="px-3 py-1.5 text-xs font-semibold text-slate-300">
                      {result.row_labels[i]}
                    </td>
                    {row.map((q, j) => (
                      <td
                        key={j}
                        className={`px-3 py-1.5 text-center font-mono ${
                          q > 0 ? "rounded-md bg-accent/10 text-accent" : "text-slate-600"
                        }`}
                      >
                        {q > 0 ? fmtNum(q) : "·"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      {result && (
        <Panel title="Method Convergence" description="Every initial × optimality combination should reach the same optimum.">
          <div className="mb-3 flex items-center gap-2">
            {result.all_methods_agree ? (
              <span className="chip bg-emerald-500/15 text-emerald-300">
                ✓ all 6 methods agree on {fmtUsdCompact(result.total_cost)}
              </span>
            ) : (
              <span className="chip bg-rose-500/15 text-rose-300">methods disagree — check inputs</span>
            )}
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {result.comparison.map((c, i) => (
              <div
                key={i}
                className="flex items-center justify-between rounded-lg border border-white/10 bg-ink/40 px-3 py-2.5"
              >
                <span className="text-xs text-slate-400">
                  {c.initial} + {c.optimize}
                </span>
                <span className="font-mono text-sm font-semibold text-white">
                  {c.total_cost.toLocaleString("en-US", { maximumFractionDigits: 0 })}
                </span>
              </div>
            ))}
          </div>
        </Panel>
      )}
    </div>
  );
}
