import type { ReactNode } from "react";

interface ResultCardProps {
  title: string;
  value: string | ReactNode;
  status: "pass" | "warn" | "fail";
  icon?: ReactNode;
}

// Horizontal status bar on the left + label/value stack — matches the
// GOV.UK "summary list" pattern but with a RAG indicator. The status
// colour is carried by a 3px left border, not a shadow or card.
const statusStyle: Record<ResultCardProps["status"], { bar: string; label: string }> = {
  pass: { bar: "bg-[var(--color-success)]", label: "text-[var(--color-success)]" },
  warn: { bar: "bg-[var(--color-warning)]", label: "text-[var(--color-warning)]" },
  fail: { bar: "bg-[var(--color-danger)]", label: "text-[var(--color-danger)]" },
};

const statusWord: Record<ResultCardProps["status"], string> = {
  pass: "Pass",
  warn: "Caution",
  fail: "Fail",
};

export default function ResultCard({
  title,
  value,
  status,
  icon,
}: ResultCardProps) {
  const s = statusStyle[status];
  return (
    <div className="relative bg-white border border-[var(--color-line)] pl-4 pr-4 py-3 flex flex-col gap-1">
      <span className={`absolute inset-y-0 left-0 w-[3px] ${s.bar}`} aria-hidden />
      <div className="flex items-center justify-between gap-2">
        <span className="text-[12px] uppercase tracking-[0.08em] text-[var(--color-ink-faint)] font-semibold">
          {title}
        </span>
        <span className={`text-[11px] font-semibold uppercase tracking-wide ${s.label}`}>
          {statusWord[status]}
        </span>
      </div>
      <div className="flex items-center gap-2 mt-0.5">
        {icon && (
          <span className="text-[var(--color-ink-muted)]" aria-hidden>
            {icon}
          </span>
        )}
        <span className="text-[15px] font-semibold text-[var(--color-ink)] leading-snug">
          {value}
        </span>
      </div>
    </div>
  );
}
