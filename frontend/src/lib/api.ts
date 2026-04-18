import type {
  UrlCheckResult,
  SmsCheckResult,
  ImageCheckResult,
  DashboardResult,
  EvaluationResult,
} from "./types";
import * as mock from "./mock-data";

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK !== "false";
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Throw a richer error for a non-OK response. Includes the endpoint,
 * status code, and as much of the response body as the server gave us —
 * essential for diagnosing 422 validation errors and 500s.
 */
async function _raise(endpoint: string, res: Response): Promise<never> {
  let body = "";
  try {
    body = await res.text();
  } catch {
    // body unreadable — fall through with what we have
  }
  const snippet = body.length > 400 ? body.slice(0, 400) + "…" : body;
  throw new Error(
    `${endpoint} ${res.status} ${res.statusText}${snippet ? `: ${snippet}` : ""}`
  );
}

export async function checkUrl(
  url: string,
  signal?: AbortSignal
): Promise<UrlCheckResult> {
  if (USE_MOCK) return mock.checkUrl(url);
  const res = await fetch(`${API_BASE}/api/v1/check-url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
    signal,
  });
  if (!res.ok) await _raise("POST /check-url", res);
  return res.json();
}

export async function checkSms(
  text: string,
  signal?: AbortSignal
): Promise<SmsCheckResult> {
  if (USE_MOCK) return mock.checkSms(text);
  const res = await fetch(`${API_BASE}/api/v1/check-sms`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
    signal,
  });
  if (!res.ok) await _raise("POST /check-sms", res);
  return res.json();
}

export async function checkImage(
  file: File,
  signal?: AbortSignal
): Promise<ImageCheckResult> {
  if (USE_MOCK) return mock.checkImage(file);
  const formData = new FormData();
  // Field name must match the backend's `file: UploadFile = File(...)` param.
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/api/v1/check-image`, {
    method: "POST",
    body: formData,
    signal,
  });
  if (!res.ok) await _raise("POST /check-image", res);
  return res.json();
}

export async function getDashboard(
  signal?: AbortSignal
): Promise<DashboardResult> {
  if (USE_MOCK) return mock.getDashboard();
  const res = await fetch(`${API_BASE}/api/v1/dashboard`, { signal });
  if (!res.ok) await _raise("GET /dashboard", res);
  return res.json();
}

/**
 * Fetch the thesis-evaluation artifacts (SMS + image metrics, ablations,
 * external held-out image results, figure URLs). Returns null sub-fields
 * when an individual report hasn't been generated yet — the Results
 * page renders a "run the eval script" nudge in that case.
 *
 * Figure URLs returned by the backend are served from /reports/... on
 * the same origin. `API_BASE` is prepended here so the Results page
 * can use them as raw <img src>.
 */
export async function getEvaluation(
  signal?: AbortSignal
): Promise<EvaluationResult> {
  if (USE_MOCK) return mock.getEvaluation();
  const res = await fetch(`${API_BASE}/api/v1/evaluation`, { signal });
  if (!res.ok) await _raise("GET /evaluation", res);
  const body = (await res.json()) as EvaluationResult;

  // The backend returns relative URLs like "/reports/sms/figures/x.png".
  // Prefix with API_BASE so <img src> points at the backend origin
  // rather than the Next.js dev server.
  const prefix = (rel?: string) => (rel ? `${API_BASE}${rel}` : rel);
  body.sms.figures = Object.fromEntries(
    Object.entries(body.sms.figures).map(([k, v]) => [k, prefix(v)])
  );
  body.image.figures = Object.fromEntries(
    Object.entries(body.image.figures).map(([k, v]) => [k, prefix(v)])
  );
  return body;
}
