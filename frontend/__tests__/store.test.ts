import { describe, it, expect, beforeEach } from "vitest";
import { useScenarioStore, DEFAULT_SETTINGS } from "@/store/useScenarioStore";
import type { Dataset } from "@/lib/types";

const DATASET = {
  meta: { name: "Acme", is_sample: false, n_periods: 12, n_suppliers: 2, n_warehouses: 2, n_orders: 5, warnings: [] },
} as unknown as Dataset;

describe("useScenarioStore", () => {
  beforeEach(() => {
    useScenarioStore.setState({
      scenario: "normal",
      settings: DEFAULT_SETTINGS,
      dataset: null,
    });
  });

  it("toggles scenario", () => {
    useScenarioStore.getState().toggleScenario();
    expect(useScenarioStore.getState().scenario).toBe("hormuz_disruption");
  });

  it("sets and clears the dataset", () => {
    useScenarioStore.getState().setDataset(DATASET);
    expect(useScenarioStore.getState().dataset?.meta.name).toBe("Acme");
    useScenarioStore.getState().clearDataset();
    expect(useScenarioStore.getState().dataset).toBeNull();
  });

  it("merges partial settings (auto-tune)", () => {
    useScenarioStore.getState().setSettings({ autoTune: true, alpha: 0.7 });
    const s = useScenarioStore.getState().settings;
    expect(s.autoTune).toBe(true);
    expect(s.alpha).toBe(0.7);
    expect(s.beta).toBe(DEFAULT_SETTINGS.beta);
  });
});
