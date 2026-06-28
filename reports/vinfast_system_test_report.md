# VinFast Data & System Test Report

Date: 2026-06-27

## Data Source

- Company: VinFast Auto Ltd. (`VFS`)
- SEC CIK: `0001913510`
- Primary annual filing used: Form 20-F filed on 2026-04-30 for fiscal year ended 2025-12-31.
- Source URL: https://www.sec.gov/Archives/edgar/data/1913510/000110465926052266/vfs-20251231x20f.htm
- Supporting filing for 2023 balance sheet comparatives: Form 20-F filed on 2025-04-30.
- Normalized fixture: `backend/test_data/vinfast_statement.json`

## Normalized Data Coverage

The normalized JSON includes 2023, 2024 and 2025 values for:

- Current assets, inventory, trade receivables, total assets
- Current liabilities, trade payables, total liabilities, total equity
- Revenue, gross profit/loss, cost of sales, operating loss as EBIT proxy, finance costs as interest expense proxy, net loss
- Operating cash flow

All values are stored in VND million.

## Calculated Metrics Snapshot

| Metric | 2023 | 2024 | 2025 |
| --- | ---: | ---: | ---: |
| Gross margin | -49.17% | -57.42% | -45.37% |
| Net margin | -216.08% | -175.73% | -110.43% |
| ROA | -41.03% | -51.09% | -58.82% |
| ROE | N/A | N/A | N/A |
| Current ratio | 0.33 | 0.38 | 0.52 |
| Quick ratio | 0.13 | 0.22 | 0.31 |
| DIO | 264.50 days | 152.88 days | 87.42 days |
| DSO | 6.15 days | 25.19 days | 20.79 days |
| DPO | 106.59 days | 86.75 days | 74.37 days |
| CCC | 164.06 days | 91.32 days | 33.84 days |
| Debt / Equity | N/A | N/A | N/A |
| Interest coverage | -3.05 | -2.90 | -3.32 |
| Quality of earnings ratio | 0.83 | 0.39 | 0.45 |

ROE and Debt / Equity are intentionally returned as `null` by the API when equity is negative.

## Interpretation

VinFast is a stress case for the current metrics model:

- Revenue grew strongly in 2025, but gross margin and net margin remained negative.
- Current and quick ratios are far below 1.0, indicating weak short-term liquidity.
- Equity is negative across the period, so ROE and Debt / Equity become mathematically misleading. The dashboard should flag negative equity before presenting ROE as a positive signal.
- CFO and net income are both negative. The current quality-of-earnings ratio is positive because it divides a negative CFO by a negative net loss, but this should not be considered healthy.

## System Test Results

Passed:

- Windows Python 3.11 was located at `C:\Users\admin\AppData\Local\Programs\Python\Python311\python.exe`.
- Backend virtual environment was created at `backend/.venv`.
- Backend dependencies installed successfully from `backend/requirements.txt`.
- Backend tests passed: `5 passed`.
- FastAPI runtime responded `200 OK` on `GET /health`.
- VinFast fixture endpoint responded `200 OK` on `GET /api/v1/fixtures/vinfast-dashboard`.
- VinFast dashboard payload returned `VFS`, latest period `2025`, quality-of-earnings alert `red`, and 12 analysis warnings.
- Latest VinFast ROE and Debt / Equity are returned as `null` because equity is negative.
- Frontend dependency install completed.
- Frontend security audit passed: `found 0 vulnerabilities`.
- `npm.cmd run lint` passed on ESLint 9 with Next.js flat config.
- `npm.cmd run typecheck` passed.
- `npm.cmd run build` passed.
- Docker Desktop daemon started successfully.
- `docker compose up -d --build` completed successfully.
- Docker backend container is healthy and responds `200 OK` at `http://127.0.0.1:8000/health`.
- Docker frontend container responds `200 OK` at `http://127.0.0.1:3000`.
- Frontend includes a VinFast button wired to the backend VinFast fixture endpoint.

## Findings

1. The ingestion and calculation contract can represent real VinFast financial data.
2. The PDF parser now supports text-layer PDF extraction, but scanned/image-only PDFs still require OCR or LLM Vision extraction.
3. The Excel/manual JSON path and the SEC fixture endpoint are valid paths for deterministic real-company testing.
4. The quality-of-earnings rule now flags the VinFast case as red when both CFO and net income are negative.
5. ROE, equity multiplier and Debt / Equity are now returned as `null` when equity is negative, with explicit warnings.
6. Docker runtime now includes `backend/test_data`, so fixture endpoints work inside the backend container.
7. Next.js and ESLint were upgraded to remove npm audit vulnerabilities.

## Recommended Fixes

- Implement the real SEC/XBRL ingestion strategy as a third parser beside PDF and Excel.
- Add OCR or LLM Vision fallback for scanned PDFs and complex layouts that do not expose reliable text tables.
- Add browser automation for button-click validation if Playwright is added to the project.
- Consider changing the frontend Dockerfile from `npm install` to `npm ci` after committing `package-lock.json` for stricter reproducible builds.

## Runtime URLs

- Backend API: http://127.0.0.1:8000
- Backend docs: http://127.0.0.1:8000/docs
- Frontend: http://127.0.0.1:3000
