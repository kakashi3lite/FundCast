"""Application configuration with security-first defaults."""

import os
from typing import List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with security and performance defaults."""
    
    # Application
    APP_NAME: str = "FundCast"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # Security
    SECRET_KEY: str = Field(..., env="SECRET_KEY", min_length=32)
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY", min_length=32)
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_EXPIRE_MINUTES: int = Field(default=30, env="JWT_EXPIRE_MINUTES")
    JWT_REFRESH_EXPIRE_DAYS: int = Field(default=7, env="JWT_REFRESH_EXPIRE_DAYS")
    
    ENCRYPTION_KEY: bytes = Field(..., env="ENCRYPTION_KEY")
    
    @validator("ENCRYPTION_KEY", pre=True)
    def parse_encryption_key(cls, v):
        """Parse encryption key from environment.

        Fernet expects the URL-safe base64-encoded key bytes (not the raw
        decoded bytes). We validate that the value decodes to exactly 32
        bytes and return the base64 text as bytes for ``Fernet``.
        """
        if isinstance(v, str):
            import base64
            stripped = v.strip()
            padded = stripped + "=" * (-len(stripped) % 4)
            try:
                decoded = base64.urlsafe_b64decode(padded)
            except Exception:
                decoded = base64.b64decode(padded)
            if len(decoded) != 32:
                raise ValueError("ENCRYPTION_KEY must decode to 32 bytes")
            return padded.encode()
        if isinstance(v, bytes):
            return v
        return v
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000"],
        env="CORS_ORIGINS"
    )
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    # Trusted hosts
    ALLOWED_HOSTS: List[str] = Field(
        default=["localhost", "127.0.0.1"],
        env="ALLOWED_HOSTS"
    )
    
    @validator("ALLOWED_HOSTS", pre=True)
    def parse_allowed_hosts(cls, v):
        """Parse allowed hosts from comma-separated string."""
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v
    
    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DATABASE_READ_URL: Optional[str] = Field(default=None, env="DATABASE_READ_URL")
    DATABASE_POOL_SIZE: int = Field(default=20, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=0, env="DATABASE_MAX_OVERFLOW")
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    RATE_LIMIT_BURST: int = Field(default=10, env="RATE_LIMIT_BURST")
    
    # AI/ML
    ONNX_MODEL_PATH: str = Field(default="models/", env="ONNX_MODEL_PATH")
    VLLM_ENDPOINT: Optional[str] = Field(default=None, env="VLLM_ENDPOINT")
    
    # External APIs
    STRIPE_SECRET_KEY: Optional[str] = Field(default=None, env="STRIPE_SECRET_KEY")
    STRIPE_PUBLISHABLE_KEY: Optional[str] = Field(default=None, env="STRIPE_PUBLISHABLE_KEY")
    STRIPE_WEBHOOK_SECRET: Optional[str] = Field(default=None, env="STRIPE_WEBHOOK_SECRET")
    
    PERSONA_API_KEY: Optional[str] = Field(default=None, env="PERSONA_API_KEY")
    PERSONA_TEMPLATE_ID: Optional[str] = Field(default=None, env="PERSONA_TEMPLATE_ID")
    
    # Observability
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = Field(default=None, env="OTEL_EXPORTER_OTLP_ENDPOINT")
    OTEL_EXPORTER_OTLP_HEADERS: Optional[str] = Field(default=None, env="OTEL_EXPORTER_OTLP_HEADERS")
    
    # Email
    SMTP_HOST: Optional[str] = Field(default=None, env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USERNAME: Optional[str] = Field(default=None, env="SMTP_USERNAME")
    SMTP_PASSWORD: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    SMTP_FROM_EMAIL: Optional[str] = Field(default=None, env="SMTP_FROM_EMAIL")
    
    # File storage
    UPLOAD_MAX_SIZE: int = Field(default=10 * 1024 * 1024, env="UPLOAD_MAX_SIZE")  # 10MB
    ALLOWED_FILE_TYPES: List[str] = Field(
        default=["pdf", "doc", "docx", "xls", "xlsx", "png", "jpg", "jpeg"],
        env="ALLOWED_FILE_TYPES"
    )
    
    @validator("ALLOWED_FILE_TYPES", pre=True)
    def parse_file_types(cls, v):
        """Parse allowed file types from comma-separated string."""
        if isinstance(v, str):
            return [ext.strip().lower() for ext in v.split(",")]
        return v
    
    # Compliance
    SEC_FILING_ENDPOINT: Optional[str] = Field(default=None, env="SEC_FILING_ENDPOINT")
    FINRA_API_ENDPOINT: Optional[str] = Field(default=None, env="FINRA_API_ENDPOINT")
    
    # Feature flags
    ENABLE_REGISTRATION: bool = Field(default=True, env="ENABLE_REGISTRATION")
    ENABLE_MARKET_CREATION: bool = Field(default=True, env="ENABLE_MARKET_CREATION")
    ENABLE_AI_FEATURES: bool = Field(default=True, env="ENABLE_AI_FEATURES")
    AI_DEFENSE_ENABLED: bool = Field(default=True, env="AI_DEFENSE_ENABLED")

    # LemonSqueezy (subscriptions / payment processing)
    LEMONSQUEEZY_API_KEY: Optional[str] = Field(default=None, env="LEMONSQUEEZY_API_KEY")
    LEMONSQUEEZY_STORE_ID: Optional[str] = Field(default=None, env="LEMONSQUEEZY_STORE_ID")
    LEMONSQUEEZY_WEBHOOK_SECRET: Optional[str] = Field(default=None, env="LEMONSQUEEZY_WEBHOOK_SECRET")
    LEMONSQUEEZY_ORACLE_MONTHLY_VARIANT: Optional[str] = Field(default=None, env="LEMONSQUEEZY_ORACLE_MONTHLY_VARIANT")
    LEMONSQUEEZY_ORACLE_ANNUAL_VARIANT: Optional[str] = Field(default=None, env="LEMONSQUEEZY_ORACLE_ANNUAL_VARIANT")
    LEMONSQUEEZY_WHALE_MONTHLY_VARIANT: Optional[str] = Field(default=None, env="LEMONSQUEEZY_WHALE_MONTHLY_VARIANT")
    LEMONSQUEEZY_WHALE_ANNUAL_VARIANT: Optional[str] = Field(default=None, env="LEMONSQUEEZY_WHALE_ANNUAL_VARIANT")
    LEMONSQUEEZY_PURPLE_MONTHLY_VARIANT: Optional[str] = Field(default=None, env="LEMONSQUEEZY_PURPLE_MONTHLY_VARIANT")
    LEMONSQUEEZY_PURPLE_ANNUAL_VARIANT: Optional[str] = Field(default=None, env="LEMONSQUEEZY_PURPLE_ANNUAL_VARIANT")
    LEMONSQUEEZY_KINGMAKER_MONTHLY_VARIANT: Optional[str] = Field(default=None, env="LEMONSQUEEZY_KINGMAKER_MONTHLY_VARIANT")
    LEMONSQUEEZY_KINGMAKER_ANNUAL_VARIANT: Optional[str] = Field(default=None, env="LEMONSQUEEZY_KINGMAKER_ANNUAL_VARIANT")

    # Polygon crypto payments (USDC)
    CRYPTO_PAYMENT_ENABLED: bool = Field(default=False, env="CRYPTO_PAYMENT_ENABLED")
    POLYGON_RPC_URL: str = Field(
        default="https://polygon-rpc.com", env="POLYGON_RPC_URL"
    )
    # Circle USDC on Polygon PoS.
    USDC_CONTRACT_ADDRESS: str = Field(
        default="0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        env="USDC_CONTRACT_ADDRESS",
    )
    GAS_SPONSOR_ENABLED: bool = Field(default=False, env="GAS_SPONSOR_ENABLED")

    # IPQS geo-restriction (jurisdiction enforcement)
    IPQS_ENABLED: bool = Field(default=False, env="IPQS_ENABLED")
    IPQS_API_KEY: Optional[str] = Field(default=None, env="IPQS_API_KEY")
    ALLOWED_JURISDICTIONS: List[str] = Field(
        default=["MA"], env="ALLOWED_JURISDICTIONS"
    )

    @validator("ALLOWED_JURISDICTIONS", pre=True)
    def parse_jurisdictions(cls, v):
        """Parse allowed jurisdictions from comma-separated string."""
        if isinstance(v, str):
            return [j.strip().upper() for j in v.split(",") if j.strip()]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()