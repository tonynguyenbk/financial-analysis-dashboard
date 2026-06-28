import { EChart } from "@/components/charts/e-chart";
import { copy, localeByLanguage, type Language } from "@/lib/i18n";
import { formatRatio, last, metricValue } from "@/lib/formatters";
import type { ChartOption } from "@/components/charts/e-chart";
import type { DashboardMetrics } from "@/types/financial";

interface DeepDiveTabProps {
  dashboard: DashboardMetrics;
  language: Language;
}

export function DeepDiveTab({ dashboard, language }: DeepDiveTabProps) {
  const t = copy[language];
  const periods = dashboard.pillars.profitability.map((point) => point.period);

  const profitabilityOption: ChartOption = {
    tooltip: { trigger: "axis" },
    legend: { bottom: 0 },
    grid: { left: 44, right: 16, top: 20, bottom: 52 },
    xAxis: { type: "category", data: periods },
    yAxis: { type: "value" },
    series: [
      {
        name: t.metrics.gross_profit_margin,
        type: "line",
        smooth: true,
        data: dashboard.pillars.profitability.map((point) =>
          metricValue(point, "gross_profit_margin")
        ),
        itemStyle: { color: "#245F73" }
      },
      {
        name: t.metrics.net_profit_margin,
        type: "line",
        smooth: true,
        data: dashboard.pillars.profitability.map((point) =>
          metricValue(point, "net_profit_margin")
        ),
        itemStyle: { color: "#2F806A" }
      },
      {
        name: t.metrics.roe,
        type: "line",
        smooth: true,
        data: dashboard.pillars.profitability.map((point) => metricValue(point, "roe")),
        itemStyle: { color: "#BC8A2C" }
      }
    ]
  };

  const liquidityEfficiencyOption: ChartOption = {
    tooltip: { trigger: "axis" },
    legend: { bottom: 0 },
    grid: { left: 44, right: 16, top: 20, bottom: 52 },
    xAxis: { type: "category", data: periods },
    yAxis: { type: "value" },
    series: [
      {
        name: t.metrics.current_ratio,
        type: "bar",
        data: dashboard.pillars.liquidity.map((point) => metricValue(point, "current_ratio")),
        itemStyle: { color: "#245F73" }
      },
      {
        name: t.metrics.quick_ratio,
        type: "bar",
        data: dashboard.pillars.liquidity.map((point) => metricValue(point, "quick_ratio")),
        itemStyle: { color: "#2F806A" }
      },
      {
        name: "CCC",
        type: "line",
        smooth: true,
        data: dashboard.pillars.efficiency.map((point) =>
          metricValue(point, "cash_conversion_cycle")
        ),
        itemStyle: { color: "#C65F4A" }
      }
    ]
  };

  return (
    <div className="grid gap-4">
      <div className="grid gap-4 xl:grid-cols-2">
        <section className="rounded-lg border border-line bg-surface p-4 shadow-soft">
          <h2 className="mb-2 text-base font-semibold text-ink">{t.deepDive.profitability}</h2>
          <EChart option={profitabilityOption} height={340} />
        </section>

        <section className="rounded-lg border border-line bg-surface p-4 shadow-soft">
          <h2 className="mb-2 text-base font-semibold text-ink">{t.deepDive.liquidityCcc}</h2>
          <EChart option={liquidityEfficiencyOption} height={340} />
        </section>
      </div>

      <DupontTree dashboard={dashboard} language={language} />
    </div>
  );
}

function DupontTree({ dashboard, language }: { dashboard: DashboardMetrics; language: Language }) {
  const t = copy[language];
  const locale = localeByLanguage[language];
  const latestDupont = last(dashboard.dupont);

  const nodes = [
    {
      label: "NPM",
      value: formatRatio(metricValue(latestDupont, "net_profit_margin"), {
        percent: true,
        locale
      })
    },
    {
      label: t.deepDive.assetTurnover,
      value: formatRatio(metricValue(latestDupont, "asset_turnover"), { locale })
    },
    {
      label: t.deepDive.equityMultiplier,
      value: formatRatio(metricValue(latestDupont, "equity_multiplier"), { locale })
    }
  ];

  return (
    <section className="rounded-lg border border-line bg-surface p-4 shadow-soft">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <h2 className="text-base font-semibold text-ink">{t.deepDive.dupont}</h2>
        <p className="text-sm font-medium text-ink/58">
          ROE {formatRatio(metricValue(latestDupont, "roe_dupont"), { percent: true, locale })}
        </p>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
        <div className="rounded-lg border border-marine/20 bg-marine/8 p-5">
          <p className="text-sm font-medium text-marine">{t.deepDive.returnOnEquity}</p>
          <p className="mt-3 text-4xl font-semibold text-ink">
            {formatRatio(metricValue(latestDupont, "roe_dupont"), { percent: true, locale })}
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          {nodes.map((node) => (
            <article key={node.label} className="rounded-lg border border-line bg-paper p-4">
              <p className="text-sm font-medium text-ink/58">{node.label}</p>
              <p className="mt-3 text-2xl font-semibold text-ink">{node.value}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
