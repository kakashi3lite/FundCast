"""Circuit breaker pattern implementation for resilient service calls."""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional, Union, TypeVar, Generic
from dataclasses import dataclass
from enum import Enum
import random

import structlog
from contextlib import asynccontextmanager

from ..exceptions import CircuitBreakerError, ServiceUnavailableError

logger = structlog.get_logger(__name__)

T = TypeVar('T')


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"           # Circuit is open, failing fast
    HALF_OPEN = "half_open" # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5          # Failures before opening
    recovery_timeout: int = 60          # Seconds to wait before trying half-open
    success_threshold: int = 3          # Successes needed to close from half-open
    timeout: float = 30.0               # Request timeout in seconds
    expected_exception: tuple = (Exception,)  # Exceptions that count as failures
    
    # Advanced settings
    rolling_window_size: int = 100      # Size of rolling window for failure tracking
    minimum_throughput: int = 10        # Minimum requests before considering failure rate
    slow_call_duration_threshold: float = 10.0  # Slow calls treated as failures
    slow_call_rate_threshold: float = 50.0      # % of slow calls that trigger opening


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics."""
    state: CircuitState
    failure_count: int
    success_count: int
    total_requests: int
    last_failure_time: Optional[datetime]
    last_success_time: Optional[datetime]
    next_attempt_time: Optional[datetime]
    failure_rate: float
    slow_call_rate: float
    average_response_time: float


class CallResult:
    """Result of a circuit breaker call."""
    
    def __init__(
        self,
        success: bool,
        duration: float,
        exception: Optional[Exception] = None,
        result: Any = None
    ):
        self.success = success
        self.duration = duration
        self.exception = exception
        self.result = result
        self.timestamp = datetime.now()


class RollingWindow:
    """Rolling window for tracking call results."""
    
    def __init__(self, size: int):
        self.size = size
        self.results: list[CallResult] = []
        self.index = 0
    
    def add_result(self, result: CallResult):
        """Add a call result to the rolling window."""
        if len(self.results) < self.size:
            self.results.append(result)
        else:
            self.results[self.index] = result
            self.index = (self.index + 1) % self.size
    
    def get_failure_rate(self, time_window: Optional[timedelta] = None) -> float:
        """Get failure rate as percentage."""
        if not self.results:
            return 0.0
        
        relevant_results = self.results
        
        if time_window:
            cutoff = datetime.now() - time_window
            relevant_results = [r for r in self.results if r.timestamp >= cutoff]
        
        if not relevant_results:
            return 0.0
        
        failures = sum(1 for r in relevant_results if not r.success)
        return (failures / len(relevant_results)) * 100
    
    def get_slow_call_rate(self, slow_threshold: float) -> float:
        """Get slow call rate as percentage."""
        if not self.results:
            return 0.0
        
        slow_calls = sum(1 for r in self.results if r.duration > slow_threshold)
        return (slow_calls / len(self.results)) * 100
    
    def get_average_response_time(self) -> float:
        """Get average response time."""
        if not self.results:
            return 0.0
        
        total_duration = sum(r.duration for r in self.results)
        return total_duration / len(self.results)
    
    def clear(self):
        """Clear all results."""
        self.results.clear()
        self.index = 0


class CircuitBreaker(Generic[T]):
    """Circuit breaker implementation with advanced failure detection."""
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        # State management
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.next_attempt_time: Optional[datetime] = None
        
        # Rolling window for advanced failure detection
        self.rolling_window = RollingWindow(self.config.rolling_window_size)
        
        # Thread safety
        self._lock = asyncio.Lock()
    
    async def call(
        self,
        func: Callable[..., T],
        *args,
        fallback: Optional[Callable[..., T]] = None,
        **kwargs
    ) -> T:
        """Execute function with circuit breaker protection."""
        async with self._lock:
            # Check if we can make the call
            if not self._can_attempt_call():
                if fallback:
                    logger.warning(
                        "Circuit breaker open, using fallback",
                        circuit=self.name,
                        state=self.state.value
                    )
                    return await self._safe_call(fallback, *args, **kwargs)
                else:
                    raise CircuitBreakerError(
                        f"Circuit breaker '{self.name}' is {self.state.value}"
                    )
        
        # Make the call
        start_time = time.time()
        
        try:
            # Handle both sync and async functions
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.config.timeout
                )
            else:
                result = await asyncio.wait_for(
                    asyncio.to_thread(func, *args, **kwargs),
                    timeout=self.config.timeout
                )
            
            duration = time.time() - start_time
            
            # Record success
            call_result = CallResult(
                success=True,
                duration=duration,
                result=result
            )
            
            async with self._lock:
                await self._record_success(call_result)
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Determine if this should count as a failure
            is_failure = isinstance(e, self.config.expected_exception)
            
            call_result = CallResult(
                success=not is_failure,
                duration=duration,
                exception=e
            )
            
            async with self._lock:
                if is_failure:
                    await self._record_failure(call_result)
                else:
                    await self._record_success(call_result)
            
            # Use fallback if available and it's a failure
            if is_failure and fallback:
                logger.warning(
                    "Circuit breaker call failed, using fallback",
                    circuit=self.name,
                    error=str(e)
                )
                return await self._safe_call(fallback, *args, **kwargs)
            
            raise
    
    async def _safe_call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Safely call a fallback function."""
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return await asyncio.to_thread(func, *args, **kwargs)
        except Exception as e:
            logger.error("Fallback function failed", circuit=self.name, error=str(e))
            raise
    
    def _can_attempt_call(self) -> bool:
        """Check if we can attempt a call based on current state."""
        now = datetime.now()
        
        if self.state == CircuitState.CLOSED:
            return True
        
        elif self.state == CircuitState.OPEN:
            # Check if enough time has passed to try half-open
            if self.next_attempt_time and now >= self.next_attempt_time:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info("Circuit breaker transitioning to half-open", circuit=self.name)
                return True
            return False
        
        elif self.state == CircuitState.HALF_OPEN:
            return True
        
        return False
    
    async def _record_success(self, call_result: CallResult):
        """Record a successful call."""
        self.rolling_window.add_result(call_result)
        self.success_count += 1
        
        if self.state == CircuitState.HALF_OPEN:
            if self.success_count >= self.config.success_threshold:
                self._close_circuit()
        
        logger.debug(
            "Circuit breaker success recorded",
            circuit=self.name,
            state=self.state.value,
            duration=call_result.duration
        )
    
    async def _record_failure(self, call_result: CallResult):
        """Record a failed call."""
        self.rolling_window.add_result(call_result)
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        # Check if we should open the circuit
        should_open = self._should_open_circuit()
        
        if should_open and self.state != CircuitState.OPEN:
            self._open_circuit()
        elif self.state == CircuitState.HALF_OPEN:
            # Any failure in half-open goes back to open
            self._open_circuit()
        
        logger.warning(
            "Circuit breaker failure recorded",
            circuit=self.name,
            state=self.state.value,
            failure_count=self.failure_count,
            duration=call_result.duration,
            error=str(call_result.exception)
        )
    
    def _should_open_circuit(self) -> bool:
        """Determine if circuit should be opened based on failure patterns."""
        # Not enough throughput to make decision
        if len(self.rolling_window.results) < self.config.minimum_throughput:
            return False
        
        # Check failure rate
        failure_rate = self.rolling_window.get_failure_rate()
        if failure_rate >= (100 - (self.config.failure_threshold / len(self.rolling_window.results)) * 100):
            return True
        
        # Check slow call rate
        slow_call_rate = self.rolling_window.get_slow_call_rate(
            self.config.slow_call_duration_threshold
        )
        if slow_call_rate >= self.config.slow_call_rate_threshold:
            return True
        
        return False
    
    def _open_circuit(self):
        """Open the circuit breaker."""
        self.state = CircuitState.OPEN
        self.next_attempt_time = datetime.now() + timedelta(seconds=self.config.recovery_timeout)
        
        logger.warning(
            "Circuit breaker opened",
            circuit=self.name,
            failure_count=self.failure_count,
            next_attempt=self.next_attempt_time.isoformat()
        )
    
    def _close_circuit(self):
        """Close the circuit breaker."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.next_attempt_time = None
        self.rolling_window.clear()
        
        logger.info("Circuit breaker closed", circuit=self.name)
    
    def get_stats(self) -> CircuitBreakerStats:
        """Get current circuit breaker statistics."""
        return CircuitBreakerStats(
            state=self.state,
            failure_count=self.failure_count,
            success_count=self.success_count,
            total_requests=len(self.rolling_window.results),
            last_failure_time=self.last_failure_time,
            last_success_time=datetime.now() if self.success_count > 0 else None,
            next_attempt_time=self.next_attempt_time,
            failure_rate=self.rolling_window.get_failure_rate(),
            slow_call_rate=self.rolling_window.get_slow_call_rate(
                self.config.slow_call_duration_threshold
            ),
            average_response_time=self.rolling_window.get_average_response_time()
        )
    
    async def force_open(self):
        """Manually force circuit breaker open."""
        async with self._lock:
            self._open_circuit()
    
    async def force_close(self):
        """Manually force circuit breaker closed."""
        async with self._lock:
            self._close_circuit()
    
    async def reset(self):
        """Reset circuit breaker to initial state."""
        async with self._lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None
            self.next_attempt_time = None
            self.rolling_window.clear()
            
            logger.info("Circuit breaker reset", circuit=self.name)


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""
    
    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}
    
    def get_breaker(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker(name, config)
            logger.info("Circuit breaker created", name=name)
        
        return self.breakers[name]
    
    def get_all_stats(self) -> Dict[str, CircuitBreakerStats]:
        """Get statistics for all circuit breakers."""
        return {name: breaker.get_stats() for name, breaker in self.breakers.items()}
    
    async def reset_all(self):
        """Reset all circuit breakers."""
        for breaker in self.breakers.values():
            await breaker.reset()
        
        logger.info("All circuit breakers reset")


# Global registry
_registry = CircuitBreakerRegistry()


def get_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """Get a circuit breaker instance."""
    return _registry.get_breaker(name, config)


def circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None,
    fallback: Optional[Callable] = None
):
    """Decorator for circuit breaker protection."""
    def decorator(func: Callable) -> Callable:
        breaker = get_circuit_breaker(name, config)
        
        async def wrapper(*args, **kwargs):
            return await breaker.call(func, *args, fallback=fallback, **kwargs)
        
        # Copy function metadata
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.circuit_breaker = breaker
        
        return wrapper
    
    return decorator


# Predefined circuit breaker configurations
EXTERNAL_API_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=30,
    success_threshold=2,
    timeout=10.0,
    expected_exception=(Exception,),
    slow_call_duration_threshold=5.0,
    slow_call_rate_threshold=50.0
)

DATABASE_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout=15,
    success_threshold=2,
    timeout=30.0,
    expected_exception=(Exception,),
    slow_call_duration_threshold=10.0,
    slow_call_rate_threshold=30.0
)

CACHE_CONFIG = CircuitBreakerConfig(
    failure_threshold=10,
    recovery_timeout=5,
    success_threshold=3,
    timeout=2.0,
    expected_exception=(Exception,),
    slow_call_duration_threshold=1.0,
    slow_call_rate_threshold=60.0
)


# Context manager for temporary circuit breaker
@asynccontextmanager
async def protected_call(
    name: str,
    config: Optional[CircuitBreakerConfig] = None,
    fallback: Optional[Callable] = None
):
    """Context manager for protected calls."""
    breaker = get_circuit_breaker(name, config)
    
    class ProtectedCallContext:
        async def call(self, func: Callable, *args, **kwargs):
            return await breaker.call(func, *args, fallback=fallback, **kwargs)
    
    yield ProtectedCallContext()


# Utility functions for common patterns
async def with_retry_and_circuit_breaker(
    func: Callable,
    circuit_name: str,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    backoff_multiplier: float = 2.0,
    circuit_config: Optional[CircuitBreakerConfig] = None,
    fallback: Optional[Callable] = None,
    *args,
    **kwargs
) -> Any:
    """Combine retry logic with circuit breaker protection."""
    breaker = get_circuit_breaker(circuit_name, circuit_config)
    
    for attempt in range(max_retries + 1):
        try:
            return await breaker.call(func, *args, fallback=fallback, **kwargs)
        
        except CircuitBreakerError:
            # Circuit breaker is open, don't retry
            raise
        
        except Exception as e:
            if attempt == max_retries:
                raise
            
            # Wait before retry with exponential backoff
            delay = retry_delay * (backoff_multiplier ** attempt)
            jitter = random.uniform(0, delay * 0.1)  # Add jitter
            await asyncio.sleep(delay + jitter)
            
            logger.warning(
                "Retrying after failure",
                circuit=circuit_name,
                attempt=attempt + 1,
                max_retries=max_retries,
                error=str(e)
            )


# Health check integration
async def circuit_breaker_health_check() -> Dict[str, Any]:
    """Health check for all circuit breakers."""
    stats = _registry.get_all_stats()
    
    health_status = "healthy"
    issues = []
    
    for name, stat in stats.items():
        if stat.state == CircuitState.OPEN:
            health_status = "degraded"
            issues.append(f"Circuit breaker '{name}' is open")
        elif stat.failure_rate > 50:
            health_status = "degraded" if health_status == "healthy" else health_status
            issues.append(f"Circuit breaker '{name}' has high failure rate: {stat.failure_rate:.1f}%")
    
    return {
        "status": health_status,
        "circuit_breakers": {
            name: {
                "state": stat.state.value,
                "failure_rate": stat.failure_rate,
                "total_requests": stat.total_requests,
                "average_response_time": stat.average_response_time
            }
            for name, stat in stats.items()
        },
        "issues": issues
    }