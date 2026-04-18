"""
Evaluation artifact endpoint — GET /api/v1/evaluation.

Serves the JSON reports produced by the scripts/*evaluate*.py and
scripts/ablation_*.py tools. The frontend Results page consumes this to
render live tables of accuracy / precision / recall / F1 / ECE, the
ablation matrix, and the per-category OOD breakdown.

Why an API endpoint (rather than a static mount of the JSON):
  * The frontend gets a typed, camelCase payload via Pydantic aliases —
    the same pattern the other three checker endpoints use.
  * Missing files degrade gracefully (sms = null) instead of 404s.
  * We can add derived fields (summary deltas, provenance) without
    changing the file layout.

The accompanying PNG figures are served separately via the /reports
static mount registered in main.py.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from config import BACKEND_DIR

REPORTS_DIR = BACKEND_DIR / "reports"


router = APIRouter(tags=["evaluation"])


# ---------------------------------------------------------------------------
# Response models. Fields are intentionally loose (dict[str, Any]) for the
# metrics/ablation bodies — the eval scripts own that schema and we don't
# want two places to change whenever the report grows a new field.
# ---------------------------------------------------------------------------
class EvaluationFigures(BaseModel):
    """Relative URLs under /reports for the PNG plots."""
    model_config = ConfigDict(populate_by_name=True)


class SmsEvaluation(BaseModel):
    metrics: dict[str, Any] | None = None
    ablation: dict[str, Any] | None = None
    figures: dict[str, str] = Field(default_factory=dict)


class ImageEvaluation(BaseModel):
    metrics: dict[str, Any] | None = None
    ablation: dict[str, Any] | None = None
    external: dict[str, Any] | None = None
    figures: dict[str, str] = Field(default_factory=dict)


class EvaluationResponse(BaseModel):
    generated_at: str = Field(alias="generatedAt")
    sms: SmsEvaluation
    image: ImageEvaluation

    model_config = ConfigDict(populate_by_name=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _safe_read_json(path: Path) -> dict[str, Any] | None:
    """Return the parsed JSON at `path`, or None if missing / corrupt.

    Returning None (rather than raising) lets the frontend render a clean
    "no data — run the eval script" state on a fresh clone.
    """
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _exists(rel_path: str) -> str | None:
    """Return a /reports-rooted URL if the file exists, else None.

    The Results page uses the truthiness of each figure URL to decide
    whether to render the <img>, so we keep the absent state explicit.
    """
    full = REPORTS_DIR / rel_path
    return f"/reports/{rel_path}" if full.is_file() else None


def _collect_figures(rel_paths: dict[str, str]) -> dict[str, str]:
    """Filter to only figures that actually exist on disk."""
    out: dict[str, str] = {}
    for key, rel in rel_paths.items():
        url = _exists(rel)
        if url is not None:
            out[key] = url
    return out


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------
@router.get(
    "/evaluation",
    response_model=EvaluationResponse,
    response_model_by_alias=True,
)
def get_evaluation() -> EvaluationResponse:
    """Return the latest evaluation artifacts produced by the scripts/."""
    sms_metrics = _safe_read_json(REPORTS_DIR / "sms" / "metrics.json")
    sms_ablation = _safe_read_json(REPORTS_DIR / "sms" / "ablation.json")
    image_metrics = _safe_read_json(REPORTS_DIR / "image" / "metrics.json")
    image_ablation = _safe_read_json(REPORTS_DIR / "image" / "ablation.json")
    image_external = _safe_read_json(REPORTS_DIR / "image" / "external_metrics.json")

    sms_figures = _collect_figures({
        "confusionUci": "sms/figures/confusion_uci.png",
        "confusionOod": "sms/figures/confusion_ood.png",
        "reliabilityUci": "sms/figures/reliability_uci.png",
        "reliabilityOod": "sms/figures/reliability_ood.png",
        "ablationUci": "sms/figures/ablation_uci.png",
        "ablationOod": "sms/figures/ablation_ood.png",
    })
    image_figures = _collect_figures({
        "confusionVal": "image/figures/confusion_val.png",
        "reliabilityVal": "image/figures/reliability_val.png",
        "ablationVal": "image/figures/ablation_val.png",
        "confusionExternal": "image/figures/confusion_external.png",
        "reliabilityExternal": "image/figures/reliability_external.png",
    })

    return EvaluationResponse(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        sms=SmsEvaluation(
            metrics=sms_metrics,
            ablation=sms_ablation,
            figures=sms_figures,
        ),
        image=ImageEvaluation(
            metrics=image_metrics,
            ablation=image_ablation,
            external=image_external,
            figures=image_figures,
        ),
    )
