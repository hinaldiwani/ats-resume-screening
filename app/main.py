"""
app/main.py

FastAPI application entrypoint.

Responsibilities of this file ONLY:
  - Create the FastAPI app instance
  - Load settings and configure logging
  - Mount static files and templates
  - Register middleware (CORS, request logging)
  - Register global exception handlers
  - Include the v1 API router
  - Expose a health check endpoint

No business logic, no DB queries, no AI calls belong here.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.config import get_settings
from app.core.logging_config import configure_logging, logger
from app.middlewares.error_handler import register_exception_handlers
from app.middlewares.request_logger import RequestLoggingMiddleware
from app.api.v1.api import api_router

settings = get_settings()

# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.APP_DEBUG,
)

# ---------------------------------------------------------------------------
# Startup / shutdown events
# ---------------------------------------------------------------------------
@app.on_event("startup")
def on_startup() -> None:
    configure_logging()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} starting up (env={settings.APP_ENV})")


@app.on_event("shutdown")
def on_shutdown() -> None:
    logger.info(f"{settings.APP_NAME} shutting down")


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------
register_exception_handlers(app)

# ---------------------------------------------------------------------------
# Static files & templates
# ---------------------------------------------------------------------------
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# ---------------------------------------------------------------------------
# Health check (useful for Docker/k8s probes and load balancers)
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
def health_check():
    return {"success": True, "data": {"status": "ok"}, "message": "Service is healthy"}
