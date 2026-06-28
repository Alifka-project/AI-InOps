// Typed fetch client for the Digital Twin backend.
//
// Features: timeout, bounded retry with backoff (to mask cold starts on free
// hosting tiers), structured error parsing, and full response typing.

import type {
  DataResponse,
  ForecastParams,
  ForecastResponse,
  MaterialsResponse,
  ScenarioComparison,
  ScenarioName,
  SimulateRequest,
  SimulateResponse,
  SupplierResponse,
  TransportRequest,
  TransportResponse,
  WarehouseRequest,
  WarehouseResponse,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  type: string;
  constructor(message: string, status: number, type = "error") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.type = type;
  }
}

interface RequestOptions {
  method?: "GET" | "POST";
  body?: unknown;
  retries?: number;
  timeoutMs?: number;
  signal?: AbortSignal;
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const {
    method = "GET",
    body,
    retries = 2,
    timeoutMs = 20000,
    signal,
  } = opts;
  const url = `${API_BASE}${path}`;

  let lastError: unknown;
  for (let attempt = 0; attempt <= retries; attempt++) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    if (signal) {
      signal.addEventListener("abort", () => controller.abort(), { once: true });
    }
    try {
      const res = await fetch(url, {
        method,
        headers: body ? { "Content-Type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
        cache: "no-store",
      });
      clearTimeout(timeout);

      if (!res.ok) {
        let message = `Request failed (${res.status})`;
        let type = "http_error";
        try {
          const data = await res.json();
          if (data?.error?.message) {
            message = data.error.message;
            type = data.error.type ?? type;
          }
        } catch {
          // non-JSON error body; keep default message
        }
        // 4xx are client errors — do not retry.
        if (res.status >= 400 && res.status < 500) {
          throw new ApiError(message, res.status, type);
        }
        lastError = new ApiError(message, res.status, type);
      } else {
        return (await res.json()) as T;
      }
    } catch (err) {
      clearTimeout(timeout);
      if (err instanceof ApiError && err.status >= 400 && err.status < 500) {
        throw err;
      }
      lastError = err;
    }

    if (attempt < retries) {
      await sleep(500 * Math.pow(2, attempt));
    }
  }

  if (lastError instanceof ApiError) throw lastError;
  throw new ApiError(
    lastError instanceof Error ? lastError.message : "Network error",
    0,
    "network_error",
  );
}

export const api = {
  health: () => request<{ status: string }>("/health", { retries: 1 }),

  getData: (scenario: ScenarioName) =>
    request<DataResponse>(`/api/data?scenario=${scenario}`),

  forecastDemand: (params: ForecastParams) =>
    request<ForecastResponse>("/api/forecast/demand", {
      method: "POST",
      body: params,
    }),

  forecastSuppliers: (params: ForecastParams) =>
    request<SupplierResponse>("/api/forecast/suppliers", {
      method: "POST",
      body: params,
    }),

  optimizeTransport: (req: TransportRequest) =>
    request<TransportResponse>("/api/optimize/transport", {
      method: "POST",
      body: req,
    }),

  warehousePolicy: (req: WarehouseRequest) =>
    request<WarehouseResponse>("/api/warehouse/policy", {
      method: "POST",
      body: req,
    }),

  materialsRecovery: (scenario: ScenarioName) =>
    request<MaterialsResponse>(`/api/materials/recovery?scenario=${scenario}`),

  simulate: (req: SimulateRequest) =>
    request<SimulateResponse>("/api/simulate", { method: "POST", body: req }),

  compareScenarios: (req: SimulateRequest) =>
    request<ScenarioComparison>("/api/simulate/compare", {
      method: "POST",
      body: req,
    }),
};
