"""SRE middleware for request monitoring and SLO tracking."""

import time
from typing import Callable
import asyncio

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .slo_monitoring import get_slo_manager
from .monitoring import record_request_metrics

logger = structlog.get_logger(__name__)


class SREMiddleware(BaseHTTPMiddleware):
    """Site Reliability Engineering middleware for comprehensive monitoring."""
    
    def __init__(self, app, enable_detailed_logging: bool = False):
        super().__init__(app)
        self.enable_detailed_logging = enable_detailed_logging
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Start timing
        start_time = time.time()
        
        # Extract request information
        method = request.method
        path = str(request.url.path)
        user_agent = request.headers.get("user-agent", "")
        client_ip = self._get_client_ip(request)
        
        # Generate request context
        request_context = {
            "method": method,
            "path": path,
            "user_agent": user_agent,
            "client_ip": client_ip,
            "timestamp": start_time
        }
        
        response = None
        error_occurred = False
        
        try:
            # Process the request
            response = await call_next(request)
            
        except Exception as e:
            error_occurred = True
            logger.error(
                "Request processing error",
                **request_context,
                error=str(e),
                exc_info=True
            )
            # Re-raise the exception to be handled by global exception handlers
            raise
        
        finally:
            # Calculate metrics
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            # Get response status if available
            status_code = getattr(response, 'status_code', 500 if error_occurred else 200)
            
            # Record metrics asynchronously
            asyncio.create_task(
                self._record_metrics(
                    request_context,
                    duration_ms,
                    status_code,
                    error_occurred
                )
            )
            
            # Add SRE headers to response
            if response:
                response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
                response.headers["X-Request-ID"] = getattr(request.state, "request_id", "unknown")
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check various headers for the real client IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    async def _record_metrics(
        self,
        request_context: dict,
        duration_ms: float,
        status_code: int,
        error_occurred: bool
    ):
        """Record comprehensive metrics for the request."""
        try:
            # Determine success/failure
            is_success = not error_occurred and 200 <= status_code < 400
            
            # Record general request metrics
            await record_request_metrics(
                response_time_ms=duration_ms,
                status_code=status_code,
                endpoint=request_context["path"]
            )
            
            # Record SLO measurements
            await self._record_slo_measurements(
                request_context,
                duration_ms,
                is_success,
                status_code
            )
            
            # Log detailed request info if enabled
            if self.enable_detailed_logging:
                logger.info(
                    "Request completed",
                    method=request_context["method"],
                    path=request_context["path"],
                    status_code=status_code,
                    duration_ms=duration_ms,
                    client_ip=request_context["client_ip"],
                    success=is_success
                )
        
        except Exception as e:
            logger.error("Failed to record request metrics", error=str(e))
    
    async def _record_slo_measurements(
        self,
        request_context: dict,
        duration_ms: float,
        is_success: bool,
        status_code: int
    ):
        """Record SLO measurements for this request."""
        try:
            slo_manager = await get_slo_manager()
            
            # Record API availability SLO
            await slo_manager.record_request(
                slo_name="api_availability",
                success=is_success,
                metadata={
                    "method": request_context["method"],
                    "path": request_context["path"],
                    "status_code": status_code
                }
            )
            
            # Record API latency SLO
            await slo_manager.record_request(
                slo_name="api_latency",
                success=is_success,
                latency_ms=duration_ms,
                metadata={
                    "method": request_context["method"],
                    "path": request_context["path"],
                    "duration_ms": duration_ms
                }
            )
            
            # Record error rate SLO
            await slo_manager.record_request(
                slo_name="api_error_rate",
                success=is_success,
                status_code=status_code,
                metadata={
                    "method": request_context["method"],
                    "path": request_context["path"],
                    "status_code": status_code
                }
            )
            
        except Exception as e:
            logger.error("Failed to record SLO measurements", error=str(e))


class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    """Middleware to integrate circuit breakers with FastAPI routes."""
    
    def __init__(self, app):
        super().__init__(app)
        # Circuit breaker configurations for different route patterns
        self.route_circuit_breakers = {
            "/api/v1/auth": "auth_service",
            "/api/v1/users": "user_service", 
            "/api/v1/markets": "market_service",
            "/api/v1/compliance": "compliance_service"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if this route should be protected by a circuit breaker
        circuit_breaker_name = self._get_circuit_breaker_for_route(request.url.path)
        
        if not circuit_breaker_name:
            # No circuit breaker for this route
            return await call_next(request)
        
        try:
            # Import here to avoid circular imports
            from .circuit_breaker import get_circuit_breaker, CircuitBreakerError
            
            breaker = get_circuit_breaker(circuit_breaker_name)
            
            # Execute request through circuit breaker
            response = await breaker.call(call_next, request)
            return response
            
        except CircuitBreakerError as e:
            # Circuit breaker is open, return 503 Service Unavailable
            logger.warning(
                "Circuit breaker blocked request",
                path=request.url.path,
                circuit_breaker=circuit_breaker_name,
                error=str(e)
            )
            
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=503,
                content={
                    "error": "service_unavailable",
                    "message": f"Service temporarily unavailable: {circuit_breaker_name}",
                    "retry_after": 60  # seconds
                },
                headers={"Retry-After": "60"}
            )
    
    def _get_circuit_breaker_for_route(self, path: str) -> str:
        """Determine which circuit breaker to use for a given route."""
        for route_pattern, breaker_name in self.route_circuit_breakers.items():
            if path.startswith(route_pattern):
                return breaker_name
        return None


class RateLimitingEnhancementMiddleware(BaseHTTPMiddleware):
    """Enhanced rate limiting with SRE integration."""
    
    def __init__(self, app):
        super().__init__(app)
        self.blocked_requests_count = 0
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # The actual rate limiting is handled by RateLimitMiddleware
        # This middleware just records metrics for rate limit violations
        
        response = await call_next(request)
        
        # Check if request was rate limited
        if response.status_code == 429:
            self.blocked_requests_count += 1
            
            # Record rate limit violation
            await self._record_rate_limit_violation(request)
        
        return response
    
    async def _record_rate_limit_violation(self, request: Request):
        """Record rate limit violation for monitoring."""
        try:
            client_ip = request.client.host if request.client else "unknown"
            
            logger.warning(
                "Rate limit violation",
                client_ip=client_ip,
                path=request.url.path,
                method=request.method,
                user_agent=request.headers.get("user-agent", "")
            )
            
            # This could trigger additional security measures
            # like temporary IP blocking for repeated violations
            
        except Exception as e:
            logger.error("Failed to record rate limit violation", error=str(e))


class HealthCheckEnhancementMiddleware(BaseHTTPMiddleware):
    """Enhance health checks with SRE data."""
    
    def __init__(self, app):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only enhance health check endpoints
        if request.url.path in ["/health", "/health/", "/api/health"]:
            return await self._enhanced_health_check(request)
        
        return await call_next(request)
    
    async def _enhanced_health_check(self, request: Request) -> Response:
        """Provide enhanced health check with SRE metrics."""
        try:
            from fastapi.responses import JSONResponse
            from .monitoring import get_monitoring_service
            from .circuit_breaker import circuit_breaker_health_check
            
            # Get basic health info
            health_data = {
                "status": "healthy",
                "timestamp": time.time(),
                "version": getattr(__import__("src.api"), "__version__", "unknown")
            }
            
            # Add SRE monitoring data if requested
            if request.query_params.get("detailed") == "true":
                monitoring_service = await get_monitoring_service()
                dashboard_data = await monitoring_service.dashboard.get_dashboard_data()
                
                # Add SRE metrics to health check
                health_data["sre_metrics"] = {
                    "slo_status": dashboard_data["slo_status"],
                    "circuit_breakers": await circuit_breaker_health_check(),
                    "system_metrics": {
                        "cpu_percent": dashboard_data["system_metrics"]["cpu_percent"],
                        "memory_percent": dashboard_data["system_metrics"]["memory_percent"],
                        "request_rate": dashboard_data["application_metrics"]["request_rate"],
                        "error_rate": dashboard_data["application_metrics"]["error_rate"]
                    }
                }
                
                # Determine overall health status
                if any(slo["status"] == "critical" for slo in dashboard_data["slo_status"].values()):
                    health_data["status"] = "degraded"
                elif dashboard_data["system_metrics"]["cpu_percent"] > 80:
                    health_data["status"] = "degraded"
                elif dashboard_data["system_metrics"]["memory_percent"] > 85:
                    health_data["status"] = "degraded"
            
            # Return appropriate HTTP status based on health
            status_code = 200 if health_data["status"] == "healthy" else 503
            
            return JSONResponse(
                status_code=status_code,
                content=health_data
            )
            
        except Exception as e:
            logger.error("Enhanced health check failed", error=str(e))
            
            # Fallback to basic health check
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "error": "Health check system failure",
                    "timestamp": time.time()
                }
            )


# Middleware factory function
def create_sre_middleware_stack():
    """Create the complete SRE middleware stack."""
    return [
        SREMiddleware,
        CircuitBreakerMiddleware,
        RateLimitingEnhancementMiddleware,
        HealthCheckEnhancementMiddleware
    ]