"""
Application configuration.

Loads environment variables from a .env file (or the OS environment) into a
typed Settings object. Access config elsewhere via: `from config import settings`.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    # VirusTotal API key. Empty string = skip VirusTotal checks (dev-friendly).
    virustotal_api_key: str = ""

    # Which origins can call this API from a browser. The frontend runs on 3000.
    cors_origins: list[str] = ["http://localhost:3000"]

    # Timeout (seconds) for all outbound HTTP requests.
    request_timeout: int = 10

    # --- ML model config ---
    # SMS classifier: a pre-trained SMS-spam model from Hugging Face Hub.
    # First-run download ~17 MB. Swap this to a local path to use fine-tuned
    # weights (see scripts/train_sms.py).
    sms_model_name: str = "mrm8488/bert-tiny-finetuned-sms-spam-detection"

    # Image classifier: optional path to fine-tuned ResNet-18 weights. When
    # empty, the image service runs in "demo mode" using ImageNet features
    # (see services/image_classifier.py).
    image_model_path: str = ""

    # Where Grad-CAM heatmaps are written for serving via /static.
    static_dir: Path = BACKEND_DIR / "static"
    gradcam_subdir: str = "gradcams"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


# Singleton — import this everywhere, don't instantiate Settings() elsewhere.
settings = Settings()

# Defense-in-depth: a misconfigured STATIC_DIR env var must never let the
# /static mount escape the backend directory (e.g. serving `/`).
_static_resolved = Path(settings.static_dir).resolve()
if not _static_resolved.is_relative_to(BACKEND_DIR.resolve()):
    raise RuntimeError(
        f"Refusing to start: static_dir {_static_resolved} is not under "
        f"BACKEND_DIR {BACKEND_DIR}. Fix STATIC_DIR in your .env."
    )

# Ensure the static/gradcams dir exists at startup so we never fail on first save.
(settings.static_dir / settings.gradcam_subdir).mkdir(parents=True, exist_ok=True)
