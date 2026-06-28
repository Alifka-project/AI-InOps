"use client";

import { useScenarioStore } from "@/store/useScenarioStore";
import type { ScenarioName } from "@/lib/types";

const OPTIONS: { value: ScenarioName; label: string }[] = [
  { value: "normal", label: "Normal" },
  { value: "hormuz_disruption", label: "Hormuz Disruption" },
];

export function ScenarioToggle() {
  const scenario = useScenarioStore((s) => s.scenario);
  const setScenario = useScenarioStore((s) => s.setScenario);

  return (
    <div
      role="radiogroup"
      aria-label="Operating scenario"
      className="inline-flex items-center rounded-lg border border-white/10 bg-white/5 p-1"
    >
      {OPTIONS.map((opt) => {
        const active = scenario === opt.value;
        const disrupt = opt.value === "hormuz_disruption";
        return (
          <button
            key={opt.value}
            role="radio"
            aria-checked={active}
            onClick={() => setScenario(opt.value)}
            className={`rounded-md px-3 py-1.5 text-xs font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 ${
              active
                ? disrupt
                  ? "bg-rose-500 text-white"
                  : "bg-accent text-navy-900"
                : "text-slate-300 hover:text-white"
            }`}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
