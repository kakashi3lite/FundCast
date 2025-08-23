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
    PerformanceMiddleware,
)
from .cache import get_cache, warm_cache
from .database_optimization import initialize_database_pools, cleanup_database_pools
from .async_tasks import get_task_manager
from .sre import (
    get_slo_manager, setup_default_slos, get_monitoring_service,
    SREMiddleware, CircuitBreakerMiddleware
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
    """Application lifespan management with performance optimizations."""
    # Startup
    startup_start = time.time()
    logger.info("Starting FundCast API", version=__version__)
    
    try:
        # Setup observability
        setup_observability()
        
        # Initialize optimized database pools
        await initialize_database_pools()
        logger.info("Optimized database pools initialized")
        
        # Initialize cache system
        cache = await get_cache()
        await cache.connect()
        logger.info("Multi-layer cache system initialized")
        
        # Initialize task manager
        task_manager = await get_task_manager()
        await task_manager.start(num_workers=5)
        logger.info("Async task manager started")
        
        # Initialize SRE systems
        await setup_default_slos()
        slo_manager = await get_slo_manager()
        await slo_manager.start_monitoring(interval_seconds=60)
        logger.info("SLO monitoring started")
        
        monitoring_service = await get_monitoring_service()
        await monitoring_service.start_monitoring(interval_seconds=60)
        logger.info("Advanced monitoring started")
        
        # Initialize database tables (using original engine for compatibility)
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
        
        await engine.dispose()  # Close temporary engine
        
        # Warm cache with common queries
        if not settings.DEBUG:
            try:
                await warm_cache([
                    # Add cache warming functions here
                ])
                logger.info("Cache warming completed")
            except Exception as e:
                logger.warning("Cache warming failed", error=str(e))
        
        startup_duration = time.time() - startup_start
        logger.info("FundCast API startup completed", duration=f"{startup_duration:.2f}s")
        
        yield
        
    except Exception as e:
        logger.error("Startup failed", error=str(e), exc_info=True)
        raise
    finally:
        # Shutdown sequence
        shutdown_start = time.time()
        logger.info("Shutting down FundCast API")
        
        try:
            # Stop SRE systems
            slo_manager = await get_slo_manager()
            await slo_manager.stop_monitoring()
            logger.info("SLO monitoring stopped")
            
            monitoring_service = await get_monitoring_service()
            await monitoring_service.stop_monitoring()
            logger.info("Advanced monitoring stopped")
            
            # Stop task manager
            task_manager = await get_task_manager()
            await task_manager.stop()
            logger.info("Task manager stopped")
            
            # Clean up cache
            cache = await get_cache()
            await cache.clear()
            logger.info("Cache cleared")
            
            # Close database pools
            await cleanup_database_pools()
            logger.info("Database pools closed")
            
        except Exception as e:
            logger.error("Shutdown error", error=str(e), exc_info=True)
        
        shutdown_duration = time.time() - shutdown_start
        logger.info("FundCast API shutdown completed", duration=f"{shutdown_duration:.2f}s")


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
    
    # Custom middleware (order matters for performance!)
    app.add_middleware(SREMiddleware)  # SRE monitoring first for comprehensive coverage
    app.add_middleware(CircuitBreakerMiddleware)  # Circuit breakers for resilience
    app.add_middleware(PerformanceMiddleware)  # Monitor performance
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
    
    # Performance monitoring endpoints
    @app.get("/admin/stats", tags=["admin"])
    async def system_stats() -> Dict[str, Any]:
        """Get system performance statistics."""
        cache = await get_cache()
        task_manager = await get_task_manager()
        
        return {
            "cache_stats": await cache.get_stats(),
            "task_stats": task_manager.get_stats(),
            "system_info": {
                "version": __version__,
                "environment": settings.ENVIRONMENT,
                "uptime": time.time() - startup_start,
            }
        }
    
    @app.get("/admin/sre/dashboard", tags=["admin"])
    async def sre_dashboard() -> Dict[str, Any]:
        """Get comprehensive SRE monitoring dashboard."""
        monitoring_service = await get_monitoring_service()
        dashboard_data = await monitoring_service.dashboard.get_dashboard_data()
        return dashboard_data
    
    @app.get("/admin/sre/slos", tags=["admin"])
    async def slo_status() -> Dict[str, Any]:
        """Get Service Level Objective status."""
        slo_manager = await get_slo_manager()
        slo_status = await slo_manager.get_all_slo_status()
        
        return {
            "slos": {
                name: {
                    "current_percentage": status.current_percentage,
                    "target_percentage": status.target_percentage,
                    "error_budget_remaining": status.error_budget_remaining,
                    "status": status.status.value,
                    "measurements_count": status.measurements_count
                }
                for name, status in slo_status.items()
            }
        }
    
    @app.get("/admin/sre/circuit-breakers", tags=["admin"])
    async def circuit_breaker_status() -> Dict[str, Any]:
        """Get circuit breaker status."""
        from .sre.circuit_breaker import circuit_breaker_health_check
        return await circuit_breaker_health_check()
    
    @app.post("/admin/sre/circuit-breakers/{name}/reset", tags=["admin"])
    async def reset_circuit_breaker(name: str) -> Dict[str, str]:
        """Reset a specific circuit breaker."""
        from .sre.circuit_breaker import get_circuit_breaker
        
        try:
            breaker = get_circuit_breaker(name)
            await breaker.reset()
            return {"status": f"Circuit breaker '{name}' reset successfully"}
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Circuit breaker '{name}' not found")
    
    @app.post("/admin/cache/clear", tags=["admin"])
    async def clear_cache() -> Dict[str, str]:
        """Clear all cache layers."""
        cache = await get_cache()
        await cache.clear()
        return {"status": "cache_cleared"}
    
    @app.get("/admin/tasks/{task_id}", tags=["admin"])
    async def get_task_result(task_id: str) -> Dict[str, Any]:
        """Get task execution result."""
        task_manager = await get_task_manager()
        result = task_manager.get_task_result(task_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {
            "task_id": task_id,
            "status": result.status,
            "result": result.result,
            "error": result.error,
            "duration": result.duration,
            "retry_count": result.retry_count,
        }
    
    # Store startup time for uptime calculation
    startup_start = time.time()
    
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