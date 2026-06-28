import { Activity, ShieldCheck, TrendingUp, WalletCards } from "lucide-react";

import { copy, localeByLanguage, type Language } from "@/lib/i18n";
import { formatDays, formatRatio, last, metricValue } from "@/lib/formatters";
import type { DashboardMetrics } from "@/types/financial";

interface HealthIndicatorProps {
  dashboard: DashboardMetrics;
  language: Language;
}

type Tone = "green" | "yellow" | "red";

const toneClass: Record<Tone, string> = {
  green: "bg-mint text-white",
  yellow: "bg-gold text-white",
  red: "bg-coral text-white"
};

export function HealthIndicator({ dashboard, language }: HealthIndicatorProps) {
  const t = copy[language];
  const locale = localeByLanguage[language];
  const dayLabel = language === "vi" ? "ngày" : "days";
  const profitability = last(dashboard.pillars.profitability);
  const liquidity = last(dashboard.pillars.liquidity);
  const efficiency = last(dashboard.pillars.efficiency);
  const solvency = last(dashboard.pillars.solvency);
  const latestEquity = dashboard.summary.total_equity ?? null;

  const items = [
    {
      label: t.health.profitability,
      value: formatRatio(metricValue(profitability, "roe"), { percent: true, locale }),
      tone: scoreRoe(metricValue(profitability, "roe"), latestEquity),
      icon: TrendingUp
    },
    {
      label: t.health.liquidity,
      value: formatRatio(metricValue(liquidity, "current_ratio"), { locale }),
      tone: scoreCurrentRatio(metricValue(liquidity, "current_ratio")),
      icon: WalletCards
    },
    {
      label: t.health.efficiency,
      value: formatDays(metricValue(efficiency, "cash_conversion_cycle"), locale, dayLabel),
      tone: scoreCycle(metricValue(efficiency, "cash_conversion_cycle")),
      icon: Activity
    },
    {
      label: t.health.leverage,
      value: formatRatio(metricValue(solvency, "debt_to_equity"), { locale }),
      tone: scoreDebt(metricValue(solvency, "debt_to_equity"), latestEquity),
      icon: ShieldCheck
    }
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <article key={item.label} className="rounded-lg border border-line bg-surface p-4 shadow-soft">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-ink/58">{item.label}</p>
                <p className="mt-2 text-xl font-semibold text-ink">{item.value}</p>
              </div>
              <div className={`grid h-10 w-10 place-items-center rounded-md ${toneClass[item.tone]}`}>
                <Icon className="h-5 w-5" aria-hidden />
              </div>
            </div>
          </article>
        );
      })}
    </div>
  );
}

function scoreRoe(value: number | null, equity: number | null): Tone {
  if (equity !== null && equity <= 0) return "red";
  if (value === null) return "yellow";
  if (value >= 0.16) return "green";
  if (value >= 0.08) return "yellow";
  return "red";
}

function scoreCurrentRatio(value: number | null): Tone {
  if (value === null) return "yellow";
  if (value >= 1.2) return "green";
  if (value >= 1) return "yellow";
  return "red";
}

function scoreCycle(value: number | null): Tone {
  if (value === null) return "yellow";
  if (value <= 85) return "green";
  if (value <= 130) return "yellow";
  return "red";
}

function scoreDebt(value: number | null, equity: number | null): Tone {
  if (equity !== null && equity <= 0) return "red";
  if (value === null) return "yellow";
  if (value <= 1.5) return "green";
  if (value <= 2.5) return "yellow";
  return "red";
}
