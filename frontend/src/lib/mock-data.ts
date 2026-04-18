import type {
  UrlCheckResult,
  SmsCheckResult,
  ImageCheckResult,
  DashboardResult,
  EvaluationResult,
} from "./types";

function delay<T>(data: T, ms = 1200): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(data), ms));
}

export function checkUrl(_url: string): Promise<UrlCheckResult> {
  return delay({
    url: _url || "http://cheap-meds-pharmacy.xyz/buy-now",
    riskScore: 78,
    isHttps: false,
    domainAge: "47 days",
    domainAgeDays: 47,
    isGphcRegistered: false,
    whoisRegistrant: "Privacy Protected, Panama",
    virusTotalScore: 35,
    redirectCount: 3,
    flags: [
      "Domain registered less than 6 months ago",
      "Not found in GPhC register",
      "WHOIS registrant uses privacy protection",
      "3 redirect hops detected",
      "No HTTPS — connection is not encrypted",
      "Flagged by 35% of VirusTotal engines",
    ],
  });
}

export function checkSms(_text: string): Promise<SmsCheckResult> {
  const text =
    _text ||
    "URGENT: Your NHS prescription is ready. Verify your identity at bit.ly/nhs-rx to avoid cancellation. Reply STOP to opt out.";
  return delay({
    text,
    riskScore: 91,
    prediction: "scam",
    confidence: 0.94,
    limeHighlights: [
      { word: "URGENT:", weight: 0.82 },
      { word: "Your", weight: 0.05 },
      { word: "NHS", weight: -0.12 },
      { word: "prescription", weight: -0.08 },
      { word: "is", weight: 0.01 },
      { word: "ready.", weight: 0.02 },
      { word: "Verify", weight: 0.76 },
      { word: "your", weight: 0.03 },
      { word: "identity", weight: 0.41 },
      { word: "at", weight: 0.01 },
      { word: "bit.ly/nhs-rx", weight: 0.88 },
      { word: "to", weight: 0.01 },
      { word: "avoid", weight: 0.52 },
      { word: "cancellation.", weight: 0.67 },
      { word: "Reply", weight: -0.05 },
      { word: "STOP", weight: -0.03 },
      { word: "to", weight: 0.0 },
      { word: "opt", weight: -0.02 },
      { word: "out.", weight: -0.01 },
    ],
  });
}

export function checkImage(_file: File): Promise<ImageCheckResult> {
  return delay({
    riskScore: 65,
    prediction: "counterfeit",
    confidence: 0.72,
    gradCamUrl: "",
    details: [
      "Inconsistent font detected on dosage label",
      "Barcode region flagged — encoding does not match expected format",
      "Colour saturation deviates from reference packaging",
      "Batch number area shows signs of digital alteration",
    ],
  });
}

export function getEvaluation(): Promise<EvaluationResult> {
  // Mock evaluation mirrors the real backend payload shape with a
  // single representative sample per section. Numbers come from an
  // actual training run so the Results page looks plausible in
  // mock mode; they're not fabricated.
  return delay({
    generatedAt: new Date().toISOString(),
    sms: {
      metrics: {
        generated_at: new Date().toISOString(),
        model: {
          source: "models_cache/sms (mock)",
          is_finetuned: true,
          spam_idx: 1,
        },
        splits: {
          uci_heldout: {
            name: "uci_heldout",
            n: 837,
            accuracy: 0.99,
            precision: 0.991,
            recall: 0.937,
            f1: 0.963,
            ece: 0.004,
            confusion_matrix: { tp: 104, tn: 725, fp: 1, fn: 7 },
            per_category: {},
          },
          ood_pharma: {
            name: "ood_pharma",
            n: 30,
            accuracy: 0.733,
            precision: 0.667,
            recall: 0.933,
            f1: 0.778,
            ece: 0.224,
            confusion_matrix: { tp: 14, tn: 8, fp: 7, fn: 1 },
            per_category: {
              "nhs-impersonation": { n: 3, accuracy: 1.0, f1: 1.0 },
              "gp-legitimate": { n: 3, accuracy: 0.0, f1: 0.0 },
            },
          },
        },
      },
      ablation: null,
      figures: {},
    },
    image: {
      metrics: {
        model: { is_finetuned: true, weights_path: "(mock)" },
        split: { seed: 42, val_frac: 0.2, class_order: ["authentic", "counterfeit"] },
        metrics: {
          n: 135,
          accuracy: 0.993,
          precision: 0.98,
          recall: 1.0,
          f1: 0.99,
          ece: 0.018,
          confusion_matrix: { tp: 47, tn: 87, fp: 1, fn: 0 },
        },
      },
      ablation: null,
      external: null,
      figures: {},
    },
  });
}

export function getDashboard(): Promise<DashboardResult> {
  return delay({
    overallRiskScore: 82,
    urlResult: {
      url: "http://cheap-meds-pharmacy.xyz/buy-now",
      riskScore: 78,
      isHttps: false,
      domainAge: "47 days",
      domainAgeDays: 47,
      isGphcRegistered: false,
      whoisRegistrant: "Privacy Protected, Panama",
      virusTotalScore: 35,
      redirectCount: 3,
      flags: [
        "Domain registered less than 6 months ago",
        "Not found in GPhC register",
      ],
    },
    smsResult: {
      text: "URGENT: Your NHS prescription is ready. Verify your identity at bit.ly/nhs-rx to avoid cancellation.",
      riskScore: 91,
      prediction: "scam",
      confidence: 0.94,
      limeHighlights: [
        { word: "URGENT:", weight: 0.82 },
        { word: "Verify", weight: 0.76 },
        { word: "bit.ly/nhs-rx", weight: 0.88 },
      ],
    },
    imageResult: {
      riskScore: 65,
      prediction: "counterfeit",
      confidence: 0.72,
      gradCamUrl: "",
      details: ["Inconsistent font on dosage label", "Barcode region flagged"],
    },
    timestamp: new Date().toISOString(),
  });
}
