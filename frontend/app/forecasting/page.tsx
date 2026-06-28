"use client";

import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Dataset, Series } from "@/lib/types";
import { useScenarioStore } from "@/store/useScenarioStore";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { fmtInt, fmtNum } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import { Panel } from "@/components/Panel";
import { Slider } from "@/components/Slider";
import { AsyncBoundary } from "@/components/AsyncBoundary";
import { CardSkeleton } from "@/components/Skeleton";
import { RequireDataset } from "@/components/RequireDataset";

const COLORS = { adjusted: "#16D6C9", linear: "#2E9BFF", seasonal: "#F59E0B" };

export default function ForecastingPage() {
  return (
    <RequireDataset>
      <ForecastingBody />
    </RequireDataset>
  );
}

function MetricsTable({ series }: { series: { key: string; s: Series }[] }) {
  const best = series
    .filter((x) => x.s.metrics)
    .reduce(
      (acc, x) =>
        x.s.metrics && x.s.metrics.MAD < acc.mad
          ? { name: x.s.name, mad: x.s.metrics.MAD }
          : acc,
      { name: "", mad: Infinity },
    );
  return (
    <table className="table-base">
      <thead>
        <tr>
          <th>Method</th>
          <th className="text-right">MAD</th>
          <th className="text-right">MSE</th>
          <th className="text-right">MAPE</th>
          <th className="text-right">Bias</th>
        </tr>
      </thead>
      <tbody>
        {series.map(({ key, s }) => (
          <tr key={key}>
            <td className="font-medium text-white">
              {s.name}
              {s.name === best.name && (
                <span className="ml-2 chip bg-emerald-500/15 text-emerald-300">best fit</span>
              )}
            </td>
            <td className="text-right font-mono">{fmtNum(s.metrics?.MAD ?? NaN)}</td>
            <td className="text-right font-mono">{fmtNum(s.metrics?.MSE ?? NaN)}</td>
            <td className="text-right font-mono">{fmtNum(s.metrics?.MAPE ?? NaN)}%</td>
            <td className="text-right font-mono">{fmtNum(s.metrics?.Bias ?? NaN)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

type Granularity = "none" | "weekly" | "monthly";
const GRANULARITIES: { value: Granularity; label: string }[] = [
  { value: "none", label: "Per period" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
];

function ForecastingBody() {
  const dataset = useScenarioStore((s) => s.dataset) as Dataset;
  const scenario = useScenarioStore((s) => s.scenario);
  const settings = useScenarioStore((s) => s.settings);
  const setSettings = useScenarioStore((s) => s.setSettings);
  const [granularity, setGranularity] = useState<Granularity>("monthly");

  const fc = useApi(
    () => api.forecastDemand(dataset, scenario, settings, granularity),
    [
      dataset.meta.name,
      scenario,
      settings.alpha,
      settings.beta,
      settings.horizon,
      settings.autoTune,
      granularity,
    ],
  );

  const d = fc.data;
  const lastIdx = d ? d.months.length - 1 : 0;
  // Historical points (actual + in-sample fits) plus the forward forecast,
  // appended after the data so the prediction is visible beyond history.
  const historical =
    d?.months.map((m, i) => ({
      month: m,
      actual: d.actual[i],
      adjusted: d.adjusted_es.fitted[i],
      linear: d.linear_trend.fitted[i],
      seasonal: d.seasonal.fitted[i],
      forecast: i === lastIdx ? d.actual[i] : null, // connect the forecast line
    })) ?? [];
  const future =
    d?.forecast_horizon.map((v, k) => ({
      month: d.forecast_labels[k] ?? `+${k + 1}`,
      actual: null,
      adjusted: null,
      linear: null,
      seasonal: null,
      forecast: v,
    })) ?? [];
  const chartData = [...historical, ...future];
  const boundaryLabel = d?.months[lastIdx];
  const seasonalData =
    d?.seasonal_factors.map((f, i) => ({ idx: `S${i + 1}`, factor: f })) ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Demand Forecasting"
        description="Adjusted Exponential Smoothing, Linear Trend, and Seasonal Adjustment on your historical sales — validated out-of-sample."
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Panel title="Parameters" description="Tune smoothing or let the model fit." className="lg:col-span-1">
          <div className="space-y-5">
            <label className="flex cursor-pointer items-center justify-between gap-3 rounded-lg border border-white/10 bg-ink/40 px-3 py-2.5">
              <span className="text-sm font-medium text-white">
                Auto-tune α, β
                <span className="block text-xs font-normal text-slate-400">
                  Grid-search to minimise validation error
                </span>
              </span>
              <input
                type="checkbox"
                className="h-4 w-4 accent-accent"
                checked={settings.autoTune}
                onChange={(e) => setSettings({ autoTune: e.target.checked })}
              />
            </label>
            <Slider
              label="Alpha (level)"
              value={d ? d.alpha : settings.alpha}
              min={0.05}
              max={1}
              step={0.05}
              onChange={(v) => setSettings({ alpha: v, autoTune: false })}
              format={(v) => v.toFixed(2)}
            />
            <Slider
              label="Beta (trend)"
              value={d ? d.beta : settings.beta}
              min={0}
              max={1}
              step={0.05}
              onChange={(v) => setSettings({ beta: v, autoTune: false })}
              format={(v) => v.toFixed(2)}
            />
            <div>
              <p className="label mb-1.5">Granularity</p>
              <div className="inline-flex w-full rounded-lg border border-white/10 bg-ink/40 p-1">
                {GRANULARITIES.map((g) => (
                  <button
                    key={g.value}
                    onClick={() => setGranularity(g.value)}
                    className={`flex-1 rounded-md px-2 py-1.5 text-xs font-medium transition ${
                      granularity === g.value
                        ? "bg-accent text-navy-900"
                        : "text-slate-300 hover:text-white"
                    }`}
                  >
                    {g.label}
                  </button>
                ))}
              </div>
            </div>
            <Slider
              label="Forecast horizon"
              value={settings.horizon}
              min={1}
              max={24}
              step={1}
              onChange={(v) => setSettings({ horizon: v })}
              format={(v) =>
                granularity === "monthly"
                  ? `${v} months`
                  : granularity === "weekly"
                    ? `${v} weeks`
                    : `${v} periods`
              }
            />
            <p className="-mt-2 text-[11px] text-slate-500">
              {granularity === "none"
                ? "Periods match your data's raw frequency."
                : `Demand is rolled up to ${granularity} totals, so the horizon is in ${granularity === "monthly" ? "months" : "weeks"}.`}{" "}
              The forecast extends past the marker.
            </p>
            {d && (
              <div className="space-y-3">
                <div className="rounded-lg border border-white/10 bg-ink/40 p-3">
                  <p className="label">Next-period planning demand</p>
                  <p className="mt-1 text-2xl font-semibold text-accent">
                    {fmtInt(d.planning_demand_next)}
                  </p>
                  <p className="text-xs text-slate-400">
                    base {fmtInt(d.next_forecast)} × {d.recovered_demand_multiplier.toFixed(2)}{" "}
                    scenario × {d.external_factor.toFixed(2)} market trend
                  </p>
                </div>
                <div className="rounded-lg border border-white/10 bg-ink/40 p-3">
                  <p className="label">Validation (out-of-sample back-test)</p>
                  <p className="mt-1 text-sm text-slate-200">
                    Held out {d.validation.holdout} periods · MAD{" "}
                    <span className="font-mono text-accent">{d.validation.mad}</span> · MAPE{" "}
                    <span className="font-mono text-accent">{d.validation.mape}%</span>
                  </p>
                  {d.auto_tuned && d.tuning && (
                    <p className="mt-1 text-xs text-emerald-300">
                      Auto-tuned over {d.tuning.grid_size} (α,β) pairs → α={d.alpha}, β={d.beta}
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        </Panel>

        <div className="lg:col-span-2">
          <AsyncBoundary loading={fc.loading} error={fc.error} onRetry={fc.reload} skeleton={<CardSkeleton />}>
            <Panel
              title="Actual, Fitted & Forward Forecast"
              description={`In-sample fit plus the next ${future.length}-period prediction (to the right of the marker).`}
            >
              <div className="h-80 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" minTickGap={24} tickLine={false} />
                    <YAxis tickLine={false} width={48} />
                    <Tooltip contentStyle={{ background: "#0E1B2E", border: "1px solid rgba(255,255,255,0.1)" }} />
                    {boundaryLabel && (
                      <ReferenceLine
                        x={boundaryLabel}
                        stroke="#64748B"
                        strokeDasharray="4 2"
                        label={{ value: "forecast →", position: "insideTopRight", fill: "#E879F9", fontSize: 11 }}
                      />
                    )}
                    <Line type="monotone" dataKey="actual" name="Actual" stroke="#E2E8F0" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="adjusted" name="Adjusted ES" stroke={COLORS.adjusted} strokeWidth={1.6} dot={false} />
                    <Line type="monotone" dataKey="linear" name="Linear Trend" stroke={COLORS.linear} strokeWidth={1.6} dot={false} />
                    <Line type="monotone" dataKey="seasonal" name="Seasonal" stroke={COLORS.seasonal} strokeWidth={1.4} strokeDasharray="4 2" dot={false} />
                    <Line
                      type="monotone"
                      dataKey="forecast"
                      name="Forecast"
                      stroke="#E879F9"
                      strokeWidth={2.6}
                      dot={{ r: 2.5, fill: "#E879F9" }}
                      connectNulls
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-400">
                <Legend color="#E2E8F0" label="Actual" />
                <Legend color={COLORS.adjusted} label="Adjusted ES" />
                <Legend color={COLORS.linear} label="Linear Trend" />
                <Legend color={COLORS.seasonal} label="Seasonal" />
                <Legend color="#E879F9" label={`Forecast (next ${future.length})`} />
              </div>
              {d && future.length > 0 && (
                <p className="mt-2 text-xs text-slate-400">
                  Next {future.length} periods:{" "}
                  <span className="font-mono text-fuchsia-300">
                    {future.map((f) => fmtInt(f.forecast)).join(" · ")}
                  </span>{" "}
                  units
                </p>
              )}
            </Panel>
          </AsyncBoundary>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <AsyncBoundary loading={fc.loading} error={fc.error} onRetry={fc.reload} skeleton={<CardSkeleton height="h-40" />}>
          <Panel title="Forecast Accuracy" description="Lower MAD / MSE / MAPE is better; bias near zero is unbiased.">
            {d && (
              <MetricsTable
                series={[
                  { key: "aes", s: d.adjusted_es },
                  { key: "lt", s: d.linear_trend },
                  { key: "se", s: d.seasonal },
                ]}
              />
            )}
          </Panel>
        </AsyncBoundary>

        <AsyncBoundary loading={fc.loading} error={fc.error} onRetry={fc.reload} skeleton={<CardSkeleton height="h-40" />}>
          <Panel title="Seasonal Factors" description="Multiplicative index per season position (1.0 = average).">
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={seasonalData} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="idx" tickLine={false} />
                  <YAxis tickLine={false} width={40} domain={[0, "auto"]} />
                  <Tooltip
                    contentStyle={{ background: "#0E1B2E", border: "1px solid rgba(255,255,255,0.1)" }}
                    formatter={(v: number) => v.toFixed(2)}
                  />
                  <ReferenceLine y={1} stroke="#64748B" strokeDasharray="4 2" />
                  <Bar dataKey="factor" radius={[4, 4, 0, 0]}>
                    {seasonalData.map((entry, i) => (
                      <Cell key={i} fill={entry.factor >= 1 ? "#16D6C9" : "#2E9BFF"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Panel>
        </AsyncBoundary>
      </div>
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="h-2.5 w-2.5 rounded-full" style={{ background: color }} />
      {label}
    </span>
  );
}
