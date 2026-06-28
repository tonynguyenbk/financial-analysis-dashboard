"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  FileUp,
  Globe2,
  LoaderCircle,
  Monitor,
  Moon,
  Play,
  Sun,
  Upload
} from "lucide-react";

import { calculateMetrics, parseStatementFile } from "@/lib/api/client";
import {
  copy,
  languageOptions,
  themeOptions,
  type Language,
  type ThemeMode
} from "@/lib/i18n";
import type {
  DashboardMetrics,
  DashboardTab,
  FinancialStatement,
  ParseJobSnapshot
} from "@/types/financial";
import { BenchmarkingTab } from "@/components/dashboard/tabs/benchmarking-tab";
import { DeepDiveTab } from "@/components/dashboard/tabs/deep-dive-tab";
import { StandardizedReportView } from "@/components/dashboard/standardized-report-view";
import { SummaryTab } from "@/components/dashboard/tabs/summary-tab";

export function DashboardShell() {
  const [language, setLanguage] = useState<Language>("vi");
  const [themeMode, setThemeMode] = useState<ThemeMode>("system");
  const [activeTab, setActiveTab] = useState<DashboardTab>("summary");
  const [statement, setStatement] = useState<FinancialStatement | null>(null);
  const [dashboard, setDashboard] = useState<DashboardMetrics | null>(null);
  const [parseJob, setParseJob] = useState<ParseJobSnapshot | null>(null);
  const [isParsing, setIsParsing] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const analyzeProgress = useEstimatedProgress(isAnalyzing, 12000);

  const t = copy[language];
  const tabs: Array<{ id: DashboardTab; label: string }> = [
    { id: "summary", label: t.tabs.summary },
    { id: "deep-dive", label: t.tabs.deepDive },
    { id: "benchmarking", label: t.tabs.benchmarking }
  ];

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");

    function applyTheme() {
      const resolvedTheme = themeMode === "system" ? (media.matches ? "dark" : "light") : themeMode;
      document.documentElement.classList.toggle("dark", resolvedTheme === "dark");
      document.documentElement.dataset.theme = resolvedTheme;
    }

    applyTheme();
    media.addEventListener("change", applyTheme);
    return () => media.removeEventListener("change", applyTheme);
  }, [themeMode]);

  async function handleUpload(file: File | undefined) {
    if (!file) {
      return;
    }

    setIsParsing(true);
    setParseJob(null);
    setError(null);
    setDashboard(null);
    setStatement(null);
    try {
      const handleParseProgress = (snapshot: ParseJobSnapshot) => {
        setParseJob(snapshot);
        if (snapshot.statement) {
          setStatement(snapshot.statement);
          setActiveTab("summary");
        }
      };

      const parsedStatement = await parseStatementFile(file, handleParseProgress);
      setStatement(parsedStatement);
      setActiveTab("summary");
    } catch (err) {
      setError(err instanceof Error ? err.message : t.errors.parse);
    } finally {
      setIsParsing(false);
      setParseJob(null);
    }
  }

  async function handleAnalyze() {
    if (!statement) {
      return;
    }

    setIsAnalyzing(true);
    setError(null);
    try {
      setDashboard(await calculateMetrics(statement));
      setActiveTab("summary");
    } catch (err) {
      setError(err instanceof Error ? err.message : t.errors.analyze);
    } finally {
      setIsAnalyzing(false);
    }
  }

  const companyLabel = useMemo(() => {
    const company = dashboard?.company ?? statement?.company;
    if (!company) {
      return t.appName;
    }
    return company.ticker ? `${company.name} (${company.ticker})` : company.name;
  }, [dashboard, statement, t.appName]);

  return (
    <main className="min-h-screen px-4 py-4 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-4">
        <header className="rounded-lg border border-line bg-surface/88 p-4 shadow-soft">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
            <div className="min-w-0">
              <div className="flex items-center gap-2 text-sm font-semibold text-marine">
                <BarChart3 className="h-4 w-4" aria-hidden />
                <span>{statement ? t.workflow.reviewTitle : t.workflow.uploadTitle}</span>
              </div>
              <h1 className="mt-1 break-words text-2xl font-semibold tracking-normal text-ink sm:text-3xl">
                {companyLabel}
              </h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-ink/64">{t.appSubtitle}</p>
            </div>

            <div className="flex flex-col gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <SegmentedLanguage value={language} onChange={setLanguage} label={t.language} />
                <SegmentedTheme value={themeMode} onChange={setThemeMode} label={t.themeLabel} language={language} />
              </div>

              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-end">
                <label className="inline-flex h-10 cursor-pointer items-center justify-center gap-2 rounded-md border border-marine bg-marine px-3 text-sm font-semibold text-white transition hover:bg-marine/90">
                  <Upload className="h-4 w-4" aria-hidden />
                  <span>{isParsing ? t.actions.uploading : statement ? t.actions.replaceFile : t.actions.upload}</span>
                  <input
                    className="sr-only"
                    type="file"
                    accept=".pdf,.xls,.xlsx"
                    disabled={isParsing || isAnalyzing}
                    onChange={(event) => void handleUpload(event.target.files?.[0])}
                  />
                </label>

                <button
                  type="button"
                  className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-line bg-surface px-3 text-sm font-semibold text-ink transition hover:border-marine/50 disabled:cursor-not-allowed disabled:opacity-50"
                  onClick={() => void handleAnalyze()}
                  disabled={!statement || isParsing || isAnalyzing}
                >
                  <Play className="h-4 w-4" aria-hidden />
                  <span>{isAnalyzing ? t.actions.analyzing : t.actions.analyze}</span>
                </button>
              </div>
            </div>
          </div>
        </header>

        <WorkflowStrip
          language={language}
          hasStatement={Boolean(statement)}
          hasDashboard={Boolean(dashboard)}
        />

        {error ? (
          <div className="flex items-start gap-3 rounded-lg border border-coral/30 bg-coral/10 p-3 text-sm text-ink">
            <AlertTriangle className="mt-0.5 h-4 w-4 flex-none text-coral" aria-hidden />
            <span>{error}</span>
          </div>
        ) : null}

        {isParsing ? (
          <LoadingState
            label={t.actions.uploading}
            progress={parseJob?.progress ?? 0}
            message={parseJob?.message}
            language={language}
            kind="parse"
          />
        ) : null}

        {!isParsing && !statement ? (
          <EmptyUploadState language={language} onUpload={handleUpload} />
        ) : null}

        {statement ? (
          <StandardizedReportView
            statement={statement}
            language={language}
            onStatementChange={setStatement}
          />
        ) : null}

        {dashboard?.warnings?.length ? (
          <div className="flex items-start gap-3 rounded-lg border border-gold/35 bg-gold/10 p-3 text-sm text-ink">
            <AlertTriangle className="mt-0.5 h-4 w-4 flex-none text-gold" aria-hidden />
            <div className="grid gap-1">
              <span className="font-semibold">{dashboard.warnings.length} warnings</span>
              <span className="text-ink/68">{dashboard.warnings[0].message}</span>
            </div>
          </div>
        ) : null}

        {isAnalyzing ? (
          <LoadingState
            label={t.actions.analyzing}
            progress={analyzeProgress}
            language={language}
            kind="analyze"
          />
        ) : null}

        {dashboard ? (
          <>
            <div className="flex gap-2 overflow-x-auto rounded-lg border border-line bg-surface p-1 shadow-soft">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  className={`h-10 flex-none rounded-md px-3 text-sm font-semibold transition ${
                    activeTab === tab.id
                      ? "bg-ink text-white"
                      : "text-ink/68 hover:bg-paper hover:text-ink"
                  }`}
                  onClick={() => setActiveTab(tab.id)}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <section className="min-h-[620px]">
              {activeTab === "summary" ? <SummaryTab dashboard={dashboard} language={language} /> : null}
              {activeTab === "deep-dive" ? <DeepDiveTab dashboard={dashboard} language={language} /> : null}
              {activeTab === "benchmarking" ? (
                <BenchmarkingTab dashboard={dashboard} language={language} />
              ) : null}
            </section>
          </>
        ) : null}
      </div>
    </main>
  );
}

function useEstimatedProgress(active: boolean, expectedDurationMs: number) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (!active) {
      setProgress(0);
      return;
    }

    const startedAt = Date.now();
    setProgress(6);

    const interval = window.setInterval(() => {
      const elapsed = Date.now() - startedAt;
      const curvedProgress = 100 * (1 - Math.exp(-elapsed / (expectedDurationMs / 2.6)));
      setProgress(Math.min(96, Math.max(6, Math.round(curvedProgress))));
    }, 500);

    return () => window.clearInterval(interval);
  }, [active, expectedDurationMs]);

  return progress;
}

function WorkflowStrip({
  language,
  hasStatement,
  hasDashboard
}: {
  language: Language;
  hasStatement: boolean;
  hasDashboard: boolean;
}) {
  const t = copy[language];
  const steps = [
    { title: t.workflow.uploadTitle, body: t.workflow.uploadBody, done: true },
    { title: t.workflow.reviewTitle, body: t.workflow.reviewBody, done: hasStatement },
    { title: t.workflow.analysisTitle, body: t.workflow.analysisBody, done: hasDashboard }
  ];

  return (
    <section className="grid gap-3 md:grid-cols-3">
      {steps.map((step, index) => (
        <article
          key={step.title}
          className={`rounded-lg border p-4 shadow-soft ${
            step.done ? "border-marine/30 bg-surface" : "border-line bg-surface/72"
          }`}
        >
          <div className="flex items-center gap-2">
            <span
              className={`grid h-7 w-7 place-items-center rounded-md text-sm font-semibold ${
                step.done ? "bg-marine text-white" : "bg-paper text-ink/54"
              }`}
            >
              {index + 1}
            </span>
            <h2 className="text-sm font-semibold text-ink">{step.title}</h2>
          </div>
          <p className="mt-3 text-sm leading-6 text-ink/62">{step.body}</p>
        </article>
      ))}
    </section>
  );
}

function EmptyUploadState({
  language,
  onUpload
}: {
  language: Language;
  onUpload: (file: File | undefined) => Promise<void>;
}) {
  const t = copy[language];
  return (
    <section className="grid min-h-[420px] place-items-center rounded-lg border border-dashed border-line bg-surface p-6 text-center shadow-soft">
      <div className="max-w-xl">
        <div className="mx-auto grid h-14 w-14 place-items-center rounded-lg bg-marine/10 text-marine">
          <FileUp className="h-7 w-7" aria-hidden />
        </div>
        <h2 className="mt-5 text-xl font-semibold text-ink">{t.workflow.uploadTitle}</h2>
        <p className="mt-2 text-sm leading-6 text-ink/64">{t.workflow.uploadBody}</p>
        <label className="mt-5 inline-flex h-10 cursor-pointer items-center justify-center gap-2 rounded-md border border-marine bg-marine px-4 text-sm font-semibold text-white transition hover:bg-marine/90">
          <Upload className="h-4 w-4" aria-hidden />
          <span>{t.actions.upload}</span>
          <input
            className="sr-only"
            type="file"
            accept=".pdf,.xls,.xlsx"
            onChange={(event) => void onUpload(event.target.files?.[0])}
          />
        </label>
      </div>
    </section>
  );
}

function LoadingState({
  label,
  progress,
  message,
  language,
  kind
}: {
  label: string;
  progress: number;
  message?: string;
  language: Language;
  kind: "parse" | "analyze";
}) {
  const percentage = Math.min(100, Math.max(1, progress));
  const copyText = loadingCopy[language][kind];
  const activeStep = loadingStepIndex(percentage);

  return (
    <section
      role="status"
      aria-live="polite"
      className="rounded-lg border border-line bg-surface p-5 shadow-soft"
    >
      <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
        <div className="flex min-w-0 items-center gap-4">
          <div className="grid h-12 w-12 flex-none place-items-center rounded-md bg-mint/10 text-mint">
            <LoaderCircle className="h-7 w-7 animate-spin" aria-hidden />
          </div>
          <div className="min-w-0">
            <div className="text-base font-semibold text-ink">{label}</div>
            <p className="mt-1 text-sm leading-6 text-ink/62">{message ?? copyText.status}</p>
          </div>
        </div>

        <div className="flex items-center gap-3 text-sm font-semibold text-ink">
          <span className="text-ink/58">{copyText.progressLabel}</span>
          <span className="min-w-14 rounded-md bg-marine/10 px-3 py-1 text-center text-marine">
            {percentage}%
          </span>
        </div>
      </div>

      <div className="mt-5 h-3 overflow-hidden rounded-full bg-paper ring-1 ring-line">
        <div
          className="h-full rounded-full bg-mint transition-[width] duration-500 ease-out"
          style={{ width: `${percentage}%` }}
        />
      </div>

      <ol className="mt-4 grid gap-2 text-sm sm:grid-cols-3">
        {copyText.steps.map((step, index) => {
          const done = index < activeStep;
          const current = index === activeStep;
          return (
            <li
              key={step}
              className={`flex items-center gap-2 rounded-md border px-3 py-2 ${
                done
                  ? "border-mint/30 bg-mint/10 text-ink"
                  : current
                    ? "border-marine/30 bg-marine/10 text-ink"
                    : "border-line bg-paper text-ink/58"
              }`}
            >
              {done ? (
                <CheckCircle2 className="h-4 w-4 flex-none text-mint" aria-hidden />
              ) : (
                <span
                  className={`h-2.5 w-2.5 flex-none rounded-full ${
                    current ? "animate-pulse bg-marine" : "bg-line"
                  }`}
                />
              )}
              <span className="min-w-0 truncate">{step}</span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function loadingStepIndex(progress: number) {
  if (progress >= 72) {
    return 2;
  }
  if (progress >= 32) {
    return 1;
  }
  return 0;
}

const loadingCopy = {
  en: {
    parse: {
      progressLabel: "Actual",
      status: "Reading the uploaded file, extracting tables and normalizing financial line items.",
      steps: ["File received", "Extracting data", "Normalizing report"]
    },
    analyze: {
      progressLabel: "Estimated",
      status: "Calculating ratios, DuPont decomposition and earnings quality checks.",
      steps: ["Financials loaded", "Calculating ratios", "Preparing dashboard"]
    }
  },
  vi: {
    parse: {
      progressLabel: "Thuc te",
      status: "Dang doc file, trich xuat bang va chuan hoa cac chi tieu tai chinh.",
      steps: ["Da nhan file", "Dang trich xuat", "Dang chuan hoa"]
    },
    analyze: {
      progressLabel: "Uoc tinh",
      status: "Dang tinh cac ty so, phan ra DuPont va kiem tra chat luong loi nhuan.",
      steps: ["Da nap bao cao", "Dang tinh chi so", "Dang tao dashboard"]
    }
  }
} as const;

function SegmentedLanguage({
  value,
  onChange,
  label
}: {
  value: Language;
  onChange: (value: Language) => void;
  label: string;
}) {
  return (
    <div className="flex items-center gap-2 rounded-md border border-line bg-paper p-1">
      <Globe2 className="ml-1 h-4 w-4 text-ink/54" aria-hidden />
      <span className="sr-only">{label}</span>
      {languageOptions.map((option) => (
        <button
          key={option.value}
          type="button"
          className={`h-8 rounded px-2 text-xs font-semibold transition ${
            value === option.value ? "bg-surface text-ink shadow-soft" : "text-ink/58 hover:text-ink"
          }`}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

function SegmentedTheme({
  value,
  onChange,
  label,
  language
}: {
  value: ThemeMode;
  onChange: (value: ThemeMode) => void;
  label: string;
  language: Language;
}) {
  const t = copy[language];
  const icons = {
    light: Sun,
    dark: Moon,
    system: Monitor
  };

  return (
    <div className="flex items-center gap-1 rounded-md border border-line bg-paper p-1">
      <span className="sr-only">{label}</span>
      {themeOptions.map((option) => {
        const Icon = icons[option.value];
        return (
          <button
            key={option.value}
            type="button"
            title={t.theme[option.labelKey]}
            className={`grid h-8 w-8 place-items-center rounded transition ${
              value === option.value ? "bg-surface text-ink shadow-soft" : "text-ink/58 hover:text-ink"
            }`}
            onClick={() => onChange(option.value)}
          >
            <Icon className="h-4 w-4" aria-hidden />
          </button>
        );
      })}
    </div>
  );
}
