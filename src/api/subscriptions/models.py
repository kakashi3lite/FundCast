"""
Subscription Management Models
"""

import uuid
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from src.api.database import Base


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    PAUSED = "paused"
    TRIALING = "trialing"


class BillingCycle(str, Enum):
    MONTHLY = "monthly"
    ANNUAL = "annual"


class FeaturingType(str, Enum):
    HERO = "hero"
    GRID = "grid"
    STORY = "story"


class FeaturingStatus(str, Enum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SubscriptionTier(Base):
    """Subscription tier definitions with pricing and features"""

    __tablename__ = "subscription_tiers"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False)
    slug = Column(String(50), unique=True, nullable=False)

    # Pricing (in cents)
    price_monthly = Column(Integer, nullable=False)
    price_annual = Column(Integer)  # With discount applied

    # Limits and features
    max_position_size = Column(Integer)  # Max bet size in cents
    features = Column(JSON, nullable=False)  # Feature list

    # Psychology and marketing
    psychology_notes = Column(Text)
    marketing_tagline = Column(String(200))
    highlight_features = Column(JSON)  # Key features to highlight

    # Status
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)  # Show prominently in pricing
    display_order = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subscriptions = relationship("UserSubscription", back_populates="tier")

    @hybrid_property
    def monthly_price_dollars(self) -> float:
        """Convert cents to dollars for display"""
        return self.price_monthly / 100.0

    @hybrid_property
    def annual_price_dollars(self) -> float:
        """Convert cents to dollars for display"""
        if self.price_annual:
            return self.price_annual / 100.0
        return (self.price_monthly * 12) / 100.0

    @hybrid_property
    def annual_discount_percent(self) -> int:
        """Calculate annual discount percentage"""
        if not self.price_annual:
            return 0

        monthly_annual_cost = self.price_monthly * 12
        discount = monthly_annual_cost - self.price_annual
        return int((discount / monthly_annual_cost) * 100)

    def has_feature(self, feature_name: str) -> bool:
        """Check if tier includes a specific feature"""
        return feature_name in self.features

    def __repr__(self):
        return f"<SubscriptionTier {self.name} ${self.monthly_price_dollars}/mo>"


class UserSubscription(Base):
    """User subscription instances"""

    __tablename__ = "user_subscriptions"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    tier_id = Column(UUID, ForeignKey("subscription_tiers.id"), nullable=False)

    # Subscription details
    status = Column(String(20), nullable=False, default=SubscriptionStatus.ACTIVE)
    billing_cycle = Column(String(10), nullable=False, default=BillingCycle.MONTHLY)

    # Billing periods
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    trial_ends_at = Column(DateTime)
    canceled_at = Column(DateTime)

    # Payment processing
    payment_provider = Column(String(50), nullable=False, default="lemonsqueezy")
    external_subscription_id = Column(String(255), unique=True, nullable=False)
    external_customer_id = Column(String(255))

    # Purple tier specific features
    home_featuring_enabled = Column(Boolean, default=False)
    featuring_weight = Column(Integer, default=1)  # For rotation algorithm
    last_featured_at = Column(DateTime)
    total_featuring_time = Column(Integer, default=0)  # Hours featured total

    # Metrics
    total_paid = Column(Integer, default=0)  # Total paid in cents
    payment_failures = Column(Integer, default=0)
    referral_code = Column(String(50))  # For referral tracking

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="subscription")
    tier = relationship("SubscriptionTier", back_populates="subscriptions")
    featuring_schedules = relationship(
        "PurpleFeaturingSchedule", back_populates="subscription"
    )

    @hybrid_property
    def is_active(self) -> bool:
        """Check if subscription is currently active"""
        return (
            self.status == SubscriptionStatus.ACTIVE
            and self.current_period_end > datetime.utcnow()
        )

    @hybrid_property
    def is_purple_tier(self) -> bool:
        """Check if this is a Purple or Kingmaker subscription"""
        return self.tier.slug in ["purple", "kingmaker"]

    @hybrid_property
    def days_until_renewal(self) -> int:
        """Days until next billing cycle"""
        return (self.current_period_end - datetime.utcnow()).days

    def calculate_next_billing_date(self) -> datetime:
        """Calculate next billing date based on cycle"""
        if self.billing_cycle == BillingCycle.MONTHLY:
            return self.current_period_end + timedelta(days=30)
        else:  # Annual
            return self.current_period_end + timedelta(days=365)

    def get_price_paid(self) -> int:
        """Get the price paid for current billing cycle"""
        if self.billing_cycle == BillingCycle.ANNUAL:
            return self.tier.price_annual or (self.tier.price_monthly * 12)
        return self.tier.price_monthly

    def __repr__(self):
        return f"<UserSubscription {self.user_id} {self.tier.name} {self.status}>"


class PurpleFeaturingSchedule(Base):
    """Schedule for Purple tier home screen featuring"""

    __tablename__ = "purple_featuring_schedule"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    subscription_id = Column(UUID, ForeignKey("user_subscriptions.id"), nullable=False)

    # Featuring details
    featuring_type = Column(String(20), nullable=False)  # hero, grid, story
    scheduled_start = Column(DateTime, nullable=False)
    scheduled_end = Column(DateTime, nullable=False)
    status = Column(String(20), default=FeaturingStatus.SCHEDULED)

    # Custom content for featuring
    custom_bio = Column(Text)
    achievement_highlight = Column(Text)
    cta_text = Column(String(100))
    custom_tags = Column(JSON)  # Custom tags/badges

    # Analytics tracking
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    profile_views = Column(Integer, default=0)
    connections_generated = Column(Integer, default=0)
    opportunities_generated = Column(Integer, default=0)

    # Algorithm weights
    algorithm_weight = Column(Integer, default=1)
    boost_factor = Column(Integer, default=1)  # Temporary boost

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
    subscription = relationship(
        "UserSubscription", back_populates="featuring_schedules"
    )

    @hybrid_property
    def is_active(self) -> bool:
        """Check if currently being featured"""
        now = datetime.utcnow()
        return (
            self.status == FeaturingStatus.ACTIVE
            and self.scheduled_start <= now <= self.scheduled_end
        )

    @hybrid_property
    def duration_hours(self) -> int:
        """Get featuring duration in hours"""
        return int((self.scheduled_end - self.scheduled_start).total_seconds() / 3600)

    @hybrid_property
    def engagement_score(self) -> float:
        """Calculate engagement score for analytics"""
        if self.impressions == 0:
            return 0.0

        click_rate = self.clicks / self.impressions
        profile_rate = (
            self.profile_views / self.impressions if self.impressions > 0 else 0
        )
        connection_rate = (
            self.connections_generated / self.clicks if self.clicks > 0 else 0
        )

        # Weighted engagement score
        return (click_rate * 0.4) + (profile_rate * 0.3) + (connection_rate * 0.3)

    def __repr__(self):
        return f"<PurpleFeaturingSchedule {self.user_id} {self.featuring_type} {self.status}>"


class FeaturingImpression(Base):
    """Individual impression tracking for Purple tier featuring"""

    __tablename__ = "featuring_impressions"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    featuring_schedule_id = Column(
        UUID, ForeignKey("purple_featuring_schedule.id"), nullable=False
    )

    # Impression details
    interaction_type = Column(
        String(20), nullable=False
    )  # view, click, profile, connect
    user_agent = Column(Text)
    ip_address = Column(String(45))  # Support IPv6
    referrer = Column(Text)

    # User context (if available)
    viewer_user_id = Column(UUID, ForeignKey("users.id"), nullable=True)
    session_id = Column(String(100))

    # Metadata
    metadata = Column(JSON)  # Additional tracking data

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    featuring_schedule = relationship("PurpleFeaturingSchedule")
    viewer_user = relationship("User")

    def __repr__(self):
        return f"<FeaturingImpression {self.featuring_schedule_id} {self.interaction_type}>"


class FeaturingAnalytics(Base):
    """Daily analytics for Purple featuring performance"""

    __tablename__ = "featuring_analytics"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    subscription_id = Column(UUID, ForeignKey("user_subscriptions.id"), nullable=False)
    date = Column(DateTime, nullable=False)

    # Visibility metrics
    home_impressions = Column(Integer, default=0)
    profile_clicks = Column(Integer, default=0)
    connection_requests = Column(Integer, default=0)

    # Engagement metrics
    markets_participated = Column(Integer, default=0)
    new_followers = Column(Integer, default=0)
    messages_received = Column(Integer, default=0)
    predictions_made = Column(Integer, default=0)

    # Business impact metrics
    opportunities_generated = Column(Integer, default=0)
    meetings_booked = Column(Integer, default=0)
    deals_attributed = Column(Integer, default=0)
    revenue_attributed = Column(Integer, default=0)  # In cents

    # Social metrics
    shares_generated = Column(Integer, default=0)
    mentions = Column(Integer, default=0)
    social_reach = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")
    subscription = relationship("UserSubscription")

    @hybrid_property
    def conversion_rate(self) -> float:
        """Calculate conversion rate from impressions to connections"""
        if self.home_impressions == 0:
            return 0.0
        return self.connection_requests / self.home_impressions

    @hybrid_property
    def roi_score(self) -> float:
        """Calculate ROI score based on business metrics"""
        # Weight different activities for ROI calculation
        score = (
            self.opportunities_generated * 10
            + self.meetings_booked * 25
            + self.deals_attributed * 100
        )
        return score

    def __repr__(self):
        return f"<FeaturingAnalytics {self.user_id} {self.date.date()}>"
