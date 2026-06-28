# Digital Twin — Electrolux UAE Operations

A production-grade, full-stack **digital twin** for Electrolux UAE supply-chain
and warehouse operations, focused on **sensitive-material supply resilience**
(lithium, cobalt, silicon, aluminium, copper) during the **2026 Strait of Hormuz
crisis**.

A global **Scenario toggle** (Normal ↔ Hormuz Disruption) flows through every
layer of the system. Under disruption: lead times extend by ~12 days, transport
cost rises ×1.3 with an $85/t war-risk insurance surcharge, the Jebel Ali → KEZAD
direct route is disabled (forcing a Gulf-of-Oman reroute), and recovered-material
demand rises ×1.25 — flipping the transportation network from a supply surplus to
a supply shortfall.

> Built on a verified Operations-Research engine (`core/`): exponential &
> trend-adjusted smoothing, linear/seasonal trend, the transportation simplex
> (NWC / Least-Cost / Vogel → Stepping-Stone / MODI), supplier forecasting, and
> EOQ/ROP/safety-stock inventory policy.

---

## Architecture

```
Next.js 14 (App Router · TS strict · Tailwind · Recharts · Zustand)
        │  HTTPS · typed fetch client (lib/api.ts)
        ▼
FastAPI (Python 3.11 · pydantic v2 · uvicorn)  ──▶  core/ engine (pure, stateless)
        │                                              forecasting · transportation
   Render web service                                  supplier · warehouse · metrics
   Vercel hosts the frontend                           scenarios
```

- The **frontend never reimplements algorithms** — it calls the API.
- `core/` stays **pure and stateless**; the backend is a thin typed layer plus
  scenario orchestration.
- Configuration is **environment-only** (no secrets in code).

### Repository layout

```
digital-twin-logistics/
├── core/                  # verified OR engine (+ scenarios.py)
├── backend/               # FastAPI app, tests, Dockerfile, render.yaml
│   └── app/
│       ├── main.py        # app, routers, CORS, exception handlers, logging
│       ├── config.py      # pydantic-settings (env)
│       ├── models.py      # pydantic v2 request/response schemas
│       ├── scenarios.py   # API adapter over core.scenarios
│       ├── service.py     # orchestrates core/ calls per scenario
│       └── routers/       # data · forecast · transport · warehouse · simulate
├── frontend/              # Next.js dashboard (6 pages)
│   ├── app/               # overview · forecasting · suppliers · transportation · warehouse · scenario
│   ├── components/        # KPI cards, charts, matrix editor, scenario toggle, nav, skeletons
│   ├── lib/               # api.ts (typed client) · types.ts · useApi · format
│   ├── store/             # Zustand (scenario + forecast params)
│   └── __tests__/         # vitest + React Testing Library
├── .github/workflows/ci.yml
├── verify.py  pipeline_demo.py
```

---

## Live demo

| Surface  | URL                                              |
| -------- | ------------------------------------------------ |
| Frontend | _set after Vercel deploy_                         |
| Backend  | _set after Render deploy_ (`/health`, `/docs`)   |

> Update these once deployed. The frontend keeps the backend warm with a
> health-check ping every 4 minutes to mask free-tier cold starts.

---

## Local development

### Prerequisites

- Python 3.11 (3.9+ works locally; CI and Docker pin 3.11)
- Node.js 20+

### 1. Backend

```bash
cd digital-twin-logistics
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt

# Frozen acceptance tests for the engine
python verify.py
python pipeline_demo.py

# Run the API (http://localhost:8000 — docs at /docs)
cd backend
uvicorn app.main:app --reload
```

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local          # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                          # http://localhost:3000
```

---

## Testing & quality

```bash
# Backend
cd backend
ruff check app ../core/scenarios.py
black --check app ../core/scenarios.py
python -m pytest                      # scenario math + every endpoint (TestClient)

# Frontend
cd frontend
npm run lint
npm run typecheck
npm run test                          # vitest + RTL
npm run build                         # production build
```

CI (`.github/workflows/ci.yml`) runs all of the above — plus `verify.py` — on
every push and pull request to `main`.

### Frozen acceptance results (never regress)

- Exp. smoothing α=0.5 on `[37,40,41,37,45,50]` → F₁..F₄ = 37, 37, 38.5, 39.75
- Linear trend (same series) → a = 34.0667, b = 2.1714
- Balanced transport (the 3×3 textbook problem) → **4525** for every
  initial × optimality combination
- Unbalanced supply > demand → **2424**; demand > supply → **1250**

---

## API surface

All POST endpoints accept `scenario: "normal" | "hormuz_disruption"`.

| Method & path                | Purpose                                                   |
| ---------------------------- | --------------------------------------------------------- |
| `GET  /health`               | Liveness probe                                            |
| `GET  /api/data`             | Reference network + editable transport seeds              |
| `GET  /api/scenarios`        | Scenario metadata                                         |
| `POST /api/forecast/demand`  | Adjusted ES + linear trend + seasonal, with MAD/MSE/MAPE/Bias |
| `POST /api/forecast/suppliers` | Collection-center availability vs capacity              |
| `POST /api/optimize/transport` | Allocation, total cost, balanced/dummy info, method comparison |
| `POST /api/warehouse/policy` | Safety stock / ROP / EOQ + OK/REORDER/CRITICAL status     |
| `GET  /api/materials/recovery` | Recovered-material tonnage & value                      |
| `POST /api/simulate`         | Full twin payload (powers the overview)                   |
| `POST /api/simulate/compare` | Normal vs Disruption KPI deltas                           |

---

## Deployment

### Backend → Render

The repo ships `backend/render.yaml` (a Render Blueprint) and a root-context
`backend/Dockerfile`.

1. In Render: **New → Blueprint**, point it at this repository.
2. Render reads `backend/render.yaml` and builds the Docker image (build context
   is the repo root so it can copy both `core/` and `backend/app/`).
3. Set `CORS_ORIGINS` to your Vercel origin (comma-separated). `/health` is the
   health-check path.

### Frontend → Vercel

1. **New Project** → import this repo → set the **root directory** to `frontend`.
2. Add env var `NEXT_PUBLIC_API_URL` = your Render backend URL (no trailing slash).
3. Deploy. Next.js is detected automatically.

---

## The Hormuz scenario, end to end

| Layer           | Normal              | Hormuz Disruption                              |
| --------------- | ------------------- | ---------------------------------------------- |
| Supplier lead   | as contracted       | **+12 days** (Cape-of-Good-Hope reroute)       |
| Transport cost  | base                | **×1.3 + $85/t** war-risk insurance            |
| Routes          | all open            | Jebel Ali → KEZAD **disabled**                 |
| Recovered demand| base                | **×1.25** (import substitution)                |
| Network balance | supply surplus      | **supply shortfall** → dummy source appears    |

Flip the toggle in the header and every page — KPIs, forecasts, supplier bars,
the transportation allocation, and inventory status chips — recomputes live.
