"""
SMS checker route — POST /api/v1/check-sms.

Pipeline: DistilBERT classifier → LIME per-word explanation → stored
in the dashboard aggregator.
"""

from fastapi import APIRouter

from models.sms import SmsCheckRequest, SmsCheckResponse
from services import aggregator, lime_explainer, sms_classifier

router = APIRouter(tags=["sms"])


@router.post(
    "/check-sms",
    response_model=SmsCheckResponse,
    response_model_by_alias=True,
)
def check_sms(body: SmsCheckRequest) -> SmsCheckResponse:
    result = sms_classifier.classify(body.text)
    highlights = lime_explainer.explain(body.text)

    response = SmsCheckResponse(
        text=body.text,
        risk_score=result["risk_score"],
        prediction=result["prediction"],
        confidence=result["confidence"],
        lime_highlights=highlights,
    )

    aggregator.save_sms_result(response)
    return response
