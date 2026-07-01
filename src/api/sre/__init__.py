"""Site Reliability Engineering (SRE) module for FundCast."""

from .circuit_breaker import (
    CACHE_CONFIG,
    DATABASE_CONFIG,
    EXTERNAL_API_CONFIG,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    circuit_breaker,
    get_circuit_breaker,
)
from .middleware import (
    CircuitBreakerMiddleware,
    HealthCheckEnhancementMiddleware,
    RateLimitingEnhancementMiddleware,
    SREMiddleware,
    create_sre_middleware_stack,
)
from .monitoring import (
    MonitoringService,
    get_monitoring_service,
    record_request_metrics,
)
from .slo_monitoring import (
    SLOManager,
    SLOTarget,
    SLOType,
    get_slo_manager,
    setup_default_slos,
)

__all__ = [
    # SLO Monitoring
    "SLOManager",
    "SLOTarget",
    "SLOType",
    "get_slo_manager",
    "setup_default_slos",
    # Circuit Breakers
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitState",
    "get_circuit_breaker",
    "circuit_breaker",
    "EXTERNAL_API_CONFIG",
    "DATABASE_CONFIG",
    "CACHE_CONFIG",
    # Monitoring
    "MonitoringService",
    "get_monitoring_service",
    "record_request_metrics",
    # Middleware
    "SREMiddleware",
    "CircuitBreakerMiddleware",
    "RateLimitingEnhancementMiddleware",
    "HealthCheckEnhancementMiddleware",
    "create_sre_middleware_stack",
]
