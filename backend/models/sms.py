"""Pydantic models for the SMS checker endpoint."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SmsCheckRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class LimeHighlight(BaseModel):
    word: str
    weight: float = Field(ge=-1.0, le=1.0)


class SmsCheckResponse(BaseModel):
    text: str
    risk_score: int = Field(alias="riskScore", ge=0, le=100)
    prediction: Literal["scam", "legitimate"]
    confidence: float = Field(ge=0.0, le=1.0)
    lime_highlights: list[LimeHighlight] = Field(alias="limeHighlights")

    model_config = ConfigDict(populate_by_name=True)
