"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Dataset, ScenarioName } from "@/lib/types";

export interface AnalysisSettings {
  alpha: number;
  beta: number;
  horizon: number;
  serviceLevel: number;
  autoTune: boolean;
}

interface AppState {
  scenario: ScenarioName;
  settings: AnalysisSettings;
  dataset: Dataset | null;
  setScenario: (scenario: ScenarioName) => void;
  toggleScenario: () => void;
  setSettings: (patch: Partial<AnalysisSettings>) => void;
  setDataset: (dataset: Dataset | null) => void;
  clearDataset: () => void;
}

export const DEFAULT_SETTINGS: AnalysisSettings = {
  alpha: 0.5,
  beta: 0.3,
  horizon: 6,
  serviceLevel: 0.95,
  autoTune: false,
};

export const useScenarioStore = create<AppState>()(
  persist(
    (set) => ({
      scenario: "normal",
      settings: DEFAULT_SETTINGS,
      dataset: null,
      setScenario: (scenario) => set({ scenario }),
      toggleScenario: () =>
        set((s) => ({
          scenario: s.scenario === "normal" ? "hormuz_disruption" : "normal",
        })),
      setSettings: (patch) =>
        set((s) => ({ settings: { ...s.settings, ...patch } })),
      setDataset: (dataset) => set({ dataset }),
      clearDataset: () => set({ dataset: null }),
    }),
    {
      name: "digital-twin-store",
      // Persist the dataset + preferences so a refresh keeps the user's data.
      partialize: (s) => ({
        scenario: s.scenario,
        settings: s.settings,
        dataset: s.dataset,
      }),
    },
  ),
);
