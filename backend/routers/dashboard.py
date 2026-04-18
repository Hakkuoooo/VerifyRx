"""
Dashboard route — GET /api/v1/dashboard.

Returns the most recent result from each checker plus an overall
combined risk score (max of the three). State lives in
services.aggregator.
"""

from datetime import datetime, timezone

from fastapi import APIRouter

from models.dashboard import DashboardResponse
from services import aggregator

router = APIRouter(tags=["dashboard"])


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    response_model_by_alias=True,
)
def get_dashboard() -> DashboardResponse:
    snap = aggregator.snapshot()
    return DashboardResponse(
        overall_risk_score=int(snap["overall_risk_score"]),
        url_result=snap["url"],
        sms_result=snap["sms"],
        image_result=snap["image"],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
