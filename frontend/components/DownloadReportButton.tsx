"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useScenarioStore } from "@/store/useScenarioStore";

export function DownloadReportButton({
  variant = "ghost",
}: {
  variant?: "ghost" | "primary";
}) {
  const dataset = useScenarioStore((s) => s.dataset);
  const scenario = useScenarioStore((s) => s.scenario);
  const settings = useScenarioStore((s) => s.settings);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onClick = async () => {
    if (!dataset) return;
    setBusy(true);
    setError(null);
    try {
      const blob = await api.downloadReport(dataset, scenario, settings);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      const tag = dataset.meta.is_sample ? "sample" : scenario;
      a.href = url;
      a.download = `digital-twin-report-${tag}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Report failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col items-end">
      <button
        onClick={onClick}
        disabled={!dataset || busy}
        className={variant === "primary" ? "btn-primary" : "btn-ghost"}
        title={dataset ? "Download the analysis as a PDF" : "Load a dataset first"}
      >
        <svg
          className="h-4 w-4"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.7}
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 3v12m0 0l-4-4m4 4l4-4M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2"
          />
        </svg>
        {busy ? "Generating…" : "Download report"}
      </button>
      {error && <span className="mt-1 text-[11px] text-rose-300">{error}</span>}
    </div>
  );
}
