"""
Image classifier — ResNet-18 for authentic vs counterfeit medicine packs.

Loading strategy:
  1. If settings.image_model_path is set and the file exists, load
     fine-tuned weights from there.
  2. Else, if models_cache/image/resnet18_finetuned.pt exists, load it.
  3. Else, fall back to an ImageNet-pretrained ResNet-18 with a
     randomly-initialised 2-class head — "demo mode". Predictions are
     effectively random; the router flags this so the UI can warn the
     user.

Training is the student's responsibility via scripts/train_image.py.
Inference is always available.
"""

from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from torchvision import models, transforms

from config import BACKEND_DIR, settings

_DEFAULT_FINETUNED_PATH = BACKEND_DIR / "models_cache" / "image" / "resnet18_finetuned.pt"

# Canonical class order: index 0 = authentic, 1 = counterfeit.
# train_image.py saves weights trained with this same ordering.
CLASS_NAMES = ["authentic", "counterfeit"]

# Standard ImageNet preprocessing. The ResNet backbone was trained with
# these stats, and our fine-tune keeps them.
_preprocess = transforms.Compose(
    [
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        ),
    ]
)

_lock = Lock()
_bundle: dict[str, Any] | None = None


def _build_model() -> nn.Module:
    """Create a ResNet-18 with a 2-class head."""
    net = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
    net.fc = nn.Linear(net.fc.in_features, len(CLASS_NAMES))
    return net


def _resolve_weights_path() -> Path | None:
    """Which fine-tuned weights file to use, if any."""
    candidate = settings.image_model_path or str(_DEFAULT_FINETUNED_PATH)
    path = Path(candidate)
    return path if path.is_file() else None


def _load() -> dict[str, Any]:
    global _bundle
    if _bundle is not None:
        return _bundle

    with _lock:
        if _bundle is not None:
            return _bundle

        net = _build_model()
        weights_path = _resolve_weights_path()
        is_finetuned = False

        if weights_path is not None:
            state = torch.load(weights_path, map_location="cpu", weights_only=True)
            net.load_state_dict(state)
            is_finetuned = True

        net.eval()
        _bundle = {
            "model": net,
            "is_finetuned": is_finetuned,
            "weights_path": str(weights_path) if weights_path else None,
        }
        return _bundle


def _preprocess_image(image: Image.Image) -> torch.Tensor:
    """Convert a PIL image to a (1, 3, 224, 224) float tensor."""
    if image.mode != "RGB":
        image = image.convert("RGB")
    return _preprocess(image).unsqueeze(0)


def predict(image: Image.Image) -> dict[str, Any]:
    """
    Classify a single image.

    Returns a dict with:
        prediction:   "authentic" | "counterfeit"
        confidence:   float in [0, 1]
        risk_score:   int in [0, 100]  (100 = certain counterfeit)
        is_finetuned: bool
    """
    bundle = _load()
    net = bundle["model"]

    tensor = _preprocess_image(image)
    with torch.no_grad():
        logits = net(tensor)
    probs = F.softmax(logits, dim=1)[0].cpu().numpy()
    counterfeit_prob = float(probs[1])

    prediction = "counterfeit" if counterfeit_prob >= 0.5 else "authentic"
    confidence = counterfeit_prob if prediction == "counterfeit" else 1.0 - counterfeit_prob
    return {
        "prediction": prediction,
        "confidence": round(float(confidence), 4),
        "risk_score": round(counterfeit_prob * 100),
        "is_finetuned": bundle["is_finetuned"],
    }


def get_model_and_transform() -> tuple[nn.Module, transforms.Compose]:
    """
    Accessor used by the Grad-CAM service. Returns the loaded network
    (weights attached) and the preprocessing pipeline so the two stay
    in sync.
    """
    bundle = _load()
    return bundle["model"], _preprocess
