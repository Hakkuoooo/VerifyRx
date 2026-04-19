export const RISK_THRESHOLDS = {
  LOW: 30,
  MEDIUM: 60,
  HIGH: 100,
} as const;

// Palette matches the new ink/surface/action system in globals.css.
// Deeper, less saturated than default Tailwind so the results panel
// reads as a public-service page rather than a traffic-light demo.
export const RISK_COLORS = {
  low: { bg: "#e6f4ec", text: "#005a38", ring: "#00784a", border: "#9ed2b8" },
  medium: { bg: "#fff4e5", text: "#6b3a00", ring: "#8a4b00", border: "#e6c28c" },
  high: { bg: "#fbe9e7", text: "#8a1d17", ring: "#b3261e", border: "#e6a39c" },
} as const;

export const MODULE_WEIGHTS = {
  url: 0.3,
  sms: 0.35,
  image: 0.35,
} as const;
