# Backend

FastAPI backend for ingesting financial statements, normalizing them into a standard JSON contract, and calculating financial analysis metrics.

PDF uploads are parsed with `pdfplumber` when the file has an extractable text layer. Scanned/image-only PDFs require a later OCR or LLM Vision strategy.

## Run Locally

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Swagger UI: `http://127.0.0.1:8000/docs`

## API Surface

- `GET /health`
- `GET /api/v1/mock-statement`
- `GET /api/v1/mock-dashboard`
- `GET /api/v1/fixtures/vinfast-statement`
- `GET /api/v1/fixtures/vinfast-dashboard`
- `POST /api/v1/parse`
- `POST /api/v1/analyze`
- `POST /api/v1/metrics`

## Normalized JSON Shape

```json
{
  "company": {
    "name": "Demo Manufacturing JSC",
    "ticker": "DEMO"
  },
  "currency": "VND",
  "unit": "million",
  "source_type": "pdf",
  "periods": [
    {
      "period": "2024",
      "fiscal_year": 2024,
      "balance_sheet": {
        "current_assets": 580000,
        "inventory": 155000,
        "accounts_receivable": 128000,
        "total_assets": 1350000,
        "current_liabilities": 295000,
        "accounts_payable": 97000,
        "total_liabilities": 720000,
        "total_equity": 630000
      },
      "income_statement": {
        "net_revenue": 1120000,
        "gross_profit": 342000,
        "cost_of_goods_sold": 778000,
        "ebit": 181000,
        "interest_expense": 35000,
        "net_income": 116000
      },
      "cash_flow": {
        "operating_cash_flow": 121000
      }
    }
  ]
}
```
