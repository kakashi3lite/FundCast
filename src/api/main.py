"""FastAPI application with comprehensive security and observability."""

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List

import structlog
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import create_async_engine

from . import __version__
from .auth.middleware import AuthMiddleware, RBACMiddleware, RateLimitMiddleware
from .auth.router import auth_router
from .compliance.router import compliance_router
from .markets.router import markets_router
from .users.router import users_router
from .config import settings
from .database import Base, get_database
from .exceptions import FundCastException
from .middleware import (
    SecurityHeadersMiddleware,
    LoggingMiddleware,
    RequestValidationMiddleware,
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Security configuration
security = HTTPBearer(auto_error=False)


def setup_observability() -> None:
    """Configure OpenTelemetry tracing and metrics."""
    resource = Resource.create({
        "service.name": "fundcast-api",
        "service.version": __version__,
        "deployment.environment": settings.ENVIRONMENT,
    })
    
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    
    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            headers={"Authorization": f"Bearer {settings.OTEL_EXPORTER_OTLP_HEADERS}"}
            if settings.OTEL_EXPORTER_OTLP_HEADERS
            else None,
        )
        span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(span_processor)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("Starting FundCast API", version=__version__)
    
    # Setup observability
    setup_observability()
    
    # Initialize database
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_size=20,
        max_overflow=0,
        pool_pre_ping=True,
        pool_recycle=300,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down FundCast API")
    await engine.dispose()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="FundCast API",
        description="AI-first social funding + forecasting platform for SaaS founders",
        version=__version__,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )
    
    # Security middleware (order matters!)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
        max_age=86400,  # 24 hours
    )
    
    # Custom middleware
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestValidationMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuthMiddleware)
    app.add_middleware(RBACMiddleware)
    
    # Routes
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["authentication"])
    app.include_router(users_router, prefix="/api/v1/users", tags=["users"])
    app.include_router(compliance_router, prefix="/api/v1/compliance", tags=["compliance"])
    app.include_router(markets_router, prefix="/api/v1/markets", tags=["markets"])
    
    # Health check endpoint
    @app.get("/health", tags=["health"])
    async def health_check() -> Dict[str, Any]:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": __version__,
            "timestamp": time.time(),
            "environment": settings.ENVIRONMENT,
        }
    
    # Exception handlers
    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
        """Handle Pydantic validation errors."""
        logger.warning("Validation error", errors=exc.errors(), path=request.url.path)
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_failed",
                "message": "Request validation failed",
                "details": exc.errors(),
            },
        )
    
    @app.exception_handler(FundCastException)
    async def fundcast_exception_handler(request: Request, exc: FundCastException) -> JSONResponse:
        """Handle custom FundCast exceptions."""
        logger.error(
            "FundCast exception",
            error_code=exc.error_code,
            message=exc.message,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
            },
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Handle HTTP exceptions with structured logging."""
        logger.warning(
            "HTTP exception",
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "http_error",
                "message": exc.detail,
            },
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions."""
        logger.error(
            "Unexpected exception",
            exception=str(exc),
            path=request.url.path,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred",
            },
        )
    
    # Instrument with OpenTelemetry
    FastAPIInstrumentor.instrument_app(app, tracer_provider=trace.get_tracer_provider())
    HTTPXClientInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()
    
    return app


# Create the application instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else 4,
        log_level="info",
        access_log=False,  # Use custom logging middleware instead
    )