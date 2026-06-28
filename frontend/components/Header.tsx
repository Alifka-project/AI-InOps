"use client";

import { usePathname } from "next/navigation";
import { NAV_ITEMS } from "@/lib/nav";
import { useScenarioStore } from "@/store/useScenarioStore";
import { ScenarioToggle } from "./ScenarioToggle";

export function Header() {
  const pathname = usePathname();
  const scenario = useScenarioStore((s) => s.scenario);
  const current =
    NAV_ITEMS.find((n) => n.href === pathname) ?? NAV_ITEMS[0];
  const disrupted = scenario === "hormuz_disruption";

  return (
    <header className="sticky top-0 z-20 border-b border-white/5 bg-ink/80 backdrop-blur">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
        <div className="min-w-0">
          <p className="label">Operations Console</p>
          <h1 className="truncate text-lg font-semibold text-white">
            {current.label}
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`chip hidden sm:inline-flex ${
              disrupted
                ? "bg-rose-500/15 text-rose-300 ring-1 ring-inset ring-rose-500/30"
                : "bg-accent/15 text-accent ring-1 ring-inset ring-accent/30"
            }`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                disrupted ? "bg-rose-400" : "bg-accent"
              }`}
            />
            {disrupted ? "Disruption Active" : "Normal Operations"}
          </span>
          <ScenarioToggle />
        </div>
      </div>
    </header>
  );
}
