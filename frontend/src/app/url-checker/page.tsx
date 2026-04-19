"use client";

import { useEffect, useRef, useState } from "react";
import {
  Lock,
  LockOpen,
  Clock,
  ShieldCheck,
  ShieldX,
  Bug,
  ArrowRightLeft,
} from "lucide-react";
import { checkUrl } from "@/lib/api";
import type { UrlCheckResult } from "@/lib/types";
import RiskScoreGauge from "@/components/RiskScoreGauge";
import ResultCard from "@/components/ResultCard";
import LoadingSpinner from "@/components/LoadingSpinner";
import { getRiskLevel } from "@/lib/utils";

// Result-panel copy keyed by risk level. Kept in page-scope so the
// phrasing for URL specifically can diverge from SMS/Image over time.
const VERDICT_COPY = {
  low: {
    title: "This website looks safe to use.",
    body: "Signals from the pharmacy register, certificate and URL analysis did not turn up anything that matches known scam patterns. Still verify the pharmacy on the GPhC register before sharing payment details.",
  },
  medium: {
    title: "Use caution with this website.",
    body: "We found a mix of signals. The site may be legitimate but it shares characteristics with pharmacies we have seen defrauding UK consumers. Cross-check it on the GPhC register before you buy.",
  },
  high: {
    title: "Do not buy from this website.",
    body: "Multiple strong indicators suggest this site is not a legitimate pharmacy. Close the tab and do not enter payment or NHS details. If you have already paid, contact your bank straight away.",
  },
} as const;

export default function UrlCheckerPage() {
  const [url, setUrl] = useState("");
  const [result, setResult] = useState<UrlCheckResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Cancel the prior in-flight request if the user submits again so a
  // slow first response can't overwrite a faster second one.
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await checkUrl(url.trim(), controller.signal);
      if (controller.signal.aborted) return;
      setResult(data);
      sessionStorage.setItem("verifyrx_url", JSON.stringify(data));
    } catch (err) {
      if (controller.signal.aborted) return;
      console.error("checkUrl failed", err);
      setError(
        err instanceof Error && err.message
          ? `We could not check that URL. ${err.message}`
          : "We could not check that URL. Please try again in a moment."
      );
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }

  const level = result ? getRiskLevel(result.riskScore) : null;
  const verdict = level ? VERDICT_COPY[level] : null;

  return (
    <div className="max-w-3xl mx-auto px-4 py-10 md:py-14">
      {/* ─── Page header ─── */}
      <p className="text-[12px] font-semibold tracking-[0.1em] uppercase text-[var(--color-primary)]">
        Check a website
      </p>
      <h1 className="display mt-2 text-[32px] md:text-[40px] font-semibold text-[var(--color-ink)]">
        Is this pharmacy website legitimate?
      </h1>
      <p className="mt-3 text-[17px] text-[var(--color-ink-muted)] leading-relaxed max-w-2xl">
        Paste the full web address you want to check. We look it up against the{" "}
        <a
          href="https://www.pharmacyregulation.org/registers"
          target="_blank"
          rel="noopener noreferrer"
          className="prose-link"
        >
          General Pharmaceutical Council register
        </a>
        , check its security certificate, domain age and known-malicious lists.
      </p>

      {/* ─── Form ─── */}
      <form onSubmit={handleSubmit} className="mt-8 max-w-2xl">
        <label
          htmlFor="url-input"
          className="block text-sm font-semibold text-[var(--color-ink)] mb-1"
        >
          Website address
        </label>
        <p
          id="url-hint"
          className="text-[13px] text-[var(--color-ink-muted)] mb-2"
        >
          Include <span className="font-mono">https://</span> if you have it. Example:{" "}
          <span className="font-mono">https://pharmacy2u.co.uk</span>
        </p>
        <input
          id="url-input"
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          aria-describedby="url-hint"
          placeholder="https://"
          className="w-full h-12 px-3 border-2 border-[var(--color-ink)] bg-white text-[var(--color-ink)] font-mono text-[15px] focus:outline-none focus:border-[var(--color-primary)]"
          disabled={loading}
          autoComplete="off"
          spellCheck={false}
        />
        <button
          type="submit"
          disabled={loading || !url.trim()}
          className="mt-4 h-12 px-5 bg-[var(--color-action)] hover:bg-[var(--color-action-hover)] disabled:bg-[var(--color-ink-faint)] disabled:cursor-not-allowed text-white text-[15px] font-semibold rounded-[2px] transition-colors"
        >
          {loading ? "Checking…" : "Check this website"}
        </button>
      </form>

      {loading && <LoadingSpinner text="Checking the URL, register and security signals…" />}

      {error && (
        <div
          role="alert"
          className="mt-6 border-l-[4px] border-[var(--color-danger)] bg-[var(--color-danger-light)] p-4"
        >
          <p className="text-sm font-semibold text-[var(--color-danger)]">
            Check failed
          </p>
          <p className="text-sm text-[var(--color-ink)] mt-1">{error}</p>
        </div>
      )}

      {/* ─── Result ─── */}
      {result && verdict && level && (
        <section className="mt-10">
          {/* Verdict banner — the single dominant visual of the result. */}
          <div
            className="border-l-[6px] bg-white border border-[var(--color-line)] p-5 md:p-6 flex flex-col md:flex-row md:items-center gap-6"
            style={{
              borderLeftColor: `var(--color-${level === "high" ? "danger" : level === "medium" ? "warning" : "success"})`,
            }}
          >
            <div className="flex-1">
              <p
                className="text-[12px] font-semibold uppercase tracking-[0.1em]"
                style={{
                  color: `var(--color-${level === "high" ? "danger" : level === "medium" ? "warning" : "success"})`,
                }}
              >
                {level === "high"
                  ? "High risk"
                  : level === "medium"
                    ? "Caution"
                    : "Low risk"}
              </p>
              <h2 className="mt-1 text-2xl font-semibold text-[var(--color-ink)] tracking-tight">
                {verdict.title}
              </h2>
              <p className="mt-2 text-[15px] text-[var(--color-ink-muted)] leading-relaxed">
                {verdict.body}
              </p>
              <p className="mt-3 text-[12px] text-[var(--color-ink-faint)] font-mono break-all">
                {result.url}
              </p>
            </div>
            <div className="shrink-0">
              <RiskScoreGauge score={result.riskScore} size="md" />
            </div>
          </div>

          {/* Findings — flat list, not card grid */}
          <h3 className="mt-10 text-lg font-semibold text-[var(--color-ink)]">
            What we checked
          </h3>
          <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
            <ResultCard
              title="HTTPS"
              value={result.isHttps ? "Encrypted connection" : "Not encrypted"}
              status={result.isHttps ? "pass" : "fail"}
              icon={result.isHttps ? <Lock className="w-4 h-4" /> : <LockOpen className="w-4 h-4" />}
            />
            <ResultCard
              title="Domain age"
              value={result.domainAge}
              status={
                result.domainAgeDays > 180
                  ? "pass"
                  : result.domainAgeDays > 30
                    ? "warn"
                    : "fail"
              }
              icon={<Clock className="w-4 h-4" />}
            />
            <ResultCard
              title="GPhC register"
              value={result.isGphcRegistered ? "Listed" : "Not listed"}
              status={result.isGphcRegistered ? "pass" : "fail"}
              icon={
                result.isGphcRegistered ? (
                  <ShieldCheck className="w-4 h-4" />
                ) : (
                  <ShieldX className="w-4 h-4" />
                )
              }
            />
            <ResultCard
              title="VirusTotal"
              value={`${result.virusTotalScore}% of engines flag this URL`}
              status={
                result.virusTotalScore < 10
                  ? "pass"
                  : result.virusTotalScore < 30
                    ? "warn"
                    : "fail"
              }
              icon={<Bug className="w-4 h-4" />}
            />
            <ResultCard
              title="Redirects"
              value={`${result.redirectCount} hop${result.redirectCount === 1 ? "" : "s"} before final page`}
              status={
                result.redirectCount === 0
                  ? "pass"
                  : result.redirectCount <= 2
                    ? "warn"
                    : "fail"
              }
              icon={<ArrowRightLeft className="w-4 h-4" />}
            />
            <ResultCard
              title="WHOIS registrant"
              value={result.whoisRegistrant}
              status={
                result.whoisRegistrant.toLowerCase().includes("privacy")
                  ? "warn"
                  : "pass"
              }
            />
          </div>

          {/* Warning flags — only when there are any */}
          {result.flags.length > 0 && (
            <div className="mt-8 border-l-[4px] border-[var(--color-danger)] bg-[var(--color-danger-light)] p-5">
              <p className="text-[12px] font-semibold uppercase tracking-[0.1em] text-[var(--color-danger)]">
                Why this URL is suspicious
              </p>
              <ul className="mt-3 space-y-2">
                {result.flags.map((flag, i) => (
                  <li
                    key={i}
                    className="text-[15px] text-[var(--color-ink)] flex items-start gap-2 leading-relaxed"
                  >
                    <span className="mt-2 w-1 h-1 rounded-full bg-[var(--color-danger)] shrink-0" />
                    {flag}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* What to do next */}
          <div className="mt-8 bg-white border border-[var(--color-line)] p-5">
            <h3 className="text-lg font-semibold text-[var(--color-ink)]">
              What to do next
            </h3>
            <ul className="mt-3 space-y-2 text-[15px] text-[var(--color-ink-muted)] leading-relaxed">
              {level === "high" ? (
                <>
                  <li>• Do not enter card, bank or NHS details on this site.</li>
                  <li>
                    • If you already paid, contact your bank and report the
                    site to{" "}
                    <a
                      href="https://www.actionfraud.police.uk/"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="prose-link"
                    >
                      Action Fraud
                    </a>
                    .
                  </li>
                  <li>
                    • If you have taken a medicine bought here and feel unwell,
                    call{" "}
                    <a
                      href="https://111.nhs.uk/"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="prose-link"
                    >
                      NHS 111
                    </a>
                    .
                  </li>
                </>
              ) : level === "medium" ? (
                <>
                  <li>
                    • Look up the pharmacy on the{" "}
                    <a
                      href="https://www.pharmacyregulation.org/registers"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="prose-link"
                    >
                      GPhC register
                    </a>{" "}
                    before buying.
                  </li>
                  <li>
                    • Check it is listed in the MHRA database of approved
                    online sellers.
                  </li>
                  <li>
                    • If anything seems off, don&rsquo;t buy — ask your GP for
                    a prescription instead.
                  </li>
                </>
              ) : (
                <>
                  <li>
                    • Even when a site looks safe, confirm it on the{" "}
                    <a
                      href="https://www.pharmacyregulation.org/registers"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="prose-link"
                    >
                      GPhC register
                    </a>
                    .
                  </li>
                  <li>
                    • A legitimate pharmacy will display its GPhC number and
                    the superintendent pharmacist&rsquo;s name.
                  </li>
                </>
              )}
            </ul>
          </div>
        </section>
      )}
    </div>
  );
}
