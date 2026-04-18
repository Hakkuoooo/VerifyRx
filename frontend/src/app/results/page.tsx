"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import {
  FlaskConical,
  Gauge,
  SplitSquareHorizontal,
  Image as ImageIcon,
  MessageSquare,
  Info,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";
import type {
  EvaluationResult,
  EvaluationMetrics,
  EvaluationFigures,
} from "@/lib/types";
import { getEvaluation } from "@/lib/api";

// ---------------------------------------------------------------------------
// Typed accessors — the eval JSON comes from Python scripts that own its
// schema, so we narrow defensively at the read site rather than asserting
// a brittle full type. Each helper returns `undefined` when the shape
// doesn't match, and the UI renders an em-dash.
// ---------------------------------------------------------------------------
function asRecord(v: unknown): Record<string, unknown> | undefined {
  return v && typeof v === "object" && !Array.isArray(v)
    ? (v as Record<string, unknown>)
    : undefined;
}

function asNumber(v: unknown): number | undefined {
  return typeof v === "number" && Number.isFinite(v) ? v : undefined;
}

function asString(v: unknown): string | undefined {
  return typeof v === "string" ? v : undefined;
}

function fmt(n: number | undefined, digits = 3): string {
  return n === undefined ? "—" : n.toFixed(digits);
}

function fmtInt(n: number | undefined): string {
  return n === undefined ? "—" : String(n);
}

// ---------------------------------------------------------------------------
// Small presentational components — kept in-file because they're only
// ever used here and there's no value in a new /components module yet.
// ---------------------------------------------------------------------------
function Section({
  icon: Icon,
  title,
  subtitle,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
      <div className="flex items-start gap-3 mb-4">
        <div className="w-9 h-9 rounded-lg bg-primary-light flex items-center justify-center shrink-0">
          <Icon className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
          {subtitle && (
            <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>
          )}
        </div>
      </div>
      {children}
    </section>
  );
}

function EmptyCard({ message, command }: { message: string; command: string }) {
  return (
    <div className="bg-gray-50 border border-dashed border-gray-200 rounded-lg p-4 text-sm text-gray-600">
      <div className="flex items-center gap-2 mb-2">
        <Info className="w-4 h-4 text-gray-400" />
        <span>{message}</span>
      </div>
      <code className="block mt-1 px-2 py-1 bg-white border border-gray-200 rounded text-xs font-mono text-gray-800">
        {command}
      </code>
    </div>
  );
}

function MetricPill({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string;
  tone?: "neutral" | "good" | "warn";
}) {
  const tones = {
    neutral: "bg-gray-50 text-gray-700 border-gray-200",
    good: "bg-green-50 text-green-700 border-green-200",
    warn: "bg-amber-50 text-amber-700 border-amber-200",
  };
  return (
    <div
      className={`border rounded-lg px-3 py-2 text-xs ${tones[tone]}`}
    >
      <div className="uppercase tracking-wide font-medium opacity-70">
        {label}
      </div>
      <div className="text-base font-semibold tabular-nums">{value}</div>
    </div>
  );
}

type SplitRow = {
  name: string;
  n: number | undefined;
  accuracy: number | undefined;
  precision: number | undefined;
  recall: number | undefined;
  f1: number | undefined;
  ece: number | undefined;
};

function splitRowFrom(
  name: string,
  raw: unknown,
  opts: { nKey?: string } = {}
): SplitRow {
  const r = asRecord(raw) ?? {};
  const nested = asRecord(r.metrics); // image report nests metrics one level deeper
  const src = nested ?? r;
  return {
    name,
    n: asNumber(src[opts.nKey ?? "n"]),
    accuracy: asNumber(src.accuracy),
    precision: asNumber(src.precision),
    recall: asNumber(src.recall),
    f1: asNumber(src.f1),
    ece: asNumber(src.ece),
  };
}

function SplitTable({ rows }: { rows: SplitRow[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-xs uppercase text-gray-500 border-b border-gray-100">
            <th className="text-left py-2 pr-4 font-medium">Split</th>
            <th className="text-right py-2 px-2 font-medium">n</th>
            <th className="text-right py-2 px-2 font-medium">Accuracy</th>
            <th className="text-right py-2 px-2 font-medium">Precision</th>
            <th className="text-right py-2 px-2 font-medium">Recall</th>
            <th className="text-right py-2 px-2 font-medium">F1</th>
            <th className="text-right py-2 px-2 font-medium">ECE</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr
              key={r.name}
              className="border-b border-gray-50 last:border-b-0"
            >
              <td className="py-2 pr-4 font-medium text-gray-900">{r.name}</td>
              <td className="py-2 px-2 text-right tabular-nums text-gray-700">
                {fmtInt(r.n)}
              </td>
              <td className="py-2 px-2 text-right tabular-nums text-gray-700">
                {fmt(r.accuracy)}
              </td>
              <td className="py-2 px-2 text-right tabular-nums text-gray-700">
                {fmt(r.precision)}
              </td>
              <td className="py-2 px-2 text-right tabular-nums text-gray-700">
                {fmt(r.recall)}
              </td>
              <td className="py-2 px-2 text-right tabular-nums text-gray-700">
                {fmt(r.f1)}
              </td>
              <td className="py-2 px-2 text-right tabular-nums text-gray-700">
                {fmt(r.ece)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AblationTable({ rows }: { rows: unknown[] }) {
  const normalised = rows.map((raw) => {
    const r = asRecord(raw) ?? {};
    return {
      model: asString(r.model) ?? "—",
      split: asString(r.split),
      n: asNumber(r.n),
      accuracy: asNumber(r.accuracy),
      precision: asNumber(r.precision),
      recall: asNumber(r.recall),
      f1: asNumber(r.f1),
      notes: asString(r.notes),
    };
  });
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-xs uppercase text-gray-500 border-b border-gray-100">
            <th className="text-left py-2 pr-4 font-medium">Model</th>
            {normalised.some((r) => r.split) && (
              <th className="text-left py-2 px-2 font-medium">Split</th>
            )}
            <th className="text-right py-2 px-2 font-medium">n</th>
            <th className="text-right py-2 px-2 font-medium">Accuracy</th>
            <th className="text-right py-2 px-2 font-medium">Precision</th>
            <th className="text-right py-2 px-2 font-medium">Recall</th>
            <th className="text-right py-2 px-2 font-medium">F1</th>
          </tr>
        </thead>
        <tbody>
          {normalised.map((r, i) => (
            <tr
              key={`${r.model}-${r.split ?? i}`}
              className="border-b border-gray-50 last:border-b-0"
            >
              <td className="py-2 pr-4 font-medium text-gray-900">{r.model}</td>
              {normalised.some((r2) => r2.split) && (
                <td className="py-2 px-2 text-gray-600">{r.split ?? "—"}</td>
              )}
              <td className="py-2 px-2 text-right tabular-nums text-gray-700">
                {fmtInt(r.n)}
              </td>
              <td className="py-2 px-2 text-right tabular-nums text-gray-700">
                {fmt(r.accuracy)}
              </td>
              <td className="py-2 px-2 text-right tabular-nums text-gray-700">
                {fmt(r.precision)}
              </td>
              <td className="py-2 px-2 text-right tabular-nums text-gray-700">
                {fmt(r.recall)}
              </td>
              <td className="py-2 px-2 text-right tabular-nums text-gray-700">
                {fmt(r.f1)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PerCategoryTable({ per }: { per: Record<string, unknown> }) {
  const entries = Object.entries(per)
    .map(([cat, v]) => {
      const r = asRecord(v) ?? {};
      return {
        cat,
        n: asNumber(r.n),
        accuracy: asNumber(r.accuracy),
        f1: asNumber(r.f1),
      };
    })
    .sort((a, b) => (a.accuracy ?? 0) - (b.accuracy ?? 0));
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-xs uppercase text-gray-500 border-b border-gray-100">
            <th className="text-left py-2 pr-4 font-medium">Category</th>
            <th className="text-right py-2 px-2 font-medium">n</th>
            <th className="text-right py-2 px-2 font-medium">Accuracy</th>
            <th className="text-right py-2 px-2 font-medium">F1</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e) => (
            <tr
              key={e.cat}
              className="border-b border-gray-50 last:border-b-0"
            >
              <td className="py-2 pr-4 font-mono text-gray-800 text-xs">
                {e.cat}
              </td>
              <td className="py-2 px-2 text-right tabular-nums text-gray-700">
                {fmtInt(e.n)}
              </td>
              <td
                className={`py-2 px-2 text-right tabular-nums ${
                  (e.accuracy ?? 1) < 0.5
                    ? "text-red-600 font-medium"
                    : (e.accuracy ?? 1) < 1
                      ? "text-amber-600"
                      : "text-green-700"
                }`}
              >
                {fmt(e.accuracy)}
              </td>
              <td className="py-2 px-2 text-right tabular-nums text-gray-700">
                {fmt(e.f1)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FigureGrid({
  figures,
  pick,
}: {
  figures: EvaluationFigures;
  pick: { key: keyof EvaluationFigures; label: string }[];
}) {
  const available = pick
    .map(({ key, label }) => ({ key, label, url: figures[key] }))
    .filter((f): f is { key: keyof EvaluationFigures; label: string; url: string } =>
      Boolean(f.url)
    );
  if (available.length === 0) return null;
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
      {available.map((f) => (
        <figure
          key={f.key}
          className="border border-gray-100 rounded-lg p-3 bg-gray-50"
        >
          <Image
            src={f.url}
            alt={f.label}
            width={640}
            height={480}
            unoptimized
            className="w-full h-auto rounded"
          />
          <figcaption className="text-xs text-gray-500 mt-2 text-center">
            {f.label}
          </figcaption>
        </figure>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function ResultsPage() {
  const [data, setData] = useState<EvaluationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    abortRef.current = controller;
    (async () => {
      try {
        const res = await getEvaluation(controller.signal);
        if (controller.signal.aborted) return;
        setData(res);
      } catch (err) {
        if (controller.signal.aborted) return;
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    })();
    return () => controller.abort();
  }, []);

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-10">
        <div className="h-6 w-32 bg-gray-100 rounded animate-pulse mb-4" />
        <div className="h-40 bg-white rounded-xl border border-gray-100 shadow-sm animate-pulse" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-10">
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-8 text-center">
          <AlertTriangle className="w-8 h-8 text-amber-500 mx-auto mb-3" />
          <h1 className="text-xl font-semibold text-gray-900 mb-2">
            Couldn&apos;t load evaluation report
          </h1>
          <p className="text-sm text-gray-500 mb-4">
            The backend didn&apos;t return an evaluation payload. Usually this
            means the evaluation scripts haven&apos;t been run yet.
          </p>
          {error && (
            <pre className="text-xs text-left text-gray-500 bg-gray-50 border border-gray-100 rounded p-3 overflow-auto">
              {error}
            </pre>
          )}
          <code className="block mt-4 px-3 py-2 bg-gray-50 border border-gray-200 rounded text-xs font-mono text-gray-800 text-left">
            cd backend && python -m scripts.generate_evaluation_report
          </code>
        </div>
      </div>
    );
  }

  // -----------------------------------------------------------------------
  // Extract SMS data
  // -----------------------------------------------------------------------
  const smsSplits = asRecord(asRecord(data.sms.metrics)?.splits);
  const smsRows: SplitRow[] = [];
  if (smsSplits) {
    if (smsSplits.uci_heldout) {
      smsRows.push(splitRowFrom("UCI held-out", smsSplits.uci_heldout));
    }
    if (smsSplits.ood_pharma) {
      smsRows.push(splitRowFrom("OOD pharma", smsSplits.ood_pharma));
    }
  }
  const smsOodPer = asRecord(
    asRecord(smsSplits?.ood_pharma)?.per_category
  );

  const smsAblationRows =
    (asRecord(data.sms.ablation)?.rows as unknown[] | undefined) ?? [];

  const smsModel = asRecord(asRecord(data.sms.metrics)?.model);
  const smsIsFinetuned = smsModel?.is_finetuned === true;

  // -----------------------------------------------------------------------
  // Extract Image data
  // -----------------------------------------------------------------------
  const imageRows: SplitRow[] = [];
  if (data.image.metrics) {
    imageRows.push(splitRowFrom("val (in-dist)", data.image.metrics));
  }
  if (data.image.external) {
    imageRows.push(splitRowFrom("external", data.image.external));
  }
  const imageModel = asRecord(asRecord(data.image.metrics)?.model);
  const imageIsFinetuned = imageModel?.is_finetuned === true;

  const imageAblationRows =
    (asRecord(data.image.ablation)?.rows as unknown[] | undefined) ?? [];

  return (
    <div className="max-w-5xl mx-auto px-4 py-10 space-y-6">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 mb-2">
          <div className="w-10 h-10 rounded-lg bg-primary-light flex items-center justify-center">
            <FlaskConical className="w-5 h-5 text-primary" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900">
            Evaluation Results
          </h1>
        </div>
        <p className="text-gray-500">
          Live metrics, ablation studies, calibration diagrams, and the
          external held-out test — straight from{" "}
          <code className="text-xs bg-gray-100 rounded px-1 py-0.5">
            backend/reports/
          </code>
          .
        </p>
        <p className="text-xs text-gray-400 mt-1">
          Generated{" "}
          {new Date(data.generatedAt).toLocaleString(undefined, {
            dateStyle: "medium",
            timeStyle: "short",
          })}
          . Regenerate:{" "}
          <code className="text-xs bg-gray-100 rounded px-1 py-0.5 font-mono">
            python -m scripts.generate_evaluation_report
          </code>
        </p>
      </div>

      {/* ============================================================= */}
      {/* SMS section                                                    */}
      {/* ============================================================= */}
      <Section
        icon={MessageSquare}
        title="SMS classifier — metrics"
        subtitle={
          smsIsFinetuned
            ? "Fine-tuned DistilBERT · in-distribution + out-of-distribution"
            : "Pretrained fallback (no local fine-tune detected)"
        }
      >
        {smsRows.length > 0 ? (
          <>
            <SplitTable rows={smsRows} />
            <div className="flex flex-wrap gap-2 mt-4">
              <ProvenancePill
                label="Fine-tuned"
                value={smsIsFinetuned ? "yes" : "no"}
                good={smsIsFinetuned}
              />
              <ProvenancePill
                label="Source"
                value={asString(smsModel?.source) ?? "—"}
                mono
              />
            </div>
            <FigureGrid
              figures={data.sms.figures}
              pick={[
                { key: "confusionUci", label: "Confusion — UCI" },
                { key: "confusionOod", label: "Confusion — OOD pharma" },
                { key: "reliabilityUci", label: "Reliability — UCI" },
                { key: "reliabilityOod", label: "Reliability — OOD pharma" },
              ]}
            />
          </>
        ) : (
          <EmptyCard
            message="No SMS metrics on disk."
            command="python -m scripts.evaluate_sms"
          />
        )}
      </Section>

      {smsOodPer && Object.keys(smsOodPer).length > 0 && (
        <Section
          icon={Gauge}
          title="SMS — OOD per-category breakdown"
          subtitle="Ten pharma sub-scenarios, three samples each. Red cells flag categories the model struggles with — exactly the honest weak spots the thesis should cite."
        >
          <PerCategoryTable per={smsOodPer} />
        </Section>
      )}

      <Section
        icon={SplitSquareHorizontal}
        title="SMS ablation"
        subtitle="Four models, identical inputs. Answers: does fine-tuning actually buy anything over the baselines?"
      >
        {smsAblationRows.length > 0 ? (
          <>
            <AblationTable rows={smsAblationRows} />
            <FigureGrid
              figures={data.sms.figures}
              pick={[
                { key: "ablationOod", label: "Ablation — OOD pharma" },
                { key: "ablationUci", label: "Ablation — UCI" },
              ]}
            />
          </>
        ) : (
          <EmptyCard
            message="No SMS ablation on disk."
            command="python -m scripts.ablation_sms"
          />
        )}
      </Section>

      {/* ============================================================= */}
      {/* Image section                                                  */}
      {/* ============================================================= */}
      <Section
        icon={ImageIcon}
        title="Image classifier — metrics"
        subtitle={
          imageIsFinetuned
            ? "Fine-tuned ResNet-18 · val split + external held-out"
            : "Demo mode (no fine-tuned weights on disk)"
        }
      >
        {imageRows.length > 0 ? (
          <>
            <SplitTable rows={imageRows} />
            <div className="flex flex-wrap gap-2 mt-4">
              <ProvenancePill
                label="Fine-tuned"
                value={imageIsFinetuned ? "yes" : "no"}
                good={imageIsFinetuned}
              />
              <ProvenancePill
                label="Weights"
                value={asString(imageModel?.weights_path) ?? "—"}
                mono
              />
              {data.image.external && (
                <ProvenancePill
                  label="External test set"
                  value="loaded"
                  good
                />
              )}
            </div>
            <FigureGrid
              figures={data.image.figures}
              pick={[
                { key: "confusionVal", label: "Confusion — val" },
                { key: "reliabilityVal", label: "Reliability — val" },
                { key: "confusionExternal", label: "Confusion — external" },
                {
                  key: "reliabilityExternal",
                  label: "Reliability — external",
                },
              ]}
            />
          </>
        ) : (
          <EmptyCard
            message="No image metrics on disk."
            command="python -m scripts.evaluate_image"
          />
        )}
        {!data.image.external && imageRows.length > 0 && (
          <div className="mt-4 bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800">
            <div className="flex items-start gap-2">
              <Info className="w-4 h-4 shrink-0 mt-0.5" />
              <div>
                <div className="font-medium mb-0.5">
                  External held-out set not yet populated.
                </div>
                Drop images into{" "}
                <code className="font-mono">
                  backend/data/images_external/&#123;authentic,counterfeit&#125;/
                </code>{" "}
                and run{" "}
                <code className="font-mono">
                  python -m scripts.evaluate_image_external
                </code>
                . Until then only in-distribution val numbers are available.
              </div>
            </div>
          </div>
        )}
      </Section>

      <Section
        icon={SplitSquareHorizontal}
        title="Image ablation"
        subtitle="Random head vs ImageNet features + logistic regression vs full fine-tune. Same val split throughout."
      >
        {imageAblationRows.length > 0 ? (
          <>
            <AblationTable rows={imageAblationRows} />
            <FigureGrid
              figures={data.image.figures}
              pick={[{ key: "ablationVal", label: "Ablation — val" }]}
            />
          </>
        ) : (
          <EmptyCard
            message="No image ablation on disk."
            command="python -m scripts.ablation_image"
          />
        )}
      </Section>

      <div className="text-center text-xs text-gray-400 pt-2">
        Want the full write-up? See{" "}
        <Link href="/dashboard" className="text-primary hover:underline">
          the live dashboard
        </Link>{" "}
        for a single-session run, or open{" "}
        <code className="font-mono">backend/reports/SUMMARY.md</code> for the
        complete report.
      </div>
    </div>
  );
}

// Helper used by two sections — defined at end of file so section JSX reads
// top-down. Rendered pill that shows a provenance key/value with an
// optional "good" tint for confirming things like `fine-tuned: yes`.
function ProvenancePill({
  label,
  value,
  good = false,
  mono = false,
}: {
  label: string;
  value: string;
  good?: boolean;
  mono?: boolean;
}) {
  return (
    <div
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs ${
        good
          ? "bg-green-50 border-green-200 text-green-800"
          : "bg-gray-50 border-gray-200 text-gray-700"
      }`}
    >
      {good && <CheckCircle2 className="w-3.5 h-3.5" />}
      <span className="uppercase tracking-wide opacity-70">{label}</span>
      <span className={mono ? "font-mono" : "font-medium"}>{value}</span>
    </div>
  );
}

// Silence unused-symbol warnings from the optional MetricPill export that
// may be reintroduced later. Keeping it available without the linter
// complaining about the current file.
export type { EvaluationMetrics };
void MetricPill;
