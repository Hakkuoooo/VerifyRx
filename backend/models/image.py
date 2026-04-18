"""Pydantic models for the image checker endpoint."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ImageCheckResponse(BaseModel):
    risk_score: int = Field(alias="riskScore", ge=0, le=100)
    prediction: Literal["counterfeit", "authentic"]
    confidence: float = Field(ge=0.0, le=1.0)
    grad_cam_url: str = Field(alias="gradCamUrl")
    details: list[str]

    model_config = ConfigDict(populate_by_name=True)
