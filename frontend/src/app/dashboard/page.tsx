"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import type {
  UrlCheckResult,
  SmsCheckResult,
  ImageCheckResult,
} from "@/lib/types";
import { MODULE_WEIGHTS, RISK_COLORS } from "@/lib/constants";
import { getDashboard } from "@/lib/api";
import { getRiskLevel, getRiskLabel } from "@/lib/utils";
import RiskScoreGauge from "@/components/RiskScoreGauge";

// Fallback scoring for when the backend is unreachable and we have
// only sessionStorage data. The backend normally returns its own
// overallRiskScore (currently max-of-three) which takes precedence.
function computeOverallScore(
  url: UrlCheckResult | null,
  sms: SmsCheckResult | null,
  image: ImageCheckResult | null
): number {
  let totalWeight = 0;
  let weightedSum = 0;

  if (url) {
    weightedSum += url.riskScore * MODULE_WEIGHTS.url;
    totalWeight += MODULE_WEIGHTS.url;
  }
  if (sms) {
    weightedSum += sms.riskScore * MODULE_WEIGHTS.sms;
    totalWeight += MODULE_WEIGHTS.sms;
  }
  if (image) {
    weightedSum += image.riskScore * MODULE_WEIGHTS.image;
    totalWeight += MODULE_WEIGHTS.image;
  }

  return totalWeight > 0 ? Math.round(weightedSum / totalWeight) : 0;
}

export default function DashboardPage() {
  const [urlResult, setUrlResult] = useState<UrlCheckResult | null>(null);
  const [smsResult, setSmsResult] = useState<SmsCheckResult | null>(null);
  const [imageResult, setImageResult] = useState<ImageCheckResult | null>(null);
  const [backendScore, setBackendScore] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const data = await getDashboard();
        if (cancelled) return;
        setUrlResult(data.urlResult);
        setSmsResult(data.smsResult);
        setImageResult(data.imageResult);
        setBackendScore(data.overallRiskScore);
      } catch {
        // Backend unreachable — fall back to in-session state so the
        // page still shows something useful for this browser tab.
        const read = <T,>(setter: (v: T) => void, ...keys: string[]): void => {
          for (const k of keys) {
            const raw = sessionStorage.getItem(k);
            if (!raw) continue;
            try {
              setter(JSON.parse(raw) as T);
              return;
            } catch (err) {
              console.warn(`Corrupt sessionStorage entry ${k}`, err);
            }
          }
        };
        read<UrlCheckResult>(setUrlResult, "verifyrx_url", "mediguard_url");
        read<SmsCheckResult>(setSmsResult, "verifyrx_sms", "mediguard_sms");
        read<ImageCheckResult>(
          setImageResult,
          "verifyrx_image",
          "mediguard_image"
        );
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const hasAnyResult = urlResult || smsResult || imageResult;
  const overallScore =
    backendScore ?? computeOverallScore(urlResult, smsResult, imageResult);
  const overallLevel = hasAnyResult ? getRiskLevel(overallScore) : null;
  const overallCopy = overallLevel
    ? overallLevel === "high"
      ? "We would not trust this source. Don't buy, don't click, don't take."
      : overallLevel === "medium"
        ? "Mixed signals. Verify separately before you act on anything."
        : "Nothing suspicious turned up across the checks you ran."
    : "";

  return (
    <div className="max-w-5xl mx-auto px-4 py-10 md:py-14">
      {/* ─── Page header ─── */}
      <p className="text-[12px] font-semibold tracking-[0.1em] uppercase text-[var(--color-primary)]">
        My checks
      </p>
      <h1 className="display mt-2 text-[32px] md:text-[40px] font-semibold text-[var(--color-ink)]">
        Everything you&rsquo;ve checked in this session.
      </h1>
      <p className="mt-3 text-[17px] text-[var(--color-ink-muted)] leading-relaxed max-w-2xl">
        Each checker&rsquo;s latest result is kept here until you close
        this browser. Nothing is sent to another device or stored after
        you leave.
      </p>

      {!hasAnyResult ? (
        <EmptyState />
      ) : (
        <>
          {/* Combined-risk summary — the page's one hero element */}
          <section className="mt-10 bg-white border border-[var(--color-line)] p-6 md:p-8 flex flex-col md:flex-row md:items-center gap-6">
            <RiskScoreGauge score={overallScore} size="lg" />
            <div className="flex-1">
              <p
                className="text-[12px] font-semibold uppercase tracking-[0.1em]"
                style={{ color: RISK_COLORS[overallLevel!].ring }}
              >
                Combined — {getRiskLabel(overallScore)}
              </p>
              <h2 className="mt-1 text-2xl font-semibold text-[var(--color-ink)] tracking-tight">
                {overallCopy}
              </h2>
              <p className="mt-2 text-[15px] text-[var(--color-ink-muted)] leading-relaxed">
                We take the strongest signal from each check you&rsquo;ve
                run. Missing modules are ignored rather than assumed safe.
              </p>
            </div>
          </section>

          {/* Module rows */}
          <h3 className="mt-10 text-lg font-semibold text-[var(--color-ink)]">
            By module
          </h3>
          <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-4">
            <ModuleCard
              eyebrow="Website"
              title="URL check"
              href="/url-checker"
              runLabel="Check a website"
              rerunLabel="Check another"
            >
              {urlResult ? (
                <ModuleSummary
                  score={urlResult.riskScore}
                  primary={urlResult.url}
                  secondary={`${urlResult.flags.length} warning flag${
                    urlResult.flags.length === 1 ? "" : "s"
                  }`}
                />
              ) : null}
            </ModuleCard>

            <ModuleCard
              eyebrow="Text message"
              title="SMS check"
              href="/sms-checker"
              runLabel="Check a text"
              rerunLabel="Check another"
            >
              {smsResult ? (
                <ModuleSummary
                  score={smsResult.riskScore}
                  primary={
                    smsResult.prediction === "scam"
                      ? "Likely scam"
                      : "Looks legitimate"
                  }
                  secondary={`${(smsResult.confidence * 100).toFixed(1)}% confidence`}
                />
              ) : null}
            </ModuleCard>

            <ModuleCard
              eyebrow="Packaging"
              title="Image check"
              href="/image-checker"
              runLabel="Check a pack"
              rerunLabel="Check another"
            >
              {imageResult ? (
                <ModuleSummary
                  score={imageResult.riskScore}
                  primary={
                    imageResult.prediction === "counterfeit"
                      ? "Suspected counterfeit"
                      : "Looks authentic"
                  }
                  secondary={`${imageResult.details.length} finding${
                    imageResult.details.length === 1 ? "" : "s"
                  }`}
                />
              ) : null}
            </ModuleCard>
          </div>
        </>
      )}
    </div>
  );
}

// ─── Sub-components kept in-file since they're only used by the dashboard ───

function EmptyState() {
  const entries = [
    { href: "/url-checker", label: "Check a pharmacy website", eyebrow: "Website" },
    { href: "/sms-checker", label: "Check a suspicious text", eyebrow: "Text message" },
    { href: "/image-checker", label: "Check medicine packaging", eyebrow: "Packaging" },
  ];
  return (
    <div className="mt-10 bg-white border border-[var(--color-line)] p-8">
      <p className="text-[15px] text-[var(--color-ink-muted)]">
        You haven&rsquo;t run any checks yet. Start with whichever
        matches what you&rsquo;re worried about.
      </p>
      <div className="mt-5 grid grid-cols-1 md:grid-cols-3 gap-3">
        {entries.map((e) => (
          <Link
            key={e.href}
            href={e.href}
            className="group block bg-white border border-[var(--color-line)] border-l-[3px] border-l-[var(--color-primary)] p-4 hover:border-[var(--color-primary-border)]"
          >
            <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-[var(--color-ink-faint)]">
              {e.eyebrow}
            </p>
            <p className="mt-1 font-semibold text-[var(--color-ink)]">
              {e.label}
            </p>
            <span className="mt-2 inline-flex items-center text-[var(--color-primary)] text-sm font-medium">
              Start
              <ArrowRight
                className="w-4 h-4 ml-1 transition-transform group-hover:translate-x-0.5"
                aria-hidden
              />
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}

function ModuleCard({
  eyebrow,
  title,
  href,
  runLabel,
  rerunLabel,
  children,
}: {
  eyebrow: string;
  title: string;
  href: string;
  runLabel: string;
  rerunLabel: string;
  children: React.ReactNode;
}) {
  const hasResult = !!children;
  return (
    <div className="bg-white border border-[var(--color-line)] p-5 flex flex-col">
      <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-[var(--color-ink-faint)]">
        {eyebrow}
      </p>
      <h4 className="mt-1 text-[15px] font-semibold text-[var(--color-ink)]">
        {title}
      </h4>
      <div className="mt-3 flex-1">
        {hasResult ? (
          children
        ) : (
          <p className="text-[13px] text-[var(--color-ink-faint)]">
            Not run yet.
          </p>
        )}
      </div>
      <Link
        href={href}
        className="mt-4 inline-flex items-center text-[var(--color-primary)] hover:text-[var(--color-primary-hover)] text-sm font-medium"
      >
        {hasResult ? rerunLabel : runLabel}
        <ArrowRight className="w-4 h-4 ml-1" aria-hidden />
      </Link>
    </div>
  );
}

function ModuleSummary({
  score,
  primary,
  secondary,
}: {
  score: number;
  primary: string;
  secondary: string;
}) {
  return (
    <div className="flex items-start gap-4">
      <RiskScoreGauge score={score} size="sm" />
      <div className="flex-1 min-w-0">
        <p className="text-[14px] font-semibold text-[var(--color-ink)] break-words">
          {primary}
        </p>
        <p className="text-[12px] text-[var(--color-ink-faint)] mt-0.5">
          {secondary}
        </p>
      </div>
    </div>
  );
}
