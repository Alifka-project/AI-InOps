"use client";

import type { Dataset, Kpis } from "@/lib/types";
import { useScenarioStore } from "@/store/useScenarioStore";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { deltaPct, fmtInt, fmtPct, fmtUsd, fmtUsdCompact } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import { Panel } from "@/components/Panel";
import { AsyncBoundary } from "@/components/AsyncBoundary";
import { CardSkeleton } from "@/components/Skeleton";
import { RequireDataset } from "@/components/RequireDataset";

interface RowDef {
  label: string;
  pick: (k: Kpis) => number;
  format: (n: number) => string;
  goodWhenUp: boolean;
}

const ROWS: RowDef[] = [
  { label: "Next-period planning demand", pick: (k) => k.next_month_demand, format: (n) => `${fmtInt(n)} u`, goodWhenUp: false },
  { label: "Optimal transport cost", pick: (k) => k.optimal_transport_cost, format: fmtUsd, goodWhenUp: false },
  { label: "Avg supplier utilization", pick: (k) => k.avg_supplier_utilization, format: (n) => fmtPct(n), goodWhenUp: true },
  { label: "Recovered-material value", pick: (k) => k.recovered_material_value, format: fmtUsd, goodWhenUp: true },
  { label: "Hubs needing reorder", pick: (k) => k.hubs_needing_reorder, format: (n) => `${n}`, goodWhenUp: false },
  { label: "Total available supply", pick: (k) => k.total_available_t, format: (n) => `${fmtInt(n)} t`, goodWhenUp: true },
  { label: "Total network demand", pick: (k) => k.total_demand_t, format: (n) => `${fmtInt(n)} t`, goodWhenUp: false },
];

export default function ScenarioPage() {
  return (
    <RequireDataset>
      <ScenarioBody />
    </RequireDataset>
  );
}

function DeltaCell({ delta, goodWhenUp }: { delta: number; goodWhenUp: boolean }) {
  if (Math.abs(delta) < 0.0005) return <span className="text-slate-500">—</span>;
  const up = delta > 0;
  const good = up === goodWhenUp;
  return (
    <span className={`font-mono font-semibold ${good ? "text-emerald-300" : "text-rose-300"}`}>
      {up ? "▲ +" : "▼ "}
      {fmtPct(delta)}
    </span>
  );
}

function ScenarioBody() {
  const dataset = useScenarioStore((s) => s.dataset) as Dataset;
  const settings = useScenarioStore((s) => s.settings);
  const setScenario = useScenarioStore((s) => s.setScenario);

  const cmp = useApi(
    () => api.compareScenarios(dataset, settings),
    [dataset.meta.name, settings.alpha, settings.beta, settings.horizon, settings.serviceLevel],
  );

  const n = cmp.data?.normal;
  const d = cmp.data?.hormuz_disruption;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Scenario Comparison"
        description="Side-by-side resilience impact of the 2026 Strait of Hormuz disruption versus normal operations, on your data."
      />

      <div className="card card-pad">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-slate-300">
            The disruption applies <strong>+12 day</strong> lead times, a <strong>×1.3</strong>{" "}
            freight multiplier plus an <strong>$85/t</strong> war-risk surcharge, disables the first
            direct route, and lifts recovered-material demand <strong>×1.25</strong>.
          </p>
          <div className="flex gap-2">
            <button className="btn-ghost" onClick={() => setScenario("normal")}>
              View Normal
            </button>
            <button className="btn-primary" onClick={() => setScenario("hormuz_disruption")}>
              View Disruption
            </button>
          </div>
        </div>
      </div>

      <AsyncBoundary loading={cmp.loading} error={cmp.error} onRetry={cmp.reload} skeleton={<CardSkeleton />}>
        {n && d && (
          <Panel title="KPI Deltas" description="Normal → Hormuz Disruption">
            <div className="overflow-x-auto">
              <table className="table-base">
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th className="text-right">Normal</th>
                    <th className="text-right">Disruption</th>
                    <th className="text-right">Change</th>
                  </tr>
                </thead>
                <tbody>
                  {ROWS.map((row) => {
                    const nv = row.pick(n);
                    const dv = row.pick(d);
                    return (
                      <tr key={row.label}>
                        <td className="font-medium text-white">{row.label}</td>
                        <td className="text-right font-mono text-slate-300">{row.format(nv)}</td>
                        <td className="text-right font-mono text-white">{row.format(dv)}</td>
                        <td className="text-right">
                          <DeltaCell delta={deltaPct(dv, nv)} goodWhenUp={row.goodWhenUp} />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Panel>
        )}
      </AsyncBoundary>

      <AsyncBoundary loading={cmp.loading} error={cmp.error} onRetry={cmp.reload} skeleton={<CardSkeleton height="h-24" />}>
        {n && d && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <SummaryCard
              title="Normal Operations"
              accent="accent"
              cost={fmtUsdCompact(n.optimal_transport_cost)}
              value={fmtUsdCompact(n.recovered_material_value)}
              balanced={n.balanced}
            />
            <SummaryCard
              title="Hormuz Disruption"
              accent="rose"
              cost={fmtUsdCompact(d.optimal_transport_cost)}
              value={fmtUsdCompact(d.recovered_material_value)}
              balanced={d.balanced}
            />
          </div>
        )}
      </AsyncBoundary>
    </div>
  );
}

function SummaryCard({
  title,
  accent,
  cost,
  value,
  balanced,
}: {
  title: string;
  accent: "accent" | "rose";
  cost: string;
  value: string;
  balanced: boolean;
}) {
  const ring = accent === "rose" ? "ring-1 ring-inset ring-rose-500/30" : "ring-1 ring-inset ring-accent/30";
  return (
    <div className={`card card-pad ${ring}`}>
      <p className={`font-semibold ${accent === "rose" ? "text-rose-300" : "text-accent"}`}>{title}</p>
      <div className="mt-3 grid grid-cols-2 gap-4">
        <div>
          <p className="label">Transport cost</p>
          <p className="text-xl font-semibold text-white">{cost}</p>
        </div>
        <div>
          <p className="label">Recovered value</p>
          <p className="text-xl font-semibold text-white">{value}</p>
        </div>
      </div>
      <p className="mt-3 text-xs text-slate-400">
        Network is {balanced ? "balanced" : "unbalanced (supply shortfall)"}.
      </p>
    </div>
  );
}
