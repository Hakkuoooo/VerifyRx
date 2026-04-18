"use client";

import { useEffect, useRef, useState } from "react";
import { ImageIcon, CheckCircle, XCircle, AlertTriangle } from "lucide-react";
import { checkImage } from "@/lib/api";
import type { ImageCheckResult } from "@/lib/types";
import RiskScoreGauge from "@/components/RiskScoreGauge";
import FileUploader from "@/components/FileUploader";
import ExplainabilityPanel from "@/components/ExplainabilityPanel";
import LoadingSpinner from "@/components/LoadingSpinner";

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
          ? `Failed to analyse image: ${err.message}`
          : "Failed to analyse image. Please try again."
      );
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-primary-light mb-4">
          <ImageIcon className="w-6 h-6 text-primary" />
        </div>
        <h1 className="text-3xl font-bold text-gray-900">
          Medicine Image Screener
        </h1>
        <p className="text-gray-500 mt-2">
          Upload a photo of medicine packaging to check for signs of
          counterfeiting.
        </p>
      </div>

      <div className="max-w-lg mx-auto space-y-4">
        <FileUploader onFileSelect={handleFileSelect} />
        {file && !result && !loading && (
          <div className="flex justify-center">
            <button
              onClick={handleAnalyse}
              className="px-6 py-2.5 bg-primary text-white rounded-lg font-medium hover:bg-primary-dark transition-colors"
            >
              Analyse Image
            </button>
          </div>
        )}
      </div>

      {loading && <LoadingSpinner text="Analysing image..." />}

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
                  result.prediction === "counterfeit"
                    ? "bg-red-100 text-red-700"
                    : "bg-green-100 text-green-700"
                }`}
              >
                {result.prediction === "counterfeit" ? (
                  <XCircle className="w-4 h-4" />
                ) : (
                  <CheckCircle className="w-4 h-4" />
                )}
                {result.prediction === "counterfeit"
                  ? "Suspected Counterfeit"
                  : "Likely Authentic"}
              </span>
              <span className="text-sm text-gray-500">
                Confidence: {(result.confidence * 100).toFixed(1)}%
              </span>
            </div>
          </div>

          {previewUrl && (
            <ExplainabilityPanel
              type="gradcam"
              gradCamUrl={result.gradCamUrl}
              originalImageUrl={previewUrl}
            />
          )}

          {result.details.length > 0 && (
            <div className="bg-amber-50 rounded-xl border border-amber-100 p-5">
              <h3 className="text-sm font-semibold text-amber-800 flex items-center gap-2 mb-3">
                <AlertTriangle className="w-4 h-4" />
                Findings
              </h3>
              <ul className="space-y-1.5">
                {result.details.map((detail, i) => (
                  <li
                    key={i}
                    className="text-sm text-amber-700 flex items-start gap-2"
                  >
                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
                    {detail}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
