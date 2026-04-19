"use client";

import { useState } from "react";
import type { LimeHighlight } from "@/lib/types";

interface LimePanelProps {
  type: "lime";
  limeHighlights: LimeHighlight[];
}

interface GradCamPanelProps {
  type: "gradcam";
  gradCamUrl: string;
  originalImageUrl: string;
}

type ExplainabilityPanelProps = LimePanelProps | GradCamPanelProps;

// Ochre/teal highlight palette tuned to match the rest of the UI —
// no bright Tailwind red/green from the earlier demo version.
function getHighlightColor(weight: number): string {
  if (weight > 0.3) {
    const opacity = Math.min(weight, 1) * 0.55 + 0.1;
    return `rgba(179, 38, 30, ${opacity})`;
  }
  if (weight < -0.1) {
    const opacity = Math.min(Math.abs(weight), 1) * 0.55 + 0.1;
    return `rgba(0, 120, 74, ${opacity})`;
  }
  return "transparent";
}

export default function ExplainabilityPanel(props: ExplainabilityPanelProps) {
  const [opacity, setOpacity] = useState(0.5);

  if (props.type === "lime") {
    return (
      <div className="bg-white border border-[var(--color-line)] p-5">
        <p className="text-[12px] font-semibold uppercase tracking-[0.08em] text-[var(--color-ink-faint)] mb-3">
          Why the model flagged this text
        </p>
        <div className="leading-8 text-[15px] text-[var(--color-ink)]">
          {props.limeHighlights.map((h, i) => (
            <span
              key={i}
              className="px-0.5 py-0.5 mx-0.5"
              style={{ backgroundColor: getHighlightColor(h.weight) }}
              title={`Contribution weight: ${h.weight.toFixed(2)}`}
            >
              {h.word}
            </span>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2 mt-4 text-[12px] text-[var(--color-ink-muted)]">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 bg-[rgba(179,38,30,0.55)]" aria-hidden />
            Pushes toward scam
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 bg-[rgba(0,120,74,0.55)]" aria-hidden />
            Pushes toward legitimate
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 border border-[var(--color-line)]" aria-hidden />
            Neutral
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-[var(--color-line)] p-5">
      <p className="text-[12px] font-semibold uppercase tracking-[0.08em] text-[var(--color-ink-faint)] mb-3">
        Where the model looked on the pack
      </p>
      {props.gradCamUrl ? (
        <>
          <div className="relative inline-block overflow-hidden bg-[var(--color-canvas)]">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={props.originalImageUrl}
              alt="Original pack photo"
              className="max-h-80 object-contain"
            />
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={props.gradCamUrl}
              alt="Grad-CAM heatmap overlay"
              className="absolute inset-0 w-full h-full object-contain pointer-events-none"
              style={{ opacity }}
            />
          </div>
          <div className="mt-4 flex items-center gap-3">
            <label
              htmlFor="gradcam-opacity"
              className="text-[12px] text-[var(--color-ink-muted)] font-medium"
            >
              Heatmap opacity
            </label>
            <input
              id="gradcam-opacity"
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={opacity}
              onChange={(e) => setOpacity(parseFloat(e.target.value))}
              className="w-40 accent-[var(--color-primary)]"
            />
            <span className="text-[12px] text-[var(--color-ink-faint)] font-mono">
              {Math.round(opacity * 100)}%
            </span>
          </div>
        </>
      ) : (
        <div className="flex items-center justify-center h-48 bg-[var(--color-canvas)]">
          <p className="text-sm text-[var(--color-ink-faint)]">
            Heatmap will appear here once the check completes.
          </p>
        </div>
      )}
    </div>
  );
}
