"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { BarChart3, Globe, MessageSquare, ImageIcon } from "lucide-react";
import type {
  UrlCheckResult,
  SmsCheckResult,
  ImageCheckResult,
} from "@/lib/types";
import { MODULE_WEIGHTS } from "@/lib/constants";
import { getDashboard } from "@/lib/api";
import RiskScoreGauge from "@/components/RiskScoreGauge";
import ModuleStatusBadge from "@/components/ModuleStatusBadge";

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

    // Primary source: the backend aggregator. Each checker writes its
    // latest result there, so this survives page refreshes.
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
        // page still shows something useful for this browser tab. We
        // read each entry in its own try/catch so one corrupted blob
        // doesn't wipe out the other two modules. The `mediguard_*`
        // keys are legacy (pre-rename) and can be dropped after one
        // release cycle.
        const read = <T,>(
          setter: (v: T) => void,
          ...keys: string[]
        ): void => {
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
  // Prefer the backend's authoritative score; fall back to weighted
  // client-side computation when offline.
  const overallScore =
    backendScore ?? computeOverallScore(urlResult, smsResult, imageResult);

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-primary-light mb-4">
          <BarChart3 className="w-6 h-6 text-primary" />
        </div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-2">
          Combined risk assessment from all detection modules.
        </p>
      </div>

      {/* Module status badges */}
      <div className="flex flex-wrap justify-center gap-3 mb-8">
        <ModuleStatusBadge
          label="URL"
          score={urlResult?.riskScore ?? null}
        />
        <ModuleStatusBadge
          label="SMS"
          score={smsResult?.riskScore ?? null}
        />
        <ModuleStatusBadge
          label="Image"
          score={imageResult?.riskScore ?? null}
        />
      </div>

      {!hasAnyResult ? (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-10 text-center">
          <p className="text-gray-500 mb-4">
            No checks have been performed yet. Run at least one check to see
            your combined risk assessment.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link
              href="/url-checker"
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-dark transition-colors"
            >
              <Globe className="w-4 h-4" />
              Check URL
            </Link>
            <Link
              href="/sms-checker"
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-dark transition-colors"
            >
              <MessageSquare className="w-4 h-4" />
              Check SMS
            </Link>
            <Link
              href="/image-checker"
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-dark transition-colors"
            >
              <ImageIcon className="w-4 h-4" />
              Check Image
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-8">
          {/* Overall score */}
          <div className="flex justify-center">
            <RiskScoreGauge score={overallScore} size="lg" />
          </div>

          {/* Module details */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* URL result */}
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
              <div className="flex items-center gap-2 mb-3">
                <Globe className="w-4 h-4 text-primary" />
                <h3 className="font-semibold text-gray-900 text-sm">
                  URL Checker
                </h3>
              </div>
              {urlResult ? (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <RiskScoreGauge score={urlResult.riskScore} size="sm" />
                  </div>
                  <p className="text-xs text-gray-500 truncate">
                    {urlResult.url}
                  </p>
                  <p className="text-xs text-gray-400">
                    {urlResult.flags.length} warning flag
                    {urlResult.flags.length !== 1 && "s"}
                  </p>
                </div>
              ) : (
                <p className="text-xs text-gray-400">
                  <Link
                    href="/url-checker"
                    className="text-primary hover:underline"
                  >
                    Run URL check
                  </Link>
                </p>
              )}
            </div>

            {/* SMS result */}
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
              <div className="flex items-center gap-2 mb-3">
                <MessageSquare className="w-4 h-4 text-primary" />
                <h3 className="font-semibold text-gray-900 text-sm">
                  SMS Detector
                </h3>
              </div>
              {smsResult ? (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <RiskScoreGauge score={smsResult.riskScore} size="sm" />
                  </div>
                  <span
                    className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                      smsResult.prediction === "scam"
                        ? "bg-red-100 text-red-700"
                        : "bg-green-100 text-green-700"
                    }`}
                  >
                    {smsResult.prediction === "scam" ? "Scam" : "Legitimate"}
                  </span>
                  <p className="text-xs text-gray-400">
                    {(smsResult.confidence * 100).toFixed(1)}% confidence
                  </p>
                </div>
              ) : (
                <p className="text-xs text-gray-400">
                  <Link
                    href="/sms-checker"
                    className="text-primary hover:underline"
                  >
                    Run SMS check
                  </Link>
                </p>
              )}
            </div>

            {/* Image result */}
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
              <div className="flex items-center gap-2 mb-3">
                <ImageIcon className="w-4 h-4 text-primary" />
                <h3 className="font-semibold text-gray-900 text-sm">
                  Image Screener
                </h3>
              </div>
              {imageResult ? (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <RiskScoreGauge score={imageResult.riskScore} size="sm" />
                  </div>
                  <span
                    className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                      imageResult.prediction === "counterfeit"
                        ? "bg-red-100 text-red-700"
                        : "bg-green-100 text-green-700"
                    }`}
                  >
                    {imageResult.prediction === "counterfeit"
                      ? "Counterfeit"
                      : "Authentic"}
                  </span>
                  <p className="text-xs text-gray-400">
                    {imageResult.details.length} finding
                    {imageResult.details.length !== 1 && "s"}
                  </p>
                </div>
              ) : (
                <p className="text-xs text-gray-400">
                  <Link
                    href="/image-checker"
                    className="text-primary hover:underline"
                  >
                    Run image check
                  </Link>
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
