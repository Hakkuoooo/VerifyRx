"use client";

import { useEffect, useRef, useState } from "react";
import { checkSms } from "@/lib/api";
import type { SmsCheckResult } from "@/lib/types";
import RiskScoreGauge from "@/components/RiskScoreGauge";
import ExplainabilityPanel from "@/components/ExplainabilityPanel";
import LoadingSpinner from "@/components/LoadingSpinner";
import { getRiskLevel } from "@/lib/utils";

export default function SmsCheckerPage() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<SmsCheckResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // LIME runs ~500 perturbations per call, so a second click while the
  // first is in flight is a real possibility — abort so we only ever
  // surface the latest result.
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await checkSms(text.trim(), controller.signal);
      if (controller.signal.aborted) return;
      setResult(data);
      sessionStorage.setItem("verifyrx_sms", JSON.stringify(data));
    } catch (err) {
      if (controller.signal.aborted) return;
      console.error("checkSms failed", err);
      setError(
        err instanceof Error && err.message
          ? `We could not analyse that message. ${err.message}`
          : "We could not analyse that message. Please try again in a moment."
      );
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }

  const isScam = result?.prediction === "scam";
  const level = result ? getRiskLevel(result.riskScore) : null;
  const accent =
    level === "high"
      ? "danger"
      : level === "medium"
        ? "warning"
        : "success";

  return (
    <div className="max-w-3xl mx-auto px-4 py-10 md:py-14">
      {/* ─── Page header ─── */}
      <p className="text-[12px] font-semibold tracking-[0.1em] uppercase text-[var(--color-primary)]">
        Check a text message
      </p>
      <h1 className="display mt-2 text-[32px] md:text-[40px] font-semibold text-[var(--color-ink)]">
        Is this text a medicine scam?
      </h1>
      <p className="mt-3 text-[17px] text-[var(--color-ink-muted)] leading-relaxed max-w-2xl">
        Paste a text message you&rsquo;ve received — from an &ldquo;NHS
        appointment&rdquo;, &ldquo;online pharmacy&rdquo;, or anyone else.
        We compare it against patterns we&rsquo;ve seen in real pharmacy
        scam messages reported to UK authorities.
      </p>

      {/* ─── Form ─── */}
      <form onSubmit={handleSubmit} className="mt-8 max-w-2xl">
        <label
          htmlFor="sms-input"
          className="block text-sm font-semibold text-[var(--color-ink)] mb-1"
        >
          Text of the message
        </label>
        <p
          id="sms-hint"
          className="text-[13px] text-[var(--color-ink-muted)] mb-2"
        >
          Paste the full message. Don&rsquo;t include your phone number or
          any personal details.
        </p>
        <textarea
          id="sms-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          aria-describedby="sms-hint"
          placeholder="Paste the message here…"
          rows={5}
          maxLength={2000}
          className="w-full px-3 py-3 border-2 border-[var(--color-ink)] bg-white text-[var(--color-ink)] text-[15px] resize-y focus:outline-none focus:border-[var(--color-primary)]"
          disabled={loading}
        />
        <div className="mt-1 flex justify-between text-[12px] text-[var(--color-ink-faint)]">
          <span>Up to 2,000 characters.</span>
          <span className="font-mono">{text.length} / 2000</span>
        </div>
        <button
          type="submit"
          disabled={loading || !text.trim()}
          className="mt-4 h-12 px-5 bg-[var(--color-action)] hover:bg-[var(--color-action-hover)] disabled:bg-[var(--color-ink-faint)] disabled:cursor-not-allowed text-white text-[15px] font-semibold rounded-[2px] transition-colors"
        >
          {loading ? "Analysing…" : "Check this message"}
        </button>
      </form>

      {loading && (
        <LoadingSpinner text="Running the scam-detection model and building the explanation…" />
      )}

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
      {result && level && (
        <section className="mt-10">
          <div
            className="border-l-[6px] bg-white border border-[var(--color-line)] p-5 md:p-6 flex flex-col md:flex-row md:items-center gap-6"
            style={{ borderLeftColor: `var(--color-${accent})` }}
          >
            <div className="flex-1">
              <p
                className="text-[12px] font-semibold uppercase tracking-[0.1em]"
                style={{ color: `var(--color-${accent})` }}
              >
                {isScam ? "Likely scam" : "Looks legitimate"}
              </p>
              <h2 className="mt-1 text-2xl font-semibold text-[var(--color-ink)] tracking-tight">
                {isScam
                  ? "Don't reply. Don't click any links."
                  : "No scam patterns detected."}
              </h2>
              <p className="mt-2 text-[15px] text-[var(--color-ink-muted)] leading-relaxed">
                {isScam
                  ? "This message matches phrasing we have seen in UK pharmacy phishing and fake-NHS texts. If you've already clicked a link or shared details, act quickly using the steps below."
                  : "Our model did not find phrases that match known scam patterns. This is a risk indication only — always verify the sender separately if the message asks for money or personal details."}
              </p>
              <p className="mt-3 text-[12px] text-[var(--color-ink-faint)]">
                Model confidence:{" "}
                <span className="font-mono text-[var(--color-ink)]">
                  {(result.confidence * 100).toFixed(1)}%
                </span>
              </p>
            </div>
            <div className="shrink-0">
              <RiskScoreGauge score={result.riskScore} size="md" />
            </div>
          </div>

          {/* Token-level explanation */}
          <h3 className="mt-10 text-lg font-semibold text-[var(--color-ink)]">
            Explanation
          </h3>
          <p className="mt-1 text-sm text-[var(--color-ink-muted)] leading-relaxed">
            These are the words and phrases that most influenced the
            classification. Hover any word for its contribution weight.
          </p>
          <div className="mt-3">
            <ExplainabilityPanel
              type="lime"
              limeHighlights={result.limeHighlights}
            />
          </div>

          {/* What to do next */}
          <div className="mt-8 bg-white border border-[var(--color-line)] p-5">
            <h3 className="text-lg font-semibold text-[var(--color-ink)]">
              What to do next
            </h3>
            <ul className="mt-3 space-y-2 text-[15px] text-[var(--color-ink-muted)] leading-relaxed">
              {isScam ? (
                <>
                  <li>
                    • Forward the text to{" "}
                    <span className="font-semibold text-[var(--color-ink)]">
                      7726
                    </span>{" "}
                    (the free UK spam-reporting number — it spells SPAM).
                  </li>
                  <li>
                    • Do not click any links in the message. If you already
                    did and entered card details, contact your bank now.
                  </li>
                  <li>
                    • Report it to{" "}
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
                    • If the message claimed to be from the NHS, a pharmacy
                    or your GP, contact them directly using a number you
                    already trust — not one from the message.
                  </li>
                </>
              ) : (
                <>
                  <li>
                    • Even when a message looks fine, never share bank or NHS
                    login details because a text asked you to.
                  </li>
                  <li>
                    • The NHS will never ask for payment in an SMS to verify
                    your account.
                  </li>
                  <li>
                    • When in doubt, forward the message to{" "}
                    <span className="font-semibold text-[var(--color-ink)]">
                      7726
                    </span>{" "}
                    — reporting is free.
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
