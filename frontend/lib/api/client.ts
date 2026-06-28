import type { DashboardMetrics, FinancialStatement, ParseJobSnapshot } from "@/types/financial";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";

async function parseJsonResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = (await response.json()) as { detail?: string };
      detail = payload.detail ?? detail;
    } catch {
      // Keep the HTTP status text when the response is not JSON.
    }
    throw new Error(detail);
  }

  return (await response.json()) as T;
}

type ParseProgressHandler = (snapshot: ParseJobSnapshot) => void;

export async function parseStatementFile(
  file: File,
  onProgress?: ParseProgressHandler
): Promise<FinancialStatement> {
  const job = await createParseJob(file);
  onProgress?.(job);
  return waitForParseJob(job.job_id, onProgress);
}

async function createParseJob(file: File): Promise<ParseJobSnapshot> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/parse-jobs`, {
    method: "POST",
    body: formData
  });
  return parseJsonResponse<ParseJobSnapshot>(response);
}

async function getParseJob(jobId: string): Promise<ParseJobSnapshot> {
  const response = await fetch(`${API_BASE_URL}/parse-jobs/${jobId}`);
  return parseJsonResponse<ParseJobSnapshot>(response);
}

async function waitForParseJob(
  jobId: string,
  onProgress?: ParseProgressHandler
): Promise<FinancialStatement> {
  const deadline = Date.now() + 10 * 60 * 1000;

  while (Date.now() < deadline) {
    await sleep(900);
    const snapshot = await getParseJob(jobId);
    onProgress?.(snapshot);

    if (snapshot.status === "completed") {
      if (!snapshot.statement) {
        throw new Error("Parse job completed without a standardized statement.");
      }
      return snapshot.statement;
    }

    if (snapshot.status === "failed") {
      throw new Error(snapshot.error ?? snapshot.message);
    }
  }

  throw new Error("Parse job timed out.");
}

export async function calculateMetrics(
  statement: FinancialStatement
): Promise<DashboardMetrics> {
  const response = await fetch(`${API_BASE_URL}/metrics`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(statement)
  });
  return parseJsonResponse<DashboardMetrics>(response);
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
