"""Pydantic models for the URL checker endpoint."""

from pydantic import BaseModel, ConfigDict, Field


class UrlCheckRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)


class UrlCheckResponse(BaseModel):
    # Fields use Python snake_case internally but serialize as camelCase JSON
    # (via aliases) to match the frontend's TypeScript interfaces.
    url: str
    risk_score: int = Field(alias="riskScore", ge=0, le=100)
    is_https: bool = Field(alias="isHttps")
    domain_age: str = Field(alias="domainAge")
    domain_age_days: int = Field(alias="domainAgeDays", ge=0)
    is_gphc_registered: bool = Field(alias="isGphcRegistered")
    whois_registrant: str = Field(alias="whoisRegistrant")
    virus_total_score: int = Field(alias="virusTotalScore", ge=0, le=100)
    redirect_count: int = Field(alias="redirectCount", ge=0)
    flags: list[str]

    # populate_by_name=True lets us construct with snake_case OR camelCase.
    model_config = ConfigDict(populate_by_name=True)
