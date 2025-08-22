"""User management routes with RBAC security."""

from typing import List, Optional
import uuid

import structlog
from fastapi import APIRouter, Depends, Request, Query, Path
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from ..database import get_database, User
from ..exceptions import ResourceNotFoundError, AuthorizationError, ValidationError
from .dependencies import get_current_user, require_permissions

logger = structlog.get_logger(__name__)
router = APIRouter()


# Response Models
class UserProfile(BaseModel):
    """User profile response."""
    id: str
    email: str
    username: Optional[str]
    full_name: Optional[str]
    profile_image_url: Optional[str]
    bio: Optional[str]
    email_verified: bool
    kyc_status: str
    accredited_status: str
    is_active: bool
    created_at: str
    updated_at: str


class UserUpdate(BaseModel):
    """User profile update request."""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=255)
    bio: Optional[str] = Field(None, max_length=1000)
    profile_image_url: Optional[str] = Field(None, max_length=500)


class UserList(BaseModel):
    """User list response."""
    users: List[UserProfile]
    total: int
    page: int
    per_page: int


def user_to_profile(user: User) -> UserProfile:
    """Convert User model to UserProfile response."""
    return UserProfile(
        id=str(user.id),
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        profile_image_url=user.profile_image_url,
        bio=user.bio,
        email_verified=user.email_verified,
        kyc_status=user.kyc_status,
        accredited_status=user.accredited_status,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
    )


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserProfile:
    """Get current user's profile."""
    
    logger.info("Getting current user profile", user_id=str(current_user.id))
    return user_to_profile(current_user)


@router.put("/me", response_model=UserProfile)
async def update_current_user_profile(
    profile_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
) -> UserProfile:
    """Update current user's profile."""
    
    logger.info("Updating user profile", user_id=str(current_user.id))
    
    # Check username uniqueness if being updated
    if profile_update.username and profile_update.username != current_user.username:
        existing_user = await db.execute(
            select(User).where(
                User.username == profile_update.username,
                User.id != current_user.id
            )
        )
        if existing_user.scalar_one_or_none():
            raise ValidationError("Username is already taken", "username")
    
    # Update fields
    update_data = profile_update.model_dump(exclude_unset=True)
    
    await db.execute(
        update(User)
        .where(User.id == current_user.id)
        .values(**update_data)
    )
    
    await db.commit()
    
    # Refresh user data
    await db.refresh(current_user)
    
    logger.info("User profile updated", user_id=str(current_user.id))
    return user_to_profile(current_user)


@router.get("/", response_model=UserList)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, max_length=255, description="Search query"),
    current_user: User = Depends(require_permissions(["admin", "user:list"])),
    db: AsyncSession = Depends(get_database),
) -> UserList:
    """List users with pagination and search (admin only)."""
    
    logger.info(
        "Listing users",
        admin_user_id=str(current_user.id),
        page=page,
        per_page=per_page,
        search=search,
    )
    
    # Build query
    query = select(User)
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            User.email.ilike(search_term) |
            User.full_name.ilike(search_term) |
            User.username.ilike(search_term)
        )
    
    # Get total count
    count_query = select(User.id)
    if search:
        search_term = f"%{search}%"
        count_query = count_query.where(
            User.email.ilike(search_term) |
            User.full_name.ilike(search_term) |
            User.username.ilike(search_term)
        )
    
    total_result = await db.execute(count_query)
    total = len(total_result.all())
    
    # Get paginated results
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(User.created_at.desc())
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return UserList(
        users=[user_to_profile(user) for user in users],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{user_id}", response_model=UserProfile)
async def get_user_by_id(
    user_id: uuid.UUID = Path(..., description="User ID"),
    current_user: User = Depends(require_permissions(["admin", "user:read"])),
    db: AsyncSession = Depends(get_database),
) -> UserProfile:
    """Get user by ID (admin only)."""
    
    logger.info("Getting user by ID", admin_user_id=str(current_user.id), target_user_id=str(user_id))
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise ResourceNotFoundError("User", str(user_id))
    
    return user_to_profile(user)


@router.put("/{user_id}/deactivate")
async def deactivate_user(
    user_id: uuid.UUID = Path(..., description="User ID"),
    current_user: User = Depends(require_permissions(["admin", "user:deactivate"])),
    db: AsyncSession = Depends(get_database),
):
    """Deactivate user (admin only)."""
    
    logger.info(
        "Deactivating user",
        admin_user_id=str(current_user.id),
        target_user_id=str(user_id),
    )
    
    # Prevent self-deactivation
    if user_id == current_user.id:
        raise ValidationError("Cannot deactivate your own account")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise ResourceNotFoundError("User", str(user_id))
    
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(is_active=False)
    )
    
    await db.commit()
    
    logger.info("User deactivated", target_user_id=str(user_id))
    
    return {"message": "User deactivated successfully"}


@router.put("/{user_id}/activate")
async def activate_user(
    user_id: uuid.UUID = Path(..., description="User ID"),
    current_user: User = Depends(require_permissions(["admin", "user:activate"])),
    db: AsyncSession = Depends(get_database),
):
    """Activate user (admin only)."""
    
    logger.info(
        "Activating user",
        admin_user_id=str(current_user.id),
        target_user_id=str(user_id),
    )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise ResourceNotFoundError("User", str(user_id))
    
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(is_active=True)
    )
    
    await db.commit()
    
    logger.info("User activated", target_user_id=str(user_id))
    
    return {"message": "User activated successfully"}


# Export router
users_router = router