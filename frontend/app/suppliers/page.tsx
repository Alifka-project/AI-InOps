"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Dataset } from "@/lib/types";
import { useScenarioStore } from "@/store/useScenarioStore";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { fmtNum, fmtPct } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import { Panel } from "@/components/Panel";
import { KpiCard } from "@/components/KpiCard";
import { AsyncBoundary } from "@/components/AsyncBoundary";
import { CardSkeleton, KpiSkeletonRow } from "@/components/Skeleton";
import { RequireDataset } from "@/components/RequireDataset";

export default function SuppliersPage() {
  return (
    <RequireDataset>
      <SuppliersBody />
    </RequireDataset>
  );
}

function SuppliersBody() {
  const dataset = useScenarioStore((s) => s.dataset) as Dataset;
  const scenario = useScenarioStore((s) => s.scenario);
  const settings = useScenarioStore((s) => s.settings);

  const sup = useApi(
    () => api.forecastSuppliers(dataset, scenario, settings),
    [dataset.meta.name, scenario, settings.alpha, settings.beta, settings.horizon],
  );

  const d = sup.data;
  const chartData =
    d?.suppliers.map((s) => ({
      center: s.center.length > 14 ? s.center.slice(0, 13) + "…" : s.center,
      available: s.available_t,
      capacity: s.monthly_capacity_t,
    })) ?? [];
  const disrupted = scenario === "hormuz_disruption";

  return (
    <div className="space-y-6">
      <PageHeader
        title="Supplier Availability"
        description="Forecast available tonnage per supplier from historical shipments, capped by contractual capacity."
      />

      {disrupted && d && d.lead_time_add_days > 0 && (
        <div className="card card-pad ring-1 ring-inset ring-rose-500/30">
          <p className="text-sm text-rose-200">
            <span className="font-semibold">Disruption impact:</span> lead times extended by{" "}
            <span className="font-semibold">{d.lead_time_add_days} days</span> across all
            suppliers (Cape-of-Good-Hope rerouting) — raising required safety stock downstream.
          </p>
        </div>
      )}

      <AsyncBoundary loading={sup.loading} error={sup.error} onRetry={sup.reload} skeleton={<KpiSkeletonRow count={3} />}>
        {d && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <KpiCard label="Total Available" value={`${fmtNum(d.total_available_t)} t`} sublabel="next period" />
            <KpiCard label="Avg Utilization" value={fmtPct(d.avg_capacity_utilization)} sublabel="of capacity" />
            <KpiCard
              label="Lead-Time Penalty"
              value={`+${d.lead_time_add_days} d`}
              accent={d.lead_time_add_days > 0 ? "warn" : "default"}
              sublabel={disrupted ? "disruption" : "normal"}
            />
          </div>
        )}
      </AsyncBoundary>

      <AsyncBoundary loading={sup.loading} error={sup.error} onRetry={sup.reload} skeleton={<CardSkeleton />}>
        <Panel title="Availability vs Capacity" description="Forecast available tonnage relative to each supplier's ceiling.">
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="center" tickLine={false} />
                <YAxis tickLine={false} width={48} />
                <Tooltip
                  contentStyle={{ background: "#0E1B2E", border: "1px solid rgba(255,255,255,0.1)" }}
                  formatter={(v: number) => `${fmtNum(v)} t`}
                />
                <Legend />
                <Bar dataKey="capacity" name="Capacity" fill="#1E3A5F" radius={[4, 4, 0, 0]} />
                <Bar dataKey="available" name="Available" fill="#16D6C9" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </AsyncBoundary>

      <AsyncBoundary loading={sup.loading} error={sup.error} onRetry={sup.reload} skeleton={<CardSkeleton height="h-40" />}>
        <Panel title="Suppliers">
          <div className="overflow-x-auto">
            <table className="table-base">
              <thead>
                <tr>
                  <th>Supplier</th>
                  <th className="text-right">Lead Time</th>
                  <th className="text-right">Capacity (t)</th>
                  <th className="text-right">Forecast (t)</th>
                  <th className="text-right">Available (t)</th>
                  <th className="text-right">Utilization</th>
                  <th className="text-right">Price/t</th>
                </tr>
              </thead>
              <tbody>
                {d?.suppliers.map((s) => (
                  <tr key={s.center}>
                    <td className="font-medium text-white">{s.center}</td>
                    <td className="text-right font-mono">{s.lead_time_days} d</td>
                    <td className="text-right font-mono">{s.monthly_capacity_t}</td>
                    <td className="text-right font-mono">{fmtNum(s.forecast_next_t)}</td>
                    <td className="text-right font-mono">{fmtNum(s.available_t)}</td>
                    <td className="text-right font-mono">{fmtPct(s.capacity_utilization)}</td>
                    <td className="text-right font-mono">${s.gate_fee_per_t}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </AsyncBoundary>
    </div>
  );
}
