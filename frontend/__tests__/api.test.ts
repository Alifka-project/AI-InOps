import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { api, ApiError } from "@/lib/api";
import type { Dataset } from "@/lib/types";

const DATASET = {
  meta: { name: "t", is_sample: false, n_periods: 1, n_suppliers: 1, n_warehouses: 1, n_orders: 0, warnings: [] },
} as unknown as Dataset;

const PARAMS = { alpha: 0.5, beta: 0.3, horizon: 3, serviceLevel: 0.95, autoTune: false };

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("api client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns parsed JSON on success", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({ status: "ok" }));
    const res = await api.health();
    expect(res.status).toBe("ok");
    expect(spy).toHaveBeenCalledOnce();
  });

  it("sends the dataset in the body for compute calls", async () => {
    const spy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse({ scenario: {}, months: [] }));
    await api.forecastDemand(DATASET, "normal", PARAMS);
    const [, init] = spy.mock.calls[0];
    const body = JSON.parse((init?.body as string) ?? "{}");
    expect(body.dataset.meta.name).toBe("t");
    expect(body.scenario).toBe("normal");
    expect(body.auto_tune).toBe(false);
  });

  it("does not retry on 4xx and surfaces the structured error", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ error: { type: "validation_error", message: "bad alpha" } }, 422),
    );
    await expect(api.forecastDemand(DATASET, "normal", PARAMS)).rejects.toMatchObject({
      status: 422,
      message: "bad alpha",
    });
    expect(spy).toHaveBeenCalledOnce();
  });

  it("retries on 5xx then succeeds", async () => {
    const spy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ error: { message: "boom" } }, 500))
      .mockResolvedValueOnce(jsonResponse({ status: "ok" }));
    const res = await api.health();
    expect(res.status).toBe("ok");
    expect(spy).toHaveBeenCalledTimes(2);
  });

  it("wraps network failures in ApiError", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("offline"));
    await expect(api.getSample()).rejects.toBeInstanceOf(ApiError);
  });

  it("downloadReport returns the response blob", async () => {
    const sentinel = new Blob(["%PDF-1.4"], { type: "application/pdf" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      blob: async () => sentinel,
    } as Response);
    const blob = await api.downloadReport(DATASET, "normal", PARAMS);
    expect(blob).toBe(sentinel);
  });
});
