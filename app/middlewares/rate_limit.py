"""
app/middlewares/rate_limit.py

Thread-safe, sliding-window rate limiting middleware for FastAPI.
Protects API endpoints against brute force, credential stuffing, and
resource exhaustion while allowing normal frontend/API traffic.
"""

import time
import threading
from collections import defaultdict, deque
from typing import Dict, Deque, Tuple, Optional

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings
from app.core.logging_config import logger


class InMemoryRateLimiter:
    """
    Sliding window in-memory rate limiter with per-IP and per-bucket tracking.
    Zero external dependencies, thread-safe, and self-cleaning.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Key: (ip, bucket) -> deque of timestamps
        self._records: Dict[Tuple[str, str], Deque[float]] = defaultdict(deque)
        self._last_cleanup = time.time()

    def check_rate_limit(
        self, ip: str, bucket: str, limit: int, window_seconds: float = 60.0
    ) -> Tuple[bool, int, int]:
        """
        Checks if the given IP has exceeded the limit in the sliding window.
        Returns: (is_allowed, remaining_requests, retry_after_seconds)
        """
        now = time.time()
        window_start = now - window_seconds

        with self._lock:
            # Periodic cleanup of expired buckets every 300 seconds
            if now - self._last_cleanup > 300.0:
                self._cleanup(now)

            record = self._records[(ip, bucket)]

            # Drop timestamps outside the sliding window
            while record and record[0] < window_start:
                record.popleft()

            if len(record) >= limit:
                # Rate limit exceeded
                oldest_timestamp = record[0]
                retry_after = max(1, int(oldest_timestamp + window_seconds - now) + 1)
                return False, 0, retry_after

            # Allowed - record request timestamp
            record.append(now)
            remaining = max(0, limit - len(record))
            return True, remaining, 0

    def _cleanup(self, now: float) -> None:
        """Removes stale buckets to prevent unbounded memory growth."""
        cutoff = now - 3600.0  # Remove buckets inactive for over 1 hour
        stale_keys = [
            k for k, q in self._records.items()
            if not q or q[-1] < cutoff
        ]
        for k in stale_keys:
            del self._records[k]
        self._last_cleanup = now

    def reset(self) -> None:
        """Clears all rate limit records. Useful for test isolation."""
        with self._lock:
            self._records.clear()
            self._last_cleanup = time.time()


# Global limiter instance
limiter = InMemoryRateLimiter()


def get_client_ip(request: Request) -> str:
    """Extracts client IP from X-Forwarded-For header or direct client host."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # First IP in the comma-separated list is the original client
        client_ip = forwarded.split(",")[0].strip()
        if client_ip:
            return client_ip
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


def get_rate_limit_rules(path: str, method: str) -> Optional[Tuple[str, int, float]]:
    """
    Resolves (bucket_name, max_requests, window_seconds) for a request.
    Returns None if the route is exempt from rate limiting.
    """
    settings = get_settings()

    # Preflight requests and static assets are exempt
    if method == "OPTIONS" or path.startswith("/static") or path in ("/health", "/docs", "/openapi.json", "/redoc", "/favicon.ico"):
        return None

    # Sensitive authentication routes (strict limit against brute force)
    if path in ("/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/refresh"):
        return "auth", settings.RATE_LIMIT_AUTH_PER_MINUTE, 60.0

    # Resource-intensive operations (PDF parsing / embedding scoring)
    if path in ("/api/v1/resumes/upload", "/api/v1/screening/run"):
        return "sensitive", settings.RATE_LIMIT_SENSITIVE_PER_MINUTE, 60.0

    # General API routes
    if path.startswith(settings.API_V1_PREFIX) or path.startswith("/api/"):
        return "general", settings.RATE_LIMIT_DEFAULT_PER_MINUTE, 60.0

    return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware intercepting incoming requests to enforce rate limits.
    Returns standard HTTP 429 JSON response when limit is exceeded.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        rules = get_rate_limit_rules(request.url.path, request.method)
        if rules is None:
            return await call_next(request)

        bucket, limit, window = rules
        client_ip = get_client_ip(request)

        is_allowed, remaining, retry_after = limiter.check_rate_limit(
            ip=client_ip,
            bucket=bucket,
            limit=limit,
            window_seconds=window,
        )

        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded for IP={client_ip} on bucket={bucket} "
                f"path={request.url.path} limit={limit}/{window}s"
            )
            response = JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "data": None,
                    "message": f"Rate limit exceeded. Please try again in {retry_after} seconds.",
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + retry_after)),
                },
            )
            return response

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
