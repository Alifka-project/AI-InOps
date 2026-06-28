// Typed fetch client for the Digital Twin backend.
//
// The backend is stateless: every compute call carries the canonical dataset
// built from the user's uploaded CSVs. Features: timeout, bounded retry with
// backoff (masks free-tier cold starts), structured error parsing, full typing.

import type {
  Dataset,
  DataResponse,
  ForecastResponse,
  InputKind,
  MaterialsResponse,
  ScenarioComparison,
  ScenarioName,
  SimulateResponse,
  SupplierResponse,
  TransportResponse,
  ValidationResponse,
  WarehouseResponse,
} from "./types";

// Where the backend lives. An explicit NEXT_PUBLIC_API_URL always wins. Otherwise:
// in production we default to the same-origin path the platform mounts the
// backend under (routePrefix "/_/backend"); in dev we hit the local uvicorn.
const FALLBACK_BASE =
  process.env.NODE_ENV === "production" ? "/_/backend" : "http://localhost:8000";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || FALLBACK_BASE;

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
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function parseError(res: Response): Promise<ApiError> {
  let message = `Request failed (${res.status})`;
  let type = "http_error";
  try {
    const data = await res.json();
    if (data?.error?.message) {
      message = data.error.message;
      type = data.error.type ?? type;
    } else if (typeof data?.detail === "string") {
      message = data.detail;
    }
  } catch {
    /* non-JSON body */
  }
  return new ApiError(message, res.status, type);
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, retries = 2, timeoutMs = 30000 } = opts;
  const url = `${API_BASE}${path}`;

  let lastError: unknown;
  for (let attempt = 0; attempt <= retries; attempt++) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetch(url, {
        method,
        headers: body ? { "Content-Type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
        cache: "no-store",
      });
      clearTimeout(timeout);
      if (res.ok) return (await res.json()) as T;
      const err = await parseError(res);
      if (res.status >= 400 && res.status < 500) throw err; // client error, no retry
      lastError = err;
    } catch (err) {
      clearTimeout(timeout);
      if (err instanceof ApiError && err.status >= 400 && err.status < 500) throw err;
      lastError = err;
    }
    if (attempt < retries) await sleep(500 * Math.pow(2, attempt));
  }
  if (lastError instanceof ApiError) throw lastError;
  throw new ApiError(
    lastError instanceof Error ? lastError.message : "Network error",
    0,
    "network_error",
  );
}

interface BaseParams {
  alpha: number;
  beta: number;
  horizon: number;
  serviceLevel: number;
  autoTune: boolean;
}

export const api = {
  health: () => request<{ status: string }>("/health", { retries: 1 }),

  // ---- datasets --------------------------------------------------------
  getSample: () => request<Dataset>("/api/datasets/sample"),

  parseUpload: async (
    name: string,
    files: Partial<Record<InputKind | "materials", File>>,
  ): Promise<ValidationResponse> => {
    const form = new FormData();
    form.append("name", name);
    for (const [kind, file] of Object.entries(files)) {
      if (file) form.append(kind, file, file.name);
    }
    const res = await fetch(`${API_BASE}/api/datasets/parse`, {
      method: "POST",
      body: form,
      cache: "no-store",
    });
    if (!res.ok) throw await parseError(res);
    return (await res.json()) as ValidationResponse;
  },

  getTemplate: (kind: string) =>
    request<{ kind: string; filename: string; csv: string; columns: string[] }>(
      `/api/datasets/templates/${kind}`,
    ),

  // Upload ONE combined file (Excel workbook, ZIP of CSVs, or canonical JSON).
  parseCombined: async (name: string, file: File): Promise<ValidationResponse> => {
    const form = new FormData();
    form.append("name", name);
    form.append("file", file, file.name);
    const res = await fetch(`${API_BASE}/api/datasets/parse-combined`, {
      method: "POST",
      body: form,
      cache: "no-store",
    });
    if (!res.ok) throw await parseError(res);
    return (await res.json()) as ValidationResponse;
  },

  // Download the combined template (xlsx workbook by default, or a zip).
  downloadCombinedTemplate: async (format: "xlsx" | "zip" = "xlsx"): Promise<Blob> => {
    const res = await fetch(
      `${API_BASE}/api/datasets/template-combined?format=${format}`,
      { cache: "no-store" },
    );
    if (!res.ok) throw await parseError(res);
    return res.blob();
  },

  // ---- analysis (stateless: dataset travels in the body) ---------------
  getData: (dataset: Dataset, scenario: ScenarioName) =>
    request<DataResponse>("/api/data", {
      method: "POST",
      body: { dataset, scenario },
    }),

  forecastDemand: (dataset: Dataset, scenario: ScenarioName, p: BaseParams) =>
    request<ForecastResponse>("/api/forecast/demand", {
      method: "POST",
      body: {
        dataset,
        scenario,
        alpha: p.alpha,
        beta: p.beta,
        horizon: p.horizon,
        auto_tune: p.autoTune,
      },
    }),

  forecastSuppliers: (dataset: Dataset, scenario: ScenarioName, p: BaseParams) =>
    request<SupplierResponse>("/api/forecast/suppliers", {
      method: "POST",
      body: { dataset, scenario, alpha: p.alpha, beta: p.beta, horizon: p.horizon },
    }),

  optimizeTransport: (
    dataset: Dataset,
    scenario: ScenarioName,
    body: {
      initial: string;
      optimize: string;
      cost?: number[][];
      supply?: number[];
      demand?: number[];
    },
  ) =>
    request<TransportResponse>("/api/optimize/transport", {
      method: "POST",
      body: { dataset, scenario, ...body },
    }),

  warehousePolicy: (dataset: Dataset, scenario: ScenarioName, p: BaseParams) =>
    request<WarehouseResponse>("/api/warehouse/policy", {
      method: "POST",
      body: {
        dataset,
        scenario,
        alpha: p.alpha,
        beta: p.beta,
        service_level: p.serviceLevel,
      },
    }),

  materialsRecovery: (dataset: Dataset, scenario: ScenarioName) =>
    request<MaterialsResponse>("/api/materials/recovery", {
      method: "POST",
      body: { dataset, scenario },
    }),

  simulate: (dataset: Dataset, scenario: ScenarioName, p: BaseParams) =>
    request<SimulateResponse>("/api/simulate", {
      method: "POST",
      body: {
        dataset,
        scenario,
        alpha: p.alpha,
        beta: p.beta,
        horizon: p.horizon,
        service_level: p.serviceLevel,
        auto_tune: p.autoTune,
      },
    }),

  compareScenarios: (dataset: Dataset, p: BaseParams) =>
    request<ScenarioComparison>("/api/simulate/compare", {
      method: "POST",
      body: {
        dataset,
        alpha: p.alpha,
        beta: p.beta,
        horizon: p.horizon,
        service_level: p.serviceLevel,
      },
    }),

  // ---- report (binary download) ----------------------------------------
  downloadReport: async (
    dataset: Dataset,
    scenario: ScenarioName,
    p: BaseParams,
  ): Promise<Blob> => {
    const res = await fetch(`${API_BASE}/api/report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dataset,
        scenario,
        alpha: p.alpha,
        beta: p.beta,
        horizon: p.horizon,
        service_level: p.serviceLevel,
        auto_tune: p.autoTune,
      }),
      cache: "no-store",
    });
    if (!res.ok) throw await parseError(res);
    return res.blob();
  },
};
