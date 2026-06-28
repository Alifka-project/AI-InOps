"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
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

export default function OverviewPage() {
  const scenario = useScenarioStore((s) => s.scenario);
  const settings = useScenarioStore((s) => s.settings);

  const req = {
    scenario,
    alpha: settings.alpha,
    beta: settings.beta,
    horizon: settings.horizon,
    service_level: settings.serviceLevel,
  };

  const sim = useApi(() => api.simulate(req), [
    scenario,
    settings.alpha,
    settings.beta,
    settings.horizon,
    settings.serviceLevel,
  ]);

  const cmp = useApi(() => api.compareScenarios(req), [
    settings.alpha,
    settings.beta,
    settings.horizon,
    settings.serviceLevel,
  ]);

  const chartData =
    sim.data?.months.map((m, i) => ({
      month: m,
      actual: sim.data?.actual[i] ?? null,
      fitted: sim.data?.forecast_fitted[i] ?? null,
    })) ?? [];
  const horizonStart = sim.data?.months.length ?? 0;
  const horizonData =
    sim.data?.forecast_horizon.map((v, i) => ({
      month: `+${i + 1}`,
      forecast: v,
    })) ?? [];

  const k = sim.data?.kpis;
  const cmpData = cmp.data;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Operations Overview"
        description="A live snapshot of the Electrolux UAE recovery network under the selected scenario."
      />

      <AsyncBoundary
        loading={cmp.loading}
        error={cmp.error}
        onRetry={cmp.reload}
        skeleton={<CardSkeleton height="h-20" />}
      >
        {cmpData && <DeltaBanner comparison={cmpData} scenario={scenario} />}
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
              label="Next-Month Demand"
              value={`${fmtInt(k.next_month_demand)}`}
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
              value={`${k.hubs_needing_reorder} / 3`}
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
        skeleton={<CardSkeleton />}
      >
        <Panel
          title="Returned-Appliance Demand"
          description="Historical volume with the in-sample adjusted exponential-smoothing fit."
        >
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
                <defs>
                  <linearGradient id="demandFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#16D6C9" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#16D6C9" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" minTickGap={24} tickLine={false} />
                <YAxis tickLine={false} width={48} />
                <Tooltip
                  contentStyle={{ background: "#0E1B2E", border: "1px solid rgba(255,255,255,0.1)" }}
                  labelStyle={{ color: "#94a3b8" }}
                />
                <Area
                  type="monotone"
                  dataKey="actual"
                  name="Actual"
                  stroke="#16D6C9"
                  strokeWidth={2}
                  fill="url(#demandFill)"
                />
                <Line
                  type="monotone"
                  dataKey="fitted"
                  name="Adjusted ES fit"
                  stroke="#2E9BFF"
                  strokeWidth={1.6}
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          {horizonData.length > 0 && (
            <p className="mt-3 text-xs text-slate-400">
              Forward {horizonData.length}-month forecast (from period {horizonStart}):{" "}
              <span className="font-mono text-accent">
                {horizonData.map((h) => fmtInt(h.forecast)).join(" · ")}
              </span>{" "}
              units
            </p>
          )}
        </Panel>
      </AsyncBoundary>
    </div>
  );
}
