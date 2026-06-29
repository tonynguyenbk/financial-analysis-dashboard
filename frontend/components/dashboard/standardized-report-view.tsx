"use client";

import { useState, type PointerEvent } from "react";
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
  onStatementChange?: (statement: FinancialStatement) => void;
}

type SectionKey = "balance_sheet" | "income_statement" | "cash_flow";
type EditableCellKind = "note" | "value";
type StatementColumnWidthMap = Record<string, number>;

interface EditableCellChange {
  tableIndex: number;
  tableKey: string;
  rowIndex: number;
  columnKey: string;
  kind: EditableCellKind;
  value: string | number | null;
}

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
const defaultStatementColumnWidths: Record<string, number> = {
  label: 390,
  code: 64,
  note: 86,
  value: 180
};

export function StandardizedReportView({ statement, language, onStatementChange }: StandardizedReportViewProps) {
  const t = copy[language];
  const locale = localeByLanguage[language];
  const metadataEntries = Object.entries(statement.metadata ?? {}).filter(
    ([key, value]) => !hiddenMetadataKeys.has(key) && value !== null && value !== undefined && value !== ""
  );
  const noteText = typeof statement.metadata?.notes === "string" ? statement.metadata.notes : null;
  const extractedPages = getExtractedPages(statement.metadata?.extracted_pages);
  const reportNavigation = getReportNavigation(statement.metadata?.report_navigation);
  const statementTables = getStatementTables(statement.metadata?.statement_tables);
  const editedCells = getEditedStatementCells(statement.metadata?.statement_table_edits);

  function handleStatementTableCellChange(change: EditableCellChange) {
    onStatementChange?.(updateStatementTableCell(statement, change));
  }

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
          <MainStatementTables
            tables={statementTables}
            language={language}
            locale={locale}
            currency={statement.currency}
            companyName={statement.company.name}
            editedCells={editedCells}
            onCellChange={handleStatementTableCellChange}
          />
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
  locale,
  currency,
  companyName,
  editedCells,
  onCellChange
}: {
  tables: StatementTable[];
  language: Language;
  locale: string;
  currency: string;
  companyName: string;
  editedCells: Set<string>;
  onCellChange: (change: EditableCellChange) => void;
}) {
  const labels = statementTableLabels[language];
  const [columnWidths, setColumnWidths] = useState<StatementColumnWidthMap>({});

  function handleColumnResize(tableKey: string, columnKey: string, width: number) {
    setColumnWidths((current) => ({
      ...current,
      [statementColumnWidthKey(tableKey, columnKey)]: width
    }));
  }

  return (
    <div className="grid gap-8">
      {tables.map((table, tableIndex) => {
        const valueColumns = table.columns.filter(
          (column) => !["code", "label", "note"].includes(column.key)
        );
        const itemLabel = getColumnLabel(table, "label", labels.item);
        const codeLabel = getColumnLabel(table, "code", labels.code);
        const noteLabel = getColumnLabel(table, "note", labels.note);
        const tableColumns = [
          { key: "label", label: itemLabel, align: "left" as const, minWidth: 280 },
          { key: "code", label: codeLabel, align: "center" as const, minWidth: 76 },
          { key: "note", label: noteLabel, align: "center" as const, minWidth: 90 },
          ...valueColumns.map((column) => ({
            key: column.key,
            label: column.label,
            align: "right" as const,
            minWidth: 140
          }))
        ];
        const resolvedWidths = tableColumns.map((column) =>
          getStatementColumnWidth(table.key, column.key, columnWidths)
        );
        const tableWidth = resolvedWidths.reduce((total, width) => total + width, 0);
        const pageWidth = Math.max(tableWidth + 96, 860);

        return (
          <section key={table.key} className="rounded-lg border border-line bg-surface p-3 shadow-soft">
            <div className="overflow-x-auto">
              <div
                className="mx-auto bg-white px-12 py-10 text-neutral-950 shadow-[0_18px_60px_rgba(0,0,0,0.18)]"
                style={{
                  width: `${pageWidth}px`,
                  fontFamily: '"Times New Roman", Times, serif'
                }}
              >
                <StatementPdfHeader
                  table={table}
                  companyName={companyName}
                  valueColumns={valueColumns}
                  language={language}
                />

                <table
                  className="table-fixed border-separate border-spacing-0 text-left text-[14px] leading-[1.16] text-neutral-950"
                  style={{ width: `${tableWidth}px` }}
                >
                  <colgroup>
                    {tableColumns.map((column, columnIndex) => (
                      <col key={column.key} style={{ width: `${resolvedWidths[columnIndex]}px` }} />
                    ))}
                  </colgroup>
                  <thead>
                    <tr className="text-neutral-950">
                      {tableColumns.map((column, columnIndex) => (
                        <ResizableStatementHeader
                          key={column.key}
                          label={column.label}
                          align={column.align}
                          width={resolvedWidths[columnIndex]}
                          minWidth={column.minWidth}
                          currency={valueColumns.some((valueColumn) => valueColumn.key === column.key) ? currency : null}
                          onResize={(width) => handleColumnResize(table.key, column.key, width)}
                        />
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {table.rows.map((row, rowIndex) => {
                      const rowLevel = getStatementRowLevel(row);
                      const emphasized = rowLevel <= 2 || isStatementTotalRow(table.key, row.code);
                      const sectionLike = rowLevel <= 1;
                      const totalLike = isStatementTotalRow(table.key, row.code);
                      const topRuleClass = totalLike ? "border-t border-neutral-950" : "";
                      const labelIndent = Math.max(0, rowLevel - 1) * 14;
                      const rowPaddingClass = sectionLike ? "pb-[3px] pt-4" : "py-[3px]";

                      return (
                        <tr
                          key={`${table.key}-${row.page ?? "p"}-${row.code}-${row.label}-${rowIndex}`}
                        >
                          <td
                            className={`${rowPaddingClass} pr-3 align-top ${topRuleClass} ${
                              emphasized ? "font-bold" : "font-normal"
                            } ${sectionLike ? "uppercase" : ""}`}
                            style={{ paddingLeft: `${labelIndent}px` }}
                            title={row.raw_label && row.raw_label !== row.label ? row.raw_label : undefined}
                          >
                            {row.label}
                          </td>
                          <td className={`px-2 ${rowPaddingClass} text-center align-top ${topRuleClass} ${emphasized ? "font-bold" : "font-normal"}`}>
                            {row.code}
                          </td>
                          <td className={`px-2 ${rowPaddingClass} text-center align-top ${topRuleClass}`}>
                            <EditableStatementCell
                              align="center"
                              value={row.note ?? null}
                              displayValue={row.note ?? "-"}
                              edited={editedCells.has(statementCellKey(table.key, rowIndex, "note"))}
                              onCommit={(value) =>
                                onCellChange({
                                  tableIndex,
                                  tableKey: table.key,
                                  rowIndex,
                                  columnKey: "note",
                                  kind: "note",
                                  value
                                })
                              }
                            />
                          </td>
                          {valueColumns.map((column) => (
                            <td
                              key={`${row.code}-${column.key}`}
                              className={`px-2 ${rowPaddingClass} text-right align-top tabular-nums ${
                                emphasized ? "font-bold" : "font-normal"
                              } ${topRuleClass}`}
                            >
                              <EditableStatementCell
                                align="right"
                                value={row.values[column.key] ?? null}
                                displayValue={formatStatementNumber(row.values[column.key], locale)}
                                edited={editedCells.has(statementCellKey(table.key, rowIndex, `value:${column.key}`))}
                                onCommit={(value) => {
                                  const parsedValue = parseEditableNumber(value);
                                  if (parsedValue !== undefined) {
                                    onCellChange({
                                      tableIndex,
                                      tableKey: table.key,
                                      rowIndex,
                                      columnKey: column.key,
                                      kind: "value",
                                      value: parsedValue
                                    });
                                  }
                                }}
                              />
                            </td>
                          ))}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        );
      })}
    </div>
  );
}

function StatementPdfHeader({
  table,
  companyName,
  valueColumns,
  language
}: {
  table: StatementTable;
  companyName: string;
  valueColumns: StatementTable["columns"];
  language: Language;
}) {
  const labels = statementPdfHeaderLabels[language];
  const formCode = getStatementFormCode(table.key);
  const periodCaption = getStatementPeriodCaption(table, valueColumns, language);
  const cashFlowMethod = getCashFlowMethodLabel(table, language);

  return (
    <header className="mb-7 grid grid-cols-[1fr_auto] gap-8 text-[16px] leading-[1.08] text-neutral-950">
      <div className="font-bold">
        <p>{companyName}</p>
        <p>
          {table.title}
          {periodCaption ? ` ${periodCaption}` : ""}
        </p>
        {cashFlowMethod ? <p>{cashFlowMethod}</p> : null}
      </div>
      <div className="min-w-[250px] text-center text-[14px] leading-[1.14]">
        <p className="font-bold">{formCode}</p>
        <p className="italic">{labels.circularLine1}</p>
        <p className="italic">{labels.circularLine2}</p>
      </div>
    </header>
  );
}

function ResizableStatementHeader({
  label,
  align,
  width,
  minWidth,
  currency,
  onResize
}: {
  label: string;
  align: "left" | "center" | "right";
  width: number;
  minWidth: number;
  currency?: string | null;
  onResize: (width: number) => void;
}) {
  function handlePointerDown(event: PointerEvent<HTMLButtonElement>) {
    event.preventDefault();
    event.stopPropagation();

    const startX = event.clientX;
    const startWidth = width;
    const originalCursor = document.body.style.cursor;
    const originalUserSelect = document.body.style.userSelect;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    function handlePointerMove(moveEvent: globalThis.PointerEvent) {
      const nextWidth = Math.max(minWidth, startWidth + moveEvent.clientX - startX);
      onResize(Math.round(nextWidth));
    }

    function handlePointerUp() {
      document.body.style.cursor = originalCursor;
      document.body.style.userSelect = originalUserSelect;
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
    }

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp, { once: true });
  }

  return (
    <th
      className={`relative border-b border-neutral-950 px-2 pb-2 pt-1 align-bottom font-bold leading-[1.05] ${
        align === "right" ? "text-right" : align === "center" ? "text-center" : "text-left"
      }`}
      style={{ width: `${width}px`, minWidth: `${minWidth}px` }}
      scope="col"
    >
      <span className="block whitespace-normal pr-2">{label}</span>
      {currency ? <span className="block pr-2">{currency}</span> : null}
      <button
        type="button"
        className="absolute right-0 top-1 h-[calc(100%-8px)] w-3 cursor-col-resize border-r border-transparent transition hover:border-amber-500 hover:bg-amber-100/70 active:border-amber-600"
        aria-label={`Resize ${label}`}
        onPointerDown={handlePointerDown}
      />
    </th>
  );
}

function EditableStatementCell({
  value,
  displayValue,
  edited,
  align,
  onCommit
}: {
  value: string | number | null;
  displayValue: string;
  edited: boolean;
  align: "center" | "right";
  onCommit: (value: string) => void;
}) {
  return (
    <input
      key={`${displayValue}-${edited ? "edited" : "clean"}`}
      type="text"
      defaultValue={displayValue}
      className={`h-[22px] w-full min-w-0 border bg-transparent px-1 text-[14px] leading-none text-neutral-950 outline-none transition focus:border-emerald-700 focus:bg-emerald-50 focus:ring-1 focus:ring-emerald-700/20 ${
        align === "right" ? "text-right tabular-nums" : "text-center"
      } ${
        edited
          ? "border-amber-500 bg-amber-100/70 ring-1 ring-amber-500/40"
          : "border-transparent hover:border-neutral-300"
      }`}
      onBlur={(event) => {
        const nextValue = event.currentTarget.value;
        if (!editableValuesEqual(value, nextValue)) {
          onCommit(nextValue);
        }
      }}
      onKeyDown={(event) => {
        if (event.key === "Enter") {
          event.currentTarget.blur();
        }
        if (event.key === "Escape") {
          event.currentTarget.value = displayValue;
          event.currentTarget.blur();
        }
      }}
    />
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

function getStatementFormCode(tableKey: string): string {
  const formCodes: Record<string, string> = {
    financial_position: "Mẫu B 01 - DN/HN",
    income_statement: "Mẫu B 02 - DN/HN",
    cash_flow: "Mẫu B 03 - DN/HN"
  };
  return formCodes[tableKey] ?? "Mẫu báo cáo";
}

function getStatementPeriodCaption(
  table: StatementTable,
  valueColumns: StatementTable["columns"],
  language: Language
): string {
  const year = getFirstStatementYear(valueColumns);
  if (!year) {
    return "";
  }

  if (language === "en") {
    return table.key === "financial_position"
      ? `as at 31 December ${year}`
      : `for the year ended 31 December ${year}`;
  }

  return table.key === "financial_position"
    ? `tại ngày 31 tháng 12 năm ${year}`
    : `cho năm kết thúc ngày 31 tháng 12 năm ${year}`;
}

function getFirstStatementYear(valueColumns: StatementTable["columns"]): string | null {
  for (const column of valueColumns) {
    const match = `${column.label} ${column.key}`.match(/\b(19|20)\d{2}\b/);
    if (match) {
      return match[0];
    }
  }
  return null;
}

function getCashFlowMethodLabel(table: StatementTable, language: Language): string | null {
  if (table.key !== "cash_flow") {
    return null;
  }
  const isDirect = table.template_key === "cash_flow_direct";
  if (language === "en") {
    return isDirect ? "(Direct method)" : "(Indirect method)";
  }
  return isDirect ? "(Phương pháp trực tiếp)" : "(Phương pháp gián tiếp)";
}

function getStatementRowLevel(row: StatementTable["rows"][number]): number {
  if (typeof row.level === "number" && Number.isFinite(row.level)) {
    return Math.max(1, row.level);
  }
  return 2;
}

function isStatementTotalRow(tableKey: string, code: string): boolean {
  const totalCodes: Record<string, Set<string>> = {
    financial_position: new Set(["100", "200", "270", "300", "400", "440"]),
    income_statement: new Set(["10", "20", "30", "40", "50", "60", "62", "70", "71"]),
    cash_flow: new Set(["08", "20", "30", "40", "50", "60", "70"])
  };
  return totalCodes[tableKey]?.has(code) ?? false;
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

function getEditedStatementCells(value: unknown): Set<string> {
  return new Set(Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : []);
}

function getStatementColumnWidth(
  tableKey: string,
  columnKey: string,
  widths: StatementColumnWidthMap
): number {
  const storedWidth = widths[statementColumnWidthKey(tableKey, columnKey)];
  if (typeof storedWidth === "number" && Number.isFinite(storedWidth)) {
    return storedWidth;
  }
  return defaultStatementColumnWidths[columnKey] ?? defaultStatementColumnWidths.value;
}

function statementColumnWidthKey(tableKey: string, columnKey: string): string {
  return `${tableKey}:${columnKey}`;
}

function updateStatementTableCell(statement: FinancialStatement, change: EditableCellChange): FinancialStatement {
  const tables = getStatementTables(statement.metadata?.statement_tables);
  const table = tables[change.tableIndex];
  const row = table?.rows[change.rowIndex];
  if (!table || !row || table.key !== change.tableKey) {
    return statement;
  }

  const updatedTables = tables.map((currentTable, tableIndex) => {
    if (tableIndex !== change.tableIndex) {
      return currentTable;
    }

    return {
      ...currentTable,
      rows: currentTable.rows.map((currentRow, rowIndex) => {
        if (rowIndex !== change.rowIndex) {
          return currentRow;
        }

        if (change.kind === "note") {
          const noteValue = normalizeEditableNote(String(change.value ?? ""));
          return {
            ...currentRow,
            note: noteValue
          };
        }

        return {
          ...currentRow,
          values: {
            ...currentRow.values,
            [change.columnKey]: typeof change.value === "number" ? change.value : null
          }
        };
      })
    };
  });

  const editKey = statementCellKey(
    change.tableKey,
    change.rowIndex,
    change.kind === "note" ? "note" : `value:${change.columnKey}`
  );
  const editedCells = getEditedStatementCells(statement.metadata?.statement_table_edits);
  editedCells.add(editKey);

  const updatedStatement: FinancialStatement = {
    ...statement,
    metadata: {
      ...(statement.metadata ?? {}),
      statement_tables: updatedTables,
      statement_table_edits: Array.from(editedCells)
    }
  };

  if (change.kind !== "value") {
    return updatedStatement;
  }

  return {
    ...updatedStatement,
    periods: updatePeriodsFromStatementTableCell(
      statement.periods,
      change.tableKey,
      row.code,
      change.columnKey,
      typeof change.value === "number" ? change.value : null
    )
  };
}

function updatePeriodsFromStatementTableCell(
  periods: FinancialPeriod[],
  tableKey: string,
  code: string,
  periodKey: string,
  value: number | null
): FinancialPeriod[] {
  const fieldPath = statementCodeFieldPaths[tableKey]?.[code];
  if (!fieldPath) {
    return periods;
  }

  return periods.map((period) => {
    const matchesPeriod =
      period.period === periodKey ||
      (period.fiscal_year !== null && period.fiscal_year !== undefined && String(period.fiscal_year) === periodKey);
    if (!matchesPeriod) {
      return period;
    }

    return {
      ...period,
      [fieldPath.section]: {
        ...period[fieldPath.section],
        [fieldPath.field]: value
      }
    };
  });
}

function statementCellKey(tableKey: string, rowIndex: number, columnKey: string): string {
  return `${tableKey}:${rowIndex}:${columnKey}`;
}

function normalizeEditableNote(value: string): string | null {
  const trimmed = value.trim();
  return trimmed && trimmed !== "-" ? trimmed : null;
}

function parseEditableNumber(value: string): number | null | undefined {
  const trimmed = value.trim();
  if (!trimmed || trimmed === "-") {
    return null;
  }

  const negativeByParentheses = trimmed.startsWith("(") && trimmed.endsWith(")");
  let cleaned = trimmed.replace(/[()]/g, "").replace(/\s/g, "");
  cleaned = cleaned.replace(/[^0-9,.-]/g, "");
  if (!cleaned || cleaned === "-" || cleaned === "." || cleaned === ",") {
    return undefined;
  }

  const negativeBySign = cleaned.startsWith("-");
  if (negativeBySign) {
    cleaned = cleaned.slice(1);
  }

  cleaned = normalizeEditableNumberSeparators(cleaned);
  const parsed = Number(cleaned);
  if (!Number.isFinite(parsed)) {
    return undefined;
  }

  return negativeByParentheses || negativeBySign ? -parsed : parsed;
}

function normalizeEditableNumberSeparators(value: string): string {
  if (value.includes(",") && value.includes(".")) {
    return value.lastIndexOf(",") > value.lastIndexOf(".")
      ? value.replace(/\./g, "").replace(",", ".")
      : value.replace(/,/g, "");
  }

  if (value.includes(".")) {
    const parts = value.split(".");
    if (parts.length > 2 || (parts.length === 2 && parts[1]?.length === 3 && parts[0].length <= 3)) {
      return parts.join("");
    }
  }

  if (value.includes(",")) {
    const parts = value.split(",");
    if (parts.length > 2 || (parts.length === 2 && parts[1]?.length === 3 && parts[0].length <= 3)) {
      return parts.join("");
    }
    return value.replace(",", ".");
  }

  return value;
}

function editableValuesEqual(currentValue: string | number | null, nextValue: string): boolean {
  if (typeof currentValue === "number") {
    const parsed = parseEditableNumber(nextValue);
    return parsed !== undefined && parsed === currentValue;
  }

  const normalizedCurrent = normalizeEditableNote(currentValue ?? "");
  const normalizedNext = normalizeEditableNote(nextValue);
  return normalizedCurrent === normalizedNext;
}

const statementCodeFieldPaths: Record<string, Record<string, { section: SectionKey; field: string }>> = {
  financial_position: {
    "100": { section: "balance_sheet", field: "current_assets" },
    "130": { section: "balance_sheet", field: "accounts_receivable" },
    "131": { section: "balance_sheet", field: "accounts_receivable" },
    "140": { section: "balance_sheet", field: "inventory" },
    "141": { section: "balance_sheet", field: "inventory" },
    "270": { section: "balance_sheet", field: "total_assets" },
    "300": { section: "balance_sheet", field: "total_liabilities" },
    "310": { section: "balance_sheet", field: "current_liabilities" },
    "311": { section: "balance_sheet", field: "accounts_payable" },
    "400": { section: "balance_sheet", field: "total_equity" }
  },
  income_statement: {
    "10": { section: "income_statement", field: "net_revenue" },
    "11": { section: "income_statement", field: "cost_of_goods_sold" },
    "20": { section: "income_statement", field: "gross_profit" },
    "23": { section: "income_statement", field: "interest_expense" },
    "30": { section: "income_statement", field: "ebit" },
    "60": { section: "income_statement", field: "net_income" }
  },
  cash_flow: {
    "20": { section: "cash_flow", field: "operating_cash_flow" }
  }
};

function formatStatementNumber(value: number | null | undefined, locale: string): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "-";
  }
  const absoluteValue = Math.abs(value);
  const digits = Number.isInteger(absoluteValue) ? 0 : Math.min(absoluteValue.toString().split(".")[1]?.length ?? 0, 20);
  const formatted = Intl.NumberFormat(locale, {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
    useGrouping: true
  }).format(absoluteValue);
  return value < 0 ? `(${formatted})` : formatted;
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

const statementPdfHeaderLabels = {
  en: {
    circularLine1: "(Issued under Circular 202/2014/TT-BTC",
    circularLine2: "dated 22 December 2014 by the Ministry of Finance)"
  },
  vi: {
    circularLine1: "(Ban hành theo Thông tư số 202/2014/TT-BTC",
    circularLine2: "ngày 22 tháng 12 năm 2014 của Bộ Tài chính)"
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
