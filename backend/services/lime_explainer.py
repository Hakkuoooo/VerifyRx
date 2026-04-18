"""
LIME wrapper — per-word explanations for SMS classification.

LIME (Local Interpretable Model-agnostic Explanations) works by
perturbing the input (removing random words), asking the real model to
re-predict on those variants, and fitting a simple linear model to the
perturbations. The linear model's coefficients are the "weights" per
word — positive = pushes toward scam, negative = pushes toward
legitimate.

It's model-agnostic: we could swap DistilBERT for any other classifier
with zero changes here.
"""

from __future__ import annotations

from threading import Lock

from lime.lime_text import LimeTextExplainer

from models.sms import LimeHighlight
from services import sms_classifier

# Number of perturbed samples LIME generates per explanation. Higher =
# more stable weights but slower. 500 takes ~2s on CPU for DistilBERT.
_NUM_SAMPLES = 500

# Maximum number of highlighted tokens returned to the frontend.
_TOP_K = 15

_lock = Lock()
_explainer: LimeTextExplainer | None = None


def _get_explainer() -> LimeTextExplainer:
    """Lazy-init a reusable explainer. Safe to share across requests."""
    global _explainer
    if _explainer is not None:
        return _explainer
    with _lock:
        if _explainer is None:
            _explainer = LimeTextExplainer(
                class_names=["legitimate", "scam"],
                bow=False,  # respect word order — matters for attention-based models
            )
    return _explainer


def explain(text: str) -> list[LimeHighlight]:
    """
    Return the top-K token-level weights for a single SMS.

    Returns an empty list on any failure (LIME's perturbation loop can
    occasionally produce degenerate cases on very short inputs). That's
    acceptable — the rest of the response still renders cleanly.
    """
    try:
        explainer = _get_explainer()
        explanation = explainer.explain_instance(
            text,
            sms_classifier.predict_proba,
            num_features=_TOP_K,
            num_samples=_NUM_SAMPLES,
            labels=[1],  # explain the "scam" class only
        )
        # as_list(label=1) returns [(word, weight), ...] sorted by
        # importance. Positive weight pushes toward scam.
        pairs = explanation.as_list(label=1)
    except Exception:
        return []

    highlights: list[LimeHighlight] = []
    for word, weight in pairs:
        # LIME weights are unbounded; clip to [-1, 1] to match the
        # Pydantic schema and the frontend's gauge rendering.
        clipped = max(-1.0, min(1.0, float(weight)))
        highlights.append(LimeHighlight(word=word, weight=clipped))
    return highlights
