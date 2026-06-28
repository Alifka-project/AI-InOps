"use client";

import { create } from "zustand";
import type { ScenarioName } from "@/lib/types";

export interface ForecastSettings {
  alpha: number;
  beta: number;
  horizon: number;
  serviceLevel: number;
}

interface ScenarioState {
  scenario: ScenarioName;
  settings: ForecastSettings;
  setScenario: (scenario: ScenarioName) => void;
  toggleScenario: () => void;
  setSettings: (patch: Partial<ForecastSettings>) => void;
}

export const DEFAULT_SETTINGS: ForecastSettings = {
  alpha: 0.5,
  beta: 0.3,
  horizon: 6,
  serviceLevel: 0.95,
};

export const useScenarioStore = create<ScenarioState>((set) => ({
  scenario: "normal",
  settings: DEFAULT_SETTINGS,
  setScenario: (scenario) => set({ scenario }),
  toggleScenario: () =>
    set((s) => ({
      scenario: s.scenario === "normal" ? "hormuz_disruption" : "normal",
    })),
  setSettings: (patch) =>
    set((s) => ({ settings: { ...s.settings, ...patch } })),
}));
