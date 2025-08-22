"""Security utilities for authentication and encryption."""

import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

import bcrypt
from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from ..config import settings
from ..exceptions import AuthenticationError


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Encryption for sensitive data at rest
cipher_suite = Fernet(settings.ENCRYPTION_KEY)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT refresh token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Verify token type
        if payload.get("type") != token_type:
            raise AuthenticationError("Invalid token type")
        
        # Check expiration
        exp = payload.get("exp")
        if exp is None or datetime.utcfromtimestamp(exp) < datetime.utcnow():
            raise AuthenticationError("Token has expired")
        
        return payload
        
    except JWTError as e:
        raise AuthenticationError(f"Token verification failed: {str(e)}")


def encrypt_sensitive_data(data: str) -> str:
    """Encrypt sensitive data for storage."""
    return cipher_suite.encrypt(data.encode()).decode()


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """Decrypt sensitive data from storage."""
    return cipher_suite.decrypt(encrypted_data.encode()).decode()


def generate_secure_token(length: int = 32) -> str:
    """Generate cryptographically secure random token."""
    return secrets.token_urlsafe(length)


def generate_api_key() -> str:
    """Generate API key for external integrations."""
    return f"fc_{secrets.token_urlsafe(32)}"


class TokenBlacklist:
    """Simple in-memory token blacklist (use Redis in production)."""
    
    _blacklisted_tokens: set = set()
    
    @classmethod
    def add_token(cls, token: str) -> None:
        """Add token to blacklist."""
        cls._blacklisted_tokens.add(token)
    
    @classmethod
    def is_blacklisted(cls, token: str) -> bool:
        """Check if token is blacklisted."""
        return token in cls._blacklisted_tokens
    
    @classmethod
    def clear_expired(cls) -> None:
        """Clear expired tokens from blacklist."""
        # In production, implement with Redis TTL
        pass


def validate_password_strength(password: str) -> bool:
    """Validate password meets security requirements."""
    if len(password) < 8:
        return False
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
    
    return all([has_upper, has_lower, has_digit, has_special])


def generate_password_reset_token(user_id: str) -> str:
    """Generate secure password reset token."""
    data = {
        "user_id": user_id,
        "purpose": "password_reset",
        "issued_at": datetime.utcnow().isoformat(),
    }
    
    # Short expiration for security
    expires_delta = timedelta(hours=1)
    return create_access_token(data, expires_delta)