"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useScenarioStore } from "@/store/useScenarioStore";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { fmtNum } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import { Panel } from "@/components/Panel";
import { KpiCard } from "@/components/KpiCard";
import { StatusChip } from "@/components/StatusChip";
import { Slider } from "@/components/Slider";
import { AsyncBoundary } from "@/components/AsyncBoundary";
import { CardSkeleton, KpiSkeletonRow } from "@/components/Skeleton";

const STATUS_FILL: Record<string, string> = {
  OK: "#34D399",
  REORDER: "#F59E0B",
  CRITICAL: "#FB7185",
};

export default function WarehousePage() {
  const scenario = useScenarioStore((s) => s.scenario);
  const settings = useScenarioStore((s) => s.settings);
  const setSettings = useScenarioStore((s) => s.setSettings);

  const wh = useApi(
    () =>
      api.warehousePolicy({
        scenario,
        alpha: settings.alpha,
        beta: settings.beta,
        service_level: settings.serviceLevel,
      }),
    [scenario, settings.alpha, settings.beta, settings.serviceLevel],
  );

  const d = wh.data;
  const chartData =
    d?.policies.map((p) => ({
      hub: p.hub.replace(/ (Recycling|Processing|Recovery) Hub/, ""),
      stock: p.current_stock,
      rop: p.reorder_point,
      safety: p.safety_stock,
      status: p.status,
    })) ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Warehouse Inventory Policy"
        description="Safety stock, reorder point, and EOQ per recycling hub at the chosen service level."
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
        <Panel title="Service Level" className="lg:col-span-1">
          <div className="space-y-5">
            <Slider
              label="Cycle service level"
              value={settings.serviceLevel}
              min={0.9}
              max={0.99}
              step={0.005}
              onChange={(v) => setSettings({ serviceLevel: v })}
              format={(v) => `${(v * 100).toFixed(1)}%`}
            />
            <p className="text-xs text-slate-400">
              Higher service levels demand larger safety stock. The z-multiplier
              snaps to 90 / 95 / 97.5 / 99% bands.
            </p>
            {d && (
              <div className="space-y-2 rounded-lg border border-white/10 bg-ink/40 p-3 text-sm">
                <Row label="Planning demand" value={`${fmtNum(d.forecast_demand)} t`} />
                <Row label="Avg lead time" value={`${fmtNum(d.avg_lead_time_days)} d`} />
                <Row
                  label="Hubs to reorder"
                  value={`${d.hubs_needing_reorder} / ${d.policies.length}`}
                />
              </div>
            )}
          </div>
        </Panel>

        <div className="space-y-6 lg:col-span-3">
          <AsyncBoundary
            loading={wh.loading}
            error={wh.error}
            onRetry={wh.reload}
            skeleton={<KpiSkeletonRow count={3} />}
          >
            {d && (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <KpiCard
                  label="Critical Hubs"
                  value={`${d.policies.filter((p) => p.status === "CRITICAL").length}`}
                  accent="danger"
                  sublabel="below safety stock"
                />
                <KpiCard
                  label="Reorder Hubs"
                  value={`${d.policies.filter((p) => p.status === "REORDER").length}`}
                  accent="warn"
                  sublabel="below ROP"
                />
                <KpiCard
                  label="Healthy Hubs"
                  value={`${d.policies.filter((p) => p.status === "OK").length}`}
                  sublabel="above ROP"
                />
              </div>
            )}
          </AsyncBoundary>

          <AsyncBoundary
            loading={wh.loading}
            error={wh.error}
            onRetry={wh.reload}
            skeleton={<CardSkeleton />}
          >
            <Panel
              title="Stock vs Reorder Point"
              description="Current stock against the reorder threshold per hub."
            >
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="hub" tickLine={false} />
                    <YAxis tickLine={false} width={48} />
                    <Tooltip
                      contentStyle={{ background: "#0E1B2E", border: "1px solid rgba(255,255,255,0.1)" }}
                      formatter={(v: number) => `${fmtNum(v)} t`}
                    />
                    <Bar dataKey="stock" name="Current stock" radius={[4, 4, 0, 0]}>
                      {chartData.map((entry, i) => (
                        <Cell key={i} fill={STATUS_FILL[entry.status] ?? "#16D6C9"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Panel>
          </AsyncBoundary>
        </div>
      </div>

      <AsyncBoundary
        loading={wh.loading}
        error={wh.error}
        onRetry={wh.reload}
        skeleton={<CardSkeleton height="h-40" />}
      >
        <Panel title="Inventory Policy by Hub">
          <div className="overflow-x-auto">
            <table className="table-base">
              <thead>
                <tr>
                  <th>Hub</th>
                  <th className="text-right">Current Stock</th>
                  <th className="text-right">Safety Stock</th>
                  <th className="text-right">Reorder Point</th>
                  <th className="text-right">EOQ</th>
                  <th className="text-right">Suggested Order</th>
                  <th className="text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {d?.policies.map((p) => (
                  <tr key={p.hub}>
                    <td className="font-medium text-white">{p.hub}</td>
                    <td className="text-right font-mono">{fmtNum(p.current_stock)}</td>
                    <td className="text-right font-mono">{fmtNum(p.safety_stock)}</td>
                    <td className="text-right font-mono">{fmtNum(p.reorder_point)}</td>
                    <td className="text-right font-mono">{fmtNum(p.eoq)}</td>
                    <td className="text-right font-mono">
                      {p.suggested_order > 0 ? fmtNum(p.suggested_order) : "—"}
                    </td>
                    <td className="text-center">
                      <StatusChip status={p.status} />
                    </td>
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

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-slate-400">{label}</span>
      <span className="font-mono text-white">{value}</span>
    </div>
  );
}
