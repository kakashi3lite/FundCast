"""Custom exception classes for FundCast API."""

from typing import Any, Dict, Optional


class FundCastException(Exception):
    """Base exception class for FundCast-specific errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(FundCastException):
    """Authentication-related errors."""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="authentication_failed",
            status_code=401,
            details=details,
        )


class AuthorizationError(FundCastException):
    """Authorization-related errors."""
    
    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="authorization_failed",
            status_code=403,
            details=details,
        )


class ValidationError(FundCastException):
    """Input validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        if field:
            details["field"] = field
        
        super().__init__(
            message=message,
            error_code="validation_failed",
            status_code=422,
            details=details,
        )


class ResourceNotFoundError(FundCastException):
    """Resource not found errors."""
    
    def __init__(self, resource: str, identifier: Any = None):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        
        super().__init__(
            message=message,
            error_code="resource_not_found",
            status_code=404,
            details={"resource": resource, "identifier": str(identifier) if identifier else None},
        )


class ConflictError(FundCastException):
    """Resource conflict errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="resource_conflict",
            status_code=409,
            details=details,
        )


class RateLimitError(FundCastException):
    """Rate limiting errors."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        details = {}
        if retry_after:
            details["retry_after"] = retry_after
            
        super().__init__(
            message=message,
            error_code="rate_limit_exceeded",
            status_code=429,
            details=details,
        )


class ComplianceError(FundCastException):
    """Compliance-related errors."""
    
    def __init__(self, message: str, regulation: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        if regulation:
            details["regulation"] = regulation
            
        super().__init__(
            message=message,
            error_code="compliance_violation",
            status_code=400,
            details=details,
        )


class MarketError(FundCastException):
    """Market operation errors."""
    
    def __init__(self, message: str, market_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        if market_id:
            details["market_id"] = market_id
            
        super().__init__(
            message=message,
            error_code="market_operation_failed",
            status_code=400,
            details=details,
        )


class InferenceError(FundCastException):
    """AI inference errors."""
    
    def __init__(self, message: str, model: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        if model:
            details["model"] = model
            
        super().__init__(
            message=message,
            error_code="inference_failed",
            status_code=500,
            details=details,
        )


class ExternalServiceError(FundCastException):
    """External service integration errors."""
    
    def __init__(self, service: str, message: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["service"] = service
        
        super().__init__(
            message=f"{service}: {message}",
            error_code="external_service_error",
            status_code=502,
            details=details,
        )


class CacheError(FundCastException):
    """Cache read/write failures."""

    def __init__(self, message: str = "Cache operation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="cache_error",
            status_code=503,
            details=details,
        )


class TaskError(FundCastException):
    """Background task execution errors."""

    def __init__(self, message: str, task_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        if task_id:
            details["task_id"] = task_id
        super().__init__(
            message=message,
            error_code="task_error",
            status_code=500,
            details=details,
        )


class DatabaseError(FundCastException):
    """Database connection/query errors."""

    def __init__(self, message: str = "Database operation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="database_error",
            status_code=503,
            details=details,
        )


class CircuitBreakerError(FundCastException):
    """Circuit breaker open/tripped errors."""

    def __init__(self, message: str = "Circuit breaker is open", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="circuit_breaker_open",
            status_code=503,
            details=details,
        )


class ServiceUnavailableError(FundCastException):
    """Dependency service unavailable."""

    def __init__(self, service: str = "dependency", message: str = "Service unavailable", details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["service"] = service
        super().__init__(
            message=f"{service}: {message}",
            error_code="service_unavailable",
            status_code=503,
            details=details,
        )