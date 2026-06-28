"use client";

import {
  Area,
  ComposedChart,
  CartesianGrid,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Dataset, SimulateResponse } from "@/lib/types";
import { useScenarioStore } from "@/store/useScenarioStore";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { fmtInt, fmtPct, fmtUsdCompact } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import { KpiCard } from "@/components/KpiCard";
import { Panel } from "@/components/Panel";
import { DeltaBanner } from "@/components/DeltaBanner";
import { AsyncBoundary } from "@/components/AsyncBoundary";
import { CardSkeleton, KpiSkeletonRow } from "@/components/Skeleton";
import { RequireDataset } from "@/components/RequireDataset";
import { DownloadReportButton } from "@/components/DownloadReportButton";

export default function OverviewPage() {
  return (
    <RequireDataset>
      <OverviewBody />
    </RequireDataset>
  );
}

function OverviewBody() {
  const dataset = useScenarioStore((s) => s.dataset) as Dataset;
  const scenario = useScenarioStore((s) => s.scenario);
  const settings = useScenarioStore((s) => s.settings);
  const key = [
    dataset.meta.name,
    scenario,
    settings.alpha,
    settings.beta,
    settings.horizon,
    settings.serviceLevel,
    settings.autoTune,
  ];

  const sim = useApi(() => api.simulate(dataset, scenario, settings), [...key]);
  const cmp = useApi(
    () => api.compareScenarios(dataset, settings),
    [dataset.meta.name, settings.alpha, settings.beta, settings.horizon, settings.serviceLevel],
  );

  const months = sim.data?.months ?? [];
  const lastIdx = months.length - 1;
  const historical = months.map((m, i) => ({
    month: m,
    actual: sim.data?.actual[i] ?? null,
    fitted: sim.data?.forecast_fitted[i] ?? null,
    forecast: i === lastIdx ? (sim.data?.actual[i] ?? null) : null,
  }));
  const future =
    sim.data?.forecast_horizon.map((v, i) => ({
      month: sim.data?.forecast_labels[i] ?? `+${i + 1}`,
      actual: null,
      fitted: null,
      forecast: v,
    })) ?? [];
  const chartData = [...historical, ...future];
  const boundaryLabel = months[lastIdx];
  const horizonData = future;

  const k = sim.data?.kpis;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Operations Overview"
        description={`Live snapshot of "${dataset.meta.name}" under the selected scenario.`}
        actions={<DownloadReportButton variant="primary" />}
      />

      <AsyncBoundary
        loading={cmp.loading}
        error={cmp.error}
        onRetry={cmp.reload}
        skeleton={<CardSkeleton height="h-20" />}
      >
        {cmp.data && <DeltaBanner comparison={cmp.data} scenario={scenario} />}
      </AsyncBoundary>

      <AsyncBoundary
        loading={sim.loading}
        error={sim.error}
        onRetry={sim.reload}
        skeleton={<KpiSkeletonRow count={5} />}
      >
        {k && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <KpiCard
              label="Next-Period Demand"
              value={fmtInt(k.next_month_demand)}
              sublabel="planning units"
            />
            <KpiCard
              label="Optimal Transport Cost"
              value={fmtUsdCompact(k.optimal_transport_cost)}
              sublabel="per cycle"
            />
            <KpiCard
              label="Avg Supplier Utilization"
              value={fmtPct(k.avg_supplier_utilization)}
              sublabel="of capacity"
            />
            <KpiCard
              label="Recovered Value"
              value={fmtUsdCompact(k.recovered_material_value)}
              sublabel="per cycle"
            />
            <KpiCard
              label="Hubs Needing Reorder"
              value={`${k.hubs_needing_reorder} / ${dataset.meta.n_warehouses}`}
              accent={k.hubs_needing_reorder > 0 ? "warn" : "default"}
              sublabel={k.balanced ? "network balanced" : "network unbalanced"}
            />
          </div>
        )}
      </AsyncBoundary>

      <AsyncBoundary
        loading={sim.loading}
        error={sim.error}
        onRetry={sim.reload}
        skeleton={<CardSkeleton height="h-40" />}
      >
        {sim.data && (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Panel
              title="Analysis Summary"
              description="Findings computed from your data for this scenario."
            >
              <ul className="space-y-2.5">
                {sim.data.insights.map((line, i) => (
                  <li key={i} className="flex gap-2.5 text-sm text-slate-200">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                    <span>{line}</span>
                  </li>
                ))}
              </ul>
            </Panel>

            <Panel
              title="Methodology — what the twin computed"
              description="Each required element, the technique applied, and its result."
            >
              <div className="space-y-2.5">
                {sim.data.methodology.map((m, i) => (
                  <div
                    key={i}
                    className="rounded-lg border border-white/10 bg-ink/40 px-3 py-2.5"
                  >
                    <p className="text-sm font-semibold text-white">
                      {i + 1}. {m.element}
                    </p>
                    <p className="mt-0.5 text-xs text-slate-400">{m.technique}</p>
                    <p className="mt-1 font-mono text-xs text-accent">→ {m.result}</p>
                  </div>
                ))}
              </div>
            </Panel>
          </div>
        )}
      </AsyncBoundary>

      <AsyncBoundary
        loading={sim.loading}
        error={sim.error}
        onRetry={sim.reload}
        skeleton={<CardSkeleton />}
      >
        <Panel
          title="Demand: Actual vs Forecast"
          description="Historical sales (teal) and the forward forecast (fuchsia, right of the marker)."
        >
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
                <defs>
                  <linearGradient id="demandFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#16D6C9" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#16D6C9" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" minTickGap={28} tickLine={false} />
                <YAxis tickLine={false} width={48} />
                <Tooltip
                  contentStyle={{ background: "#0E1B2E", border: "1px solid rgba(255,255,255,0.12)" }}
                  labelStyle={{ color: "#94a3b8" }}
                  itemStyle={{ color: "#e2e8f0" }}
                />
                {boundaryLabel && (
                  <ReferenceLine
                    x={boundaryLabel}
                    stroke="#64748B"
                    strokeDasharray="4 2"
                    label={{ value: "forecast →", position: "insideTopRight", fill: "#E879F9", fontSize: 11 }}
                  />
                )}
                <Area
                  type="monotone"
                  dataKey="actual"
                  name="Actual"
                  stroke="#16D6C9"
                  strokeWidth={2}
                  fill="url(#demandFill)"
                  connectNulls={false}
                />
                <Line
                  type="monotone"
                  dataKey="fitted"
                  name="Model fit"
                  stroke="#2E9BFF"
                  strokeWidth={1.4}
                  dot={false}
                  connectNulls={false}
                />
                <Line
                  type="monotone"
                  dataKey="forecast"
                  name="Forecast"
                  stroke="#E879F9"
                  strokeWidth={2.4}
                  dot={{ r: 2, fill: "#E879F9" }}
                  connectNulls
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-slate-400">
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-accent" /> Actual (your data)
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: "#2E9BFF" }} />{" "}
              Model fit
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: "#E879F9" }} />{" "}
              Forecast (next {horizonData.length})
            </span>
          </div>
          {horizonData.length > 0 && (
            <p className="mt-2 text-xs text-slate-400">
              Forward forecast:{" "}
              <span className="font-mono text-fuchsia-300">
                {horizonData.map((h) => fmtInt(h.forecast as number)).join(" · ")}
              </span>{" "}
              units
            </p>
          )}
        </Panel>
      </AsyncBoundary>

      <AsyncBoundary
        loading={sim.loading}
        error={sim.error}
        onRetry={sim.reload}
        skeleton={<CardSkeleton height="h-56" />}
      >
        {sim.data && sim.data.forecast_fitted.length > 0 && (
          <AccuracyPanel data={sim.data} />
        )}
      </AsyncBoundary>
    </div>
  );
}

function AccuracyPanel({ data }: { data: SimulateResponse }) {
  const months = data.months;
  const n = months.length;
  // Walk-forward one-step-ahead back-test: forecast_fitted[t] is the model's
  // forecast for period t computed from periods 0..t-1 only (no look-ahead).
  const window = Math.min(18, n);
  const start = n - window;
  const rows: { label: string; actual: number; predicted: number }[] = [];
  let sumPct = 0;
  let sumAbs = 0;
  let cnt = 0;
  for (let i = start; i < n; i++) {
    const a = data.actual[i];
    const p = data.forecast_fitted[i];
    rows.push({ label: months[i], actual: a, predicted: p });
    if (a) {
      sumPct += Math.abs(a - p) / Math.abs(a);
      sumAbs += Math.abs(a - p);
      cnt += 1;
    }
  }
  const mape = cnt ? (sumPct / cnt) * 100 : 0;
  const mad = cnt ? sumAbs / cnt : 0;
  const accuracy = Math.max(0, 100 - mape);
  const v = data.validation;
  const blindAcc = v ? Math.max(0, 100 - v.mape) : null;

  return (
    <Panel
      title="Forecast Accuracy — Back-test on Your Real Data"
      description="Each point is forecast using only the periods before it (walk-forward), then compared to what actually happened. The closer the two lines, the more reliable the prediction."
    >
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="space-y-3">
          <div className="rounded-lg border border-emerald-500/25 bg-emerald-500/5 p-4">
            <p className="label">One-step-ahead accuracy</p>
            <p className="mt-1 text-3xl font-semibold text-emerald-300">
              {accuracy.toFixed(1)}%
            </p>
            <p className="mt-1 text-xs text-slate-400">
              MAPE {mape.toFixed(1)}% · MAD {fmtInt(mad)} units over the last {cnt} periods
            </p>
          </div>
          {blindAcc !== null && v && (
            <div className="rounded-lg border border-white/10 bg-ink/40 p-3">
              <p className="text-xs text-slate-300">
                Strict blind holdout:{" "}
                <span className="font-mono text-accent">{blindAcc.toFixed(1)}%</span>
              </p>
              <p className="mt-0.5 text-[11px] text-slate-500">
                Trained on {v.train_size} periods, then forecast the next {v.holdout}{" "}
                fully blind (MAPE {v.mape}%).
              </p>
            </div>
          )}
          <p className="text-xs leading-relaxed text-slate-400">
            Every number here is derived only from <strong>your</strong> uploaded sales —
            no assumptions, no synthetic values. The accuracy is measured against the real
            outcomes the model had not yet used, which is what makes the forward forecast
            trustworthy.
          </p>
        </div>
        <div className="lg:col-span-2">
          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={rows} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="label" tickLine={false} minTickGap={24} />
                <YAxis tickLine={false} width={48} />
                <Tooltip
                  contentStyle={{ background: "#0E1B2E", border: "1px solid rgba(255,255,255,0.12)" }}
                  labelStyle={{ color: "#94a3b8" }}
                  itemStyle={{ color: "#e2e8f0" }}
                  formatter={(val: number) => fmtInt(val)}
                />
                <Line
                  type="monotone"
                  dataKey="actual"
                  name="Actual (real)"
                  stroke="#16D6C9"
                  strokeWidth={2.2}
                  dot={{ r: 2, fill: "#16D6C9" }}
                />
                <Line
                  type="monotone"
                  dataKey="predicted"
                  name="Forecast"
                  stroke="#E879F9"
                  strokeWidth={2.2}
                  strokeDasharray="4 2"
                  dot={{ r: 2, fill: "#E879F9" }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-4 text-xs text-slate-400">
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-accent" /> Actual (your real data)
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: "#E879F9" }} />{" "}
              Model forecast (from prior data only)
            </span>
          </div>
        </div>
      </div>
    </Panel>
  );
}
