"""
VerifyRX UK FastAPI backend — entry point.

Run locally with:
    uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import BACKEND_DIR, settings
from routers import dashboard, evaluation, image, sms, url

app = FastAPI(
    title="VerifyRX UK API",
    description="Counterfeit medicine detection — URL, SMS, and image analysis.",
    version="0.1.0",
)

# CORS — allow the frontend (localhost:3000) to call this API from the browser.
# Wildcard origins combined with allow_credentials=True is silently blocked by
# browsers and is a footgun; fail loudly at startup instead.
if "*" in settings.cors_origins:
    raise RuntimeError(
        "CORS misconfiguration: allow_credentials=True is incompatible with "
        "wildcard origins. Set CORS_ORIGINS to an explicit list in .env."
    )
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# All feature routes live under /api/v1 so we can version the API later
# without breaking existing clients.
API_PREFIX = "/api/v1"
app.include_router(url.router, prefix=API_PREFIX)
app.include_router(sms.router, prefix=API_PREFIX)
app.include_router(image.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(evaluation.router, prefix=API_PREFIX)

# Serve Grad-CAM heatmaps and any other static assets. The image checker
# writes PNGs to {static_dir}/gradcams/ and returns URLs like
# http://localhost:8000/static/gradcams/<uuid>.png to the frontend.
app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

# Serve evaluation-report PNGs (confusion matrices, reliability diagrams,
# ablation bars). The Results page renders <img src="/reports/..."/>
# against this mount. The directory is created lazily on first eval run
# so `mkdir` here guarantees the mount never 500s on a fresh clone.
_REPORTS_DIR = BACKEND_DIR / "reports"
_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/reports", StaticFiles(directory=_REPORTS_DIR), name="reports")


@app.get("/health")
def health():
    """Simple liveness check. Returns 200 if the server is up."""
    return {"status": "ok"}
