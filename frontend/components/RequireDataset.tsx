"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { ReactNode } from "react";
import { useScenarioStore } from "@/store/useScenarioStore";

/**
 * Gates analysis pages behind an active dataset. Until the user uploads data
 * (or loads the sample) the page shows an explanatory empty-state pointing to
 * the Data page — no analysis ever runs on fabricated data.
 */
export function RequireDataset({ children }: { children: ReactNode }) {
  const dataset = useScenarioStore((s) => s.dataset);
  // Avoid hydration flash: only judge "no dataset" after mount (store rehydrates
  // from localStorage on the client).
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);

  if (!ready) {
    return (
      <div className="card card-pad">
        <div className="h-40 animate-pulse rounded-md bg-white/5" />
      </div>
    );
  }

  if (!dataset) {
    return (
      <div className="card card-pad mx-auto max-w-xl text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-accent/15 text-accent">
          <svg
            className="h-6 w-6"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.6}
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M7 16a4 4 0 01-.88-7.9A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 13l3-3m0 0l3 3m-3-3v9"
            />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-white">No dataset loaded</h3>
        <p className="mx-auto mt-2 max-w-md text-sm text-slate-400">
          This twin analyses <strong>your</strong> data. Upload the eight CSV
          inputs (historical sales, suppliers, transport, external factors,
          inventory, orders, warehouse parameters, and transport history) or load
          the labelled sample to explore.
        </p>
        <Link href="/data" className="btn-primary mt-5 inline-flex">
          Go to Data &amp; Upload
        </Link>
      </div>
    );
  }

  return <>{children}</>;
}
