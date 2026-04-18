"""
URL checker route — POST /api/v1/check-url.

Delegates all logic to services.url_checker.check_url(). Sync def is
intentional — FastAPI runs sync handlers in a threadpool, which is
what we want for blocking I/O (requests, whois).
"""

from fastapi import APIRouter, HTTPException, status

from models.url import UrlCheckRequest, UrlCheckResponse
from services import aggregator
from services.url_checker import check_url as run_url_check

router = APIRouter(tags=["url"])


@router.post(
    "/check-url",
    response_model=UrlCheckResponse,
    response_model_by_alias=True,  # emit camelCase to match the frontend
)
def check_url_endpoint(body: UrlCheckRequest) -> UrlCheckResponse:
    try:
        response = run_url_check(body.url)
    except ValueError as exc:
        # validate_url() raises ValueError for malformed URLs, bad
        # schemes, and SSRF attempts. 422 ("Unprocessable Entity") is
        # the right code — the request was well-formed HTTP but the URL
        # itself failed validation.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    aggregator.save_url_result(response)
    return response
