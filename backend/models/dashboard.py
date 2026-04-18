"""Pydantic models for the dashboard endpoint."""

from pydantic import BaseModel, ConfigDict, Field

from models.image import ImageCheckResponse
from models.sms import SmsCheckResponse
from models.url import UrlCheckResponse


class DashboardResponse(BaseModel):
    overall_risk_score: int = Field(alias="overallRiskScore", ge=0, le=100)
    url_result: UrlCheckResponse | None = Field(alias="urlResult", default=None)
    sms_result: SmsCheckResponse | None = Field(alias="smsResult", default=None)
    image_result: ImageCheckResponse | None = Field(alias="imageResult", default=None)
    timestamp: str

    model_config = ConfigDict(populate_by_name=True)
