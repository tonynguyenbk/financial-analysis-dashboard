import { FileSpreadsheet, FileText } from "lucide-react";

import { copy, localeByLanguage, type Language } from "@/lib/i18n";
import { formatMoney } from "@/lib/formatters";
import type {
  ExtractedReportPage,
  FinancialPeriod,
  FinancialStatement,
  ReportNavigationItem,
  StatementTable
} from "@/types/financial";

interface StandardizedReportViewProps {
  statement: FinancialStatement;
  language: Language;
}

type SectionKey = "balance_sheet" | "income_statement" | "cash_flow";

const sectionFields: Record<SectionKey, string[]> = {
  balance_sheet: [
    "current_assets",
    "inventory",
    "accounts_receivable",
    "total_assets",
    "current_liabilities",
    "accounts_payable",
    "total_liabilities",
    "total_equity"
  ],
  income_statement: [
    "net_revenue",
    "gross_profit",
    "cost_of_goods_sold",
    "ebit",
    "interest_expense",
    "net_income"
  ],
  cash_flow: ["operating_cash_flow"]
};

const hiddenMetadataKeys = new Set(["extracted_pages", "report_navigation", "statement_tables", "notes"]);

export function StandardizedReportView({ statement, language }: StandardizedReportViewProps) {
  const t = copy[language];
  const locale = localeByLanguage[language];
  const metadataEntries = Object.entries(statement.metadata ?? {}).filter(
    ([key, value]) => !hiddenMetadataKeys.has(key) && value !== null && value !== undefined && value !== ""
  );
  const noteText = typeof statement.metadata?.notes === "string" ? statement.metadata.notes : null;
  const extractedPages = getExtractedPages(statement.metadata?.extracted_pages);
  const reportNavigation = getReportNavigation(statement.metadata?.report_navigation);
  const statementTables = getStatementTables(statement.metadata?.statement_tables);

  return (
    <div className="grid gap-4">
      <section className="rounded-lg border border-line bg-surface p-4 shadow-soft">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-sm font-semibold text-marine">
              <FileSpreadsheet className="h-4 w-4" aria-hidden />
              <span>{t.workflow.reviewTitle}</span>
            </div>
            <h2 className="mt-2 break-words text-2xl font-semibold text-ink">
              {statement.company.ticker
                ? `${statement.company.name} (${statement.company.ticker})`
                : statement.company.name}
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-ink/64">
              {t.workflow.reviewBody}
            </p>
          </div>
          <dl className="grid min-w-[220px] gap-2 text-sm text-ink/70">
            <InfoRow label={t.report.source} value={statement.source_type.toUpperCase()} />
            <InfoRow label={t.report.currency} value={statement.currency} />
            <InfoRow label={t.report.unit} value={statement.unit} />
            <InfoRow label={t.report.periods} value={statement.periods.map((p) => p.period).join(", ")} />
          </dl>
        </div>
      </section>

      {statementTables.length ? (
        <>
          <MainStatementTables tables={statementTables} language={language} locale={locale} />
          <StatementNotes noteText={noteText} language={language} />
        </>
      ) : (
        <>
          <ReportNavigation navigation={reportNavigation} language={language} />

          <ReportSection
            title={t.report.balanceSheet}
            section="balance_sheet"
            periods={statement.periods}
            unit={statement.unit}
            locale={locale}
            labels={t.metrics}
            lineItemLabel={t.report.lineItem}
          />
          <ReportSection
            title={t.report.incomeStatement}
            section="income_statement"
            periods={statement.periods}
            unit={statement.unit}
            locale={locale}
            labels={t.metrics}
            lineItemLabel={t.report.lineItem}
          />
          <ReportSection
            title={t.report.cashFlow}
            section="cash_flow"
            periods={statement.periods}
            unit={statement.unit}
            locale={locale}
            labels={t.metrics}
            lineItemLabel={t.report.lineItem}
          />

          <FullExtractedReport pages={extractedPages} language={language} />

          <div className="grid gap-4 lg:grid-cols-2">
            <section className="rounded-lg border border-line bg-surface p-4 shadow-soft">
              <h3 className="text-base font-semibold text-ink">{t.report.metadata}</h3>
              {metadataEntries.length ? (
                <dl className="mt-4 grid gap-3 text-sm">
                  {metadataEntries.map(([key, value]) => (
                    <div key={key} className="grid gap-1 rounded-md border border-line bg-paper p-3">
                      <dt className="font-semibold text-ink/58">{formatKey(key)}</dt>
                      <dd className="break-words text-ink">{formatMetadataValue(value)}</dd>
                    </div>
                  ))}
                </dl>
              ) : (
                <p className="mt-3 text-sm text-ink/62">{t.report.noMetadata}</p>
              )}
            </section>

            <section className="rounded-lg border border-line bg-surface p-4 shadow-soft">
              <h3 className="text-base font-semibold text-ink">{t.report.notes}</h3>
              <p className="mt-3 text-sm leading-6 text-ink/64">{noteText ?? t.report.notesFallback}</p>
            </section>
          </div>
        </>
      )}
    </div>
  );
}

function MainStatementTables({
  tables,
  language,
  locale
}: {
  tables: StatementTable[];
  language: Language;
  locale: string;
}) {
  const labels = statementTableLabels[language];

  return (
    <div className="grid gap-4">
      <section className="rounded-lg border border-line bg-surface p-4 shadow-soft">
        <h3 className="text-base font-semibold text-ink">{labels.title}</h3>
        <p className="mt-2 text-sm leading-6 text-ink/62">{labels.body}</p>
      </section>

      {tables.map((table) => {
        const valueColumns = table.columns.filter(
          (column) => !["code", "label", "note"].includes(column.key)
        );
        const itemLabel = getColumnLabel(table, "label", labels.item);
        const codeLabel = getColumnLabel(table, "code", labels.code);
        const noteLabel = getColumnLabel(table, "note", labels.note);
        return (
          <section key={table.key} className="rounded-lg border border-line bg-surface p-4 shadow-soft">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h3 className="text-base font-semibold text-ink">{table.title}</h3>
                {table.pages?.length ? (
                  <p className="mt-1 text-xs font-semibold text-ink/52">
                    {labels.pages} {table.pages.join(", ")}
                  </p>
                ) : null}
              </div>
              <span className="rounded-md border border-line bg-paper px-3 py-1 text-sm font-semibold text-ink/68">
                {table.rows.length} {labels.rows}
              </span>
            </div>

            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[980px] border-separate border-spacing-0 text-left text-sm">
                <thead>
                  <tr className="text-ink/56">
                    <th className="min-w-[360px] border-b border-line px-3 py-3 font-semibold">{itemLabel}</th>
                    <th className="w-24 border-b border-line px-3 py-3 text-center font-semibold">{codeLabel}</th>
                    <th className="w-28 border-b border-line px-3 py-3 text-center font-semibold">{noteLabel}</th>
                    {valueColumns.map((column) => (
                      <th key={column.key} className="w-40 border-b border-line px-3 py-3 text-right font-semibold">
                        {column.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {table.rows.map((row) => (
                    <tr key={`${table.key}-${row.page ?? "p"}-${row.code}-${row.label}`}>
                      <td
                        className="border-b border-line py-3 pr-3 font-medium text-ink"
                        style={{ paddingLeft: `${12 + Math.max(0, (row.level ?? 1) - 1) * 14}px` }}
                        title={row.raw_label && row.raw_label !== row.label ? row.raw_label : undefined}
                      >
                        {row.label}
                      </td>
                      <td className="border-b border-line px-3 py-3 text-center font-semibold text-ink/68">{row.code}</td>
                      <td className="border-b border-line px-3 py-3 text-center text-ink/62">{row.note ?? "-"}</td>
                      {valueColumns.map((column) => (
                        <td key={`${row.code}-${column.key}`} className="border-b border-line px-3 py-3 text-right font-mono text-ink/78">
                          {formatStatementNumber(row.values[column.key], locale)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        );
      })}
    </div>
  );
}

function StatementNotes({ noteText, language }: { noteText: string | null; language: Language }) {
  const labels = statementNotesLabels[language];

  if (!noteText) {
    return null;
  }

  return (
    <section className="rounded-lg border border-line bg-surface p-4 shadow-soft">
      <h3 className="text-base font-semibold text-ink">{labels.title}</h3>
      <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-ink/66">{noteText}</p>
    </section>
  );
}

function getColumnLabel(table: StatementTable, key: string, fallback: string): string {
  return table.columns.find((column) => column.key === key)?.label ?? fallback;
}

function ReportNavigation({
  navigation,
  language
}: {
  navigation: ReportNavigationItem[];
  language: Language;
}) {
  const labels = navigationLabels[language];

  if (!navigation.length) {
    return null;
  }

  return (
    <section className="rounded-lg border border-line bg-surface p-4 shadow-soft">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-base font-semibold text-ink">{labels.title}</h3>
          <p className="mt-1 text-sm leading-6 text-ink/62">{labels.body}</p>
        </div>
        <span className="rounded-md border border-line bg-paper px-3 py-1 text-sm font-semibold text-ink/68">
          {navigation.length} {labels.items}
        </span>
      </div>

      <nav className="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-3" aria-label={labels.title}>
        {navigation.map((item) => (
          <a
            key={`${item.page}-${item.title}`}
            href={`#report-page-${item.page}`}
            className="flex min-h-12 items-center justify-between gap-3 rounded-md border border-line bg-paper px-3 py-2 text-sm transition hover:border-marine/50 hover:bg-marine/10"
          >
            <span className="min-w-0 truncate font-semibold text-ink">{item.title}</span>
            <span className="flex-none text-xs font-semibold text-ink/54">
              {labels.page} {item.page}
            </span>
          </a>
        ))}
      </nav>
    </section>
  );
}

function FullExtractedReport({
  pages,
  language
}: {
  pages: ExtractedReportPage[];
  language: Language;
}) {
  const labels = fullReportLabels[language];

  return (
    <section className="rounded-lg border border-line bg-surface p-4 shadow-soft">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-sm font-semibold text-marine">
            <FileText className="h-4 w-4" aria-hidden />
            <span>{labels.title}</span>
          </div>
          <p className="mt-2 text-sm leading-6 text-ink/62">{labels.body}</p>
        </div>
        <span className="rounded-md border border-line bg-paper px-3 py-1 text-sm font-semibold text-ink/68">
          {pages.length} {labels.pages}
        </span>
      </div>

      {pages.length ? (
        <div className="mt-4 grid gap-3">
          {pages.map((page, index) => (
            <details
              key={page.page}
              id={`report-page-${page.page}`}
              className="group rounded-md border border-line bg-paper open:bg-surface"
              open={index === 0}
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-4 py-3 text-sm font-semibold text-ink">
                <span>
                  {labels.page} {page.page}
                </span>
                <span className="text-xs text-ink/52 group-open:hidden">{labels.open}</span>
                <span className="hidden text-xs text-ink/52 group-open:inline">{labels.close}</span>
              </summary>
              <pre className="max-h-[420px] overflow-auto whitespace-pre-wrap border-t border-line px-4 py-3 text-xs leading-5 text-ink/74">
                {page.text}
              </pre>
            </details>
          ))}
        </div>
      ) : (
        <p className="mt-4 rounded-md border border-line bg-paper p-3 text-sm text-ink/62">
          {labels.empty}
        </p>
      )}
    </section>
  );
}

function ReportSection({
  title,
  section,
  periods,
  unit,
  locale,
  labels,
  lineItemLabel
}: {
  title: string;
  section: SectionKey;
  periods: FinancialPeriod[];
  unit: string;
  locale: string;
  labels: Record<string, string>;
  lineItemLabel: string;
}) {
  return (
    <section className="rounded-lg border border-line bg-surface p-4 shadow-soft">
      <h3 className="text-base font-semibold text-ink">{title}</h3>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[760px] border-separate border-spacing-0 text-left text-sm">
          <thead>
            <tr className="text-ink/56">
              <th className="border-b border-line px-3 py-3 font-semibold">{lineItemLabel}</th>
              {periods.map((period) => (
                <th key={period.period} className="border-b border-line px-3 py-3 text-right font-semibold">
                  {period.period}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sectionFields[section].map((field) => (
              <tr key={field}>
                <td className="border-b border-line px-3 py-4 font-medium text-ink">
                  {labels[field] ?? formatKey(field)}
                </td>
                {periods.map((period) => (
                  <td key={`${period.period}-${field}`} className="border-b border-line px-3 py-4 text-right text-ink/72">
                    {formatMoney(getPeriodValue(period, section, field), unit, locale)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-md border border-line bg-paper px-3 py-2">
      <dt className="font-medium text-ink/54">{label}</dt>
      <dd className="min-w-0 truncate font-semibold text-ink">{value}</dd>
    </div>
  );
}

function getPeriodValue(period: FinancialPeriod, section: SectionKey, field: string): number | null {
  const source = period[section] as Record<string, number | null | undefined>;
  const value = source[field];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function formatKey(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatMetadataValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  if (typeof value === "object" && value !== null) {
    return JSON.stringify(value);
  }
  return String(value);
}

function getExtractedPages(value: unknown): ExtractedReportPage[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map<ExtractedReportPage | null>((item) => {
      if (!item || typeof item !== "object") {
        return null;
      }
      const page = (item as Record<string, unknown>).page;
      const text = (item as Record<string, unknown>).text;
      if (typeof page !== "number" || typeof text !== "string" || !text.trim()) {
        return null;
      }
      return { page, text };
    })
    .filter((page): page is ExtractedReportPage => page !== null);
}

function getReportNavigation(value: unknown): ReportNavigationItem[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map<ReportNavigationItem | null>((item) => {
      if (!item || typeof item !== "object") {
        return null;
      }

      const record = item as Record<string, unknown>;
      const title = record.title;
      const page = record.page;
      if (typeof title !== "string" || typeof page !== "number" || !title.trim()) {
        return null;
      }

      return {
        title,
        page,
        level: typeof record.level === "number" ? record.level : null,
        source: typeof record.source === "string" ? record.source : null,
        report_page: typeof record.report_page === "number" ? record.report_page : null,
        report_page_end: typeof record.report_page_end === "number" ? record.report_page_end : null
      };
    })
    .filter((item): item is ReportNavigationItem => item !== null);
}

function getStatementTables(value: unknown): StatementTable[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map<StatementTable | null>((item) => {
      if (!item || typeof item !== "object") {
        return null;
      }

      const record = item as Record<string, unknown>;
      const key = record.key;
      const title = record.title;
      const columns = record.columns;
      const rows = record.rows;
      if (
        typeof key !== "string" ||
        typeof title !== "string" ||
        !Array.isArray(columns) ||
        !Array.isArray(rows)
      ) {
        return null;
      }

      const parsedColumns = columns
        .map((column) => {
          if (!column || typeof column !== "object") {
            return null;
          }
          const source = column as Record<string, unknown>;
          return typeof source.key === "string" && typeof source.label === "string"
            ? { key: source.key, label: source.label }
            : null;
        })
        .filter((column): column is StatementTable["columns"][number] => column !== null);

      const parsedRows = rows
        .map<StatementTable["rows"][number] | null>((row) => {
          if (!row || typeof row !== "object") {
            return null;
          }
          const source = row as Record<string, unknown>;
          const values = source.values;
          if (
            typeof source.code !== "string" ||
            typeof source.label !== "string" ||
            !values ||
            typeof values !== "object"
          ) {
            return null;
          }
          return {
            code: source.code,
            label: source.label,
            note: typeof source.note === "string" ? source.note : null,
            values: values as Record<string, number | null | undefined>,
            page: typeof source.page === "number" ? source.page : null,
            raw_text: typeof source.raw_text === "string" ? source.raw_text : null,
            parent_code: typeof source.parent_code === "string" ? source.parent_code : null,
            level: typeof source.level === "number" ? source.level : null,
            raw_label: typeof source.raw_label === "string" ? source.raw_label : null,
            template_label: typeof source.template_label === "string" ? source.template_label : null,
            mapping_source: typeof source.mapping_source === "string" ? source.mapping_source : null
          };
        })
        .filter((row): row is StatementTable["rows"][number] => row !== null);

      if (!parsedColumns.length || !parsedRows.length) {
        return null;
      }

      return {
        key,
        title,
        template_key: typeof record.template_key === "string" ? record.template_key : null,
        mapping_source: typeof record.mapping_source === "string" ? record.mapping_source : null,
        pages: Array.isArray(record.pages)
          ? record.pages.filter((page): page is number => typeof page === "number")
          : [],
        columns: parsedColumns,
        rows: parsedRows
      };
    })
    .filter((table): table is StatementTable => table !== null);
}

function formatStatementNumber(value: number | null | undefined, locale: string): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "-";
  }
  const digits = Number.isInteger(value) ? 0 : Math.min(value.toString().split(".")[1]?.length ?? 0, 20);
  return Intl.NumberFormat(locale, {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
    useGrouping: true
  }).format(value);
}

const statementTableLabels = {
  en: {
    title: "Primary financial statement tables",
    body: "Only the three numeric statements are shown here: financial position, income statement and cash flow.",
    pages: "PDF pages:",
    rows: "rows",
    code: "Code",
    item: "Line item",
    note: "Note"
  },
  vi: {
    title: "Bảng số liệu báo cáo tài chính",
    body: "Tạm thời chỉ hiển thị ba bảng số liệu chính: tình hình tài chính, kết quả hoạt động kinh doanh và lưu chuyển tiền tệ.",
    pages: "Trang PDF:",
    rows: "dòng",
    code: "Mã số",
    item: "Chỉ tiêu",
    note: "Thuyết minh"
  }
} as const;

const statementNotesLabels = {
  en: {
    title: "Notes and disclosures"
  },
  vi: {
    title: "Thuyết minh báo cáo"
  }
} as const;

const navigationLabels = {
  en: {
    title: "Report navigation",
    body: "Jump to the main sections detected from the PDF table of contents and page headings.",
    items: "sections",
    page: "Page"
  },
  vi: {
    title: "Điều hướng báo cáo",
    body: "Nhảy nhanh tới các phần chính được nhận diện từ mục lục và tiêu đề trang trong PDF.",
    items: "mục",
    page: "Trang"
  }
} as const;

const fullReportLabels = {
  en: {
    title: "Full extracted report",
    body: "Every readable page extracted from the uploaded PDF is kept here for review before analysis.",
    pages: "pages",
    page: "Page",
    open: "Open",
    close: "Close",
    empty: "No full-page extracted text is available for this file."
  },
  vi: {
    title: "Toàn bộ nội dung trích xuất",
    body: "Mỗi trang đọc được từ PDF được giữ lại tại đây để kiểm tra trước khi phân tích.",
    pages: "trang",
    page: "Trang",
    open: "Mở",
    close: "Đóng",
    empty: "Chưa có nội dung từng trang được trích xuất cho file này."
  }
} as const;
