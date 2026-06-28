import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ScenarioToggle } from "@/components/ScenarioToggle";
import { useScenarioStore } from "@/store/useScenarioStore";

describe("ScenarioToggle", () => {
  beforeEach(() => {
    useScenarioStore.setState({ scenario: "normal" });
  });

  it("renders both scenario options", () => {
    render(<ScenarioToggle />);
    expect(screen.getByRole("radio", { name: "Normal" })).toBeInTheDocument();
    expect(
      screen.getByRole("radio", { name: "Hormuz Disruption" }),
    ).toBeInTheDocument();
  });

  it("marks the active scenario as checked", () => {
    render(<ScenarioToggle />);
    expect(screen.getByRole("radio", { name: "Normal" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });

  it("updates the store when the user switches scenario", async () => {
    const user = userEvent.setup();
    render(<ScenarioToggle />);
    await user.click(screen.getByRole("radio", { name: "Hormuz Disruption" }));
    expect(useScenarioStore.getState().scenario).toBe("hormuz_disruption");
    expect(
      screen.getByRole("radio", { name: "Hormuz Disruption" }),
    ).toHaveAttribute("aria-checked", "true");
  });
});
