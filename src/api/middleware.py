"""Security and observability middleware."""

import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # OWASP security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        # HSTS (only in production)
        if not request.url.hostname in ["localhost", "127.0.0.1"]:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # CSP for API responses
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; "
            "frame-ancestors 'none'; "
            "form-action 'none'; "
            "base-uri 'none'"
        )

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Structured request/response logging."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Log request
        start_time = time.time()

        logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            user_agent=request.headers.get("user-agent"),
            client_ip=request.client.host if request.client else None,
        )

        try:
            response = await call_next(request)

            # Log response
            duration = time.time() - start_time
            logger.info(
                "Request completed",
                request_id=request_id,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Request failed",
                request_id=request_id,
                duration_ms=round(duration * 1000, 2),
                error=str(e),
                exc_info=True,
            )
            raise


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Validate request size and content type."""

    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_REQUEST_SIZE:
            return JSONResponse(
                status_code=413,
                content={
                    "error": "request_too_large",
                    "message": f"Request size exceeds maximum allowed size of {self.MAX_REQUEST_SIZE} bytes",
                },
            )

        # Validate JSON content type for POST/PUT/PATCH
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if (
                not content_type.startswith("application/json")
                and not content_type.startswith("multipart/form-data")
                and "/webhook" not in str(request.url)  # Allow webhooks
            ):
                return JSONResponse(
                    status_code=415,
                    content={
                        "error": "unsupported_media_type",
                        "message": "Content-Type must be application/json or multipart/form-data",
                    },
                )

        return await call_next(request)


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Monitor and enforce performance constraints."""

    SLOW_REQUEST_THRESHOLD = 1.0  # 1 second

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time

        # Log slow requests
        if duration > self.SLOW_REQUEST_THRESHOLD:
            logger.warning(
                "Slow request detected",
                request_id=getattr(request.state, "request_id", None),
                method=request.method,
                url=str(request.url),
                duration_ms=round(duration * 1000, 2),
            )

        # Add performance headers
        response.headers["X-Response-Time"] = f"{duration:.3f}"

        return response
