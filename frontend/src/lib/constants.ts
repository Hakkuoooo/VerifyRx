export const RISK_THRESHOLDS = {
  LOW: 30,
  MEDIUM: 60,
  HIGH: 100,
} as const;

export const RISK_COLORS = {
  low: { bg: "#DCFCE7", text: "#166534", ring: "#22C55E" },
  medium: { bg: "#FEF9C3", text: "#854D0E", ring: "#EAB308" },
  high: { bg: "#FEE2E2", text: "#991B1B", ring: "#EF4444" },
} as const;

export const MODULE_WEIGHTS = {
  url: 0.3,
  sms: 0.35,
  image: 0.35,
} as const;
