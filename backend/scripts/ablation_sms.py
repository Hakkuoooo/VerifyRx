"""
Ablation study for the SMS classifier (thesis-grade).

Compares four models on the **same two eval splits** that evaluate_sms.py
uses, so the thesis chapter can state: "fine-tuning moved OOD F1 from X
to Y on identical inputs."

Baselines:
  1. majority              — always predicts "legitimate".
                             Establishes the floor given class imbalance.
  2. keyword_rule          — regex over 25 UK-pharma scam keywords
                             (nhs refund, mhra, rx, ozempic trial, …).
                             Non-ML sanity check: can you beat this with
                             a Saturday-afternoon heuristic?
  3. pretrained_hub        — mrm8488/bert-tiny-finetuned-sms-spam-detection
                             (the Hub fallback that config.py points to
                             before local training). Off-the-shelf model,
                             never saw pharma phishing.
  4. finetuned_local       — models_cache/sms/, produced by train_sms.py.

Outputs:
  backend/reports/sms/ablation.json
  backend/reports/sms/figures/ablation_bars.png

Usage:
    cd backend
    python -m scripts.ablation_sms
    python -m scripts.ablation_sms --splits ood         # OOD only (fast)
    python -m scripts.ablation_sms --splits ood uci
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import torch
from datasets import load_dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from scripts.evaluate_sms_ood import EVAL_SET, Sample

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BACKEND_DIR / "reports" / "sms"
FIGURES_DIR = REPORTS_DIR / "figures"
FINETUNED_DIR = BACKEND_DIR / "models_cache" / "sms"

HUB_PRETRAINED_ID = "mrm8488/bert-tiny-finetuned-sms-spam-detection"

# Must match scripts/train_sms.py so we evaluate on the *identical*
# held-out split.
UCI_SEED = 42
UCI_TEST_SIZE = 0.15


# ---------------------------------------------------------------------------
# Baselines
# ---------------------------------------------------------------------------
def predict_majority(texts: list[str]) -> np.ndarray:
    """Always return P(scam) = 0 → always predicts legitimate."""
    return np.zeros(len(texts), dtype=float)


# Deliberately kept narrow. A bigger list would inflate the baseline and
# hide fine-tuning's real lift. These are the 25 most distinctive
# UK-pharma-scam tokens the student can write down unaided.
_KEYWORDS = [
    r"\bnhs refund\b", r"\bnhs alert\b", r"\bmhra\b", r"\bfda\b", r"\bgphc\b",
    r"\brx\b", r"\bno prescription\b", r"\bno rx\b", r"\bfree trial\b",
    r"\blimited offer\b", r"\bclaim now\b", r"\bclaim here\b", r"\bverify\b",
    r"\bbit\.ly\b", r"\bwhatsapp\b", r"\btelegram\b",
    r"\bsemaglutide\b", r"\bozempic\b", r"\bviagra\b", r"\bcialis\b",
    r"\bxanax\b", r"\bpainkillers\b",
    r"\bunauthorised\b", r"\bunauthorized\b", r"\burgent\b",
]
_KEYWORD_RE = re.compile("|".join(_KEYWORDS), flags=re.IGNORECASE)


def predict_keyword(texts: list[str]) -> np.ndarray:
    """
    Crude rule: 0.9 scam probability if *any* keyword matches, else 0.1.
    Deterministic, zero training. Lets the thesis quantify ML uplift
    over an obvious heuristic.
    """
    out = np.empty(len(texts), dtype=float)
    for i, t in enumerate(texts):
        out[i] = 0.9 if _KEYWORD_RE.search(t) else 0.1
    return out


# ---------------------------------------------------------------------------
# Transformer inference helper (used by both pretrained and fine-tuned rows)
# ---------------------------------------------------------------------------
_SPAM_LABELS = {"spam", "label_1", "scam", "1"}
_HAM_LABELS = {"ham", "label_0", "legitimate", "not_spam", "0"}


def _transformer_predict_factory(source: str | Path) -> Callable[[list[str]], np.ndarray]:
    """
    Build a predict_proba-style callable that loads `source` (a Hub id
    or local path) once and returns scam probabilities on each call.

    Constructing via a factory keeps each ablation row's model in its
    own scope — they never contend for the module-level singleton the
    runtime service uses.
    """
    tokenizer = AutoTokenizer.from_pretrained(str(source))
    model = AutoModelForSequenceClassification.from_pretrained(str(source))
    model.eval()

    id2label = {int(i): lbl.lower() for i, lbl in model.config.id2label.items()}
    spam_idx: int | None = None
    for i, lbl in id2label.items():
        if lbl in _SPAM_LABELS:
            spam_idx = i
            break
    if spam_idx is None:
        spam_idx = 1 if model.config.num_labels == 2 else 0
    ham_idx = 1 - spam_idx if model.config.num_labels == 2 else 0

    @torch.no_grad()
    def predict(texts: list[str], batch_size: int = 32) -> np.ndarray:
        out = np.empty(len(texts), dtype=float)
        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            enc = tokenizer(
                chunk, padding=True, truncation=True,
                max_length=256, return_tensors="pt",
            )
            logits = model(**enc).logits
            probs = torch.softmax(logits, dim=-1).cpu().numpy()
            out[i : i + batch_size] = probs[:, spam_idx]
        return out

    return predict


# ---------------------------------------------------------------------------
# Metric primitives (duplicated tiny — keeping ablation self-contained so a
# reader who opens only this file gets the full picture)
# ---------------------------------------------------------------------------
@dataclass
class Row:
    model: str
    split: str
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
    per_category: dict[str, dict[str, float | int]] = field(default_factory=dict)


def _safe_div(a: float, b: float) -> float:
    return float(a / b) if b else 0.0


def _metrics(probs: np.ndarray, labels: np.ndarray) -> tuple[int, int, int, int, float, float, float, float]:
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


def _row_from_preds(
    model_name: str,
    split_name: str,
    probs: np.ndarray,
    labels: np.ndarray,
    categories: list[str] | None,
    notes: str = "",
) -> Row:
    tp, tn, fp, fn, acc, p, r, f1 = _metrics(probs, labels)
    per_category: dict[str, dict[str, float | int]] = {}
    if categories is not None:
        preds = (probs >= 0.5).astype(int)
        for cat in sorted(set(categories)):
            mask = np.array([c == cat for c in categories])
            c_probs = probs[mask]
            c_labels = labels[mask]
            c_tp, c_tn, c_fp, c_fn, c_acc, c_p, c_r, c_f1 = _metrics(c_probs, c_labels)
            per_category[cat] = {
                "n": int(mask.sum()),
                "accuracy": round(c_acc, 4),
                "precision": round(c_p, 4),
                "recall": round(c_r, 4),
                "f1": round(c_f1, 4),
                "tp": c_tp, "tn": c_tn, "fp": c_fp, "fn": c_fn,
            }
            # Silence an otherwise-unused-variable lint: preds is only
            # referenced indirectly through _metrics above.
            _ = preds
    return Row(
        model=model_name, split=split_name, n=len(labels),
        accuracy=round(acc, 4), precision=round(p, 4),
        recall=round(r, 4), f1=round(f1, 4),
        tp=tp, tn=tn, fp=fp, fn=fn,
        notes=notes, per_category=per_category,
    )


# ---------------------------------------------------------------------------
# Split loaders
# ---------------------------------------------------------------------------
def _load_uci() -> tuple[list[str], np.ndarray]:
    raw = load_dataset("sms_spam", split="train")
    split = raw.train_test_split(test_size=UCI_TEST_SIZE, seed=UCI_SEED)
    ds = split["test"]
    return list(ds["sms"]), np.asarray(ds["label"], dtype=int)


def _load_ood() -> tuple[list[str], np.ndarray, list[str]]:
    texts = [s.text for s in EVAL_SET]
    labels = np.asarray(
        [1 if s.label == "scam" else 0 for s in EVAL_SET], dtype=int
    )
    cats = [s.category for s in EVAL_SET]
    return texts, labels, cats


# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
def _plot_ablation_bars(rows: list[Row], split: str, path: Path) -> None:
    subset = [r for r in rows if r.split == split]
    if not subset:
        return
    order = {"majority": 0, "keyword_rule": 1, "pretrained_hub": 2, "finetuned_local": 3}
    subset.sort(key=lambda r: order.get(r.model, 99))

    models = [r.model for r in subset]
    accs = [r.accuracy for r in subset]
    f1s = [r.f1 for r in subset]
    recs = [r.recall for r in subset]

    x = np.arange(len(models))
    w = 0.25

    fig, ax = plt.subplots(figsize=(6.6, 4.0))
    ax.bar(x - w, accs, w, label="accuracy", color="#4c9be8")
    ax.bar(x,     f1s,  w, label="F1",       color="#f2a154")
    ax.bar(x + w, recs, w, label="recall",   color="#7bbf6a")
    ax.set_xticks(x, labels=models, rotation=15, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_title(f"SMS ablation — split: {split}")
    ax.set_ylabel("score")
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--splits", nargs="+", default=["ood", "uci"],
        choices=["ood", "uci"],
        help="Which eval splits to run.",
    )
    args = parser.parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # Pre-load transformer rows once each. Skip gracefully if the
    # fine-tuned checkpoint isn't present (fresh clone, no training yet).
    print("[ablation_sms] Loading pretrained Hub model …")
    pretrained_predict = _transformer_predict_factory(HUB_PRETRAINED_ID)

    finetuned_predict = None
    finetuned_note = ""
    if (FINETUNED_DIR / "config.json").is_file():
        print("[ablation_sms] Loading fine-tuned local model …")
        finetuned_predict = _transformer_predict_factory(FINETUNED_DIR)
    else:
        finetuned_note = f"skipped — no checkpoint at {FINETUNED_DIR}"
        print(f"[ablation_sms] WARNING: {finetuned_note}")

    all_rows: list[Row] = []

    split_loaders = {
        "ood": lambda: (*_load_ood(),),     # texts, labels, cats
        "uci": lambda: (*_load_uci(), None),
    }

    for split_name in args.splits:
        print(f"\n[ablation_sms] === split: {split_name} ===")
        texts, labels, cats = split_loaders[split_name]()
        print(f"[ablation_sms] n = {len(texts)}")

        # Majority
        all_rows.append(_row_from_preds(
            "majority", split_name,
            predict_majority(texts), labels, cats,
            notes="always predicts legitimate",
        ))

        # Keyword rule
        all_rows.append(_row_from_preds(
            "keyword_rule", split_name,
            predict_keyword(texts), labels, cats,
            notes=f"{len(_KEYWORDS)} hand-picked pharma-scam regexes",
        ))

        # Pretrained (Hub)
        all_rows.append(_row_from_preds(
            "pretrained_hub", split_name,
            pretrained_predict(texts), labels, cats,
            notes=HUB_PRETRAINED_ID,
        ))

        # Fine-tuned (local), if available
        if finetuned_predict is not None:
            all_rows.append(_row_from_preds(
                "finetuned_local", split_name,
                finetuned_predict(texts), labels, cats,
                notes=str(FINETUNED_DIR),
            ))
        else:
            all_rows.append(Row(
                model="finetuned_local", split=split_name, n=len(labels),
                accuracy=0, precision=0, recall=0, f1=0,
                tp=0, tn=0, fp=0, fn=0,
                notes=finetuned_note,
            ))

        # Print leaderboard for this split
        print(f"\n{'model':20s} {'acc':>6s} {'P':>6s} {'R':>6s} {'F1':>6s}")
        for r in all_rows:
            if r.split != split_name:
                continue
            print(f"{r.model:20s} {r.accuracy:6.3f} {r.precision:6.3f} "
                  f"{r.recall:6.3f} {r.f1:6.3f}")

        _plot_ablation_bars(
            all_rows, split_name,
            FIGURES_DIR / f"ablation_{split_name}.png",
        )

    # Persist JSON
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "splits_run": args.splits,
        "rows": [
            {
                "model": r.model, "split": r.split, "n": r.n,
                "accuracy": r.accuracy, "precision": r.precision,
                "recall": r.recall, "f1": r.f1,
                "confusion_matrix": {"tp": r.tp, "tn": r.tn, "fp": r.fp, "fn": r.fn},
                "notes": r.notes,
                "per_category": r.per_category,
            }
            for r in all_rows
        ],
    }
    (REPORTS_DIR / "ablation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"\n[ablation_sms] Wrote {REPORTS_DIR / 'ablation.json'}")


if __name__ == "__main__":
    main()
