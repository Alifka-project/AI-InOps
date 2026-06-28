# Digital Twin — Logistics Software Management System

A production-grade, full-stack **Digital Twin** for warehouse & supply-chain
operations, built for the SP Jain *AI in Logistics* brief. Case study: **increased
use of sensitive materials** (lithium, cobalt, silicon, aluminium, copper) and
supply resilience during the **2026 Strait of Hormuz crisis**.

The twin runs entirely on **your data**. You upload the eight data-augmentation
inputs as CSVs; the system forecasts demand, forecasts supplier availability,
optimises transportation, and recommends inventory policy — then lets you
**download a full PDF report**. A global **Scenario toggle** (Normal ↔ Hormuz
Disruption) is a what-if lens applied on top of the real data.

> **No fabricated operational data in production.** Every operational number
> (demand, stock, costs, capacities) comes from your uploads. Synthetic values
> exist only behind a clearly-labelled **“Load sample dataset”** button for
> demos and testing.

---

## How the brief maps to the system

### Data-augmentation inputs (all eight required)

| # | Brief category | CSV input | Key columns |
|---|---|---|---|
| 1 | Historical sales data | `sales` | period, label, sales |
| 2 | Supplier data (lead time, capacity, pricing) | `suppliers` | supplier, lead_time_days, capacity_t, price_per_t |
| 3 | Transportation costs and routes | `transport_costs` | source, destination, cost_per_t |
| 4 | External factors (seasonality, promotions, trends) | `external` | period, seasonality_index, promotion, market_trend |
| 5 | Inventory data (stock, capacity, replenishment) | `inventory` | warehouse, current_stock_t, storage_capacity_t, replenishment_rate_t |
| 6 | Customer order data (frequency, size, location) | `orders` | order_id, period, size_t, location |
| 7 | Warehouse layout / operational parameters | `warehouse_params` | parameter, value (ordering_cost, holding_cost_per_unit, service_level) |
| 8 | Historical transportation data | `transport_history` | period, source, destination, volume_t, cost |
| — | *Reference market prices (optional)* | `materials` | material, mass_share, value_per_t_usd |

CSV headers are matched flexibly (case-insensitive, common synonyms). Every
input has a downloadable template in the UI.

### Methods (from the brief → engine)

- **Demand forecasting:** Adjusted Exponential Smoothing, Linear Trend Line,
  Seasonal Adjustment — textbook-exact recursions, **validated out-of-sample**
  (held-out back-test) with optional **auto-tuning** of α/β by grid search to
  minimise validation error.
- **Supplier integration & forecasting:** availability forecast from each
  supplier’s *historical* shipment volumes, capped by contractual capacity;
  lead times, capacities, and pricing flow through.
- **Transportation optimisation:** Northwest-Corner, Least-Cost, and Vogel
  initial solutions improved by **Stepping-Stone** and **MODI**, handling
  **balanced and unbalanced** problems via an automatic dummy row/column. All
  six initial×optimality combinations are shown converging to the same optimum.
- **Warehouse management:** safety stock, reorder point, and EOQ from your
  demand, lead times, **real on-hand stock**, and **your operational
  parameters** (ordering/holding cost, service level) — no hard-coded costs.
- **Scalability & feedback:** the backend is **stateless** (the dataset travels
  in each request, so it scales horizontally); parameter auto-tuning and
  out-of-sample validation form the feedback loop the brief asks for.

---

## Architecture

```
Next.js 14 (App Router · TS strict · Tailwind · Recharts · Zustand)
        │  upload CSVs → canonical dataset (held client-side, persisted)
        │  HTTPS · typed fetch client; dataset travels in each request body
        ▼
FastAPI (Python 3.11 · pydantic v2 · uvicorn)  ──▶  core/ engine (pure, stateless)
   stateless: no server-side dataset storage           dataset · forecasting
   Render web service                                   supplier · transportation
   Vercel hosts the frontend                            warehouse · scenarios · metrics
        │
        └─ /api/report → reportlab PDF (matplotlib charts)
```

- The **frontend never reimplements algorithms** — it calls the API.
- `core/` is **pure and stateless**; the backend is a thin typed layer.
- Configuration is **environment-only**.

### Repository layout

```
digital-twin-logistics/
├── core/                  # verified OR engine
│   ├── dataset.py         # canonical schema, CSV parsing/validation (8 inputs)
│   ├── forecasting.py     # ES / trend / seasonal + autotune + back-test
│   ├── transportation.py  # NWC/LCM/VAM + Stepping-Stone/MODI (balanced/unbalanced)
│   ├── supplier.py        # availability forecast from history
│   ├── warehouse.py       # EOQ / ROP / safety stock from real params
│   ├── scenarios.py       # Normal vs Hormuz-Disruption modifiers
│   └── data_generator.py  # labelled SAMPLE dataset (only place synthetics live)
├── backend/               # FastAPI app, tests, Dockerfile, render.yaml
│   └── app/
│       ├── models.py      # pydantic v2 schemas incl. the canonical Dataset
│       ├── service.py     # stateless orchestration over core/
│       ├── report.py      # reportlab PDF report
│       └── routers/       # datasets · data · forecast · transport · warehouse · simulate · report
├── frontend/              # Next.js dashboard
│   ├── app/               # data · overview · forecasting · suppliers · transportation · warehouse · scenario
│   ├── components/        # upload cards, KPI cards, charts, matrix editor, report button …
│   ├── lib/               # api.ts · types.ts · inputs.ts · useApi · format
│   └── store/             # Zustand (dataset + scenario + params, persisted)
├── .github/workflows/ci.yml
├── verify.py  pipeline_demo.py
```

---

## Using the app

1. Open **Data & Upload**. Either:
   - **Upload** all eight CSVs (download a template per input for the exact
     columns), name the dataset, and click **Validate & load**; or
   - click **Load sample dataset** to explore with labelled synthetic data.
2. Every page (Overview, Forecasting, Suppliers, Transportation, Warehouse,
   Scenario) now analyses that dataset. Flip the **Scenario** toggle to see the
   Hormuz-disruption impact ripple through.
3. Click **Download report** (header or Overview) for a PDF of the full analysis.

The dataset is held in the browser (persisted to `localStorage`) and sent with
each request, so a refresh keeps your data and the backend stays stateless.

---

## Local development

### Prerequisites
- Python 3.11 (3.9+ works locally; CI/Docker pin 3.11)
- Node.js 20+

### Backend
```bash
cd digital-twin-logistics
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
python verify.py            # frozen acceptance tests for the engine
cd backend && uvicorn app.main:app --reload   # http://localhost:8000 (docs at /docs)
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                  # http://localhost:3000
```

---

## Testing & quality

```bash
# Backend
cd backend
ruff check app ../core/scenarios.py ../core/dataset.py
black --check app
python -m pytest             # dataset parsing, scenario math, accuracy, every endpoint, PDF

# Frontend
cd frontend
npm run lint && npm run typecheck && npm run test && npm run build
```

CI (`.github/workflows/ci.yml`) runs all of the above plus `verify.py` on every
push/PR to `main`.

### Frozen acceptance results (never regress)
- Exp. smoothing α=0.5 on `[37,40,41,37,45,50]` → 37, 37, 38.5, 39.75
- Linear trend (same series) → a = 34.0667, b = 2.1714
- Balanced transport (3×3 textbook) → **4525** for every method combination
- Unbalanced supply > demand → **2424**; demand > supply → **1250**

---

## API surface (stateless — POST bodies carry the dataset)

| Method & path | Purpose |
|---|---|
| `GET  /health` | Liveness probe |
| `POST /api/datasets/parse` | Parse & validate uploaded CSVs → canonical dataset |
| `GET  /api/datasets/sample` | Labelled synthetic sample dataset |
| `GET  /api/datasets/templates/{kind}` | CSV template for an input |
| `POST /api/data` | Reference view + editable transport seeds |
| `POST /api/forecast/demand` | 3 methods + metrics + auto-tune + out-of-sample validation |
| `POST /api/forecast/suppliers` | Availability vs capacity from history |
| `POST /api/optimize/transport` | Allocation, total cost, balanced/dummy, method comparison |
| `POST /api/warehouse/policy` | Safety stock / ROP / EOQ + status from real stock |
| `POST /api/materials/recovery` | Recovered-material tonnage & value |
| `POST /api/simulate` · `/compare` | Full twin payload · Normal-vs-Disruption KPIs |
| `POST /api/report` | Downloadable **PDF** report |

---

## Deployment

### Single platform (frontend + backend, same origin) — recommended

`deploy.json` declares both services in one deployment:

```json
{
  "experimentalServices": {
    "frontend": { "root": "frontend", "routePrefix": "/", "framework": "nextjs" },
    "backend":  { "root": "backend",  "routePrefix": "/_/backend" }
  }
}
```

- The frontend is served at `/`; the backend is mounted at **`/_/backend`** on the
  **same origin**. No CORS, no separate API URL to manage.
- The frontend automatically calls `/_/backend` in production (overridable with
  `NEXT_PUBLIC_API_URL`). The backend strips the `/_/backend` prefix before
  routing (configurable via `PROXY_PREFIX`), so it works whether or not the
  platform strips it.
- Backend start command: `backend/Procfile` (`uvicorn app.main:app …`), Python
  pinned by `backend/runtime.txt`. The `core` engine is imported from the repo
  root, which the monorepo deploy includes.

> If your platform reads the manifest under a different filename, copy
> `deploy.json`'s contents there — the app code needs no change.

### Alternative: split hosting (Render + Vercel)

Still supported. Backend → Render via `backend/render.yaml` + `backend/Dockerfile`
(set `CORS_ORIGINS`); frontend → Vercel with root `frontend` and
`NEXT_PUBLIC_API_URL` pointing at the Render URL.
