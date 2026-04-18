import { RISK_THRESHOLDS, RISK_COLORS } from "./constants";

export type RiskLevel = "low" | "medium" | "high";

export function getRiskLevel(score: number): RiskLevel {
  if (score <= RISK_THRESHOLDS.LOW) return "low";
  if (score <= RISK_THRESHOLDS.MEDIUM) return "medium";
  return "high";
}

export function getRiskColor(score: number) {
  return RISK_COLORS[getRiskLevel(score)];
}

export function getRiskLabel(score: number): string {
  const level = getRiskLevel(score);
  if (level === "low") return "Low Risk";
  if (level === "medium") return "Medium Risk";
  return "High Risk";
}
