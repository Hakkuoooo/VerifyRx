"use client";

import { getRiskColor, getRiskLabel } from "@/lib/utils";

interface RiskScoreGaugeProps {
  score: number;
  size?: "sm" | "md" | "lg";
}

const sizes = {
  sm: { dim: 80, stroke: 6, fontSize: 18, labelSize: 8 },
  md: { dim: 120, stroke: 8, fontSize: 28, labelSize: 11 },
  lg: { dim: 180, stroke: 10, fontSize: 42, labelSize: 14 },
};

export default function RiskScoreGauge({
  score,
  size = "md",
}: RiskScoreGaugeProps) {
  const { dim, stroke, fontSize, labelSize } = sizes[size];
  const color = getRiskColor(score);
  const label = getRiskLabel(score);

  const clampedScore = Math.min(Math.max(score, 0), 100);
  const radius = (dim - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = clampedScore / 100;
  const offset = circumference * (1 - progress);

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={dim} height={dim} className="-rotate-90">
        {/* Background track */}
        <circle
          cx={dim / 2}
          cy={dim / 2}
          r={radius}
          fill="none"
          stroke="#E5E7EB"
          strokeWidth={stroke}
        />
        {/* Colored arc */}
        <circle
          cx={dim / 2}
          cy={dim / 2}
          r={radius}
          fill="none"
          stroke={color.ring}
          strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-700 ease-out"
        />
        {/* Score text */}
        <text
          x={dim / 2}
          y={dim / 2}
          textAnchor="middle"
          dominantBaseline="central"
          fill={color.text}
          fontSize={fontSize}
          fontWeight="700"
          className="rotate-90"
          style={{ transformOrigin: "center" }}
        >
          {clampedScore}
        </text>
      </svg>
      <span
        className="font-semibold rounded-full px-2.5 py-0.5"
        style={{
          fontSize: labelSize,
          color: color.text,
          backgroundColor: color.bg,
        }}
      >
        {label}
      </span>
    </div>
  );
}
