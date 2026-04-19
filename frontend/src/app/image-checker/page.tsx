"use client";

import { useEffect, useRef, useState } from "react";
import { checkImage } from "@/lib/api";
import type { ImageCheckResult } from "@/lib/types";
import RiskScoreGauge from "@/components/RiskScoreGauge";
import FileUploader from "@/components/FileUploader";
import ExplainabilityPanel from "@/components/ExplainabilityPanel";
import LoadingSpinner from "@/components/LoadingSpinner";
import { getRiskLevel } from "@/lib/utils";

export default function ImageCheckerPage() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [result, setResult] = useState<ImageCheckResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Image inference + Grad-CAM takes ~2–3s. If the user swaps the file
  // and clicks again, cancel the pending request so the UI always
  // reflects the latest submission.
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  function handleFileSelect(f: File) {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(f);
    setPreviewUrl(URL.createObjectURL(f));
    setResult(null);
    setError(null);
  }

  async function handleAnalyse() {
    if (!file) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await checkImage(file, controller.signal);
      if (controller.signal.aborted) return;
      setResult(data);
      sessionStorage.setItem("verifyrx_image", JSON.stringify(data));
    } catch (err) {
      if (controller.signal.aborted) return;
      console.error("checkImage failed", err);
      setError(
        err instanceof Error && err.message
          ? `We could not analyse that image. ${err.message}`
          : "We could not analyse that image. Please try again in a moment."
      );
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }

  const isCounterfeit = result?.prediction === "counterfeit";
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
        Check packaging
      </p>
      <h1 className="display mt-2 text-[32px] md:text-[40px] font-semibold text-[var(--color-ink)]">
        Does this pack look authentic?
      </h1>
      <p className="mt-3 text-[17px] text-[var(--color-ink-muted)] leading-relaxed max-w-2xl">
        Upload a clear photo of the front of the box, blister pack or
        leaflet. Our vision model compares the print, font and layout
        against authentic reference packaging.
      </p>

      {/* ─── Uploader ─── */}
      <div className="mt-8 max-w-2xl">
        <p className="text-sm font-semibold text-[var(--color-ink)] mb-1">
          Photo of the pack
        </p>
        <p className="text-[13px] text-[var(--color-ink-muted)] mb-2">
          Good light, the front of the box in frame, no personal details
          visible. We never store your photo after the check completes.
        </p>
        <FileUploader onFileSelect={handleFileSelect} />
        {file && !result && !loading && (
          <button
            onClick={handleAnalyse}
            className="mt-4 h-12 px-5 bg-[var(--color-action)] hover:bg-[var(--color-action-hover)] text-white text-[15px] font-semibold rounded-[2px] transition-colors"
          >
            Check this pack
          </button>
        )}
      </div>

      {loading && (
        <LoadingSpinner text="Running the vision model and building the heatmap…" />
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
                {isCounterfeit ? "Suspected counterfeit" : "Looks authentic"}
              </p>
              <h2 className="mt-1 text-2xl font-semibold text-[var(--color-ink)] tracking-tight">
                {isCounterfeit
                  ? "Do not take this medicine."
                  : "No counterfeit signs detected."}
              </h2>
              <p className="mt-2 text-[15px] text-[var(--color-ink-muted)] leading-relaxed">
                {isCounterfeit
                  ? "The print quality, typography or layout of this pack does not match authentic reference packaging. Take it to a pharmacist before using it, and report it on the MHRA Yellow Card."
                  : "This pack looks consistent with authentic reference packaging on the features our model examines. Photos alone cannot catch every counterfeit — if you bought it from a non-UK pharmacy, verify with your pharmacist."}
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

          {/* Heatmap */}
          {previewUrl && (
            <>
              <h3 className="mt-10 text-lg font-semibold text-[var(--color-ink)]">
                Explanation
              </h3>
              <p className="mt-1 text-sm text-[var(--color-ink-muted)] leading-relaxed">
                The red regions show where the model focused to reach its
                decision. Drag the slider to compare with the original
                photo.
              </p>
              <div className="mt-3">
                <ExplainabilityPanel
                  type="gradcam"
                  gradCamUrl={result.gradCamUrl}
                  originalImageUrl={previewUrl}
                />
              </div>
            </>
          )}

          {/* Findings from the model */}
          {result.details.length > 0 && (
            <div className="mt-8 border-l-[4px] border-[var(--color-warning)] bg-[var(--color-warning-light)] p-5">
              <p className="text-[12px] font-semibold uppercase tracking-[0.1em] text-[var(--color-warning)]">
                Visual features flagged
              </p>
              <ul className="mt-3 space-y-2">
                {result.details.map((detail, i) => (
                  <li
                    key={i}
                    className="text-[15px] text-[var(--color-ink)] flex items-start gap-2 leading-relaxed"
                  >
                    <span className="mt-2 w-1 h-1 rounded-full bg-[var(--color-warning)] shrink-0" />
                    {detail}
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
              {isCounterfeit ? (
                <>
                  <li>• Stop taking the medicine immediately.</li>
                  <li>
                    • Keep the pack and take it to a pharmacist or your GP
                    — they can confirm and advise on next steps.
                  </li>
                  <li>
                    • Report the suspect medicine to the{" "}
                    <a
                      href="https://yellowcard.mhra.gov.uk/"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="prose-link"
                    >
                      MHRA Yellow Card scheme
                    </a>
                    .
                  </li>
                  <li>
                    • If you feel unwell, call{" "}
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
              ) : (
                <>
                  <li>
                    • Cross-check the batch number and expiry date against
                    the manufacturer&rsquo;s website if you&rsquo;re still
                    unsure.
                  </li>
                  <li>
                    • A registered pharmacist can visually confirm a pack
                    in seconds — ask when you&rsquo;re next in a pharmacy.
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
