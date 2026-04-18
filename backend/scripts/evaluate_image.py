"""
Image-classifier evaluation harness (thesis-grade).

Re-runs the loaded ResNet-18 on the **same validation split** that
train_image.py uses (seed=42, val_split=0.2, shuffled index list), and
produces:

  backend/reports/image/metrics.json
  backend/reports/image/figures/
      confusion_val.png
      reliability_val.png

Only the validation split is evaluated: this project has a single small
on-disk dataset (data/images/authentic + counterfeit). Adding a held-out
external test set is future work called out in the model card.

Usage:
    cd backend
    python -m scripts.evaluate_image
    python -m scripts.evaluate_image --batch 32 --seed 42
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import torch
from torch.utils.data import DataLoader, Subset
from torchvision import datasets

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data" / "images"
REPORTS_DIR = BACKEND_DIR / "reports" / "image"
FIGURES_DIR = REPORTS_DIR / "figures"

# Must match scripts/train_image.py exactly so we pick the same held-out images.
DEFAULT_SEED = 42
DEFAULT_VAL_SPLIT = 0.2


# ---------------------------------------------------------------------------
# Metric primitives
# ---------------------------------------------------------------------------
@dataclass
class ImageMetrics:
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

    def as_dict(self) -> dict:
        return {
            "n": self.n,
            "accuracy": round(self.accuracy, 4),
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "ece": round(self.ece, 4),
            "confusion_matrix": {
                "tp": self.tp, "tn": self.tn, "fp": self.fp, "fn": self.fn,
            },
        }


def _safe_div(a: float, b: float) -> float:
    return float(a / b) if b else 0.0


def _confusion(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[int, int, int, int]:
    """1 = counterfeit (positive). 0 = authentic."""
    tp = int(((y_pred == 1) & (y_true == 1)).sum())
    tn = int(((y_pred == 0) & (y_true == 0)).sum())
    fp = int(((y_pred == 1) & (y_true == 0)).sum())
    fn = int(((y_pred == 0) & (y_true == 1)).sum())
    return tp, tn, fp, fn


def _ece(probs_pos: np.ndarray, y_true: np.ndarray, n_bins: int = 10) -> tuple[float, list[dict]]:
    """Guo-et-al. ECE over predicted-class confidence ∈ [0.5, 1.0]."""
    y_pred = (probs_pos >= 0.5).astype(int)
    confidence = np.maximum(probs_pos, 1.0 - probs_pos)
    correct = (y_pred == y_true).astype(float)

    edges = np.linspace(0.5, 1.0, n_bins + 1)
    ece = 0.0
    n = len(probs_pos)
    bins: list[dict] = []
    for b in range(n_bins):
        lo, hi = edges[b], edges[b + 1]
        mask = (
            ((confidence >= lo) & (confidence <= hi))
            if b == n_bins - 1
            else ((confidence >= lo) & (confidence < hi))
        )
        count = int(mask.sum())
        if count == 0:
            bins.append({"lo": round(float(lo), 3), "hi": round(float(hi), 3),
                         "count": 0, "mean_conf": 0.0, "accuracy": 0.0})
            continue
        mean_conf = float(confidence[mask].mean())
        acc_b = float(correct[mask].mean())
        ece += (count / n) * abs(acc_b - mean_conf)
        bins.append({"lo": round(float(lo), 3), "hi": round(float(hi), 3),
                     "count": count, "mean_conf": round(mean_conf, 4),
                     "accuracy": round(acc_b, 4)})
    return float(ece), bins


# ---------------------------------------------------------------------------
# Val split — reconstruct train_image.py's split exactly
# ---------------------------------------------------------------------------
def _reconstruct_val_split(seed: int, val_frac: float) -> tuple[Subset, list[str]]:
    """
    Use the same random.shuffle logic as scripts/train_image.py so we
    evaluate on the identical images the training script held out.

    Returns (val_dataset, class_names).
    """
    from services import image_classifier  # lazy, avoids weights at import

    # Reuse the exact preprocessing pipeline the service uses, so the
    # numbers we report reflect what the live API would do.
    _net, preprocess = image_classifier.get_model_and_transform()

    full = datasets.ImageFolder(str(DATA_DIR), transform=preprocess)
    if full.classes != ["authentic", "counterfeit"]:
        raise SystemExit(
            f"Unexpected class ordering {full.classes}; expected "
            f"['authentic', 'counterfeit']."
        )

    n_total = len(full)
    n_val = max(1, int(n_total * val_frac))
    n_train = n_total - n_val

    # Mirror train_image.py's own rng: random.seed(seed) then shuffle.
    random.seed(seed)
    torch.manual_seed(seed)
    indices = list(range(n_total))
    random.shuffle(indices)
    _train_idx, val_idx = indices[:n_train], indices[n_train:]
    return Subset(full, val_idx), full.classes


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------
@torch.no_grad()
def _run_val(val_ds: Subset, batch_size: int) -> tuple[np.ndarray, np.ndarray]:
    """Return (probs_counterfeit, labels) for the entire val set."""
    from services import image_classifier

    net, _preprocess = image_classifier.get_model_and_transform()
    device = (
        "cuda" if torch.cuda.is_available()
        else "mps" if torch.backends.mps.is_available()
        else "cpu"
    )
    net = net.to(device).eval()

    loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)
    all_probs: list[np.ndarray] = []
    all_labels: list[np.ndarray] = []
    for x, y in loader:
        x = x.to(device)
        logits = net(x)
        probs = torch.softmax(logits, dim=1)[:, 1].cpu().numpy()  # col 1 = counterfeit
        all_probs.append(probs)
        all_labels.append(y.numpy())
    return np.concatenate(all_probs), np.concatenate(all_labels)


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------
def _plot_confusion(tp: int, tn: int, fp: int, fn: int, title: str, path: Path) -> None:
    # Row = ground truth, column = prediction. Positive class = counterfeit.
    matrix = np.array([[tp, fn], [fp, tn]], dtype=int)

    fig, ax = plt.subplots(figsize=(4.4, 3.8))
    im = ax.imshow(matrix, cmap="Blues")
    ax.set_xticks([0, 1], labels=["pred=counterfeit", "pred=authentic"])
    ax.set_yticks([0, 1], labels=["gt=counterfeit", "gt=authentic"])
    ax.set_title(title)
    for i in range(2):
        for j in range(2):
            v = matrix[i, j]
            colour = "white" if v > matrix.max() / 2 else "black"
            ax.text(j, i, str(v), ha="center", va="center", color=colour, fontsize=14)
    fig.colorbar(im, ax=ax, shrink=0.75)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _plot_reliability(bins: list[dict], ece: float, title: str, path: Path) -> None:
    centres = np.array([(b["lo"] + b["hi"]) / 2 for b in bins])
    accs = np.array([b["accuracy"] for b in bins])
    counts = np.array([b["count"] for b in bins])

    fig, ax = plt.subplots(figsize=(5.0, 3.8))
    bin_width = 0.5 / len(bins)
    ax.bar(centres, accs, width=bin_width * 0.9,
           edgecolor="black", color="#4c9be8", label="observed accuracy")
    ax.plot([0.5, 1.0], [0.5, 1.0], linestyle="--", color="black",
            label="perfect calibration")
    ax.set_xlim(0.5, 1.0)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("predicted-class confidence  max(p, 1−p)")
    ax.set_ylabel("observed accuracy")
    ax.set_title(f"{title}  (ECE = {ece:.3f})")
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
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--val-split", type=float, default=DEFAULT_VAL_SPLIT)
    args = parser.parse_args()

    if not (DATA_DIR / "authentic").is_dir() or not (DATA_DIR / "counterfeit").is_dir():
        raise SystemExit(
            f"Expected subfolders 'authentic/' and 'counterfeit/' under "
            f"{DATA_DIR}. Run the training pipeline first."
        )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[evaluate_image] Reconstructing val split (seed={args.seed}, "
          f"val_split={args.val_split}) …")
    val_ds, class_names = _reconstruct_val_split(args.seed, args.val_split)
    print(f"[evaluate_image] n_val = {len(val_ds)}  classes={class_names}")

    # Provenance
    from services import image_classifier
    bundle = image_classifier._load()
    provenance = {
        "weights_path": bundle["weights_path"],
        "is_finetuned": bool(bundle["is_finetuned"]),
    }
    if not bundle["is_finetuned"]:
        print("[evaluate_image] WARNING: running in demo mode "
              "(randomly-initialised 2-class head).")

    probs, labels = _run_val(val_ds, args.batch)
    preds = (probs >= 0.5).astype(int)
    tp, tn, fp, fn = _confusion(labels, preds)
    total = tp + tn + fp + fn
    accuracy = _safe_div(tp + tn, total)
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)
    ece_val, bins = _ece(probs, labels)

    metrics = ImageMetrics(
        n=total, accuracy=accuracy, precision=precision, recall=recall,
        f1=f1, ece=ece_val, tp=tp, tn=tn, fp=fp, fn=fn,
    )

    _plot_confusion(
        tp, tn, fp, fn,
        f"Image — val split (n={total})",
        FIGURES_DIR / "confusion_val.png",
    )
    _plot_reliability(
        bins, ece_val,
        "Image — val reliability",
        FIGURES_DIR / "reliability_val.png",
    )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": provenance,
        "split": {
            "name": "val_split",
            "seed": args.seed,
            "val_frac": args.val_split,
            "class_order": list(class_names),
        },
        "metrics": metrics.as_dict(),
        "reliability_bins": bins,
    }
    (REPORTS_DIR / "metrics.json").write_text(json.dumps(report, indent=2) + "\n")

    print(
        f"[evaluate_image] val  acc={accuracy:.3f} "
        f"P={precision:.3f} R={recall:.3f} F1={f1:.3f} ECE={ece_val:.3f}"
    )
    print(f"[evaluate_image] Wrote {REPORTS_DIR / 'metrics.json'}")
    print(f"[evaluate_image] Figures in {FIGURES_DIR}")


if __name__ == "__main__":
    main()
