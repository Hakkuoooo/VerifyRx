import type { ReactNode } from "react";

interface ResultCardProps {
  title: string;
  value: string | ReactNode;
  status: "pass" | "warn" | "fail";
  icon?: ReactNode;
}

const statusColors = {
  pass: "bg-green-500",
  warn: "bg-yellow-500",
  fail: "bg-red-500",
};

export default function ResultCard({
  title,
  value,
  status,
  icon,
}: ResultCardProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500 font-medium">{title}</span>
        <span
          className={`w-2.5 h-2.5 rounded-full ${statusColors[status]}`}
        />
      </div>
      <div className="flex items-center gap-2">
        {icon && <span className="text-gray-400">{icon}</span>}
        <span className="text-lg font-semibold text-gray-900">{value}</span>
      </div>
    </div>
  );
}
