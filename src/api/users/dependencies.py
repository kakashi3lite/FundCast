"""User authentication and authorization dependencies."""

from typing import List, Callable
import uuid

import structlog
from fastapi import Depends, Request, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_database, User
from ..exceptions import AuthenticationError, AuthorizationError
from ..auth.security import verify_token

logger = structlog.get_logger(__name__)
security = HTTPBearer()


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_database),
) -> User:
    """Get current authenticated user."""
    
    # Get user ID from request state (set by AuthMiddleware)
    user_id = getattr(request.state, "user_id", None)
    
    if not user_id:
        raise AuthenticationError("User not authenticated")
    
    try:
        # Convert string UUID to UUID object
        user_uuid = uuid.UUID(user_id)
        
        # Get user from database
        result = await db.execute(select(User).where(User.id == user_uuid))
        user = result.scalar_one_or_none()
        
        if not user:
            raise AuthenticationError("User not found")
        
        if not user.is_active:
            raise AuthenticationError("User account is deactivated")
        
        return user
        
    except ValueError:
        raise AuthenticationError("Invalid user ID format")
    except Exception as e:
        logger.error("Failed to get current user", error=str(e), user_id=user_id)
        raise AuthenticationError("Failed to authenticate user")


def require_permissions(required_permissions: List[str]) -> Callable:
    """Dependency factory for permission-based authorization."""
    
    def permission_checker(
        request: Request,
        current_user: User = Depends(get_current_user),
    ) -> User:
        """Check if user has required permissions."""
        
        user_roles = set(getattr(request.state, "user_roles", []))
        user_permissions = set(getattr(request.state, "user_permissions", []))
        required_set = set(required_permissions)
        
        # Check if user has any of the required permissions or roles
        has_permission = bool(
            user_permissions.intersection(required_set) or 
            user_roles.intersection(required_set)
        )
        
        if not has_permission:
            logger.warning(
                "Permission denied",
                user_id=str(current_user.id),
                required_permissions=required_permissions,
                user_permissions=list(user_permissions),
                user_roles=list(user_roles),
            )
            raise AuthorizationError(
                f"Required permissions: {', '.join(required_permissions)}"
            )
        
        return current_user
    
    return permission_checker


def require_roles(required_roles: List[str]) -> Callable:
    """Dependency factory for role-based authorization."""
    
    def role_checker(
        request: Request,
        current_user: User = Depends(get_current_user),
    ) -> User:
        """Check if user has required roles."""
        
        user_roles = set(getattr(request.state, "user_roles", []))
        required_set = set(required_roles)
        
        if not user_roles.intersection(required_set):
            logger.warning(
                "Role access denied",
                user_id=str(current_user.id),
                required_roles=required_roles,
                user_roles=list(user_roles),
            )
            raise AuthorizationError(
                f"Required roles: {', '.join(required_roles)}"
            )
        
        return current_user
    
    return role_checker


async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_database),
) -> User | None:
    """Get current user if authenticated, otherwise None."""
    
    try:
        return await get_current_user(request, db)
    except AuthenticationError:
        return None


def require_verified_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require user to have verified email."""
    
    if not current_user.email_verified:
        raise AuthorizationError("Email verification required")
    
    return current_user


def require_kyc_verified_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require user to have completed KYC verification."""
    
    if current_user.kyc_status != "verified":
        raise AuthorizationError("KYC verification required")
    
    return current_user


def require_accredited_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require user to be accredited investor."""
    
    if current_user.accredited_status != "verified":
        raise AuthorizationError("Accredited investor status required")
    
    return current_user