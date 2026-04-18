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

function getHighlightColor(weight: number): string {
  if (weight > 0.3) {
    const opacity = Math.min(weight, 1) * 0.5 + 0.1;
    return `rgba(239, 68, 68, ${opacity})`; // red
  }
  if (weight < -0.1) {
    const opacity = Math.min(Math.abs(weight), 1) * 0.5 + 0.1;
    return `rgba(34, 197, 94, ${opacity})`; // green
  }
  return "transparent";
}

export default function ExplainabilityPanel(props: ExplainabilityPanelProps) {
  const [opacity, setOpacity] = useState(0.5);

  if (props.type === "lime") {
    return (
      <div className="bg-white rounded-xl border border-gray-100 p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">
          LIME Explanation — Word Contributions
        </h3>
        <div className="leading-8 text-base">
          {props.limeHighlights.map((h, i) => (
            <span
              key={i}
              className="rounded px-0.5 py-0.5 mx-0.5"
              style={{ backgroundColor: getHighlightColor(h.weight) }}
              title={`Weight: ${h.weight.toFixed(2)}`}
            >
              {h.word}
            </span>
          ))}
        </div>
        <div className="flex items-center gap-4 mt-4 text-xs text-gray-500">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-red-400/60" />
            Contributes to scam
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-green-400/60" />
            Contributes to legitimate
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-gray-100" />
            Neutral
          </div>
        </div>
      </div>
    );
  }

  // Grad-CAM mode
  return (
    <div className="bg-white rounded-xl border border-gray-100 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">
        Grad-CAM Heatmap — Region Contributions
      </h3>
      {props.gradCamUrl ? (
        <>
          <div className="relative inline-block rounded-lg overflow-hidden">
            <img
              src={props.originalImageUrl}
              alt="Original"
              className="max-h-64 object-contain"
            />
            <img
              src={props.gradCamUrl}
              alt="Grad-CAM overlay"
              className="absolute inset-0 w-full h-full object-contain"
              style={{ opacity }}
            />
          </div>
          <div className="mt-3 flex items-center gap-3">
            <label className="text-xs text-gray-500">Overlay opacity:</label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={opacity}
              onChange={(e) => setOpacity(parseFloat(e.target.value))}
              className="w-32"
            />
            <span className="text-xs text-gray-400">
              {Math.round(opacity * 100)}%
            </span>
          </div>
        </>
      ) : (
        <div className="flex items-center justify-center h-48 bg-gray-50 rounded-lg">
          <p className="text-sm text-gray-400">
            Grad-CAM heatmap will appear here when connected to the backend
          </p>
        </div>
      )}
    </div>
  );
}
