"use client";

import { useEffect, useRef, useState } from "react";
import {
  Globe,
  Lock,
  LockOpen,
  Clock,
  ShieldCheck,
  ShieldX,
  Bug,
  ArrowRightLeft,
  AlertTriangle,
} from "lucide-react";
import { checkUrl } from "@/lib/api";
import type { UrlCheckResult } from "@/lib/types";
import RiskScoreGauge from "@/components/RiskScoreGauge";
import ResultCard from "@/components/ResultCard";
import LoadingSpinner from "@/components/LoadingSpinner";

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
          ? `Failed to check URL: ${err.message}`
          : "Failed to check URL. Please try again."
      );
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-primary-light mb-4">
          <Globe className="w-6 h-6 text-primary" />
        </div>
        <h1 className="text-3xl font-bold text-gray-900">URL Checker</h1>
        <p className="text-gray-500 mt-2">
          Check if a pharmacy website is legitimate by analysing its domain,
          registration, and security.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex gap-3 max-w-2xl mx-auto">
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Enter a URL (e.g. https://pharmacy-example.com)"
          className="flex-1 px-4 py-2.5 rounded-lg border border-gray-200 bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
        />
        <button
          type="submit"
          disabled={loading || !url.trim()}
          className="px-6 py-2.5 bg-primary text-white rounded-lg font-medium hover:bg-primary-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Check
        </button>
      </form>

      {loading && <LoadingSpinner text="Checking URL..." />}

      {error && (
        <p className="text-center text-red-600 text-sm mt-6">{error}</p>
      )}

      {result && (
        <div className="mt-10 space-y-8">
          <div className="flex justify-center">
            <RiskScoreGauge score={result.riskScore} size="lg" />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <ResultCard
              title="HTTPS"
              value={result.isHttps ? "Secure" : "Not Secure"}
              status={result.isHttps ? "pass" : "fail"}
              icon={
                result.isHttps ? (
                  <Lock className="w-4 h-4" />
                ) : (
                  <LockOpen className="w-4 h-4" />
                )
              }
            />
            <ResultCard
              title="Domain Age"
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
              title="GPhC Registered"
              value={result.isGphcRegistered ? "Yes" : "No"}
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
              value={`${result.virusTotalScore}% flagged`}
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
              value={`${result.redirectCount} hop${result.redirectCount !== 1 ? "s" : ""}`}
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
              title="WHOIS Registrant"
              value={result.whoisRegistrant}
              status={
                result.whoisRegistrant.toLowerCase().includes("privacy")
                  ? "warn"
                  : "pass"
              }
            />
          </div>

          {result.flags.length > 0 && (
            <div className="bg-red-50 rounded-xl border border-red-100 p-5">
              <h3 className="text-sm font-semibold text-red-800 flex items-center gap-2 mb-3">
                <AlertTriangle className="w-4 h-4" />
                Warning Flags
              </h3>
              <ul className="space-y-1.5">
                {result.flags.map((flag, i) => (
                  <li
                    key={i}
                    className="text-sm text-red-700 flex items-start gap-2"
                  >
                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-red-400 shrink-0" />
                    {flag}
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
