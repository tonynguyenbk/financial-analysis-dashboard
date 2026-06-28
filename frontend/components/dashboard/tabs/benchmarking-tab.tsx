import { copy, localeByLanguage, type Language } from "@/lib/i18n";
import { formatDays, formatRatio, last, metricValue } from "@/lib/formatters";
import type { DashboardMetrics } from "@/types/financial";

interface BenchmarkingTabProps {
  dashboard: DashboardMetrics;
  language: Language;
}

const benchmarks = {
  gross_profit_margin: 0.28,
  net_profit_margin: 0.095,
  roe: 0.15,
  current_ratio: 1.45,
  quick_ratio: 0.95,
  cash_conversion_cycle: 86,
  debt_to_equity: 1.25,
  interest_coverage_ratio: 4.2
};

export function BenchmarkingTab({ dashboard, language }: BenchmarkingTabProps) {
  const t = copy[language];
  const locale = localeByLanguage[language];
  const profitability = last(dashboard.pillars.profitability);
  const liquidity = last(dashboard.pillars.liquidity);
  const efficiency = last(dashboard.pillars.efficiency);
  const solvency = last(dashboard.pillars.solvency);

  const rows = [
    {
      metric: t.metrics.gross_profit_margin,
      company: metricValue(profitability, "gross_profit_margin"),
      benchmark: benchmarks.gross_profit_margin,
      format: "percent"
    },
    {
      metric: t.metrics.net_profit_margin,
      company: metricValue(profitability, "net_profit_margin"),
      benchmark: benchmarks.net_profit_margin,
      format: "percent"
    },
    {
      metric: t.metrics.roe,
      company: metricValue(profitability, "roe"),
      benchmark: benchmarks.roe,
      format: "percent"
    },
    {
      metric: t.metrics.current_ratio,
      company: metricValue(liquidity, "current_ratio"),
      benchmark: benchmarks.current_ratio,
      format: "ratio"
    },
    {
      metric: t.metrics.quick_ratio,
      company: metricValue(liquidity, "quick_ratio"),
      benchmark: benchmarks.quick_ratio,
      format: "ratio"
    },
    {
      metric: t.metrics.cash_conversion_cycle,
      company: metricValue(efficiency, "cash_conversion_cycle"),
      benchmark: benchmarks.cash_conversion_cycle,
      format: "days",
      inverse: true
    },
    {
      metric: t.metrics.debt_to_equity,
      company: metricValue(solvency, "debt_to_equity"),
      benchmark: benchmarks.debt_to_equity,
      format: "ratio",
      inverse: true
    },
    {
      metric: t.metrics.interest_coverage_ratio,
      company: metricValue(solvency, "interest_coverage_ratio"),
      benchmark: benchmarks.interest_coverage_ratio,
      format: "ratio"
    }
  ];

  return (
    <section className="rounded-lg border border-line bg-surface p-4 shadow-soft">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <h2 className="text-base font-semibold text-ink">{t.benchmark.title}</h2>
        <span className="text-sm text-ink/54">{dashboard.summary.latest_period}</span>
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[760px] border-separate border-spacing-0 text-left text-sm">
          <thead>
            <tr className="text-ink/56">
              <th className="border-b border-line px-3 py-3 font-semibold">{t.benchmark.metric}</th>
              <th className="border-b border-line px-3 py-3 font-semibold">{t.benchmark.company}</th>
              <th className="border-b border-line px-3 py-3 font-semibold">{t.benchmark.industry}</th>
              <th className="border-b border-line px-3 py-3 font-semibold">{t.benchmark.gap}</th>
              <th className="border-b border-line px-3 py-3 font-semibold">{t.benchmark.signal}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const gap = row.company === null ? null : row.company - row.benchmark;
              const isPositive =
                gap === null ? false : row.inverse ? gap <= 0 : gap >= 0;
              return (
                <tr key={row.metric} className="border-b border-line">
                  <td className="border-b border-line px-3 py-4 font-medium text-ink">
                    {row.metric}
                  </td>
                  <td className="border-b border-line px-3 py-4 text-ink/72">
                    {formatByType(row.company, row.format, locale, language)}
                  </td>
                  <td className="border-b border-line px-3 py-4 text-ink/72">
                    {formatByType(row.benchmark, row.format, locale, language)}
                  </td>
                  <td className="border-b border-line px-3 py-4 text-ink/72">
                    {formatByType(gap, row.format, locale, language)}
                  </td>
                  <td className="border-b border-line px-3 py-4">
                    <span
                      className={`rounded-md px-2 py-1 text-xs font-semibold ${
                        isPositive
                          ? "bg-mint/12 text-mint"
                          : "bg-coral/12 text-coral"
                      }`}
                    >
                      {isPositive ? t.benchmark.ahead : t.benchmark.watch}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function formatByType(value: number | null, type: string, locale: string, language: Language) {
  if (type === "percent") {
    return formatRatio(value, { percent: true, locale });
  }
  if (type === "days") {
    return formatDays(value, locale, language === "vi" ? "ngày" : "days");
  }
  return formatRatio(value, { locale });
}
