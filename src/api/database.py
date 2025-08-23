"""Database configuration and models."""

from datetime import datetime
from typing import AsyncGenerator, Optional, Dict, Any
import uuid

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Numeric,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    CheckConstraint,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from .config import settings


class Base(DeclarativeBase):
    """Base model with common fields."""
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(Base):
    """User model with comprehensive profile and compliance data."""
    
    __tablename__ = "users"
    
    # Basic information
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    
    # Authentication
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Profile
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    profile_image_url: Mapped[Optional[str]] = mapped_column(String(500))
    bio: Mapped[Optional[str]] = mapped_column(Text)
    
    # Compliance
    kyc_status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )  # pending, verified, rejected, expired
    
    kyc_provider: Mapped[Optional[str]] = mapped_column(String(50))
    kyc_reference_id: Mapped[Optional[str]] = mapped_column(String(255))
    kyc_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    accredited_status: Mapped[str] = mapped_column(
        String(20),
        default="unknown",
        nullable=False,
        index=True,
    )  # unknown, verified, rejected, expired
    
    accredited_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    accredited_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Role-based access control
    roles: Mapped[list] = mapped_column(JSONB, default=list)
    permissions: Mapped[list] = mapped_column(JSONB, default=list)
    
    # Compliance metadata
    compliance_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Relationships
    companies = relationship("Company", back_populates="owner")
    investments = relationship("Investment", back_populates="investor")
    market_positions = relationship("MarketPosition", back_populates="user")
    
    __table_args__ = (
        CheckConstraint("kyc_status IN ('pending', 'verified', 'rejected', 'expired')"),
        CheckConstraint("accredited_status IN ('unknown', 'verified', 'rejected', 'expired')"),
        Index("idx_user_compliance", "kyc_status", "accredited_status"),
    )


class Company(Base):
    """Company/issuer model for fundraising."""
    
    __tablename__ = "companies"
    
    # Basic information
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    website: Mapped[Optional[str]] = mapped_column(String(500))
    logo_url: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Business details
    industry: Mapped[Optional[str]] = mapped_column(String(100))
    stage: Mapped[Optional[str]] = mapped_column(String(50))
    employee_count: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Legal structure
    incorporation_state: Mapped[Optional[str]] = mapped_column(String(50))
    incorporation_country: Mapped[str] = mapped_column(String(50), default="US")
    entity_type: Mapped[Optional[str]] = mapped_column(String(50))
    tax_id: Mapped[Optional[str]] = mapped_column(String(50))
    
    # KYB (Know Your Business)
    kyb_status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )
    kyb_provider: Mapped[Optional[str]] = mapped_column(String(50))
    kyb_reference_id: Mapped[Optional[str]] = mapped_column(String(255))
    kyb_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Ownership
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Relationships
    owner = relationship("User", back_populates="companies")
    offerings = relationship("Offering", back_populates="company")
    
    __table_args__ = (
        CheckConstraint("kyb_status IN ('pending', 'verified', 'rejected', 'expired')"),
        Index("idx_company_status", "kyb_status", "is_active", "is_verified"),
    )


class Offering(Base):
    """Securities offering model (Reg CF, 506(c), etc.)."""
    
    __tablename__ = "offerings"
    
    # Basic information
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Financial terms
    target_amount: Mapped[int] = mapped_column(Numeric(15, 2), nullable=False)  # cents
    minimum_amount: Mapped[Optional[int]] = mapped_column(Numeric(15, 2))
    maximum_amount: Mapped[Optional[int]] = mapped_column(Numeric(15, 2))
    
    price_per_share: Mapped[Optional[int]] = mapped_column(Numeric(10, 2))  # cents
    minimum_investment: Mapped[int] = mapped_column(Numeric(10, 2), nullable=False)
    
    # Regulatory
    offering_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # reg_cf, reg_a, rule_506b, rule_506c
    
    sec_qualification: Mapped[Optional[str]] = mapped_column(String(50))
    cik: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Timeline
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
        nullable=False,
        index=True,
    )  # draft, pending_review, live, paused, completed, cancelled
    
    # Relationships
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    company = relationship("Company", back_populates="offerings")
    investments = relationship("Investment", back_populates="offering")
    
    # Compliance documents
    documents: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    __table_args__ = (
        CheckConstraint("offering_type IN ('reg_cf', 'reg_a', 'rule_506b', 'rule_506c')"),
        CheckConstraint("status IN ('draft', 'pending_review', 'live', 'paused', 'completed', 'cancelled')"),
        CheckConstraint("target_amount > 0"),
        CheckConstraint("minimum_investment > 0"),
        Index("idx_offering_status_type", "status", "offering_type"),
    )


class Investment(Base):
    """Investment/commitment model."""
    
    __tablename__ = "investments"
    
    # Investment details
    amount: Mapped[int] = mapped_column(Numeric(12, 2), nullable=False)  # cents
    shares: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )  # pending, confirmed, cancelled, settled
    
    # Payment
    payment_method: Mapped[Optional[str]] = mapped_column(String(50))
    payment_reference: Mapped[Optional[str]] = mapped_column(String(255))
    payment_confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    investor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    offering_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("offerings.id"), nullable=False)
    
    investor = relationship("User", back_populates="investments")
    offering = relationship("Offering", back_populates="investments")
    
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'confirmed', 'cancelled', 'settled')"),
        CheckConstraint("amount > 0"),
        Index("idx_investment_status", "status", "investor_id"),
    )


class Market(Base):
    """Prediction market model."""
    
    __tablename__ = "markets"
    
    # Basic information
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Market mechanics
    market_type: Mapped[str] = mapped_column(
        String(20),
        default="binary",
        nullable=False,
    )  # binary, categorical, scalar
    
    engine_type: Mapped[str] = mapped_column(
        String(20),
        default="orderbook",
        nullable=False,
    )  # orderbook, amm
    
    # Settlement
    resolution_source: Mapped[Optional[str]] = mapped_column(String(500))
    resolution_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolution_value: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
        index=True,
    )  # active, paused, resolved, cancelled
    
    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # AI embeddings for semantic search
    embedding: Mapped[Optional[list]] = mapped_column(Vector(384))
    
    # Relationships
    positions = relationship("MarketPosition", back_populates="market")
    
    __table_args__ = (
        CheckConstraint("market_type IN ('binary', 'categorical', 'scalar')"),
        CheckConstraint("engine_type IN ('orderbook', 'amm')"),
        CheckConstraint("status IN ('active', 'paused', 'resolved', 'cancelled')"),
        Index("idx_market_status_type", "status", "market_type"),
        Index("idx_market_embedding", "embedding", postgresql_using="ivfflat"),
    )


class MarketPosition(Base):
    """User positions in prediction markets."""
    
    __tablename__ = "market_positions"
    
    # Position details
    outcome: Mapped[str] = mapped_column(String(100), nullable=False)
    shares: Mapped[int] = mapped_column(Numeric(12, 6), nullable=False)
    avg_price: Mapped[int] = mapped_column(Numeric(8, 6), nullable=False)  # Average price paid
    
    # Current value
    current_value: Mapped[int] = mapped_column(Numeric(12, 2), default=0)
    unrealized_pnl: Mapped[int] = mapped_column(Numeric(12, 2), default=0)
    
    # Relationships
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    market_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("markets.id"), nullable=False)
    
    user = relationship("User", back_populates="market_positions")
    market = relationship("Market", back_populates="positions")
    
    __table_args__ = (
        UniqueConstraint("user_id", "market_id", "outcome", name="uq_user_market_outcome"),
        CheckConstraint("shares >= 0"),
        CheckConstraint("avg_price >= 0 AND avg_price <= 1"),
        Index("idx_position_user_market", "user_id", "market_id"),
    )


# Database session management
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=300,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# Import all models to ensure they're registered with SQLAlchemy
from .subscriptions.models import *  # noqa: F401,F403


async def get_database() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Alias for consistency with subscription router imports
get_db = get_database