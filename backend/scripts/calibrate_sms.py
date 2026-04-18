"""
Learn a temperature-scaling scalar for the fine-tuned SMS classifier.

Temperature scaling (Guo, Pleiss, Sun, Weinberger, 2017 — "On Calibration
of Modern Neural Networks") is a single-parameter post-hoc calibration
method:

    softmax_T(logits) = softmax(logits / T)

A learned T > 1 flattens over-confident distributions; T < 1 sharpens
under-confident ones. Argmax is unchanged, so accuracy / F1 are
preserved exactly — only the probability calibration changes.

This script:
  1. Reconstructs the same UCI held-out split that train_sms.py
     evaluates on (seed=42, test_size=0.15). This is a legitimate
     calibration set because (a) it's held out from training and
     (b) Guo et al. show learning T on val / recalibrating on
     test is standard and does not overfit.
  2. Collects raw logits for every held-out example (no softmax).
  3. Fits T by minimising NLL with L-BFGS in one shot.
  4. Writes `backend/models_cache/sms/temperature.json` — picked up
     automatically by services/sms_classifier.py on next load.

Usage:
    cd backend
    python -m scripts.calibrate_sms
    python -m scripts.calibrate_sms --max-iter 200
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from datasets import load_dataset

BACKEND_DIR = Path(__file__).resolve().parent.parent
FINETUNED_DIR = BACKEND_DIR / "models_cache" / "sms"
TEMPERATURE_PATH = FINETUNED_DIR / "temperature.json"

UCI_SEED = 42
UCI_TEST_SIZE = 0.15


@torch.no_grad()
def _collect_logits(texts: list[str], labels: np.ndarray, batch: int = 32) -> tuple[np.ndarray, np.ndarray]:
    """Return (logits, labels) for the held-out split. No softmax, no temperature."""
    from services import sms_classifier

    bundle = sms_classifier._load()
    tokenizer = bundle["tokenizer"]
    model = bundle["model"]
    spam_idx = bundle["spam_idx"]
    ham_idx = 1 - spam_idx

    all_logits = []
    for i in range(0, len(texts), batch):
        chunk = texts[i : i + batch]
        enc = tokenizer(chunk, padding=True, truncation=True,
                        max_length=256, return_tensors="pt")
        raw = model(**enc).logits.cpu().numpy()
        # Reorder columns to [legitimate, scam] so label index 1 = scam
        # matches the UCI label space.
        all_logits.append(np.stack([raw[:, ham_idx], raw[:, spam_idx]], axis=1))
    return np.concatenate(all_logits), labels


def _ece(probs_pos: np.ndarray, y_true: np.ndarray, n_bins: int = 10) -> float:
    """Guo-et-al ECE over predicted-class confidence ∈ [0.5, 1.0]."""
    y_pred = (probs_pos >= 0.5).astype(int)
    confidence = np.maximum(probs_pos, 1.0 - probs_pos)
    correct = (y_pred == y_true).astype(float)
    edges = np.linspace(0.5, 1.0, n_bins + 1)
    ece = 0.0
    n = len(probs_pos)
    for b in range(n_bins):
        lo, hi = edges[b], edges[b + 1]
        mask = (
            ((confidence >= lo) & (confidence <= hi))
            if b == n_bins - 1
            else ((confidence >= lo) & (confidence < hi))
        )
        if int(mask.sum()) == 0:
            continue
        ece += (mask.sum() / n) * abs(
            float(correct[mask].mean()) - float(confidence[mask].mean())
        )
    return float(ece)


def _learn_temperature(logits_np: np.ndarray, labels_np: np.ndarray, max_iter: int) -> float:
    """
    Fit a scalar T by minimising cross-entropy with L-BFGS. The
    parameter lives on log-scale (T = exp(log_T)) so the optimiser
    doesn't need a positivity constraint.
    """
    logits = torch.tensor(logits_np, dtype=torch.float32)
    labels = torch.tensor(labels_np, dtype=torch.long)

    log_T = torch.zeros(1, requires_grad=True)  # T starts at 1.0
    opt = torch.optim.LBFGS([log_T], lr=0.1, max_iter=max_iter,
                             line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        T = torch.exp(log_T)
        loss = F.cross_entropy(logits / T, labels)
        loss.backward()
        return loss

    opt.step(closure)
    return float(torch.exp(log_T).detach().item())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-iter", type=int, default=100)
    parser.add_argument("--batch", type=int, default=32)
    args = parser.parse_args()

    if not (FINETUNED_DIR / "config.json").is_file():
        raise SystemExit(
            f"No fine-tuned weights at {FINETUNED_DIR}. "
            f"Run `python -m scripts.train_sms` first."
        )

    print(f"[calibrate_sms] Loading UCI held-out split …")
    raw = load_dataset("sms_spam", split="train")
    split = raw.train_test_split(test_size=UCI_TEST_SIZE, seed=UCI_SEED)
    eval_ds = split["test"]
    texts = list(eval_ds["sms"])
    labels = np.asarray(eval_ds["label"], dtype=int)
    print(f"[calibrate_sms] n_calibration = {len(texts)}")

    print(f"[calibrate_sms] Collecting raw logits …")
    logits, labels = _collect_logits(texts, labels, batch=args.batch)

    # Baseline ECE (T = 1.0)
    probs_before = torch.softmax(torch.tensor(logits), dim=-1).numpy()[:, 1]
    ece_before = _ece(probs_before, labels)

    print(f"[calibrate_sms] Fitting temperature …")
    T = _learn_temperature(logits, labels, max_iter=args.max_iter)

    probs_after = torch.softmax(torch.tensor(logits) / T, dim=-1).numpy()[:, 1]
    ece_after = _ece(probs_after, labels)

    payload = {
        "temperature": round(T, 4),
        "calibration_split": "uci_heldout",
        "n_calibration": len(texts),
        "ece_before": round(ece_before, 4),
        "ece_after": round(ece_after, 4),
        "method": "Guo et al. 2017 — temperature scaling (L-BFGS, NLL)",
    }
    FINETUNED_DIR.mkdir(parents=True, exist_ok=True)
    TEMPERATURE_PATH.write_text(json.dumps(payload, indent=2) + "\n")

    print(f"\n[calibrate_sms] Learned T = {T:.4f}")
    print(f"[calibrate_sms] ECE  before = {ece_before:.4f}")
    print(f"[calibrate_sms] ECE  after  = {ece_after:.4f}")
    print(f"[calibrate_sms] Wrote {TEMPERATURE_PATH}")
    print(f"[calibrate_sms] services/sms_classifier.py will pick this up "
          f"automatically on next load.")


if __name__ == "__main__":
    main()
