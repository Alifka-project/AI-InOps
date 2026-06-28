import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MatrixEditor } from "@/components/MatrixEditor";

const baseProps = {
  cost: [
    [6, 8],
    [7, 11],
  ],
  supply: [150, 175],
  demand: [200, 100],
  rowLabels: ["S1", "S2"],
  colLabels: ["D1", "D2"],
};

describe("MatrixEditor", () => {
  it("renders a cell for every cost entry plus supply and demand", () => {
    render(
      <MatrixEditor
        {...baseProps}
        onCostChange={vi.fn()}
        onSupplyChange={vi.fn()}
        onDemandChange={vi.fn()}
      />,
    );
    // 4 cost + 2 supply + 2 demand = 8 number inputs
    expect(screen.getAllByRole("spinbutton")).toHaveLength(8);
  });

  it("flags an unbalanced problem", () => {
    render(
      <MatrixEditor
        {...baseProps}
        onCostChange={vi.fn()}
        onSupplyChange={vi.fn()}
        onDemandChange={vi.fn()}
      />,
    );
    // supply 325 vs demand 300 -> unbalanced
    expect(screen.getByText(/Unbalanced/i)).toBeInTheDocument();
  });

  it("invokes onCostChange when a cost cell is edited", async () => {
    const onCostChange = vi.fn();
    const user = userEvent.setup();
    render(
      <MatrixEditor
        {...baseProps}
        onCostChange={onCostChange}
        onSupplyChange={vi.fn()}
        onDemandChange={vi.fn()}
      />,
    );
    const cell = screen.getByLabelText("cost S1 to D1");
    await user.clear(cell);
    await user.type(cell, "9");
    expect(onCostChange).toHaveBeenCalled();
    const lastCall = onCostChange.mock.calls.at(-1);
    expect(lastCall?.[0]).toBe(0);
    expect(lastCall?.[1]).toBe(0);
  });
});
