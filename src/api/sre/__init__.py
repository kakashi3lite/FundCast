"""Site Reliability Engineering (SRE) module for FundCast."""

from .slo_monitoring import (
    SLOManager,
    SLOTarget,
    SLOType,
    get_slo_manager,
    setup_default_slos
)

from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    get_circuit_breaker,
    circuit_breaker,
    EXTERNAL_API_CONFIG,
    DATABASE_CONFIG,
    CACHE_CONFIG
)

from .monitoring import (
    MonitoringService,
    get_monitoring_service,
    record_request_metrics
)

from .middleware import (
    SREMiddleware,
    CircuitBreakerMiddleware,
    RateLimitingEnhancementMiddleware,
    HealthCheckEnhancementMiddleware,
    create_sre_middleware_stack
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
    "create_sre_middleware_stack"
]