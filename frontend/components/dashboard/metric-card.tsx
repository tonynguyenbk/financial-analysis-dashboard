import type { ReactNode } from "react";

interface MetricCardProps {
  label: string;
  value: string;
  tone?: "mint" | "marine" | "gold" | "coral";
  icon?: ReactNode;
  detail?: string;
}

const toneClass = {
  mint: "border-mint/28 bg-mint/8 text-mint",
  marine: "border-marine/28 bg-marine/8 text-marine",
  gold: "border-gold/30 bg-gold/10 text-gold",
  coral: "border-coral/28 bg-coral/8 text-coral"
};

export function MetricCard({ label, value, tone = "marine", icon, detail }: MetricCardProps) {
  return (
    <article className="min-h-[132px] rounded-lg border border-line bg-surface p-4 shadow-soft">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-ink/58">{label}</p>
        {icon ? (
          <div className={`grid h-9 w-9 place-items-center rounded-md border ${toneClass[tone]}`}>
            {icon}
          </div>
        ) : null}
      </div>
      <p className="mt-4 break-words text-2xl font-semibold tracking-normal text-ink">{value}</p>
      {detail ? <p className="mt-2 text-sm text-ink/56">{detail}</p> : null}
    </article>
  );
}

