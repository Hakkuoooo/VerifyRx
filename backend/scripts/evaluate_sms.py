"""
Full SMS-classifier evaluation harness (thesis-grade).

Produces, for the currently loaded SMS model:
  1. UCI SMS Spam Collection held-out split metrics (in-distribution,
     reconstructed with the same seed=42 / test_size=0.15 as train_sms.py).
  2. Out-of-distribution metrics on the 30 hand-curated pharma samples
     in scripts/evaluate_sms_ood.py (EVAL_SET).
  3. Expected Calibration Error (ECE) on both splits.
  4. Confusion-matrix PNGs and reliability-diagram PNGs for each split.
  5. A per-category breakdown of the OOD split.
  6. A machine-readable metrics.json bundling everything.

Artifacts land in backend/reports/sms/:
    metrics.json
    figures/
        confusion_uci.png
        confusion_ood.png
        reliability_uci.png
        reliability_ood.png

Usage:
    cd backend
    python -m scripts.evaluate_sms
    python -m scripts.evaluate_sms --uci-only    # skip OOD
    python -m scripts.evaluate_sms --ood-only    # skip UCI (fast)
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import matplotlib

# Agg backend: evaluation runs headless (CI, SSH, student laptop
# without a display session). Must be set before importing pyplot.
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from datasets import load_dataset

from scripts.evaluate_sms_ood import EVAL_SET, Sample

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BACKEND_DIR / "reports" / "sms"
FIGURES_DIR = REPORTS_DIR / "figures"

# Must match train_sms.py so we reconstruct the *same* held-out split.
UCI_SEED = 42
UCI_TEST_SIZE = 0.15


# ---------------------------------------------------------------------------
# Metric primitives
# ---------------------------------------------------------------------------
@dataclass
class SplitMetrics:
    name: str
    n: int
    accuracy: float
    precision: float
    recall: float
    f1: float
    ece: float
    tp: int
    tn: int
    fp: int
    fn: int
    # Per-category breakdown, only populated for splits that carry
    # categories (e.g. OOD). UCI rows have no category metadata.
    per_category: dict[str, dict[str, float | int]]

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "n": self.n,
            "accuracy": round(self.accuracy, 4),
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "ece": round(self.ece, 4),
            "confusion_matrix": {
                "tp": self.tp, "tn": self.tn, "fp": self.fp, "fn": self.fn
            },
            "per_category": self.per_category,
        }


def _confusion(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[int, int, int, int]:
    """Return (tp, tn, fp, fn). Convention: 1 = scam (positive)."""
    tp = int(((y_pred == 1) & (y_true == 1)).sum())
    tn = int(((y_pred == 0) & (y_true == 0)).sum())
    fp = int(((y_pred == 1) & (y_true == 0)).sum())
    fn = int(((y_pred == 0) & (y_true == 1)).sum())
    return tp, tn, fp, fn


def _safe_div(num: float, den: float) -> float:
    return float(num / den) if den else 0.0


def _metrics_from_confusion(tp: int, tn: int, fp: int, fn: int) -> tuple[float, float, float, float]:
    total = tp + tn + fp + fn
    accuracy = _safe_div(tp + tn, total)
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)
    return accuracy, precision, recall, f1


def _expected_calibration_error(
    probs_pos: np.ndarray, y_true: np.ndarray, n_bins: int = 10
) -> tuple[float, list[dict]]:
    """
    Expected Calibration Error with equal-width bins on the **predicted
    class confidence** (Guo et al. 2017). Returns (ECE, per-bin diagnostics).

    ECE = Σ_b (|B_b| / N) · | acc(B_b) − conf(B_b) |

    Definitions:
      conf_i = max(p_scam_i, 1 − p_scam_i)   — probability of the predicted
                                               class, always in [0.5, 1.0].
      acc(B_b) = fraction in bin B_b where pred == label.
      conf(B_b) = mean conf_i in bin B_b.

    Binning ON THE POSITIVE probability would conflate "confidently ham"
    with "uncertainly spam" and produce a meaningless ECE (e.g. 0.87 for
    a 99%-accurate model). That was the previous bug.
    """
    y_pred = (probs_pos >= 0.5).astype(int)
    confidence = np.maximum(probs_pos, 1.0 - probs_pos)  # in [0.5, 1.0]
    correct = (y_pred == y_true).astype(float)

    # Confidence is max-prob, so it lives in [0.5, 1.0]. Bin there.
    edges = np.linspace(0.5, 1.0, n_bins + 1)
    ece = 0.0
    n = len(probs_pos)
    bins: list[dict] = []
    for b in range(n_bins):
        lo, hi = edges[b], edges[b + 1]
        if b == n_bins - 1:
            mask = (confidence >= lo) & (confidence <= hi)
        else:
            mask = (confidence >= lo) & (confidence < hi)
        count = int(mask.sum())
        if count == 0:
            bins.append({
                "lo": round(float(lo), 3),
                "hi": round(float(hi), 3),
                "count": 0,
                "mean_conf": 0.0,
                "accuracy": 0.0,
            })
            continue
        mean_conf = float(confidence[mask].mean())
        acc_b = float(correct[mask].mean())
        ece += (count / n) * abs(acc_b - mean_conf)
        bins.append({
            "lo": round(float(lo), 3),
            "hi": round(float(hi), 3),
            "count": count,
            "mean_conf": round(mean_conf, 4),
            "accuracy": round(acc_b, 4),
        })
    return float(ece), bins


# ---------------------------------------------------------------------------
# Split loaders
# ---------------------------------------------------------------------------
def _load_uci_heldout() -> tuple[list[str], np.ndarray]:
    """Recreate the exact held-out split train_sms.py evaluates on."""
    raw = load_dataset("sms_spam", split="train")
    split = raw.train_test_split(test_size=UCI_TEST_SIZE, seed=UCI_SEED)
    eval_ds = split["test"]
    texts = list(eval_ds["sms"])
    labels = np.asarray(eval_ds["label"], dtype=int)  # 1 = spam, 0 = ham
    return texts, labels


def _ood_texts_labels(samples: Iterable[Sample]) -> tuple[list[str], np.ndarray, list[str]]:
    texts, labels, cats = [], [], []
    for s in samples:
        texts.append(s.text)
        labels.append(1 if s.label == "scam" else 0)
        cats.append(s.category)
    return texts, np.asarray(labels, dtype=int), cats


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------
def _batched_predict(texts: list[str], batch_size: int = 32) -> np.ndarray:
    """
    Return scam probabilities (shape (N,)) using the loaded SMS model.
    Imported here (not at module top) so this script can be parsed
    without loading ~250MB of model weights.
    """
    from services import sms_classifier

    out = np.empty(len(texts), dtype=float)
    for i in range(0, len(texts), batch_size):
        chunk = texts[i : i + batch_size]
        probs = sms_classifier.predict_proba(chunk)  # (b, 2), col 1 = scam
        out[i : i + batch_size] = probs[:, 1]
    return out


# ---------------------------------------------------------------------------
# Figure helpers
# ---------------------------------------------------------------------------
def _plot_confusion(tp: int, tn: int, fp: int, fn: int, title: str, path: Path) -> None:
    # Row = ground truth, column = prediction. Convention matches
    # evaluate_sms_ood.py's text output so the thesis figures line up
    # with the sanity-check print.
    matrix = np.array([[tp, fn], [fp, tn]], dtype=int)

    fig, ax = plt.subplots(figsize=(4.2, 3.6))
    im = ax.imshow(matrix, cmap="Blues")
    ax.set_xticks([0, 1], labels=["pred=scam", "pred=legit"])
    ax.set_yticks([0, 1], labels=["gt=scam", "gt=legit"])
    ax.set_title(title)
    for i in range(2):
        for j in range(2):
            v = matrix[i, j]
            # Pick text colour that stays readable against the cell fill.
            colour = "white" if v > matrix.max() / 2 else "black"
            ax.text(j, i, str(v), ha="center", va="center", color=colour, fontsize=14)
    fig.colorbar(im, ax=ax, shrink=0.75)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _plot_reliability(bins: list[dict], ece: float, title: str, path: Path) -> None:
    """Reliability diagram: bar = observed accuracy, dashed line = perfect calibration.

    X-axis is predicted-class confidence, which by construction ∈ [0.5, 1.0].
    """
    centres = np.array([(b["lo"] + b["hi"]) / 2 for b in bins])
    accs = np.array([b["accuracy"] for b in bins])
    counts = np.array([b["count"] for b in bins])

    fig, ax = plt.subplots(figsize=(5.0, 3.8))
    bin_width = 0.5 / len(bins)
    ax.bar(
        centres, accs, width=bin_width * 0.9,
        edgecolor="black", color="#4c9be8",
        label="observed accuracy",
    )
    ax.plot([0.5, 1.0], [0.5, 1.0], linestyle="--", color="black",
            label="perfect calibration")
    ax.set_xlim(0.5, 1.0)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("predicted-class confidence  max(p, 1−p)")
    ax.set_ylabel("observed accuracy")
    ax.set_title(f"{title}  (ECE = {ece:.3f})")
    # Mark empty bins so the distribution of confidence is visible.
    for c, cnt in zip(centres, counts):
        if cnt == 0:
            ax.text(c, 0.02, "0", ha="center", va="bottom", fontsize=7, color="grey")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def _evaluate_split(
    name: str,
    texts: list[str],
    labels: np.ndarray,
    categories: list[str] | None = None,
) -> tuple[SplitMetrics, np.ndarray, list[dict]]:
    probs = _batched_predict(texts)
    preds = (probs >= 0.5).astype(int)
    tp, tn, fp, fn = _confusion(labels, preds)
    acc, prec, rec, f1 = _metrics_from_confusion(tp, tn, fp, fn)
    ece, bins = _expected_calibration_error(probs, labels)

    per_category: dict[str, dict[str, float | int]] = {}
    if categories is not None:
        for cat in sorted(set(categories)):
            mask = np.array([c == cat for c in categories])
            c_tp, c_tn, c_fp, c_fn = _confusion(labels[mask], preds[mask])
            c_acc, c_prec, c_rec, c_f1 = _metrics_from_confusion(c_tp, c_tn, c_fp, c_fn)
            per_category[cat] = {
                "n": int(mask.sum()),
                "accuracy": round(c_acc, 4),
                "precision": round(c_prec, 4),
                "recall": round(c_rec, 4),
                "f1": round(c_f1, 4),
                "tp": c_tp, "tn": c_tn, "fp": c_fp, "fn": c_fn,
            }

    return (
        SplitMetrics(
            name=name, n=len(labels),
            accuracy=acc, precision=prec, recall=rec, f1=f1, ece=ece,
            tp=tp, tn=tn, fp=fp, fn=fn,
            per_category=per_category,
        ),
        probs,
        bins,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uci-only", action="store_true")
    parser.add_argument("--ood-only", action="store_true")
    parser.add_argument("--batch", type=int, default=32)
    args = parser.parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # Load provenance up-front so the report mentions which weights
    # produced these numbers.
    from services import sms_classifier
    bundle = sms_classifier._load()
    provenance = {
        "source": str(bundle["source"]),
        "is_finetuned": bool(bundle["is_finetuned"]),
        "spam_idx": int(bundle["spam_idx"]),
    }

    report: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": provenance,
        "splits": {},
    }

    if not args.ood_only:
        print("[evaluate_sms] Reconstructing UCI held-out split …")
        uci_texts, uci_labels = _load_uci_heldout()
        print(f"[evaluate_sms] n_uci = {len(uci_texts)}")
        uci_metrics, _uci_probs, uci_bins = _evaluate_split(
            "uci_heldout", uci_texts, uci_labels
        )
        _plot_confusion(
            uci_metrics.tp, uci_metrics.tn, uci_metrics.fp, uci_metrics.fn,
            "SMS — UCI held-out (n={})".format(uci_metrics.n),
            FIGURES_DIR / "confusion_uci.png",
        )
        _plot_reliability(
            uci_bins, uci_metrics.ece,
            "SMS — UCI held-out reliability",
            FIGURES_DIR / "reliability_uci.png",
        )
        report["splits"]["uci_heldout"] = uci_metrics.as_dict()
        print(
            f"[evaluate_sms] UCI  acc={uci_metrics.accuracy:.3f} "
            f"P={uci_metrics.precision:.3f} R={uci_metrics.recall:.3f} "
            f"F1={uci_metrics.f1:.3f} ECE={uci_metrics.ece:.3f}"
        )

    if not args.uci_only:
        print("[evaluate_sms] Running OOD pharma evaluation …")
        ood_texts, ood_labels, ood_cats = _ood_texts_labels(EVAL_SET)
        ood_metrics, _ood_probs, ood_bins = _evaluate_split(
            "ood_pharma", ood_texts, ood_labels, ood_cats
        )
        _plot_confusion(
            ood_metrics.tp, ood_metrics.tn, ood_metrics.fp, ood_metrics.fn,
            "SMS — OOD pharma (n={})".format(ood_metrics.n),
            FIGURES_DIR / "confusion_ood.png",
        )
        _plot_reliability(
            ood_bins, ood_metrics.ece,
            "SMS — OOD pharma reliability",
            FIGURES_DIR / "reliability_ood.png",
        )
        report["splits"]["ood_pharma"] = ood_metrics.as_dict()
        print(
            f"[evaluate_sms] OOD  acc={ood_metrics.accuracy:.3f} "
            f"P={ood_metrics.precision:.3f} R={ood_metrics.recall:.3f} "
            f"F1={ood_metrics.f1:.3f} ECE={ood_metrics.ece:.3f}"
        )

    metrics_path = REPORTS_DIR / "metrics.json"
    metrics_path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"[evaluate_sms] Wrote {metrics_path}")
    print(f"[evaluate_sms] Figures in {FIGURES_DIR}")


if __name__ == "__main__":
    main()
