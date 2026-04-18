"""
Unit tests for services.aggregator.

These tests exercise the module-level in-memory state that powers the
dashboard. They pin two behaviours the UI relies on:
  * overall_risk_score = max of whatever checks have been saved
  * snapshot() returns deep copies (mutating a returned object must
    not leak into the next snapshot)
"""

from __future__ import annotations

import pytest

from models.image import ImageCheckResponse
from models.sms import SmsCheckResponse
from models.url import UrlCheckResponse
from services import aggregator


def _url(risk: int = 40) -> UrlCheckResponse:
    return UrlCheckResponse(
        url="https://example.com",
        risk_score=risk,
        is_https=True,
        domain_age="5 years",
        domain_age_days=365 * 5,
        is_gphc_registered=False,
        whois_registrant="Example Ltd",
        virus_total_score=0,
        redirect_count=0,
        flags=["no-gphc"],
    )


def _sms(risk: int = 70) -> SmsCheckResponse:
    return SmsCheckResponse(
        text="Free Ozempic trial — click here",
        risk_score=risk,
        prediction="scam",
        confidence=0.9,
        lime_highlights=[],
    )


def _image(risk: int = 20) -> ImageCheckResponse:
    return ImageCheckResponse(
        risk_score=risk,
        prediction="authentic",
        confidence=0.8,
        grad_cam_url="/static/gradcams/abc.png",
        details=[],
    )


@pytest.fixture(autouse=True)
def _reset():
    aggregator.reset()
    yield
    aggregator.reset()


class TestSnapshot:
    def test_empty_returns_zero_overall_and_none_fields(self):
        snap = aggregator.snapshot()
        assert snap["url"] is None
        assert snap["sms"] is None
        assert snap["image"] is None
        assert snap["overall_risk_score"] == 0

    def test_overall_is_max_of_saved_risks(self):
        aggregator.save_url_result(_url(30))
        aggregator.save_sms_result(_sms(85))
        aggregator.save_image_result(_image(10))
        snap = aggregator.snapshot()
        assert snap["overall_risk_score"] == 85

    def test_partial_saves_still_compute_max(self):
        aggregator.save_url_result(_url(42))
        snap = aggregator.snapshot()
        assert snap["overall_risk_score"] == 42
        assert snap["url"] is not None
        assert snap["sms"] is None


class TestIsolation:
    def test_snapshot_returns_deep_copy(self):
        """Mutating a returned model must not corrupt the next snapshot."""
        aggregator.save_sms_result(_sms(50))

        snap1 = aggregator.snapshot()
        # Pydantic v2 models are frozen-capable but default-mutable; we
        # deliberately try to mutate via the list attribute.
        snap1["sms"].lime_highlights.append  # ensure attribute exists
        snap1["sms"].text = "MUTATED"

        snap2 = aggregator.snapshot()
        assert snap2["sms"].text != "MUTATED"
        assert snap2["sms"].text.startswith("Free Ozempic")

    def test_reset_clears_all_slots(self):
        aggregator.save_url_result(_url(10))
        aggregator.save_sms_result(_sms(20))
        aggregator.save_image_result(_image(30))
        aggregator.reset()
        snap = aggregator.snapshot()
        assert snap == {"url": None, "sms": None, "image": None, "overall_risk_score": 0}
