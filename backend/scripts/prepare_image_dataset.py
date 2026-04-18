"""
Generate synthetic 'counterfeit' training samples from authentic images.

Motivation:
There is no public dataset of counterfeit medicine pack photos. The
standard thesis-safe approach is to take authentic pack images the
student can source legally (Boots/Superdrug product pages, own photos)
and synthesise counterfeit-looking variants via targeted augmentations
that mimic real counterfeiter mistakes:

  * Colour shift (HSV hue jitter) — cheap printers drift colour
  * JPEG re-encode at low quality — blocky compression artifacts
  * Gaussian blur + noise — out-of-focus / low-DPI print defects
  * Small rotation + brightness shift — inconsistent photo conditions

Each authentic image produces N=3 counterfeit variants by default.

Usage:
    cd backend
    python -m scripts.prepare_image_dataset
    python -m scripts.prepare_image_dataset --per-image 5 --seed 7

Expected folder layout:
    data/images/authentic/   <-- student populates this (JPG/PNG)
    data/images/counterfeit/ <-- this script writes here
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

BACKEND_DIR = Path(__file__).resolve().parent.parent
AUTHENTIC_DIR = BACKEND_DIR / "data" / "images" / "authentic"
COUNTERFEIT_DIR = BACKEND_DIR / "data" / "images" / "counterfeit"

SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def _jitter_hue(img: Image.Image, degrees: float) -> Image.Image:
    """Rotate the hue channel. `degrees` in [-180, 180]."""
    arr = np.asarray(img.convert("HSV")).astype(np.int16)
    # PIL HSV uses 0–255 for hue; 256 = full circle.
    arr[..., 0] = (arr[..., 0] + int(degrees / 360 * 256)) % 256
    return Image.fromarray(arr.astype(np.uint8), mode="HSV").convert("RGB")


def _jpeg_recompress(img: Image.Image, quality: int) -> Image.Image:
    """Save + reload through JPEG at low quality to induce blockiness."""
    from io import BytesIO

    buf = BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    return Image.open(buf).copy()


def _add_noise(img: Image.Image, sigma: float) -> Image.Image:
    arr = np.asarray(img.convert("RGB")).astype(np.float32)
    noise = np.random.normal(0, sigma, arr.shape)
    return Image.fromarray(np.clip(arr + noise, 0, 255).astype(np.uint8), mode="RGB")


def _augment(img: Image.Image, rng: random.Random) -> Image.Image:
    """Apply a random combination of counterfeit-like augmentations."""
    out = img.convert("RGB")

    # Hue jitter — chromatic drift of a cheap printer.
    out = _jitter_hue(out, rng.uniform(-30, 30))

    # JPEG recompress at low quality — blocky artifacts.
    out = _jpeg_recompress(out, quality=rng.randint(15, 35))

    # Blur — out-of-focus camera / low-DPI print.
    blur_radius = rng.uniform(1.0, 3.5)
    out = out.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    # Additive Gaussian noise — sensor noise / cheap scan.
    out = _add_noise(out, sigma=rng.uniform(3.0, 9.0))

    # Slight rotation — sloppy handheld photography.
    angle = rng.uniform(-6, 6)
    out = out.rotate(angle, resample=Image.BILINEAR, fillcolor=(0, 0, 0))

    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--per-image",
        type=int,
        default=3,
        help="Number of counterfeit variants per authentic image",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Delete existing counterfeit/ contents before generating",
    )
    args = parser.parse_args()

    rng = random.Random(args.seed)

    if not AUTHENTIC_DIR.is_dir():
        raise SystemExit(
            f"Authentic directory not found: {AUTHENTIC_DIR}\n"
            f"Populate it with pack photos (JPG/PNG) and re-run."
        )

    sources = [p for p in AUTHENTIC_DIR.iterdir() if p.suffix.lower() in SUPPORTED_EXT]
    if not sources:
        raise SystemExit(f"No images found under {AUTHENTIC_DIR}")

    COUNTERFEIT_DIR.mkdir(parents=True, exist_ok=True)
    if args.overwrite:
        for p in COUNTERFEIT_DIR.iterdir():
            if p.is_file():
                p.unlink()

    print(
        f"[prepare_image_dataset] {len(sources)} authentic image(s); "
        f"generating {args.per_image} variants each → "
        f"{len(sources) * args.per_image} total."
    )

    np.random.seed(args.seed)
    total = 0
    for src in sources:
        try:
            img = Image.open(src)
            img.load()
        except Exception as exc:
            print(f"  skipped {src.name}: {exc}")
            continue

        for i in range(args.per_image):
            out = _augment(img, rng)
            out_path = COUNTERFEIT_DIR / f"{src.stem}__fake_{i}.jpg"
            out.convert("RGB").save(out_path, format="JPEG", quality=88)
            total += 1

    print(f"[prepare_image_dataset] Wrote {total} counterfeit sample(s) to {COUNTERFEIT_DIR}")
    print(
        "[prepare_image_dataset] Next: python -m scripts.train_image"
    )


if __name__ == "__main__":
    main()
