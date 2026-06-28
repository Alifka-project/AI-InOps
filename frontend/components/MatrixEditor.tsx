"use client";

interface Props {
  cost: number[][];
  supply: number[];
  demand: number[];
  rowLabels: string[];
  colLabels: string[];
  onCostChange: (i: number, j: number, value: number) => void;
  onSupplyChange: (i: number, value: number) => void;
  onDemandChange: (j: number, value: number) => void;
}

function NumCell({
  value,
  onChange,
  label,
  tone = "cost",
}: {
  value: number;
  onChange: (v: number) => void;
  label: string;
  tone?: "cost" | "supply" | "demand";
}) {
  const toneCls =
    tone === "supply"
      ? "text-accent"
      : tone === "demand"
        ? "text-electric"
        : "text-slate-100";
  return (
    <input
      type="number"
      aria-label={label}
      value={Number.isFinite(value) ? value : 0}
      min={0}
      onChange={(e) => onChange(Number(e.target.value))}
      className={`w-16 rounded-md border border-white/10 bg-ink/60 px-2 py-1.5 text-center text-sm ${toneCls} focus:border-accent/50 focus:outline-none focus:ring-1 focus:ring-accent/40`}
    />
  );
}

export function MatrixEditor({
  cost,
  supply,
  demand,
  rowLabels,
  colLabels,
  onCostChange,
  onSupplyChange,
  onDemandChange,
}: Props) {
  const supplyTotal = supply.reduce((a, b) => a + b, 0);
  const demandTotal = demand.reduce((a, b) => a + b, 0);

  return (
    <div className="overflow-x-auto">
      <table className="border-separate border-spacing-1">
        <thead>
          <tr>
            <th className="px-2 py-1 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
              Cost / t
            </th>
            {colLabels.map((c, j) => (
              <th
                key={j}
                className="px-2 py-1 text-center text-xs font-semibold text-electric"
                title={c}
              >
                {c}
              </th>
            ))}
            <th className="px-2 py-1 text-center text-xs font-semibold uppercase tracking-wider text-accent">
              Supply
            </th>
          </tr>
        </thead>
        <tbody>
          {cost.map((row, i) => (
            <tr key={i}>
              <td
                className="px-2 py-1 text-xs font-semibold text-slate-300"
                title={rowLabels[i]}
              >
                {rowLabels[i]}
              </td>
              {row.map((val, j) => (
                <td key={j} className="text-center">
                  <NumCell
                    value={val}
                    label={`cost ${rowLabels[i]} to ${colLabels[j]}`}
                    onChange={(v) => onCostChange(i, j, v)}
                  />
                </td>
              ))}
              <td className="text-center">
                <NumCell
                  value={supply[i]}
                  tone="supply"
                  label={`supply ${rowLabels[i]}`}
                  onChange={(v) => onSupplyChange(i, v)}
                />
              </td>
            </tr>
          ))}
          <tr>
            <td className="px-2 py-1 text-xs font-semibold uppercase tracking-wider text-electric">
              Demand
            </td>
            {demand.map((val, j) => (
              <td key={j} className="text-center">
                <NumCell
                  value={val}
                  tone="demand"
                  label={`demand ${colLabels[j]}`}
                  onChange={(v) => onDemandChange(j, v)}
                />
              </td>
            ))}
            <td className="text-center text-xs text-slate-400">
              <div className={supplyTotal === demandTotal ? "" : "text-amber-300"}>
                Σ {supplyTotal.toFixed(0)} / {demandTotal.toFixed(0)}
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <p className="mt-2 text-xs text-slate-500">
        {supplyTotal === demandTotal
          ? "Balanced problem."
          : "Unbalanced — a zero-cost dummy row/column will be added automatically."}
      </p>
    </div>
  );
}
