# Frontend

Next.js dashboard UI for the Financial Analysis Dashboard.

## Stack

- Next.js App Router
- Tailwind CSS
- Apache ECharts
- Lucide React icons

## Run Locally

```bash
cd frontend
npm install
npm run dev
```

Create `.env.local` when the backend does not run on the default URL:

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

## Structure

```text
frontend/
  app/
    layout.tsx
    page.tsx
  components/
    charts/
    dashboard/
  features/
    analysis/
  lib/
    api/
    formatters.ts
  types/
    financial.ts
  public/
```
