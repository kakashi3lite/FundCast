"""Authentication routes with comprehensive security."""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_database, User
from ..exceptions import AuthenticationError, ValidationError, ConflictError
from .security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token,
    generate_secure_token,
    validate_password_strength,
    TokenBlacklist,
)

logger = structlog.get_logger(__name__)
security = HTTPBearer(auto_error=False)

router = APIRouter()


# Request/Response Models
class UserRegistration(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=255)
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    
    @validator("password")
    def validate_password(cls, v):
        if not validate_password_strength(v):
            raise ValueError(
                "Password must contain uppercase, lowercase, digit, and special character"
            )
        return v
    
    @validator("username")
    def validate_username(cls, v):
        if v and not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username can only contain letters, numbers, hyphens, and underscores")
        return v


class UserLogin(BaseModel):
    """User login request."""
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @validator("new_password")
    def validate_password(cls, v):
        if not validate_password_strength(v):
            raise ValueError(
                "Password must contain uppercase, lowercase, digit, and special character"
            )
        return v


class EmailVerificationRequest(BaseModel):
    """Email verification request."""
    token: str


# Helper functions
async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Get user by username."""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


def create_user_response(user: User) -> Dict[str, Any]:
    """Create safe user response."""
    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "email_verified": user.email_verified,
        "kyc_status": user.kyc_status,
        "accredited_status": user.accredited_status,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat(),
    }


# Routes
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegistration,
    request: Request,
    db: AsyncSession = Depends(get_database),
) -> TokenResponse:
    """Register a new user with comprehensive validation."""
    
    logger.info("User registration attempt", email=user_data.email)
    
    # Check if user already exists
    existing_user = await get_user_by_email(db, user_data.email)
    if existing_user:
        raise ConflictError("User with this email already exists")
    
    # Check username uniqueness if provided
    if user_data.username:
        existing_username = await get_user_by_username(db, user_data.username)
        if existing_username:
            raise ConflictError("Username is already taken")
    
    try:
        # Create new user
        password_hash = get_password_hash(user_data.password)
        
        user = User(
            email=user_data.email,
            password_hash=password_hash,
            full_name=user_data.full_name,
            username=user_data.username,
            roles=["user"],  # Default role
            permissions=["user:read", "user:update"],  # Basic permissions
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Create tokens
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "roles": user.roles,
            "permissions": user.permissions,
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token({"sub": str(user.id)})
        
        logger.info("User registered successfully", user_id=str(user.id), email=user.email)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=30 * 60,  # 30 minutes
            user=create_user_response(user),
        )
        
    except Exception as e:
        await db.rollback()
        logger.error("Registration failed", error=str(e), email=user_data.email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_database),
) -> TokenResponse:
    """Authenticate user and return tokens."""
    
    logger.info("Login attempt", email=credentials.email)
    
    # Get user
    user = await get_user_by_email(db, credentials.email)
    if not user:
        logger.warning("Login failed - user not found", email=credentials.email)
        raise AuthenticationError("Invalid email or password")
    
    # Check if user is active
    if not user.is_active:
        logger.warning("Login failed - user inactive", email=credentials.email)
        raise AuthenticationError("Account is deactivated")
    
    # Verify password
    if not verify_password(credentials.password, user.password_hash):
        logger.warning("Login failed - invalid password", email=credentials.email)
        raise AuthenticationError("Invalid email or password")
    
    # Create tokens
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "roles": user.roles,
        "permissions": user.permissions,
    }
    
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    logger.info("Login successful", user_id=str(user.id), email=user.email)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=30 * 60,  # 30 minutes
        user=create_user_response(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_database),
) -> TokenResponse:
    """Refresh access token using refresh token."""
    
    try:
        # Verify refresh token
        payload = verify_token(token_request.refresh_token, "refresh")
        user_id = payload.get("sub")
        
        if not user_id:
            raise AuthenticationError("Invalid refresh token")
        
        # Get user
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")
        
        # Create new tokens
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "roles": user.roles,
            "permissions": user.permissions,
        }
        
        access_token = create_access_token(token_data)
        new_refresh_token = create_refresh_token({"sub": str(user.id)})
        
        # Blacklist old refresh token
        TokenBlacklist.add_token(token_request.refresh_token)
        
        logger.info("Token refreshed", user_id=str(user.id))
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=30 * 60,
            user=create_user_response(user),
        )
        
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error("Token refresh failed", error=str(e))
        raise AuthenticationError("Token refresh failed")


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, authorization: str = Depends(security)):
    """Logout user by blacklisting token."""
    
    if not authorization:
        raise AuthenticationError("No token provided")
    
    try:
        token = authorization.credentials
        
        # Verify token (will raise exception if invalid)
        verify_token(token, "access")
        
        # Add to blacklist
        TokenBlacklist.add_token(token)
        
        logger.info("User logged out", token_prefix=token[:10])
        
        return Response(status_code=status.HTTP_204_NO_CONTENT)
        
    except Exception as e:
        logger.error("Logout failed", error=str(e))
        raise AuthenticationError("Logout failed")


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
async def forgot_password(
    request: PasswordResetRequest,
    db: AsyncSession = Depends(get_database),
):
    """Request password reset (placeholder - would send email in production)."""
    
    logger.info("Password reset requested", email=request.email)
    
    # Note: In production, this would:
    # 1. Generate secure reset token
    # 2. Store token with expiration in database
    # 3. Send reset email to user
    # 4. Return success regardless of whether email exists (security)
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_database),
):
    """Reset password using reset token (placeholder)."""
    
    logger.info("Password reset confirmation", token_prefix=reset_data.token[:10])
    
    # Note: In production, this would:
    # 1. Verify reset token
    # 2. Update user password
    # 3. Invalidate all existing tokens
    # 4. Send confirmation email
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/verify-email", status_code=status.HTTP_204_NO_CONTENT)
async def verify_email(
    verification: EmailVerificationRequest,
    db: AsyncSession = Depends(get_database),
):
    """Verify user email address (placeholder)."""
    
    logger.info("Email verification", token_prefix=verification.token[:10])
    
    # Note: In production, this would:
    # 1. Verify email token
    # 2. Update user.email_verified = True
    # 3. Grant additional permissions if needed
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Export router
auth_router = router