"use client";

import { useEffect, useState } from "react";
import { useScenarioStore } from "@/store/useScenarioStore";

export function Footer() {
  const dataset = useScenarioStore((s) => s.dataset);
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);

  let source = "Upload your data to begin";
  if (ready && dataset) {
    source = dataset.meta.is_sample
      ? "Sample dataset (synthetic) — load your own for production use"
      : `Live data · ${dataset.meta.name}`;
  }

  return (
    <footer className="border-t border-white/5 px-6 py-4 text-center text-xs text-slate-500">
      Digital Twin · Electrolux UAE Operations · {source}
    </footer>
  );
}
