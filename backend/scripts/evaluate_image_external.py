"""
Evaluate the fine-tuned image classifier on an **external held-out
dataset** — one that was *not* used for training or validation.

Motivation (thesis):
    scripts/evaluate_image.py reports numbers on the val split drawn
    from the same data/images/ pack used for training. Those numbers
    are informative but optimistic — the train and val splits share a
    photographic setup (lighting, angles, backgrounds), and a model
    could learn setup artifacts instead of counterfeit cues.

    A true generalisation measure needs a held-out set the model has
    never touched, ideally captured differently. That's what this
    script evaluates. The external set lives outside data/images/ so
    it can't accidentally leak into training.

Expected layout (configurable via --root):
    backend/data/images_external/
        authentic/    *.jpg|*.jpeg|*.png|*.webp
        counterfeit/  *.jpg|*.jpeg|*.png|*.webp

Outputs:
    backend/reports/image/external_metrics.json
    backend/reports/image/figures/confusion_external.png
    backend/reports/image/figures/reliability_external.png

Usage:
    cd backend
    python -m scripts.evaluate_image_external
    python -m scripts.evaluate_image_external --root data/images_external
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import torch
from torch.utils.data import DataLoader
from torchvision import datasets

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ROOT = BACKEND_DIR / "data" / "images_external"
REPORTS_DIR = BACKEND_DIR / "reports" / "image"
FIGURES_DIR = REPORTS_DIR / "figures"


# ---------------------------------------------------------------------------
# Metric primitives (same conventions as evaluate_image.py)
# ---------------------------------------------------------------------------
@dataclass
class ExternalMetrics:
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
    """Positive class = counterfeit (index 1)."""
    tp = int(((y_pred == 1) & (y_true == 1)).sum())
    tn = int(((y_pred == 0) & (y_true == 0)).sum())
    fp = int(((y_pred == 1) & (y_true == 0)).sum())
    fn = int(((y_pred == 0) & (y_true == 1)).sum())
    return tp, tn, fp, fn


def _ece(probs_pos: np.ndarray, y_true: np.ndarray, n_bins: int = 10) -> tuple[float, list[dict]]:
    """Guo-et-al ECE over predicted-class confidence."""
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
# Plot helpers (tiny duplication from evaluate_image.py to keep this file
# self-contained for downstream users)
# ---------------------------------------------------------------------------
def _plot_confusion(tp: int, tn: int, fp: int, fn: int, title: str, path: Path) -> None:
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
# Dataset loader + inference
# ---------------------------------------------------------------------------
def _load_external(root: Path):
    """ImageFolder over the external set. Validates structure loudly."""
    from services import image_classifier

    if not root.is_dir():
        raise SystemExit(
            f"External dataset root not found: {root}\n"
            f"Create the folder layout:\n"
            f"  {root}/authentic/<images>\n"
            f"  {root}/counterfeit/<images>\n"
            f"…and re-run."
        )
    for sub in ("authentic", "counterfeit"):
        sub_path = root / sub
        if not sub_path.is_dir():
            raise SystemExit(f"Missing required subfolder: {sub_path}")
        # ImageFolder silently skips unknown extensions; warn the user if
        # their folder is empty so they don't think the model got 100 %
        # on n=0.
        has_images = any(sub_path.iterdir())
        if not has_images:
            raise SystemExit(f"Subfolder is empty: {sub_path}")

    _net, preprocess = image_classifier.get_model_and_transform()
    ds = datasets.ImageFolder(str(root), transform=preprocess)
    if ds.classes != ["authentic", "counterfeit"]:
        raise SystemExit(
            f"Unexpected class ordering {ds.classes}; expected "
            f"['authentic', 'counterfeit'] (alphabetical)."
        )
    return ds


@torch.no_grad()
def _run(ds, batch: int) -> tuple[np.ndarray, np.ndarray]:
    from services import image_classifier

    net, _preprocess = image_classifier.get_model_and_transform()
    device = (
        "cuda" if torch.cuda.is_available()
        else "mps" if torch.backends.mps.is_available()
        else "cpu"
    )
    net = net.to(device).eval()

    loader = DataLoader(ds, batch_size=batch, shuffle=False, num_workers=0)
    ps, ys = [], []
    for x, y in loader:
        x = x.to(device)
        logits = net(x)
        probs = torch.softmax(logits, dim=1)[:, 1].cpu().numpy()
        ps.append(probs)
        ys.append(y.numpy())
    return np.concatenate(ps), np.concatenate(ys)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT,
                        help="External dataset root. Expected subfolders: "
                             "authentic/ and counterfeit/.")
    parser.add_argument("--batch", type=int, default=32)
    args = parser.parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    ds = _load_external(args.root)
    print(f"[external] root = {args.root}")
    print(f"[external] n = {len(ds)}  classes = {ds.classes}")

    # Provenance for the report
    from services import image_classifier
    bundle = image_classifier._load()
    provenance = {
        "weights_path": bundle["weights_path"],
        "is_finetuned": bool(bundle["is_finetuned"]),
    }
    if not bundle["is_finetuned"]:
        print("[external] WARNING: running in demo mode (random 2-class head).")

    probs, labels = _run(ds, args.batch)
    preds = (probs >= 0.5).astype(int)
    tp, tn, fp, fn = _confusion(labels, preds)
    total = tp + tn + fp + fn
    acc = _safe_div(tp + tn, total)
    p = _safe_div(tp, tp + fp)
    r = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * p * r, p + r)
    ece_val, bins = _ece(probs, labels)

    metrics = ExternalMetrics(
        n=total, accuracy=acc, precision=p, recall=r, f1=f1, ece=ece_val,
        tp=tp, tn=tn, fp=fp, fn=fn,
    )

    _plot_confusion(tp, tn, fp, fn,
                    f"Image — external held-out (n={total})",
                    FIGURES_DIR / "confusion_external.png")
    _plot_reliability(bins, ece_val,
                      "Image — external held-out reliability",
                      FIGURES_DIR / "reliability_external.png")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": provenance,
        "split": {
            "name": "external",
            "root": str(args.root),
            "class_order": list(ds.classes),
            "n_authentic": int((labels == 0).sum()),
            "n_counterfeit": int((labels == 1).sum()),
        },
        "metrics": metrics.as_dict(),
        "reliability_bins": bins,
    }
    out_path = REPORTS_DIR / "external_metrics.json"
    out_path.write_text(json.dumps(report, indent=2) + "\n")

    print(
        f"[external] acc={acc:.3f} P={p:.3f} R={r:.3f} F1={f1:.3f} "
        f"ECE={ece_val:.3f}"
    )
    print(f"[external] Wrote {out_path}")
    print(f"[external] Figures in {FIGURES_DIR}")


if __name__ == "__main__":
    main()
