const STYLES: Record<string, string> = {
  OK: "bg-emerald-500/15 text-emerald-300 ring-1 ring-inset ring-emerald-500/30",
  REORDER: "bg-amber-500/15 text-amber-300 ring-1 ring-inset ring-amber-500/30",
  CRITICAL: "bg-rose-500/15 text-rose-300 ring-1 ring-inset ring-rose-500/30",
};

export function StatusChip({ status }: { status: string }) {
  const cls = STYLES[status] ?? "bg-white/10 text-slate-300";
  return <span className={`chip ${cls}`}>{status}</span>;
}
