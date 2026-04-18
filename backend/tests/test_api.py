"""
API-level smoke tests via FastAPI TestClient.

Scope:
  * /health liveness
  * /api/v1/check-sms round-trip (touches the real DistilBERT model — slow
    on first import but subsequent tests reuse the singleton, ~10s one-off)
  * /api/v1/dashboard returns a well-formed payload before and after
    writes
  * /api/v1/check-url rejects SSRF attempts with HTTP 422

These are smoke tests, not coverage tests — they're here so a regression
like "router broke response_model_by_alias" or "SMS router stopped
saving to the aggregator" fails the suite loudly.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest


pytestmark = pytest.mark.smoke


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
class TestHealth:
    def test_health_returns_ok(self, test_client):
        res = test_client.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# SMS endpoint
# ---------------------------------------------------------------------------
class TestSmsEndpoint:
    def test_check_sms_returns_camel_case_schema(self, test_client, reset_aggregator):
        payload = {"text": "Free Ozempic trial — claim now at bit.ly/xyz"}
        res = test_client.post("/api/v1/check-sms", json=payload)
        assert res.status_code == 200, res.text
        body = res.json()

        # The frontend expects camelCase aliases; fail loudly if that regresses.
        assert "riskScore" in body
        assert "limeHighlights" in body
        assert body["prediction"] in {"scam", "legitimate"}
        assert 0 <= body["riskScore"] <= 100
        assert 0.0 <= body["confidence"] <= 1.0
        assert isinstance(body["limeHighlights"], list)

    def test_check_sms_rejects_empty_body(self, test_client):
        res = test_client.post("/api/v1/check-sms", json={"text": ""})
        # Pydantic min_length=1 → 422.
        assert res.status_code == 422

    def test_check_sms_persists_to_dashboard(self, test_client, reset_aggregator):
        payload = {"text": "URGENT NHS refund — click bit.ly/nhs-refund-uk"}
        res = test_client.post("/api/v1/check-sms", json=payload)
        assert res.status_code == 200

        dash = test_client.get("/api/v1/dashboard")
        assert dash.status_code == 200
        body = dash.json()
        sms_slot = body["smsResult"]
        assert sms_slot is not None
        assert sms_slot["text"] == payload["text"]
        # overall is max of risk scores — at minimum the SMS we just posted.
        assert body["overallRiskScore"] >= sms_slot["riskScore"]


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
class TestDashboard:
    def test_empty_dashboard_shape(self, test_client, reset_aggregator):
        res = test_client.get("/api/v1/dashboard")
        assert res.status_code == 200
        body = res.json()
        # camelCase aliases emitted to match the frontend TypeScript interface
        expected = {"urlResult", "smsResult", "imageResult", "overallRiskScore", "timestamp"}
        assert set(body.keys()) >= expected
        assert body["urlResult"] is None
        assert body["smsResult"] is None
        assert body["imageResult"] is None
        assert body["overallRiskScore"] == 0


# ---------------------------------------------------------------------------
# URL endpoint — SSRF rejection (no network)
# ---------------------------------------------------------------------------
class TestUrlSsrfRejection:
    def test_loopback_returns_422(self, test_client):
        # Mock DNS so the test is deterministic + offline-safe.
        with patch(
            "utils.url_validator.socket.gethostbyname",
            return_value="127.0.0.1",
        ):
            res = test_client.post(
                "/api/v1/check-url",
                json={"url": "https://innocent-looking.test"},
            )
        assert res.status_code == 422
        assert "non-public IP" in res.json()["detail"]

    def test_cloud_metadata_address_returns_422(self, test_client):
        # 169.254.169.254 — AWS/GCP instance metadata. Classic SSRF target.
        with patch(
            "utils.url_validator.socket.gethostbyname",
            return_value="169.254.169.254",
        ):
            res = test_client.post(
                "/api/v1/check-url",
                json={"url": "https://anything.test"},
            )
        assert res.status_code == 422
