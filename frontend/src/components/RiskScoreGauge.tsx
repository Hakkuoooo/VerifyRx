"use client";

import { getRiskColor, getRiskLabel } from "@/lib/utils";

interface RiskScoreGaugeProps {
  score: number;
  size?: "sm" | "md" | "lg";
}

// Kept a ring gauge because it's the one visual that makes the risk
// score legible at a glance (precedent: Scamadviser, Truecaller,
// FCA ScamSmart). Palette was tightened in constants.ts so it no
// longer reads as a Tailwind demo.
const sizes = {
  sm: { dim: 80, stroke: 6, fontSize: 18, labelSize: 9 },
  md: { dim: 120, stroke: 8, fontSize: 28, labelSize: 11 },
  lg: { dim: 160, stroke: 10, fontSize: 40, labelSize: 12 },
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
    <div className="flex flex-col items-center gap-2">
      <svg
        width={dim}
        height={dim}
        className="-rotate-90"
        role="img"
        aria-label={`Risk score ${clampedScore} out of 100, ${label}`}
      >
        {/* Background track — very faint, doesn't compete with the arc */}
        <circle
          cx={dim / 2}
          cy={dim / 2}
          r={radius}
          fill="none"
          stroke="#eceef2"
          strokeWidth={stroke}
        />
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
        <text
          x={dim / 2}
          y={dim / 2}
          textAnchor="middle"
          dominantBaseline="central"
          fill="var(--color-ink)"
          fontSize={fontSize}
          fontWeight="600"
          className="rotate-90"
          style={{
            transformOrigin: "center",
            letterSpacing: "-0.02em",
          }}
        >
          {clampedScore}
        </text>
      </svg>
      <span
        className="font-semibold uppercase tracking-[0.08em] px-2 py-0.5"
        style={{
          fontSize: labelSize,
          color: color.text,
          backgroundColor: color.bg,
          border: `1px solid ${color.border}`,
        }}
      >
        {label}
      </span>
    </div>
  );
}
