// --- URL Checker ---
export interface UrlCheckResult {
  url: string;
  riskScore: number;
  isHttps: boolean;
  domainAge: string;
  domainAgeDays: number;
  isGphcRegistered: boolean;
  whoisRegistrant: string;
  virusTotalScore: number;
  redirectCount: number;
  flags: string[];
}

// --- SMS Checker ---
export interface LimeHighlight {
  word: string;
  weight: number; // -1.0 to 1.0 (positive = contributes to scam)
}

export interface SmsCheckResult {
  text: string;
  riskScore: number;
  prediction: "scam" | "legitimate";
  confidence: number;
  limeHighlights: LimeHighlight[];
}

// --- Image Checker ---
export interface ImageCheckResult {
  riskScore: number;
  prediction: "counterfeit" | "authentic";
  confidence: number;
  gradCamUrl: string;
  details: string[];
}

// --- Dashboard / Combined ---
export interface DashboardResult {
  overallRiskScore: number;
  urlResult: UrlCheckResult | null;
  smsResult: SmsCheckResult | null;
  imageResult: ImageCheckResult | null;
  timestamp: string;
}

// --- Evaluation / Results ---
// The Python eval scripts own the shape of the nested JSON, so
// `metrics` / `ablation` / `external` stay loosely typed. The Results
// page guards each access with a truthy check rather than asserting a
// schema — mirroring how the backend surfaces null when a report is
// missing.
export type EvaluationMetrics = Record<string, unknown>;

export interface EvaluationFigures {
  // SMS figures
  confusionUci?: string;
  confusionOod?: string;
  reliabilityUci?: string;
  reliabilityOod?: string;
  ablationUci?: string;
  ablationOod?: string;
  // Image figures
  confusionVal?: string;
  reliabilityVal?: string;
  ablationVal?: string;
  confusionExternal?: string;
  reliabilityExternal?: string;
}

export interface EvaluationResult {
  generatedAt: string;
  sms: {
    metrics: EvaluationMetrics | null;
    ablation: EvaluationMetrics | null;
    figures: EvaluationFigures;
  };
  image: {
    metrics: EvaluationMetrics | null;
    ablation: EvaluationMetrics | null;
    external: EvaluationMetrics | null;
    figures: EvaluationFigures;
  };
}
