"use client";

import type { ScenarioComparison, ScenarioName } from "@/lib/types";
import { deltaPct, fmtPct, fmtUsdCompact, fmtInt } from "@/lib/format";

function Metric({
  label,
  delta,
  goodWhenUp,
  detail,
}: {
  label: string;
  delta: number;
  goodWhenUp: boolean;
  detail: string;
}) {
  const up = delta > 0;
  const good = up === goodWhenUp;
  return (
    <div className="flex flex-col">
      <span className="text-[11px] uppercase tracking-wider text-slate-400">
        {label}
      </span>
      <span
        className={`text-sm font-semibold ${
          Math.abs(delta) < 0.0005
            ? "text-slate-300"
            : good
              ? "text-emerald-300"
              : "text-rose-300"
        }`}
      >
        {Math.abs(delta) < 0.0005
          ? "no change"
          : `${up ? "▲ +" : "▼ "}${fmtPct(delta)}`}
      </span>
      <span className="text-[11px] text-slate-500">{detail}</span>
    </div>
  );
}

export function DeltaBanner({
  comparison,
  scenario,
}: {
  comparison: ScenarioComparison;
  scenario: ScenarioName;
}) {
  const n = comparison.normal;
  const d = comparison.hormuz_disruption;
  const disrupted = scenario === "hormuz_disruption";

  return (
    <div
      className={`card card-pad ${
        disrupted ? "ring-1 ring-inset ring-rose-500/30" : ""
      }`}
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="max-w-md">
          <p className="label">Resilience Impact</p>
          <p className="mt-1 text-sm text-slate-300">
            Strait of Hormuz disruption vs normal operations — modelled effect on
            the recovery network.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-x-8 gap-y-3 sm:grid-cols-4">
          <Metric
            label="Transport Cost"
            delta={deltaPct(d.optimal_transport_cost, n.optimal_transport_cost)}
            goodWhenUp={false}
            detail={fmtUsdCompact(d.optimal_transport_cost)}
          />
          <Metric
            label="Planning Demand"
            delta={deltaPct(d.next_month_demand, n.next_month_demand)}
            goodWhenUp={false}
            detail={`${fmtInt(d.next_month_demand)} u`}
          />
          <Metric
            label="Recovered Value"
            delta={deltaPct(
              d.recovered_material_value,
              n.recovered_material_value,
            )}
            goodWhenUp
            detail={fmtUsdCompact(d.recovered_material_value)}
          />
          <Metric
            label="Hubs to Reorder"
            delta={deltaPct(d.hubs_needing_reorder, n.hubs_needing_reorder)}
            goodWhenUp={false}
            detail={`${d.hubs_needing_reorder} of 3`}
          />
        </div>
      </div>
    </div>
  );
}
