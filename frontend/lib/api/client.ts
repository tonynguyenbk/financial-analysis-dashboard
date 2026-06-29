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
const PARSE_POLL_INTERVAL_MS = 900;
const PARSE_MAX_TOTAL_MS = 30 * 60 * 1000;
const PARSE_IDLE_TIMEOUT_MS = 5 * 60 * 1000;
const PARSE_TRANSIENT_ERROR_TIMEOUT_MS = 90 * 1000;

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
  const startedAt = Date.now();
  let lastProgressAt = startedAt;
  let lastTransientErrorAt: number | null = null;
  let lastProgress = -1;

  while (Date.now() - startedAt < PARSE_MAX_TOTAL_MS) {
    await sleep(PARSE_POLL_INTERVAL_MS);
    let snapshot: ParseJobSnapshot;

    try {
      snapshot = await getParseJob(jobId);
      lastTransientErrorAt = null;
    } catch (error) {
      lastTransientErrorAt ??= Date.now();
      if (Date.now() - lastTransientErrorAt >= PARSE_TRANSIENT_ERROR_TIMEOUT_MS) {
        throw error;
      }
      continue;
    }

    onProgress?.(snapshot);

    if (snapshot.progress > lastProgress) {
      lastProgress = snapshot.progress;
      lastProgressAt = Date.now();
    }

    if (snapshot.statement) {
      return snapshot.statement;
    }

    if (snapshot.status === "completed") {
      throw new Error("Parse job completed without a standardized statement.");
    }

    if (snapshot.status === "failed") {
      throw new Error(snapshot.error ?? snapshot.message);
    }

    if (Date.now() - lastProgressAt >= PARSE_IDLE_TIMEOUT_MS) {
      throw new Error("Parse job stopped making progress.");
    }
  }

  throw new Error("Parse job exceeded the maximum processing window.");
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
