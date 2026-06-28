import { BookOpenCheck } from "lucide-react";

import { copy, localeByLanguage, type Language } from "@/lib/i18n";
import { formatDays, formatRatio, last, metricValue } from "@/lib/formatters";
import type { DashboardMetrics } from "@/types/financial";

interface AnalysisNarrativeProps {
  dashboard: DashboardMetrics;
  language: Language;
}

export function AnalysisNarrative({ dashboard, language }: AnalysisNarrativeProps) {
  const t = copy[language];
  const locale = localeByLanguage[language];
  const profitability = last(dashboard.pillars.profitability);
  const liquidity = last(dashboard.pillars.liquidity);
  const efficiency = last(dashboard.pillars.efficiency);
  const solvency = last(dashboard.pillars.solvency);
  const qoe = dashboard.quality_of_earnings.latest;

  const readings = buildReadings({
    language,
    locale,
    netMargin: metricValue(profitability, "net_profit_margin"),
    roe: metricValue(profitability, "roe"),
    currentRatio: metricValue(liquidity, "current_ratio"),
    ccc: metricValue(efficiency, "cash_conversion_cycle"),
    debtToEquity: metricValue(solvency, "debt_to_equity"),
    interestCoverage: metricValue(solvency, "interest_coverage_ratio"),
    qoeRatio: metricValue(qoe, "quality_of_earnings_ratio"),
    qoeAlert: dashboard.quality_of_earnings.alert_level,
    warnings: dashboard.warnings ?? []
  });

  return (
    <section className="rounded-lg border border-line bg-surface p-4 shadow-soft">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold text-marine">
            <BookOpenCheck className="h-4 w-4" aria-hidden />
            <span>{t.narrative.title}</span>
          </div>
          <h2 className="mt-2 text-xl font-semibold text-ink">{t.narrative.currentReading}</h2>
        </div>
        <span className="rounded-md border border-line bg-paper px-2 py-1 text-xs font-semibold text-ink/62">
          {dashboard.summary.latest_period}
        </span>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        {readings.map((reading) => (
          <article key={reading.title} className="rounded-md border border-line bg-paper p-3">
            <p className="text-sm font-semibold text-ink">{reading.title}</p>
            <p className="mt-2 text-sm leading-6 text-ink/66">{reading.body}</p>
          </article>
        ))}
      </div>

      <div className="mt-4 rounded-md border border-marine/20 bg-marine/8 p-3">
        <p className="text-sm font-semibold text-marine">{t.narrative.disclosureTitle}</p>
        <p className="mt-2 text-sm leading-6 text-ink/68">{t.narrative.disclosure}</p>
      </div>
    </section>
  );
}

function buildReadings({
  language,
  locale,
  netMargin,
  roe,
  currentRatio,
  ccc,
  debtToEquity,
  interestCoverage,
  qoeRatio,
  qoeAlert,
  warnings
}: {
  language: Language;
  locale: string;
  netMargin: number | null;
  roe: number | null;
  currentRatio: number | null;
  ccc: number | null;
  debtToEquity: number | null;
  interestCoverage: number | null;
  qoeRatio: number | null;
  qoeAlert: string;
  warnings: Array<{ code: string; message: string }>;
}) {
  const t = copy[language];
  const dayLabel = language === "vi" ? "ngày" : "days";
  const hasNegativeEquity = warnings.some((warning) => warning.code === "NEGATIVE_EQUITY");

  if (language === "vi") {
    return [
      {
        title: t.health.profitability,
        body: `${t.narrative.profitability} Biên lợi nhuận ròng hiện là ${formatRatio(netMargin, {
          percent: true,
          locale
        })}; ROE là ${hasNegativeEquity ? "không có ý nghĩa do vốn chủ sở hữu âm" : formatRatio(roe, { percent: true, locale })}.`
      },
      {
        title: t.health.liquidity,
        body: `${t.narrative.liquidity} Hệ số thanh toán hiện hành hiện là ${formatRatio(currentRatio, {
          locale
        })}.`
      },
      {
        title: t.health.efficiency,
        body: `${t.narrative.efficiency} CCC hiện là ${formatDays(ccc, locale, dayLabel)}.`
      },
      {
        title: t.health.leverage,
        body: `${t.narrative.solvency} Nợ/VCSH là ${
          hasNegativeEquity ? "không có ý nghĩa do vốn chủ sở hữu âm" : formatRatio(debtToEquity, { locale })
        }; khả năng trả lãi là ${formatRatio(interestCoverage, { locale })}.`
      },
      {
        title: t.summary.qualityOfEarnings,
        body: `${t.narrative.qoe} Tỷ lệ hiện là ${formatRatio(qoeRatio, { locale })}, mức cảnh báo ${qoeAlert}.`
      }
    ];
  }

  return [
    {
      title: t.health.profitability,
      body: `${t.narrative.profitability} Latest net margin is ${formatRatio(netMargin, {
        percent: true,
        locale
      })}; ROE is ${hasNegativeEquity ? "not meaningful because equity is negative" : formatRatio(roe, { percent: true, locale })}.`
    },
    {
      title: t.health.liquidity,
      body: `${t.narrative.liquidity} Latest current ratio is ${formatRatio(currentRatio, { locale })}.`
    },
    {
      title: t.health.efficiency,
      body: `${t.narrative.efficiency} Latest CCC is ${formatDays(ccc, locale, dayLabel)}.`
    },
    {
      title: t.health.leverage,
      body: `${t.narrative.solvency} Debt/Equity is ${
        hasNegativeEquity ? "not meaningful because equity is negative" : formatRatio(debtToEquity, { locale })
      }; interest coverage is ${formatRatio(interestCoverage, { locale })}.`
    },
    {
      title: t.summary.qualityOfEarnings,
      body: `${t.narrative.qoe} Latest ratio is ${formatRatio(qoeRatio, { locale })}, with a ${qoeAlert} alert.`
    }
  ];
}
