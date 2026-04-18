"""
SMS scam classifier — DistilBERT-based.

Loading strategy (checked in order):
  1. Fine-tuned weights at models_cache/sms/ (produced by
     scripts/train_sms.py). Used when available.
  2. settings.sms_model_name — a Hugging Face Hub model id. Defaults to
     a pretrained SMS-spam classifier so the endpoint works before any
     training has been done.

The model, tokenizer, and pipeline are module-level singletons that
load lazily on the first inference call. This keeps server startup
instant and avoids the ~250MB cost when the student is iterating on
unrelated endpoints.
"""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any

import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from config import BACKEND_DIR, settings

# Fine-tuned artifacts land here after running scripts/train_sms.py.
FINETUNED_DIR = BACKEND_DIR / "models_cache" / "sms"

# Optional temperature-scaling calibration file produced by
# scripts/calibrate_sms.py. When present, logits are divided by T
# before softmax (Guo et al. 2017). Argmax is unchanged — only
# probability calibration shifts. Delete the file to disable.
TEMPERATURE_PATH = FINETUNED_DIR / "temperature.json"

# Label maps vary between models. We normalise whatever the loaded
# model reports to a canonical ("ham"/"spam") scheme.
_SPAM_LABELS = {"spam", "label_1", "scam", "1"}
_HAM_LABELS = {"ham", "label_0", "legitimate", "not_spam", "0"}

_lock = Lock()
_bundle: dict[str, Any] | None = None  # populated on first call


def _resolve_model_source() -> tuple[str, bool]:
    """Return (path-or-hub-id, is_finetuned)."""
    if FINETUNED_DIR.exists() and (FINETUNED_DIR / "config.json").is_file():
        return str(FINETUNED_DIR), True
    return settings.sms_model_name, False


def _load() -> dict[str, Any]:
    """Load tokenizer + model once, cache in module-level _bundle."""
    global _bundle
    if _bundle is not None:
        return _bundle

    with _lock:
        if _bundle is not None:
            return _bundle  # another thread loaded it while we waited

        source, is_finetuned = _resolve_model_source()
        tokenizer = AutoTokenizer.from_pretrained(source)
        model = AutoModelForSequenceClassification.from_pretrained(source)
        model.eval()

        # Build a mapping from the model's integer label indices to our
        # canonical "scam"/"legitimate" strings.
        id2label = {
            int(i): lbl.lower() for i, lbl in model.config.id2label.items()
        }
        spam_idx = None
        for i, lbl in id2label.items():
            if lbl in _SPAM_LABELS:
                spam_idx = i
                break
        # Fallback: assume label_1 is the "spam/positive" class (the
        # HuggingFace convention for binary classifiers).
        if spam_idx is None:
            spam_idx = 1 if model.config.num_labels == 2 else 0

        # Opt-in post-hoc calibration. A corrupt / mis-shaped file is
        # silently ignored so a bad calibration run can't brick
        # inference — worst case we fall back to T = 1.0.
        temperature = 1.0
        if TEMPERATURE_PATH.is_file():
            try:
                cal = json.loads(TEMPERATURE_PATH.read_text())
                t_val = float(cal.get("temperature", 1.0))
                if t_val > 0 and np.isfinite(t_val):
                    temperature = t_val
            except (ValueError, OSError, TypeError):
                temperature = 1.0

        _bundle = {
            "tokenizer": tokenizer,
            "model": model,
            "spam_idx": spam_idx,
            "is_finetuned": is_finetuned,
            "source": source,
            "temperature": temperature,
        }
        return _bundle


def predict_proba(texts: list[str]) -> np.ndarray:
    """
    Run the model and return class probabilities, shape (N, 2),
    columns = [legitimate_prob, scam_prob].

    Exposed separately from classify() because LIME needs a callable
    that accepts raw text and returns a probability matrix.
    """
    bundle = _load()
    tokenizer = bundle["tokenizer"]
    model = bundle["model"]
    spam_idx = bundle["spam_idx"]
    temperature = bundle["temperature"]

    encoded = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=256,
        return_tensors="pt",
    )
    with torch.no_grad():
        logits = model(**encoded).logits
    # Temperature scaling (Guo et al. 2017): divide logits by T before
    # softmax. T > 1 flattens over-confident probs; argmax is preserved.
    if temperature != 1.0:
        logits = logits / temperature
    probs = torch.softmax(logits, dim=-1).cpu().numpy()

    # Reorder so column 0 is always "legitimate" and column 1 is "scam"
    # regardless of the underlying model's label order.
    ham_idx = 1 - spam_idx if probs.shape[1] == 2 else 0
    return np.stack([probs[:, ham_idx], probs[:, spam_idx]], axis=1)


def classify(text: str) -> dict[str, Any]:
    """
    Classify a single SMS. Returns a dict with the fields the router needs:
        prediction:   "scam" | "legitimate"
        confidence:   float in [0, 1]
        risk_score:   int in [0, 100]
        is_finetuned: bool — True when loaded from models_cache/sms/
    """
    probs = predict_proba([text])[0]  # shape (2,)
    scam_prob = float(probs[1])
    prediction = "scam" if scam_prob >= 0.5 else "legitimate"
    confidence = scam_prob if prediction == "scam" else 1.0 - scam_prob
    return {
        "prediction": prediction,
        "confidence": round(confidence, 4),
        "risk_score": round(scam_prob * 100),
        "is_finetuned": _load()["is_finetuned"],
    }
