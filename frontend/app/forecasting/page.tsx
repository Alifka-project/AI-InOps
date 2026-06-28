"use client";

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
import { useScenarioStore } from "@/store/useScenarioStore";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { fmtInt, fmtNum } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import { Panel } from "@/components/Panel";
import { Slider } from "@/components/Slider";
import { AsyncBoundary } from "@/components/AsyncBoundary";
import { CardSkeleton } from "@/components/Skeleton";
import type { Series } from "@/lib/types";

const METHOD_COLORS = {
  adjusted: "#16D6C9",
  linear: "#2E9BFF",
  seasonal: "#F59E0B",
};

function MetricsTable({ series }: { series: { key: string; s: Series }[] }) {
  // Lowest MAD wins.
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
                <span className="ml-2 chip bg-emerald-500/15 text-emerald-300">
                  best fit
                </span>
              )}
            </td>
            <td className="text-right font-mono">{fmtNum(s.metrics?.MAD ?? NaN)}</td>
            <td className="text-right font-mono">{fmtNum(s.metrics?.MSE ?? NaN)}</td>
            <td className="text-right font-mono">
              {fmtNum(s.metrics?.MAPE ?? NaN)}%
            </td>
            <td className="text-right font-mono">{fmtNum(s.metrics?.Bias ?? NaN)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function ForecastingPage() {
  const scenario = useScenarioStore((s) => s.scenario);
  const settings = useScenarioStore((s) => s.settings);
  const setSettings = useScenarioStore((s) => s.setSettings);

  const fc = useApi(
    () =>
      api.forecastDemand({
        scenario,
        alpha: settings.alpha,
        beta: settings.beta,
        horizon: settings.horizon,
      }),
    [scenario, settings.alpha, settings.beta, settings.horizon],
  );

  const d = fc.data;
  const chartData =
    d?.months.map((m, i) => ({
      month: m,
      actual: d.actual[i],
      adjusted: d.adjusted_es.fitted[i],
      linear: d.linear_trend.fitted[i],
      seasonal: d.seasonal.fitted[i],
    })) ?? [];

  const seasonalData =
    d?.seasonal_factors.map((f, i) => ({
      month: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][i] ?? `${i + 1}`,
      factor: f,
    })) ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Demand Forecasting"
        description="Compare three textbook methods on returned-appliance volume and tune the smoothing constants live."
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Panel
          title="Smoothing Parameters"
          description="Drives adjusted exponential smoothing."
          className="lg:col-span-1"
        >
          <div className="space-y-5">
            <Slider
              label="Alpha (level)"
              value={settings.alpha}
              min={0.05}
              max={1}
              step={0.05}
              onChange={(v) => setSettings({ alpha: v })}
              format={(v) => v.toFixed(2)}
            />
            <Slider
              label="Beta (trend)"
              value={settings.beta}
              min={0}
              max={1}
              step={0.05}
              onChange={(v) => setSettings({ beta: v })}
              format={(v) => v.toFixed(2)}
            />
            <Slider
              label="Forecast horizon"
              value={settings.horizon}
              min={1}
              max={12}
              step={1}
              onChange={(v) => setSettings({ horizon: v })}
              format={(v) => `${v} mo`}
            />
            {d && (
              <div className="rounded-lg border border-white/10 bg-ink/40 p-3">
                <p className="label">Next-period planning demand</p>
                <p className="mt-1 text-2xl font-semibold text-accent">
                  {fmtInt(d.planning_demand_next)}
                </p>
                <p className="text-xs text-slate-400">
                  base forecast {fmtInt(d.next_forecast)} ×{" "}
                  {d.recovered_demand_multiplier.toFixed(2)} scenario factor
                </p>
              </div>
            )}
          </div>
        </Panel>

        <div className="lg:col-span-2">
          <AsyncBoundary
            loading={fc.loading}
            error={fc.error}
            onRetry={fc.reload}
            skeleton={<CardSkeleton />}
          >
            <Panel
              title="Actual vs Forecast Methods"
              description="In-sample fit for each forecasting technique."
            >
              <div className="h-80 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" minTickGap={24} tickLine={false} />
                    <YAxis tickLine={false} width={48} />
                    <Tooltip
                      contentStyle={{ background: "#0E1B2E", border: "1px solid rgba(255,255,255,0.1)" }}
                    />
                    <Line type="monotone" dataKey="actual" name="Actual" stroke="#E2E8F0" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="adjusted" name="Adjusted ES" stroke={METHOD_COLORS.adjusted} strokeWidth={1.6} dot={false} />
                    <Line type="monotone" dataKey="linear" name="Linear Trend" stroke={METHOD_COLORS.linear} strokeWidth={1.6} dot={false} />
                    <Line type="monotone" dataKey="seasonal" name="Seasonal" stroke={METHOD_COLORS.seasonal} strokeWidth={1.6} strokeDasharray="4 2" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-400">
                <Legend color="#E2E8F0" label="Actual" />
                <Legend color={METHOD_COLORS.adjusted} label="Adjusted ES" />
                <Legend color={METHOD_COLORS.linear} label="Linear Trend" />
                <Legend color={METHOD_COLORS.seasonal} label="Seasonal" />
              </div>
            </Panel>
          </AsyncBoundary>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <AsyncBoundary
          loading={fc.loading}
          error={fc.error}
          onRetry={fc.reload}
          skeleton={<CardSkeleton height="h-40" />}
        >
          <Panel
            title="Forecast Accuracy"
            description="Lower MAD / MSE / MAPE is better; bias near zero is unbiased."
          >
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

        <AsyncBoundary
          loading={fc.loading}
          error={fc.error}
          onRetry={fc.reload}
          skeleton={<CardSkeleton height="h-40" />}
        >
          <Panel
            title="Seasonal Factors"
            description="Multiplicative index by month (1.0 = average)."
          >
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={seasonalData} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="month" tickLine={false} />
                  <YAxis tickLine={false} width={40} domain={[0, "auto"]} />
                  <Tooltip
                    contentStyle={{ background: "#0E1B2E", border: "1px solid rgba(255,255,255,0.1)" }}
                    formatter={(v: number) => v.toFixed(2)}
                  />
                  <ReferenceLine y={1} stroke="#64748B" strokeDasharray="4 2" />
                  <Bar dataKey="factor" radius={[4, 4, 0, 0]}>
                    {seasonalData.map((entry, i) => (
                      <Cell
                        key={i}
                        fill={entry.factor >= 1 ? "#16D6C9" : "#2E9BFF"}
                      />
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
