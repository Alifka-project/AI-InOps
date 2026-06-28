import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { UploadCard } from "@/components/UploadCard";
import { INPUT_DEFS } from "@/lib/inputs";

const salesDef = INPUT_DEFS.find((d) => d.kind === "sales")!;

describe("UploadCard", () => {
  it("renders the input title, brief, and expected columns", () => {
    render(<UploadCard def={salesDef} file={null} onFile={vi.fn()} />);
    expect(screen.getByText("Historical Sales")).toBeInTheDocument();
    expect(screen.getByText(/period, label, sales/)).toBeInTheDocument();
    expect(screen.getByText("required")).toBeInTheDocument();
  });

  it("calls onFile when a CSV is selected", async () => {
    const onFile = vi.fn();
    const user = userEvent.setup();
    render(<UploadCard def={salesDef} file={null} onFile={onFile} />);
    const input = screen.getByLabelText(/Upload Historical Sales CSV/i);
    const file = new File(["period,sales\n1,100\n"], "sales.csv", { type: "text/csv" });
    await user.upload(input, file);
    expect(onFile).toHaveBeenCalledWith(file);
  });

  it("shows the selected file name and a remove control", () => {
    const file = new File(["x"], "my-sales.csv", { type: "text/csv" });
    render(<UploadCard def={salesDef} file={file} onFile={vi.fn()} />);
    expect(screen.getByText(/my-sales.csv/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Remove Historical Sales/i })).toBeInTheDocument();
  });
});
