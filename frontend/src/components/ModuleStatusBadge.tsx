import { getRiskLevel } from "@/lib/utils";

interface ModuleStatusBadgeProps {
  label: string;
  score: number | null;
}

export default function ModuleStatusBadge({
  label,
  score,
}: ModuleStatusBadgeProps) {
  if (score === null) {
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-400">
        <span className="w-1.5 h-1.5 rounded-full bg-gray-300" />
        {label} — Not checked
      </span>
    );
  }

  const level = getRiskLevel(score);
  const styles = {
    low: "bg-green-50 text-green-700",
    medium: "bg-yellow-50 text-yellow-700",
    high: "bg-red-50 text-red-700",
  };
  const dotStyles = {
    low: "bg-green-500",
    medium: "bg-yellow-500",
    high: "bg-red-500",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${styles[level]}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dotStyles[level]}`} />
      {label} — {score}/100
    </span>
  );
}
