"""
app/middlewares/request_logger.py

HTTP middleware that logs each incoming request's method, path, status code,
and duration. No business logic — observability only.
"""

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logging_config import logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000, 2)

        logger.info(
            f"{request.method} {request.url.path} "
            f"status={response.status_code} duration={duration_ms}ms"
        )
        return response
