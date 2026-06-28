export function formatMoney(value?: number | null, unit = "million", locale = "en-US"): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "-";
  }

  const fractionDigits = decimalPlaces(value);
  const fullValue = Intl.NumberFormat(locale, {
    maximumFractionDigits: fractionDigits,
    minimumFractionDigits: fractionDigits,
    useGrouping: true
  }).format(value);

  return `${fullValue} ${unit}`;
}

export function formatRatio(
  value?: number | null,
  options?: { percent?: boolean; locale?: string }
): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "-";
  }

  if (options?.percent) {
    return Intl.NumberFormat(options.locale ?? "en-US", {
      style: "percent",
      minimumFractionDigits: 1,
      maximumFractionDigits: 1
    }).format(value);
  }

  return Intl.NumberFormat(options?.locale ?? "en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(value);
}

export function formatDays(value?: number | null, locale = "en-US", unitLabel = "days"): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "-";
  }

  return `${Intl.NumberFormat(locale, {
    maximumFractionDigits: 1
  }).format(value)} ${unitLabel}`;
}

export function metricValue(
  point: Record<string, unknown> | null | undefined,
  key: string
): number | null {
  const value = point?.[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function last<T>(items: T[]): T | undefined {
  return items.length > 0 ? items[items.length - 1] : undefined;
}

function decimalPlaces(value: number): number {
  if (Number.isInteger(value)) {
    return 0;
  }

  const text = value.toString().toLowerCase();
  if (!text.includes("e")) {
    return Math.min(text.split(".")[1]?.length ?? 0, 20);
  }

  const [coefficient, exponentText] = text.split("e");
  const exponent = Number(exponentText);
  if (!Number.isFinite(exponent) || exponent >= 0) {
    return 0;
  }

  const coefficientDecimals = coefficient.split(".")[1]?.length ?? 0;
  return Math.min(Math.abs(exponent) + coefficientDecimals, 20);
}
