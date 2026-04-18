"""
Image checker route — POST /api/v1/check-image.

Pipeline: validate upload → open with PIL → ResNet-18 classify →
Grad-CAM heatmap for the predicted class → save response to aggregator.

Request scheme: scheme + host from the incoming Request are used to
build absolute gradCamUrl values so the frontend can load them
directly without knowing the backend origin up front.
"""

import asyncio
from io import BytesIO

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status
from PIL import Image, UnidentifiedImageError

from models.image import ImageCheckResponse
from services import aggregator, gradcam, image_classifier

router = APIRouter(tags=["image"])

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def _absolute_url(request: Request, relative: str) -> str:
    """Turn /static/foo.png into http://host:port/static/foo.png."""
    if not relative:
        return ""
    base = str(request.base_url).rstrip("/")
    return f"{base}{relative}"


@router.post(
    "/check-image",
    response_model=ImageCheckResponse,
    response_model_by_alias=True,
)
async def check_image(
    request: Request, file: UploadFile = File(...)
) -> ImageCheckResponse:
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{file.content_type}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_MIME_TYPES))}",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large ({len(contents)} bytes); "
            f"max {MAX_FILE_SIZE_BYTES} bytes",
        )

    try:
        image = Image.open(BytesIO(contents))
        image.load()  # force decode now so we catch corrupt files up-front
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not decode image: {exc}",
        ) from exc

    # Classify — loads the model lazily on first call. The forward pass is
    # CPU-bound and runs for tens of milliseconds on laptops, so push it
    # to a worker thread to keep the event loop responsive under load.
    verdict = await asyncio.to_thread(image_classifier.predict, image)

    # Build explanation details. Be honest when running without
    # fine-tuned weights: the frontend can surface this to the user.
    details: list[str] = []
    if not verdict["is_finetuned"]:
        details.append(
            "Demo mode — no fine-tuned weights loaded. "
            "Run scripts/train_image.py to enable real predictions."
        )
    details.append(
        f"Model predicted '{verdict['prediction']}' "
        f"with {verdict['confidence']:.0%} confidence."
    )

    # Grad-CAM for the predicted class (maps the heat to whatever the
    # model thinks it sees — most interpretable for the user).
    target_class = 1 if verdict["prediction"] == "counterfeit" else 0
    # Grad-CAM does a second forward + full backward pass; same story — off
    # the event loop.
    relative_url = await asyncio.to_thread(
        gradcam.generate, image, target_class
    )
    grad_cam_url = _absolute_url(request, relative_url)

    response = ImageCheckResponse(
        risk_score=verdict["risk_score"],
        prediction=verdict["prediction"],
        confidence=verdict["confidence"],
        grad_cam_url=grad_cam_url,
        details=details,
    )
    aggregator.save_image_result(response)
    return response
