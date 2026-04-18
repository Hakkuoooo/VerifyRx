"""
Grad-CAM heatmap generator for ResNet-18.

Grad-CAM (Gradient-weighted Class Activation Mapping, Selvaraju 2017)
explains a CNN's classification by highlighting which regions of the
input image contributed most to the predicted class:

  1. Pick a convolutional layer (usually the last one — richest spatial
     features).
  2. Forward pass: cache activations at that layer.
  3. Backward pass from the target class's logit: cache gradients.
  4. For each activation channel, compute how important it is by
     global-average-pooling its gradients.
  5. Weight each activation map by its importance, sum, ReLU, normalize.
  6. Upsample to the original image size, colour-map, overlay.

The result is a (H, W) saliency map in [0, 1] — brighter = more
important to the prediction.
"""

from __future__ import annotations

import io
import uuid
from typing import Callable

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

from config import settings
from services import image_classifier

# Upper bound on PNGs kept in static/gradcams/. Each check writes one file
# (~50-300 KB), so 100 files cap this directory at ~30 MB for a long demo
# run. Pruning is best-effort and runs at the top of generate().
_MAX_GRADCAM_FILES = 100


def _prune_gradcams(keep: int = _MAX_GRADCAM_FILES) -> None:
    """Delete oldest PNGs in the gradcam dir until at most `keep` remain."""
    out_dir = settings.static_dir / settings.gradcam_subdir
    try:
        pngs = sorted(
            out_dir.glob("*.png"), key=lambda p: p.stat().st_mtime
        )
    except OSError:
        return  # dir missing — generate() will recreate it
    excess = len(pngs) - keep
    for stale in pngs[:excess] if excess > 0 else []:
        try:
            stale.unlink()
        except OSError:
            # Best-effort; another request may have deleted it already.
            pass

# Colour map for the heatmap overlay. Using a simple "jet"-like gradient
# implemented in numpy so we avoid pulling in matplotlib at runtime.
_JET_STOPS = np.array(
    [
        [0.0, 0.0, 0.5],   # deep blue
        [0.0, 0.0, 1.0],   # blue
        [0.0, 1.0, 1.0],   # cyan
        [1.0, 1.0, 0.0],   # yellow
        [1.0, 0.5, 0.0],   # orange
        [1.0, 0.0, 0.0],   # red
    ]
)


def _jet_colormap(values: np.ndarray) -> np.ndarray:
    """Map a float32 array in [0, 1] to an RGB uint8 array."""
    values = np.clip(values, 0.0, 1.0)
    n_stops = _JET_STOPS.shape[0] - 1
    scaled = values * n_stops
    low = np.floor(scaled).astype(int)
    high = np.clip(low + 1, 0, n_stops)
    frac = (scaled - low)[..., None]
    rgb = (1 - frac) * _JET_STOPS[low] + frac * _JET_STOPS[high]
    return (rgb * 255).astype(np.uint8)


def _overlay(pil_image: Image.Image, heatmap: np.ndarray, alpha: float = 0.5) -> Image.Image:
    """Alpha-blend a (H, W) heatmap over the original image."""
    # Resize heatmap to the original image size.
    hm_image = Image.fromarray(_jet_colormap(heatmap), mode="RGB").resize(
        pil_image.size, Image.BILINEAR
    )
    base = pil_image.convert("RGB")
    return Image.blend(base, hm_image, alpha)


def generate(pil_image: Image.Image, target_class: int) -> str:
    """
    Compute a Grad-CAM heatmap for the given image + class index, save
    the overlay to disk, and return its public URL path.

    Args:
        pil_image: The original user-uploaded image (PIL.Image).
        target_class: Which output class to explain (0 = authentic,
                      1 = counterfeit).

    Returns:
        A relative URL like "/static/gradcams/<uuid>.png" that the
        frontend can prefix with the backend host.
        Returns "" if heatmap generation failed — the router should
        treat this as "no visualisation available" and still render
        the prediction.
    """
    try:
        _prune_gradcams()
        model, preprocess = image_classifier.get_model_and_transform()

        tensor = preprocess(pil_image.convert("RGB")).unsqueeze(0)
        tensor.requires_grad_(True)

        # Target the last conv block of ResNet-18 — the canonical choice
        # for Grad-CAM. Registering hooks lets us intercept the
        # activations and gradients at that point in the graph.
        target_layer = model.layer4[-1]
        activations: list[torch.Tensor] = []
        gradients: list[torch.Tensor] = []

        def fwd_hook(_module, _inp, out):
            activations.append(out)

        def bwd_hook(_module, _grad_in, grad_out):
            gradients.append(grad_out[0])

        h1 = target_layer.register_forward_hook(fwd_hook)
        h2 = target_layer.register_full_backward_hook(bwd_hook)

        try:
            model.zero_grad()
            logits = model(tensor)
            # Back-prop from the target class logit only. This is what
            # "gradient with respect to class X" means.
            score = logits[0, target_class]
            score.backward()
        finally:
            h1.remove()
            h2.remove()

        act = activations[0].detach()[0]       # (C, H, W)
        grad = gradients[0].detach()[0]        # (C, H, W)
        weights = grad.mean(dim=(1, 2))         # (C,) — global average pool
        cam = (weights[:, None, None] * act).sum(dim=0)  # (H, W)
        cam = F.relu(cam)

        # Normalise to [0, 1]. Guard against all-zero maps (when ReLU
        # kills everything) so we don't divide by zero.
        cam -= cam.min()
        max_val = cam.max()
        if max_val > 0:
            cam /= max_val
        heatmap = cam.cpu().numpy()

        overlay = _overlay(pil_image, heatmap)

        # Save to the static dir with a random filename so concurrent
        # requests don't collide.
        filename = f"{uuid.uuid4().hex}.png"
        out_dir = settings.static_dir / settings.gradcam_subdir
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / filename
        overlay.save(out_path, format="PNG", optimize=True)

        return f"/static/{settings.gradcam_subdir}/{filename}"
    except Exception:
        # Heatmap generation is best-effort — any failure should not
        # break the classification response.
        return ""
