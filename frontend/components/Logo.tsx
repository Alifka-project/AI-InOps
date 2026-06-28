/**
 * Supply-chain network mark: a central hub (warehouse) linked to supplier
 * nodes — the supplier → hub → warehouse network the digital twin optimises.
 */
export function Logo({ className = "h-10 w-10" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 48 48"
      className={className}
      role="img"
      aria-label="Supply-chain network logo"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="scLogoBg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#19E0D2" />
          <stop offset="100%" stopColor="#10B4AB" />
        </linearGradient>
      </defs>
      <rect width="48" height="48" rx="12" fill="url(#scLogoBg)" />
      {/* routes from the central hub to the supplier nodes */}
      <g stroke="#041E42" strokeWidth="2.4" strokeLinecap="round" opacity="0.85">
        <line x1="24" y1="24" x2="13" y2="13" />
        <line x1="24" y1="24" x2="35" y2="13" />
        <line x1="24" y1="24" x2="13" y2="35" />
        <line x1="24" y1="24" x2="35" y2="35" />
      </g>
      {/* supplier / warehouse nodes */}
      <g fill="#041E42">
        <circle cx="13" cy="13" r="3.4" />
        <circle cx="35" cy="13" r="3.4" />
        <circle cx="13" cy="35" r="3.4" />
        <circle cx="35" cy="35" r="3.4" />
      </g>
      {/* central hub */}
      <circle cx="24" cy="24" r="5.4" fill="#041E42" />
      <circle cx="24" cy="24" r="2.2" fill="#19E0D2" />
    </svg>
  );
}
