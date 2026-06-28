// Display formatting helpers.

export const fmtInt = (n: number): string =>
  Number.isFinite(n) ? Math.round(n).toLocaleString("en-US") : "—";

export const fmtNum = (n: number, digits = 1): string =>
  Number.isFinite(n)
    ? n.toLocaleString("en-US", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      })
    : "—";

export const fmtUsd = (n: number): string =>
  Number.isFinite(n)
    ? `$${Math.round(n).toLocaleString("en-US")}`
    : "—";

export const fmtUsdCompact = (n: number): string => {
  if (!Number.isFinite(n)) return "—";
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (Math.abs(n) >= 1_000) return `$${(n / 1_000).toFixed(1)}K`;
  return `$${Math.round(n)}`;
};

export const fmtPct = (fraction: number, digits = 1): string =>
  Number.isFinite(fraction) ? `${(fraction * 100).toFixed(digits)}%` : "—";

export const deltaPct = (next: number, base: number): number => {
  if (!base) return 0;
  return (next - base) / base;
};
