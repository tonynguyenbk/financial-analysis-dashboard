import { Banknote, Coins, Landmark } from "lucide-react";

import { AnalysisNarrative } from "@/components/dashboard/analysis-narrative";
import { HealthIndicator } from "@/components/dashboard/health-indicator";
import { MetricCard } from "@/components/dashboard/metric-card";
import { EChart } from "@/components/charts/e-chart";
import { copy, localeByLanguage, type Language } from "@/lib/i18n";
import { formatMoney, formatRatio, last, metricValue } from "@/lib/formatters";
import type { ChartOption } from "@/components/charts/e-chart";
import type { DashboardMetrics } from "@/types/financial";

interface SummaryTabProps {
  dashboard: DashboardMetrics;
  language: Language;
}

export function SummaryTab({ dashboard, language }: SummaryTabProps) {
  const t = copy[language];
  const locale = localeByLanguage[language];
  const latestProfitability = last(dashboard.pillars.profitability);
  const latestQoe = dashboard.quality_of_earnings.latest;
  const periods = dashboard.financials.map((point) => point.period);

  const revenueIncomeOption: ChartOption = {
    tooltip: { trigger: "axis" },
    legend: { bottom: 0 },
    grid: { left: 44, right: 16, top: 20, bottom: 52 },
    xAxis: { type: "category", data: periods },
    yAxis: { type: "value" },
    series: [
      {
        name: t.metrics.net_revenue,
        type: "bar",
        data: dashboard.financials.map((point) => metricValue(point, "net_revenue")),
        itemStyle: { color: "#245F73" }
      },
      {
        name: t.metrics.net_profit_margin,
        type: "line",
        data: dashboard.pillars.profitability.map((point) =>
          metricValue(point, "net_profit_margin")
        ),
        yAxisIndex: 0,
        smooth: true,
        itemStyle: { color: "#2F806A" }
      }
    ]
  };

  return (
    <div className="grid gap-4">
      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard
          label={t.metrics.net_revenue}
          value={formatMoney(dashboard.summary.net_revenue, dashboard.unit, locale)}
          tone="marine"
          detail={dashboard.summary.latest_period ?? undefined}
          icon={<Landmark className="h-5 w-5" aria-hidden />}
        />
        <MetricCard
          label={t.metrics.net_income}
          value={formatMoney(dashboard.summary.net_income, dashboard.unit, locale)}
          tone="mint"
          detail={formatRatio(metricValue(latestProfitability, "net_profit_margin"), {
            percent: true,
            locale
          })}
          icon={<Coins className="h-5 w-5" aria-hidden />}
        />
        <MetricCard
          label={t.metrics.operating_cash_flow}
          value={formatMoney(dashboard.summary.operating_cash_flow, dashboard.unit, locale)}
          tone={dashboard.quality_of_earnings.alert_level === "red" ? "coral" : "gold"}
          detail={formatRatio(metricValue(latestQoe, "quality_of_earnings_ratio"), { locale })}
          icon={<Banknote className="h-5 w-5" aria-hidden />}
        />
      </div>

      <HealthIndicator dashboard={dashboard} language={language} />
      <AnalysisNarrative dashboard={dashboard} language={language} />

      <div className="grid gap-4 lg:grid-cols-[1.35fr_0.65fr]">
        <section className="rounded-lg border border-line bg-surface p-4 shadow-soft">
          <div className="mb-2 flex items-center justify-between gap-3">
            <h2 className="text-base font-semibold text-ink">{t.summary.revenueAndMargin}</h2>
            <span className="text-sm text-ink/52">{dashboard.summary.latest_period}</span>
          </div>
          <EChart option={revenueIncomeOption} height={320} />
        </section>

        <section className="rounded-lg border border-line bg-surface p-4 shadow-soft">
          <h2 className="text-base font-semibold text-ink">{t.summary.qualityOfEarnings}</h2>
          <div className="mt-4 flex items-end gap-3">
            <p className="text-4xl font-semibold text-ink">
              {formatRatio(metricValue(latestQoe, "quality_of_earnings_ratio"), { locale })}
            </p>
            <span
              className={`mb-1 rounded-md px-2 py-1 text-xs font-semibold uppercase tracking-normal text-white ${
                dashboard.quality_of_earnings.alert_level === "red"
                  ? "bg-coral"
                  : dashboard.quality_of_earnings.alert_level === "yellow"
                    ? "bg-gold"
                    : "bg-mint"
              }`}
            >
              {dashboard.quality_of_earnings.alert_level}
            </span>
          </div>
          <p className="mt-5 text-sm leading-6 text-ink/62">{dashboard.quality_of_earnings.message}</p>
          <div className="mt-6 grid grid-cols-2 gap-3">
            <div className="rounded-md border border-line bg-paper p-3">
              <p className="text-xs font-medium uppercase tracking-normal text-ink/48">
                {t.summary.streak}
              </p>
              <p className="mt-1 text-2xl font-semibold text-ink">
                {dashboard.quality_of_earnings.negative_streak}
              </p>
            </div>
            <div className="rounded-md border border-line bg-paper p-3">
              <p className="text-xs font-medium uppercase tracking-normal text-ink/48">ROE</p>
              <p className="mt-1 text-2xl font-semibold text-ink">
                {formatRatio(metricValue(latestProfitability, "roe"), {
                  percent: true,
                  locale
                })}
              </p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
