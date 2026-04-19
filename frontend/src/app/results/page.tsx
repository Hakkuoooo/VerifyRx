"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import type { EvaluationResult, EvaluationFigures } from "@/lib/types";
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
// Presentational primitives — all flat, no shadows, no rounded-xl. Matches
// the rest of the app's NHS/GOV.UK-adjacent design system.
// ---------------------------------------------------------------------------
function Section({
  eyebrow,
  title,
  subtitle,
  children,
}: {
  eyebrow: string;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="bg-white border border-[var(--color-line)] p-5 md:p-6">
      <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-[var(--color-primary)]">
        {eyebrow}
      </p>
      <h2 className="mt-1 text-xl font-semibold text-[var(--color-ink)] tracking-tight">
        {title}
      </h2>
      {subtitle && (
        <p className="mt-1 text-[14px] text-[var(--color-ink-muted)] leading-relaxed max-w-3xl">
          {subtitle}
        </p>
      )}
      <div className="mt-5">{children}</div>
    </section>
  );
}

function EmptyCard({ message, command }: { message: string; command: string }) {
  return (
    <div className="border-l-[3px] border-[var(--color-warning)] bg-[var(--color-warning-light)] p-4 text-sm text-[var(--color-ink)]">
      <p className="font-semibold">{message}</p>
      <code className="block mt-2 px-2 py-1 bg-white border border-[var(--color-line)] text-[12px] font-mono text-[var(--color-ink)]">
        {command}
      </code>
    </div>
  );
}

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
      className={`inline-flex items-center gap-2 px-2.5 py-1 border text-[12px] ${
        good
          ? "bg-[var(--color-success-light)] border-[#9ed2b8] text-[var(--color-success)]"
          : "bg-[var(--color-canvas)] border-[var(--color-line)] text-[var(--color-ink)]"
      }`}
    >
      <span className="uppercase tracking-[0.08em] opacity-80">{label}</span>
      <span className={mono ? "font-mono" : "font-semibold"}>{value}</span>
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
          <tr className="text-[11px] uppercase tracking-wider text-[var(--color-ink-faint)] border-b border-[var(--color-line-strong)]">
            <th className="text-left py-2.5 pr-4 font-semibold">Split</th>
            <th className="text-right py-2.5 px-2 font-semibold">n</th>
            <th className="text-right py-2.5 px-2 font-semibold">Accuracy</th>
            <th className="text-right py-2.5 px-2 font-semibold">Precision</th>
            <th className="text-right py-2.5 px-2 font-semibold">Recall</th>
            <th className="text-right py-2.5 px-2 font-semibold">F1</th>
            <th className="text-right py-2.5 px-2 font-semibold">ECE</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr
              key={r.name}
              className="border-b border-[var(--color-line)] last:border-b-0"
            >
              <td className="py-2.5 pr-4 font-semibold text-[var(--color-ink)]">
                {r.name}
              </td>
              <td className="py-2.5 px-2 text-right tabular-nums text-[var(--color-ink-muted)]">
                {fmtInt(r.n)}
              </td>
              <td className="py-2.5 px-2 text-right tabular-nums text-[var(--color-ink)]">
                {fmt(r.accuracy)}
              </td>
              <td className="py-2.5 px-2 text-right tabular-nums text-[var(--color-ink)]">
                {fmt(r.precision)}
              </td>
              <td className="py-2.5 px-2 text-right tabular-nums text-[var(--color-ink)]">
                {fmt(r.recall)}
              </td>
              <td className="py-2.5 px-2 text-right tabular-nums text-[var(--color-ink)]">
                {fmt(r.f1)}
              </td>
              <td className="py-2.5 px-2 text-right tabular-nums text-[var(--color-ink)]">
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
  const hasSplit = normalised.some((r) => r.split);
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-[11px] uppercase tracking-wider text-[var(--color-ink-faint)] border-b border-[var(--color-line-strong)]">
            <th className="text-left py-2.5 pr-4 font-semibold">Model</th>
            {hasSplit && (
              <th className="text-left py-2.5 px-2 font-semibold">Split</th>
            )}
            <th className="text-right py-2.5 px-2 font-semibold">n</th>
            <th className="text-right py-2.5 px-2 font-semibold">Accuracy</th>
            <th className="text-right py-2.5 px-2 font-semibold">Precision</th>
            <th className="text-right py-2.5 px-2 font-semibold">Recall</th>
            <th className="text-right py-2.5 px-2 font-semibold">F1</th>
          </tr>
        </thead>
        <tbody>
          {normalised.map((r, i) => (
            <tr
              key={`${r.model}-${r.split ?? i}`}
              className="border-b border-[var(--color-line)] last:border-b-0"
            >
              <td className="py-2.5 pr-4 font-semibold text-[var(--color-ink)]">
                {r.model}
              </td>
              {hasSplit && (
                <td className="py-2.5 px-2 text-[var(--color-ink-muted)]">
                  {r.split ?? "—"}
                </td>
              )}
              <td className="py-2.5 px-2 text-right tabular-nums text-[var(--color-ink-muted)]">
                {fmtInt(r.n)}
              </td>
              <td className="py-2.5 px-2 text-right tabular-nums text-[var(--color-ink)]">
                {fmt(r.accuracy)}
              </td>
              <td className="py-2.5 px-2 text-right tabular-nums text-[var(--color-ink)]">
                {fmt(r.precision)}
              </td>
              <td className="py-2.5 px-2 text-right tabular-nums text-[var(--color-ink)]">
                {fmt(r.recall)}
              </td>
              <td className="py-2.5 px-2 text-right tabular-nums text-[var(--color-ink)]">
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
          <tr className="text-[11px] uppercase tracking-wider text-[var(--color-ink-faint)] border-b border-[var(--color-line-strong)]">
            <th className="text-left py-2.5 pr-4 font-semibold">Category</th>
            <th className="text-right py-2.5 px-2 font-semibold">n</th>
            <th className="text-right py-2.5 px-2 font-semibold">Accuracy</th>
            <th className="text-right py-2.5 px-2 font-semibold">F1</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e) => (
            <tr
              key={e.cat}
              className="border-b border-[var(--color-line)] last:border-b-0"
            >
              <td className="py-2.5 pr-4 font-mono text-[var(--color-ink)] text-[13px]">
                {e.cat}
              </td>
              <td className="py-2.5 px-2 text-right tabular-nums text-[var(--color-ink-muted)]">
                {fmtInt(e.n)}
              </td>
              <td
                className={`py-2.5 px-2 text-right tabular-nums font-semibold ${
                  (e.accuracy ?? 1) < 0.5
                    ? "text-[var(--color-danger)]"
                    : (e.accuracy ?? 1) < 1
                      ? "text-[var(--color-warning)]"
                      : "text-[var(--color-success)]"
                }`}
              >
                {fmt(e.accuracy)}
              </td>
              <td className="py-2.5 px-2 text-right tabular-nums text-[var(--color-ink)]">
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
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6">
      {available.map((f) => (
        <figure
          key={f.key}
          className="border border-[var(--color-line)] bg-[var(--color-canvas)] p-3"
        >
          <Image
            src={f.url}
            alt={f.label}
            width={640}
            height={480}
            unoptimized
            className="w-full h-auto bg-white"
          />
          <figcaption className="text-[12px] text-[var(--color-ink-muted)] mt-2 text-center">
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
      <div className="max-w-5xl mx-auto px-4 py-10 md:py-14">
        <div className="h-4 w-32 bg-[var(--color-line)] animate-pulse mb-4" />
        <div className="h-8 w-72 bg-[var(--color-line)] animate-pulse mb-6" />
        <div className="h-40 bg-white border border-[var(--color-line)] animate-pulse" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-10 md:py-14">
        <p className="text-[12px] font-semibold tracking-[0.1em] uppercase text-[var(--color-warning)]">
          Methodology
        </p>
        <h1 className="display mt-2 text-[32px] font-semibold text-[var(--color-ink)]">
          Evaluation report not available.
        </h1>
        <p className="mt-3 text-[15px] text-[var(--color-ink-muted)] leading-relaxed">
          The backend didn&apos;t return an evaluation payload. Usually this
          means the evaluation scripts haven&apos;t been run yet.
        </p>
        {error && (
          <pre className="mt-4 text-xs text-[var(--color-ink-muted)] bg-white border border-[var(--color-line)] p-3 overflow-auto">
            {error}
          </pre>
        )}
        <code className="block mt-4 px-3 py-2 bg-white border border-[var(--color-line)] text-[13px] font-mono text-[var(--color-ink)]">
          cd backend && python -m scripts.generate_evaluation_report
        </code>
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
    <div className="max-w-5xl mx-auto px-4 py-10 md:py-14">
      {/* ─── Page header ─── */}
      <p className="text-[12px] font-semibold tracking-[0.1em] uppercase text-[var(--color-primary)]">
        Methodology
      </p>
      <h1 className="display mt-2 text-[32px] md:text-[40px] font-semibold text-[var(--color-ink)]">
        How we evaluate our models.
      </h1>
      <p className="mt-3 text-[17px] text-[var(--color-ink-muted)] leading-relaxed max-w-3xl">
        Live metrics, calibration diagrams, ablation studies and the
        external held-out test — straight from{" "}
        <code className="font-mono text-[15px] bg-[var(--color-canvas)] border border-[var(--color-line)] px-1">
          backend/reports/
        </code>
        . Nothing here is fabricated; every figure is regenerated from
        disk on the last training run.
      </p>
      <p className="mt-3 text-[13px] text-[var(--color-ink-faint)]">
        Generated{" "}
        {new Date(data.generatedAt).toLocaleString(undefined, {
          dateStyle: "medium",
          timeStyle: "short",
        })}
        . Regenerate:{" "}
        <code className="font-mono bg-[var(--color-canvas)] border border-[var(--color-line)] px-1">
          python -m scripts.generate_evaluation_report
        </code>
      </p>

      <div className="mt-10 space-y-6">
        {/* SMS section */}
        <Section
          eyebrow="Text classifier"
          title="SMS — DistilBERT fine-tune"
          subtitle={
            smsIsFinetuned
              ? "In-distribution (UCI spam) and out-of-distribution (UK pharma) evaluation on the fine-tuned DistilBERT model."
              : "Pretrained fallback — no local fine-tune detected."
          }
        >
          {smsRows.length > 0 ? (
            <>
              <SplitTable rows={smsRows} />
              <div className="flex flex-wrap gap-2 mt-5">
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
                  { key: "confusionUci", label: "Confusion — UCI held-out" },
                  { key: "confusionOod", label: "Confusion — OOD pharma" },
                  { key: "reliabilityUci", label: "Reliability — UCI held-out" },
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
            eyebrow="Failure analysis"
            title="SMS — OOD per-category breakdown"
            subtitle="Ten UK pharma sub-scenarios, three samples each. Red cells show the categories the model struggles on — the honest weak spots."
          >
            <PerCategoryTable per={smsOodPer} />
          </Section>
        )}

        <Section
          eyebrow="Ablation"
          title="SMS — does fine-tuning help?"
          subtitle="Four models, identical inputs. Answers whether the DistilBERT fine-tune actually beats the baselines on both splits."
        >
          {smsAblationRows.length > 0 ? (
            <>
              <AblationTable rows={smsAblationRows} />
              <FigureGrid
                figures={data.sms.figures}
                pick={[
                  { key: "ablationOod", label: "Ablation — OOD pharma" },
                  { key: "ablationUci", label: "Ablation — UCI held-out" },
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

        {/* Image section */}
        <Section
          eyebrow="Vision classifier"
          title="Image — ResNet-18 fine-tune"
          subtitle={
            imageIsFinetuned
              ? "Validation split plus an external held-out set kept strictly separate from training."
              : "Demo mode — no fine-tuned weights on disk."
          }
        >
          {imageRows.length > 0 ? (
            <>
              <SplitTable rows={imageRows} />
              <div className="flex flex-wrap gap-2 mt-5">
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
            <div className="mt-5 border-l-[3px] border-[var(--color-warning)] bg-[var(--color-warning-light)] p-4 text-[13px] text-[var(--color-ink)]">
              <p className="font-semibold">
                External held-out set not yet populated.
              </p>
              <p className="mt-1 leading-relaxed">
                Drop images into{" "}
                <code className="font-mono">
                  backend/data/images_external/&#123;authentic,counterfeit&#125;/
                </code>{" "}
                and run{" "}
                <code className="font-mono">
                  python -m scripts.evaluate_image_external
                </code>
                . Until then only in-distribution val numbers are available.
              </p>
            </div>
          )}
        </Section>

        <Section
          eyebrow="Ablation"
          title="Image — how much does fine-tuning buy us?"
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
      </div>

      <p className="mt-10 text-[13px] text-[var(--color-ink-faint)]">
        For a single-session run of all three checkers, open{" "}
        <Link href="/dashboard" className="prose-link">
          My checks
        </Link>
        . The complete machine-readable report lives in{" "}
        <code className="font-mono bg-[var(--color-canvas)] border border-[var(--color-line)] px-1">
          backend/reports/SUMMARY.md
        </code>
        .
      </p>
    </div>
  );
}
