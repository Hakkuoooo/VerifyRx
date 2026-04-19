import { Loader2 } from "lucide-react";

interface LoadingSpinnerProps {
  text?: string;
  align?: "left" | "center";
}

export default function LoadingSpinner({
  text = "Checking…",
  align = "left",
}: LoadingSpinnerProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={`flex items-center gap-3 py-6 text-[var(--color-ink-muted)] ${
        align === "center" ? "justify-center" : ""
      }`}
    >
      <Loader2
        className="w-4 h-4 animate-spin text-[var(--color-primary)]"
        aria-hidden
      />
      <p className="text-sm font-medium">{text}</p>
    </div>
  );
}
