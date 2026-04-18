"use client";

import { useEffect, useRef, useState } from "react";
import { MessageSquare, CheckCircle, XCircle } from "lucide-react";
import { checkSms } from "@/lib/api";
import type { SmsCheckResult } from "@/lib/types";
import RiskScoreGauge from "@/components/RiskScoreGauge";
import ExplainabilityPanel from "@/components/ExplainabilityPanel";
import LoadingSpinner from "@/components/LoadingSpinner";

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
          ? `Failed to analyse SMS: ${err.message}`
          : "Failed to analyse SMS. Please try again."
      );
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-primary-light mb-4">
          <MessageSquare className="w-6 h-6 text-primary" />
        </div>
        <h1 className="text-3xl font-bold text-gray-900">SMS Scam Detector</h1>
        <p className="text-gray-500 mt-2">
          Paste a suspicious text message to detect medicine-related scams using
          NLP analysis.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="max-w-2xl mx-auto space-y-3">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste the SMS text here..."
          rows={4}
          className="w-full px-4 py-3 rounded-lg border border-gray-200 bg-white text-gray-900 placeholder-gray-400 resize-none focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
        />
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={loading || !text.trim()}
            className="px-6 py-2.5 bg-primary text-white rounded-lg font-medium hover:bg-primary-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Analyse
          </button>
        </div>
      </form>

      {loading && <LoadingSpinner text="Analysing SMS..." />}

      {error && (
        <p className="text-center text-red-600 text-sm mt-6">{error}</p>
      )}

      {result && (
        <div className="mt-10 space-y-8">
          <div className="flex flex-col sm:flex-row items-center justify-center gap-6">
            <RiskScoreGauge score={result.riskScore} size="lg" />
            <div className="flex flex-col items-center sm:items-start gap-2">
              <span
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold ${
                  result.prediction === "scam"
                    ? "bg-red-100 text-red-700"
                    : "bg-green-100 text-green-700"
                }`}
              >
                {result.prediction === "scam" ? (
                  <XCircle className="w-4 h-4" />
                ) : (
                  <CheckCircle className="w-4 h-4" />
                )}
                {result.prediction === "scam" ? "Scam Detected" : "Legitimate"}
              </span>
              <span className="text-sm text-gray-500">
                Confidence: {(result.confidence * 100).toFixed(1)}%
              </span>
            </div>
          </div>

          <ExplainabilityPanel
            type="lime"
            limeHighlights={result.limeHighlights}
          />

          <p className="text-xs text-gray-400 text-center">
            Words highlighted in red contributed most to the scam
            classification. Green words suggest legitimacy.
          </p>
        </div>
      )}
    </div>
  );
}
