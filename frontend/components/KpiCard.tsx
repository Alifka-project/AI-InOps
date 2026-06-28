import type { ReactNode } from "react";

interface Props {
  label: string;
  value: string;
  sublabel?: ReactNode;
  delta?: { value: number; goodWhenUp?: boolean } | null;
  accent?: "default" | "warn" | "danger";
}

function DeltaBadge({
  value,
  goodWhenUp = true,
}: {
  value: number;
  goodWhenUp?: boolean;
}) {
  if (!Number.isFinite(value) || Math.abs(value) < 0.0005) {
    return <span className="text-xs text-slate-500">no change</span>;
  }
  const up = value > 0;
  const good = up === goodWhenUp;
  const pct = `${up ? "+" : ""}${(value * 100).toFixed(1)}%`;
  return (
    <span
      className={`chip ${
        good
          ? "bg-emerald-500/15 text-emerald-300"
          : "bg-rose-500/15 text-rose-300"
      }`}
    >
      {up ? "▲" : "▼"} {pct}
    </span>
  );
}

export function KpiCard({
  label,
  value,
  sublabel,
  delta,
  accent = "default",
}: Props) {
  const ring =
    accent === "danger"
      ? "ring-1 ring-inset ring-rose-500/30"
      : accent === "warn"
        ? "ring-1 ring-inset ring-amber-500/30"
        : "";
  return (
    <div className={`card card-pad ${ring}`}>
      <p className="label">{label}</p>
      <p className="mt-1.5 text-2xl font-semibold tracking-tight text-white">
        {value}
      </p>
      <div className="mt-2 flex items-center gap-2">
        {delta && <DeltaBadge value={delta.value} goodWhenUp={delta.goodWhenUp} />}
        {sublabel && <span className="text-xs text-slate-400">{sublabel}</span>}
      </div>
    </div>
  );
}
