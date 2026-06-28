# Financial Analysis Dashboard

Full-stack project initialized from `financial_dashboard_spec.md`.

## Stack

- Backend: FastAPI, Pydantic, Pandas, NumPy, openpyxl, pdfplumber
- Frontend: Next.js App Router, TypeScript, Tailwind CSS, Apache ECharts
- Ingestion: Strategy Pattern for PDF text/table parsing and Excel Pandas parsing

## Structure

```text
backend/
  app/
    api/routes/          FastAPI routers for health, parsing and analysis
    core/                Runtime configuration
    parsers/             Strategy Pattern for PDF and Excel ingestion
    schemas/             Pydantic contracts for normalized financial data
    services/            Calculation engine and orchestration services
  tests/                 Backend tests
  requirements.txt       Python dependencies

frontend/
  app/                   Next.js App Router pages and layouts
  components/            Shared UI, charts, dashboard widgets
  features/              Feature-scoped modules such as analysis workflows
  lib/                   API clients and utilities
  types/                 TypeScript contracts mirroring backend schemas
  public/                Static assets
```

## Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs: `http://127.0.0.1:8000/docs`

Core endpoints:

- `GET /health`
- `GET /api/v1/mock-statement`
- `GET /api/v1/mock-dashboard`
- `GET /api/v1/fixtures/vinfast-statement`
- `GET /api/v1/fixtures/vinfast-dashboard`
- `POST /api/v1/parse`
- `POST /api/v1/analyze`
- `POST /api/v1/metrics`

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard: `http://localhost:3000`

Create `frontend/.env.local` if the API host is different:

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

## Docker

```bash
docker compose up --build
```

Frontend: `http://localhost:3000`  
Backend docs: `http://localhost:8000/docs`

## Parse Cache Note

- Async parse jobs cache completed standardized statements by the uploaded file content hash (`SHA-256`), so uploading the same PDF again can return immediately.
- Docker stores the cache in the `backend_parse_cache` volume mounted at `/app/.cache/parse_jobs`.
- The current cache has no TTL, file-count limit, or size limit; its practical limit is available disk space.
- Cache survives normal container restart/recreate, but is removed if Docker volumes are deleted, for example with `docker compose down -v`.
- Production follow-up: add an eviction policy such as `max 200 files + 30 day TTL`, or `max 2GB + 14 day TTL` for heavier PDF testing.

## Current Scope

- Primary workflow: upload a PDF/XLSX report, review the standardized statement, then click Analyze.
- PDF parser supports digital PDFs with an extractable text layer and recognizable financial statement labels.
- Scanned/image-only PDFs use Tesseract OCR, prioritize the three primary financial statements first, and continue the remaining pages in the background.
- Excel parser supports long and wide financial templates through Pandas.
- Metrics engine calculates profitability, liquidity, efficiency, solvency, DuPont 3-step and quality of earnings.
- Frontend supports English/Vietnamese language switching and light/dark/system themes.
