import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { api, ApiError } from "@/lib/api";

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
    const spy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse({ status: "ok" }));
    const res = await api.health();
    expect(res.status).toBe("ok");
    expect(spy).toHaveBeenCalledOnce();
  });

  it("does not retry on 4xx and surfaces the structured error", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(
        { error: { type: "validation_error", message: "alpha out of range" } },
        422,
      ),
    );
    await expect(
      api.forecastDemand({
        scenario: "normal",
        alpha: 2,
        beta: 0.3,
        horizon: 3,
      }),
    ).rejects.toMatchObject({ status: 422, message: "alpha out of range" });
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
    await expect(api.getData("normal")).rejects.toBeInstanceOf(ApiError);
  });
});
