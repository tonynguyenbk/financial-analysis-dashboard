export type AlertLevel = "green" | "yellow" | "red";

export type SourceType = "pdf" | "excel" | "mock" | "manual" | "sec";

export interface CompanyInfo {
  name: string;
  ticker?: string | null;
  industry?: string | null;
}

export interface BalanceSheet {
  current_assets?: number | null;
  inventory?: number | null;
  accounts_receivable?: number | null;
  total_assets?: number | null;
  current_liabilities?: number | null;
  accounts_payable?: number | null;
  total_liabilities?: number | null;
  total_equity?: number | null;
}

export interface IncomeStatement {
  net_revenue?: number | null;
  gross_profit?: number | null;
  cost_of_goods_sold?: number | null;
  ebit?: number | null;
  interest_expense?: number | null;
  net_income?: number | null;
}

export interface CashFlowStatement {
  operating_cash_flow?: number | null;
}

export interface FinancialPeriod {
  period: string;
  fiscal_year?: number | null;
  balance_sheet: BalanceSheet;
  income_statement: IncomeStatement;
  cash_flow: CashFlowStatement;
}

export interface FinancialStatement {
  company: CompanyInfo;
  currency: string;
  unit: string;
  source_type: SourceType;
  periods: FinancialPeriod[];
  metadata?: Record<string, unknown>;
}

export interface ExtractedReportPage {
  page: number;
  text: string;
}

export interface ReportNavigationItem {
  title: string;
  page: number;
  level?: number | null;
  source?: string | null;
  report_page?: number | null;
  report_page_end?: number | null;
}

export interface StatementTableColumn {
  key: string;
  label: string;
}

export interface StatementTableRow {
  code: string;
  label: string;
  note?: string | null;
  values: Record<string, number | null | undefined>;
  parent_code?: string | null;
  level?: number | null;
  raw_label?: string | null;
  template_label?: string | null;
  mapping_source?: string | null;
  page?: number | null;
  raw_text?: string | null;
}

export interface StatementTable {
  key: string;
  template_key?: string | null;
  mapping_source?: string | null;
  title: string;
  pages?: number[];
  columns: StatementTableColumn[];
  rows: StatementTableRow[];
}

export type ParseJobStatus = "queued" | "running" | "completed" | "failed";

export interface ParseJobSnapshot {
  job_id: string;
  status: ParseJobStatus;
  progress: number;
  stage: string;
  message: string;
  file_name?: string | null;
  statement?: FinancialStatement | null;
  error?: string | null;
}

export interface MetricPoint {
  period: string;
  fiscal_year?: number | null;
  [metric: string]: string | number | boolean | null | undefined;
}

export interface DashboardMetrics {
  company: CompanyInfo;
  currency: string;
  unit: string;
  source_type: SourceType;
  summary: {
    latest_period?: string | null;
    net_revenue?: number | null;
    net_income?: number | null;
    operating_cash_flow?: number | null;
    total_assets?: number | null;
    total_equity?: number | null;
  };
  warnings?: Array<{
    period?: string | null;
    code: string;
    severity: AlertLevel;
    message: string;
  }>;
  financials: MetricPoint[];
  pillars: {
    profitability: MetricPoint[];
    liquidity: MetricPoint[];
    efficiency: MetricPoint[];
    solvency: MetricPoint[];
  };
  dupont: MetricPoint[];
  quality_of_earnings: {
    series: MetricPoint[];
    latest?: MetricPoint | null;
    negative_streak: number;
    cash_loss_streak?: number;
    alert_level: AlertLevel;
    message: string;
  };
}

export type DashboardTab = "summary" | "deep-dive" | "benchmarking";
