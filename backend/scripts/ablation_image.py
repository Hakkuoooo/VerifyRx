"""
Ablation study for the image classifier (thesis-grade).

Compares four models on the **same train/val split** that train_image.py
uses (seed=42, val_split=0.2), so the thesis can quote apples-to-apples
numbers for "what does fine-tuning actually buy us over simpler options?"

Rows:
  1. random_head            — ImageNet-pretrained ResNet-18 with a fresh
                              randomly-initialised 2-class head. No
                              training of any kind. The chance-level
                              floor that the service falls back to when
                              no fine-tuned weights exist ("demo mode").

  2. imagenet_logreg        — Use a frozen ImageNet ResNet-18 as a
                              feature extractor (512-d avgpool output),
                              fit scikit-learn logistic regression on
                              the 80% train subset, evaluate on val.
                              Answers: do ImageNet features alone
                              separate authentic from counterfeit?

  3. finetuned_local        — The actual service weights at
                              models_cache/image/resnet18_finetuned.pt,
                              produced by train_image.py.

Artifacts:
  backend/reports/image/ablation.json
  backend/reports/image/figures/ablation_val.png

Usage:
    cd backend
    python -m scripts.ablation_image
    python -m scripts.ablation_image --skip-logreg   # fastest run
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, models

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data" / "images"
REPORTS_DIR = BACKEND_DIR / "reports" / "image"
FIGURES_DIR = REPORTS_DIR / "figures"
FINETUNED_WEIGHTS = BACKEND_DIR / "models_cache" / "image" / "resnet18_finetuned.pt"

DEFAULT_SEED = 42
DEFAULT_VAL_SPLIT = 0.2


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------
@dataclass
class Row:
    model: str
    n: int
    accuracy: float
    precision: float
    recall: float
    f1: float
    tp: int
    tn: int
    fp: int
    fn: int
    notes: str = ""


def _safe_div(a: float, b: float) -> float:
    return float(a / b) if b else 0.0


def _scores(probs: np.ndarray, labels: np.ndarray) -> tuple[int, int, int, int, float, float, float, float]:
    preds = (probs >= 0.5).astype(int)
    tp = int(((preds == 1) & (labels == 1)).sum())
    tn = int(((preds == 0) & (labels == 0)).sum())
    fp = int(((preds == 1) & (labels == 0)).sum())
    fn = int(((preds == 0) & (labels == 1)).sum())
    acc = _safe_div(tp + tn, tp + tn + fp + fn)
    p = _safe_div(tp, tp + fp)
    r = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * p * r, p + r)
    return tp, tn, fp, fn, acc, p, r, f1


def _row(name: str, probs: np.ndarray, labels: np.ndarray, notes: str = "") -> Row:
    tp, tn, fp, fn, acc, p, r, f1 = _scores(probs, labels)
    return Row(
        model=name, n=len(labels),
        accuracy=round(acc, 4), precision=round(p, 4),
        recall=round(r, 4), f1=round(f1, 4),
        tp=tp, tn=tn, fp=fp, fn=fn, notes=notes,
    )


# ---------------------------------------------------------------------------
# Split reconstruction
# ---------------------------------------------------------------------------
def _reconstruct_split(seed: int, val_frac: float) -> tuple[Subset, Subset, list[str]]:
    """
    Return (train_subset, val_subset, class_names) using the exact
    indexing logic of scripts/train_image.py. The subsets share the
    eval-time preprocessing (Resize→CenterCrop→Normalize) — no train-time
    augmentation in the feature-extraction pipeline because we want
    deterministic features for logistic regression.
    """
    from services import image_classifier  # for the preprocess transform

    _net, preprocess = image_classifier.get_model_and_transform()
    full = datasets.ImageFolder(str(DATA_DIR), transform=preprocess)
    if full.classes != ["authentic", "counterfeit"]:
        raise SystemExit(
            f"Unexpected class ordering {full.classes}; expected "
            f"['authentic', 'counterfeit']."
        )

    random.seed(seed)
    torch.manual_seed(seed)
    n_total = len(full)
    n_val = max(1, int(n_total * val_frac))
    n_train = n_total - n_val
    indices = list(range(n_total))
    random.shuffle(indices)
    return (
        Subset(full, indices[:n_train]),
        Subset(full, indices[n_train:]),
        full.classes,
    )


def _device() -> str:
    return (
        "cuda" if torch.cuda.is_available()
        else "mps" if torch.backends.mps.is_available()
        else "cpu"
    )


# ---------------------------------------------------------------------------
# Row 1: random-head baseline
# ---------------------------------------------------------------------------
@torch.no_grad()
def _row_random_head(val_ds: Subset, batch: int, seed: int) -> Row:
    """
    Build a fresh ResNet-18 with ImageNet backbone + a newly-initialised
    2-class fc, set it to eval mode, run over the val set. Seeded so the
    result is reproducible.
    """
    torch.manual_seed(seed)
    net = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
    net.fc = nn.Linear(net.fc.in_features, 2)
    device = _device()
    net = net.to(device).eval()

    loader = DataLoader(val_ds, batch_size=batch, shuffle=False, num_workers=0)
    ps, ys = [], []
    for x, y in loader:
        x = x.to(device)
        logits = net(x)
        probs = torch.softmax(logits, dim=1)[:, 1].cpu().numpy()
        ps.append(probs)
        ys.append(y.numpy())
    return _row(
        "random_head",
        np.concatenate(ps),
        np.concatenate(ys),
        notes="ImageNet backbone, random 2-class fc, no training",
    )


# ---------------------------------------------------------------------------
# Row 2: ImageNet features + logistic regression
# ---------------------------------------------------------------------------
@torch.no_grad()
def _extract_features(ds: Subset, batch: int) -> tuple[np.ndarray, np.ndarray]:
    """Frozen ImageNet ResNet-18 avgpool features (512-d) for every image."""
    # Strip the fc — everything up to and including avgpool is a feature
    # extractor that outputs (B, 512, 1, 1). Flatten to (B, 512).
    net = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
    net.fc = nn.Identity()
    device = _device()
    net = net.to(device).eval()

    loader = DataLoader(ds, batch_size=batch, shuffle=False, num_workers=0)
    feats, labels = [], []
    for x, y in loader:
        x = x.to(device)
        f = net(x).cpu().numpy()  # (B, 512)
        feats.append(f)
        labels.append(y.numpy())
    return np.concatenate(feats), np.concatenate(labels)


def _row_imagenet_logreg(train_ds: Subset, val_ds: Subset, batch: int, seed: int) -> Row:
    """Train a logistic regression on frozen ImageNet features."""
    from sklearn.linear_model import LogisticRegression

    print("[ablation_image]   extracting train features …")
    x_train, y_train = _extract_features(train_ds, batch)
    print("[ablation_image]   extracting val features …")
    x_val, y_val = _extract_features(val_ds, batch)

    # max_iter bumped so L-BFGS converges on 512-d features + small N.
    # Class weight 'balanced' adjusts for the authentic/counterfeit imbalance.
    clf = LogisticRegression(
        max_iter=2000, class_weight="balanced", random_state=seed,
    )
    clf.fit(x_train, y_train)
    probs = clf.predict_proba(x_val)[:, 1]
    return _row(
        "imagenet_logreg",
        probs, y_val,
        notes="frozen ResNet-18 avgpool → sklearn LogisticRegression",
    )


# ---------------------------------------------------------------------------
# Row 3: fine-tuned model (shared with evaluate_image.py)
# ---------------------------------------------------------------------------
@torch.no_grad()
def _row_finetuned(val_ds: Subset, batch: int) -> Row | None:
    """Run the service's fine-tuned weights. Returns None in demo mode."""
    from services import image_classifier

    bundle = image_classifier._load()
    if not bundle["is_finetuned"]:
        return None
    net = bundle["model"]
    device = _device()
    net = net.to(device).eval()

    loader = DataLoader(val_ds, batch_size=batch, shuffle=False, num_workers=0)
    ps, ys = [], []
    for x, y in loader:
        x = x.to(device)
        logits = net(x)
        probs = torch.softmax(logits, dim=1)[:, 1].cpu().numpy()
        ps.append(probs)
        ys.append(y.numpy())
    return _row(
        "finetuned_local",
        np.concatenate(ps), np.concatenate(ys),
        notes=str(bundle["weights_path"]),
    )


# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
def _plot_ablation(rows: list[Row], path: Path) -> None:
    order = {"random_head": 0, "imagenet_logreg": 1, "finetuned_local": 2}
    rows = sorted(rows, key=lambda r: order.get(r.model, 99))

    models_ = [r.model for r in rows]
    accs = [r.accuracy for r in rows]
    f1s = [r.f1 for r in rows]
    recs = [r.recall for r in rows]

    x = np.arange(len(models_))
    w = 0.25

    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    ax.bar(x - w, accs, w, label="accuracy", color="#4c9be8")
    ax.bar(x,     f1s,  w, label="F1",       color="#f2a154")
    ax.bar(x + w, recs, w, label="recall",   color="#7bbf6a")
    ax.set_xticks(x, labels=models_, rotation=15, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_title("Image ablation — val split")
    ax.set_ylabel("score")
    ax.grid(axis="y", linestyle=":", alpha=0.5)
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
    parser.add_argument(
        "--skip-logreg", action="store_true",
        help="Skip the ImageNet+LogReg row (feature extraction can be slow on CPU)."
    )
    args = parser.parse_args()

    if not (DATA_DIR / "authentic").is_dir() or not (DATA_DIR / "counterfeit").is_dir():
        raise SystemExit(
            f"Expected subfolders 'authentic/' and 'counterfeit/' under {DATA_DIR}."
        )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[ablation_image] Reconstructing split (seed={args.seed}, "
          f"val_frac={args.val_split}) …")
    train_ds, val_ds, class_names = _reconstruct_split(args.seed, args.val_split)
    print(f"[ablation_image] train={len(train_ds)}  val={len(val_ds)}  "
          f"classes={class_names}")

    rows: list[Row] = []

    print("[ablation_image] 1/3  random_head …")
    rows.append(_row_random_head(val_ds, args.batch, args.seed))

    if not args.skip_logreg:
        print("[ablation_image] 2/3  imagenet_logreg …")
        rows.append(_row_imagenet_logreg(train_ds, val_ds, args.batch, args.seed))
    else:
        rows.append(Row(
            model="imagenet_logreg", n=len(val_ds),
            accuracy=0, precision=0, recall=0, f1=0,
            tp=0, tn=0, fp=0, fn=0,
            notes="skipped via --skip-logreg",
        ))

    print("[ablation_image] 3/3  finetuned_local …")
    finetuned = _row_finetuned(val_ds, args.batch)
    if finetuned is None:
        rows.append(Row(
            model="finetuned_local", n=len(val_ds),
            accuracy=0, precision=0, recall=0, f1=0,
            tp=0, tn=0, fp=0, fn=0,
            notes="skipped — no fine-tuned weights at models_cache/image/",
        ))
    else:
        rows.append(finetuned)

    print(f"\n{'model':20s} {'acc':>6s} {'P':>6s} {'R':>6s} {'F1':>6s}")
    for r in rows:
        print(f"{r.model:20s} {r.accuracy:6.3f} {r.precision:6.3f} "
              f"{r.recall:6.3f} {r.f1:6.3f}")

    _plot_ablation(rows, FIGURES_DIR / "ablation_val.png")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "split": {
            "seed": args.seed, "val_frac": args.val_split,
            "class_order": list(class_names),
            "n_train": len(train_ds), "n_val": len(val_ds),
        },
        "rows": [
            {
                "model": r.model, "n": r.n,
                "accuracy": r.accuracy, "precision": r.precision,
                "recall": r.recall, "f1": r.f1,
                "confusion_matrix": {"tp": r.tp, "tn": r.tn, "fp": r.fp, "fn": r.fn},
                "notes": r.notes,
            }
            for r in rows
        ],
    }
    (REPORTS_DIR / "ablation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"\n[ablation_image] Wrote {REPORTS_DIR / 'ablation.json'}")


if __name__ == "__main__":
    main()
