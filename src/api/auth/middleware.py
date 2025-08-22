"""Authentication and authorization middleware."""

import time
from typing import Callable, Dict, List, Optional, Set
from collections import defaultdict
import json

import redis
import structlog
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import settings
from ..exceptions import AuthenticationError, AuthorizationError, RateLimitError
from .security import verify_token, TokenBlacklist


logger = structlog.get_logger(__name__)

# Redis client for rate limiting (fallback to in-memory if not available)
try:
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_client.ping()  # Test connection
except (redis.ConnectionError, redis.TimeoutError):
    redis_client = None
    logger.warning("Redis not available, using in-memory rate limiting")


class InMemoryRateLimit:
    """In-memory rate limiting fallback."""
    
    def __init__(self):
        self.requests = defaultdict(list)
        self.cleanup_interval = 60  # seconds
        self.last_cleanup = time.time()
    
    def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        """Check if request is allowed and return remaining count."""
        now = time.time()
        
        # Cleanup old entries periodically
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup(now)
            self.last_cleanup = now
        
        # Remove expired entries for this key
        self.requests[key] = [
            timestamp for timestamp in self.requests[key]
            if now - timestamp < window
        ]
        
        current_count = len(self.requests[key])
        
        if current_count >= limit:
            return False, 0
        
        # Add current request
        self.requests[key].append(now)
        remaining = limit - current_count - 1
        
        return True, remaining
    
    def _cleanup(self, now: float):
        """Remove expired entries."""
        for key in list(self.requests.keys()):
            self.requests[key] = [
                timestamp for timestamp in self.requests[key]
                if now - timestamp < 3600  # Keep entries for 1 hour max
            ]
            if not self.requests[key]:
                del self.requests[key]


# Global rate limiter instance
in_memory_limiter = InMemoryRateLimit()


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT authentication middleware."""
    
    # Routes that don't require authentication
    PUBLIC_ROUTES = {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/forgot-password",
        "/api/v1/auth/reset-password",
        "/api/v1/auth/verify-email",
    }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip authentication for public routes
        if any(request.url.path.startswith(route) for route in self.PUBLIC_ROUTES):
            return await call_next(request)
        
        # Extract token from Authorization header
        authorization = request.headers.get("Authorization")
        if not authorization:
            return self._unauthorized_response("Missing authorization header")
        
        try:
            scheme, token = authorization.split(" ", 1)
            if scheme.lower() != "bearer":
                return self._unauthorized_response("Invalid authentication scheme")
        except ValueError:
            return self._unauthorized_response("Invalid authorization header format")
        
        try:
            # Check if token is blacklisted
            if TokenBlacklist.is_blacklisted(token):
                return self._unauthorized_response("Token has been revoked")
            
            # Verify token
            payload = verify_token(token, "access")
            
            # Add user information to request state
            request.state.user_id = payload.get("sub")
            request.state.user_email = payload.get("email")
            request.state.user_roles = payload.get("roles", [])
            request.state.user_permissions = payload.get("permissions", [])
            request.state.token_payload = payload
            
            logger.debug(
                "User authenticated",
                user_id=request.state.user_id,
                email=request.state.user_email,
                roles=request.state.user_roles,
            )
            
            return await call_next(request)
            
        except AuthenticationError as e:
            return self._unauthorized_response(str(e))
        except Exception as e:
            logger.error("Authentication error", error=str(e), exc_info=True)
            return self._unauthorized_response("Authentication failed")
    
    def _unauthorized_response(self, message: str) -> JSONResponse:
        """Return unauthorized response."""
        return JSONResponse(
            status_code=401,
            content={
                "error": "authentication_failed",
                "message": message,
            },
        )


class RBACMiddleware(BaseHTTPMiddleware):
    """Role-based access control middleware."""
    
    # Route permissions mapping
    ROUTE_PERMISSIONS = {
        # Admin routes
        "/api/v1/admin": ["admin"],
        
        # User management
        "/api/v1/users": {
            "GET": ["user:read", "admin"],
            "POST": ["user:create", "admin"],
            "PUT": ["user:update", "admin"],
            "DELETE": ["user:delete", "admin"],
        },
        
        # Compliance routes
        "/api/v1/compliance": {
            "GET": ["compliance:read", "admin"],
            "POST": ["compliance:create", "admin"],
            "PUT": ["compliance:update", "admin"],
        },
        
        # Market routes
        "/api/v1/markets": {
            "GET": ["market:read"],
            "POST": ["market:create", "admin"],
            "PUT": ["market:update", "admin"],
            "DELETE": ["market:delete", "admin"],
        },
    }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip RBAC for routes that don't require authentication
        if not hasattr(request.state, "user_id"):
            return await call_next(request)
        
        # Check permissions for this route
        if not self._check_permissions(request):
            return self._forbidden_response("Insufficient permissions")
        
        return await call_next(request)
    
    def _check_permissions(self, request: Request) -> bool:
        """Check if user has required permissions for the route."""
        path = request.url.path
        method = request.method
        user_roles = set(getattr(request.state, "user_roles", []))
        user_permissions = set(getattr(request.state, "user_permissions", []))
        
        # Find matching route pattern
        required_perms = None
        for route_pattern, perms in self.ROUTE_PERMISSIONS.items():
            if path.startswith(route_pattern):
                if isinstance(perms, dict):
                    required_perms = perms.get(method, [])
                else:
                    required_perms = perms
                break
        
        # If no specific permissions required, allow
        if not required_perms:
            return True
        
        # Check if user has any of the required permissions or roles
        required_set = set(required_perms)
        return bool(
            user_permissions.intersection(required_set) or 
            user_roles.intersection(required_set)
        )
    
    def _forbidden_response(self, message: str) -> JSONResponse:
        """Return forbidden response."""
        return JSONResponse(
            status_code=403,
            content={
                "error": "authorization_failed",
                "message": message,
            },
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with Redis backend."""
    
    def __init__(self, app, calls_per_minute: int = None, burst_limit: int = None):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute or settings.RATE_LIMIT_PER_MINUTE
        self.burst_limit = burst_limit or settings.RATE_LIMIT_BURST
        self.window_size = 60  # 1 minute
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Check rate limit
        is_allowed, remaining = await self._check_rate_limit(client_id)
        
        if not is_allowed:
            logger.warning(
                "Rate limit exceeded",
                client_id=client_id,
                path=request.url.path,
                method=request.method,
            )
            return self._rate_limit_response()
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.calls_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + self.window_size)
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Use authenticated user ID if available
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"
        
        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        return f"ip:{client_ip}"
    
    async def _check_rate_limit(self, client_id: str) -> tuple[bool, int]:
        """Check if client is within rate limits."""
        if redis_client:
            return await self._redis_rate_limit(client_id)
        else:
            return self._memory_rate_limit(client_id)
    
    async def _redis_rate_limit(self, client_id: str) -> tuple[bool, int]:
        """Redis-based rate limiting with sliding window."""
        key = f"rate_limit:{client_id}"
        now = time.time()
        
        try:
            # Use Redis pipeline for atomic operations
            pipe = redis_client.pipeline()
            
            # Remove expired entries
            pipe.zremrangebyscore(key, 0, now - self.window_size)
            
            # Count current requests
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(now): now})
            
            # Set expiration
            pipe.expire(key, self.window_size)
            
            results = pipe.execute()
            current_count = results[1]
            
            if current_count >= self.calls_per_minute:
                return False, 0
            
            remaining = self.calls_per_minute - current_count - 1
            return True, remaining
            
        except Exception as e:
            logger.error("Redis rate limiting error", error=str(e))
            # Fall back to memory-based limiting
            return self._memory_rate_limit(client_id)
    
    def _memory_rate_limit(self, client_id: str) -> tuple[bool, int]:
        """In-memory rate limiting fallback."""
        return in_memory_limiter.is_allowed(
            client_id, 
            self.calls_per_minute, 
            self.window_size
        )
    
    def _rate_limit_response(self) -> JSONResponse:
        """Return rate limit exceeded response."""
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limit_exceeded",
                "message": "Too many requests",
            },
            headers={
                "Retry-After": str(self.window_size),
            }
        )