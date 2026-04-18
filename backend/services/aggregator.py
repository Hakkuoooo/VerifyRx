"""
In-memory aggregator for dashboard results.

Module 5 (dashboard) shows the user's most recent URL / SMS / image
check results side-by-side with a combined risk score. The three
checkers call save_*() after each analysis; GET /api/v1/dashboard
reads the current snapshot.

This is single-user in-memory state — fine for a thesis demo. A real
deployment would key results by session id and back them with Redis.
"""

from __future__ import annotations

from threading import Lock

from models.image import ImageCheckResponse
from models.sms import SmsCheckResponse
from models.url import UrlCheckResponse

_lock = Lock()
_state: dict[str, object] = {
    "url": None,
    "sms": None,
    "image": None,
}


def save_url_result(result: UrlCheckResponse) -> None:
    with _lock:
        _state["url"] = result


def save_sms_result(result: SmsCheckResponse) -> None:
    with _lock:
        _state["sms"] = result


def save_image_result(result: ImageCheckResponse) -> None:
    with _lock:
        _state["image"] = result


def snapshot() -> dict[str, object]:
    """Return the current results, plus a combined risk score.

    Returns deep copies of each Pydantic model so callers cannot mutate
    the stored state — important once we serialise them while another
    request is updating the same slot.
    """
    with _lock:
        url = _state["url"]
        sms = _state["sms"]
        image = _state["image"]
        url_copy = url.model_copy(deep=True) if url is not None else None
        sms_copy = sms.model_copy(deep=True) if sms is not None else None
        image_copy = (
            image.model_copy(deep=True) if image is not None else None
        )

    scores = [
        r.risk_score
        for r in (url_copy, sms_copy, image_copy)
        if r is not None
    ]
    overall = max(scores) if scores else 0

    return {
        "url": url_copy,
        "sms": sms_copy,
        "image": image_copy,
        "overall_risk_score": overall,
    }


def reset() -> None:
    """Clear all stored results. Used by tests."""
    with _lock:
        _state["url"] = None
        _state["sms"] = None
        _state["image"] = None
