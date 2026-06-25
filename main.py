import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.complaints import router as complaint_router
from routes.auth import router as auth_router
from routes.admin import router as admin_router
from routes.officer import router as officer_router
from routes.citizen import router as citizen_router
from scheduler.notification_scheduler import start_notification_scheduler, stop_notification_scheduler
from services.storage_service import is_s3_enabled

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("civic_ai")

app = FastAPI(title="Civic Complaint AI Backend", version="1.0.0")

origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(complaint_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(officer_router)
app.include_router(citizen_router)

# Legacy local uploads — only mount when S3 is off or old files may still exist
uploads_path = Path("uploads")
if not is_s3_enabled() or uploads_path.exists():
    uploads_path.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")


@app.on_event("startup")
def on_startup() -> None:
    start_notification_scheduler()


@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_notification_scheduler()


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    started = time.perf_counter()
    logger.info(
        "HTTP request started method=%s path=%s query=%s client=%s",
        request.method,
        request.url.path,
        request.url.query,
        request.client.host if request.client else "unknown",
    )

    try:
        response = await call_next(request)
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.exception(
            "HTTP request failed method=%s path=%s duration_ms=%.2f error=%s",
            request.method,
            request.url.path,
            elapsed_ms,
            exc,
        )
        raise

    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info(
        "HTTP request completed method=%s path=%s status=%s duration_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.get("/")
def home():
    return {"message": "Backend is running"}
