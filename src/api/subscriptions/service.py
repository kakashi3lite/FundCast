"""
Subscription Service - Main business logic for subscription management
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from .featuring import PurpleFeaturingService
from .lemonsqueezy import LemonSqueezyClient, SubscriptionPricing
from .models import (
    FeaturingAnalytics,
    PurpleFeaturingSchedule,
    SubscriptionStatus,
    SubscriptionTier,
    UserSubscription,
)


class SubscriptionService:
    """Main service for subscription management"""

    def __init__(self, db: Session):
        self.db = db
        self.payment_client = LemonSqueezyClient()
        self.featuring_service = PurpleFeaturingService(db)

    async def get_available_tiers(self, include_inactive: bool = False) -> List[Dict]:
        """Get all available subscription tiers with pricing"""

        query = self.db.query(SubscriptionTier)

        if not include_inactive:
            query = query.filter(SubscriptionTier.is_active == True)

        tiers = query.order_by(SubscriptionTier.display_order).all()
        return SubscriptionPricing.get_tier_comparison(tiers)

    async def get_user_subscription(self, user_id: str) -> Optional[Dict]:
        """Get user's current active subscription"""

        subscription = (
            self.db.query(UserSubscription)
            .join(SubscriptionTier)
            .filter(
                UserSubscription.user_id == user_id,
                UserSubscription.status == SubscriptionStatus.ACTIVE,
            )
            .first()
        )

        if not subscription:
            return None

        return {
            "id": str(subscription.id),
            "user_id": str(subscription.user_id),
            "tier": {
                "id": str(subscription.tier.id),
                "name": subscription.tier.name,
                "slug": subscription.tier.slug,
                "price_monthly": subscription.tier.price_monthly,
                "price_annual": subscription.tier.price_annual,
                "features": subscription.tier.features,
            },
            "status": subscription.status,
            "billing_cycle": subscription.billing_cycle,
            "current_period_start": subscription.current_period_start.isoformat(),
            "current_period_end": subscription.current_period_end.isoformat(),
            "trial_ends_at": (
                subscription.trial_ends_at.isoformat()
                if subscription.trial_ends_at
                else None
            ),
            "canceled_at": (
                subscription.canceled_at.isoformat()
                if subscription.canceled_at
                else None
            ),
            # Purple tier features
            "home_featuring_enabled": subscription.home_featuring_enabled,
            "is_purple_tier": subscription.is_purple_tier,
            "last_featured_at": (
                subscription.last_featured_at.isoformat()
                if subscription.last_featured_at
                else None
            ),
            "total_featuring_time": subscription.total_featuring_time,
            # Financial info
            "total_paid": subscription.total_paid,
            "next_billing_amount": subscription.get_price_paid(),
            "days_until_renewal": subscription.days_until_renewal,
            # Referral
            "referral_code": subscription.referral_code,
            # Timestamps
            "created_at": subscription.created_at.isoformat(),
            "updated_at": subscription.updated_at.isoformat(),
        }

    async def create_checkout_session(
        self,
        user_id: str,
        user_email: str,
        user_name: str,
        tier_slug: str,
        billing_cycle: str = "monthly",
        trial_days: int = 0,
        referral_code: Optional[str] = None,
    ) -> Dict:
        """Create checkout session for new subscription"""

        # Validate tier exists
        tier = (
            self.db.query(SubscriptionTier)
            .filter(
                SubscriptionTier.slug == tier_slug, SubscriptionTier.is_active == True
            )
            .first()
        )

        if not tier:
            raise ValueError(f"Invalid subscription tier: {tier_slug}")

        # Check if user already has active subscription
        existing_subscription = (
            self.db.query(UserSubscription)
            .filter(
                UserSubscription.user_id == user_id,
                UserSubscription.status == SubscriptionStatus.ACTIVE,
            )
            .first()
        )

        if existing_subscription:
            raise ValueError("User already has an active subscription")

        # Create checkout URL
        checkout_url = await self.payment_client.create_checkout_url(
            user_id=user_id,
            user_email=user_email,
            user_name=user_name,
            tier_slug=tier_slug,
            billing_cycle=billing_cycle,
            trial_days=trial_days,
        )

        return {
            "checkout_url": checkout_url,
            "tier": {
                "name": tier.name,
                "slug": tier.slug,
                "price_monthly": tier.monthly_price_dollars,
                "price_annual": (
                    tier.annual_price_dollars if tier.price_annual else None
                ),
                "features": tier.features,
            },
            "billing_cycle": billing_cycle,
            "trial_days": trial_days,
            "referral_code": referral_code,
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        }

    async def upgrade_subscription(
        self, user_id: str, new_tier_slug: str, billing_cycle: Optional[str] = None
    ) -> Dict:
        """Upgrade user's subscription to a higher tier"""

        current_subscription = (
            self.db.query(UserSubscription)
            .filter(
                UserSubscription.user_id == user_id,
                UserSubscription.status == SubscriptionStatus.ACTIVE,
            )
            .first()
        )

        if not current_subscription:
            raise ValueError("No active subscription found")

        new_tier = (
            self.db.query(SubscriptionTier)
            .filter(
                SubscriptionTier.slug == new_tier_slug,
                SubscriptionTier.is_active == True,
            )
            .first()
        )

        if not new_tier:
            raise ValueError(f"Invalid tier: {new_tier_slug}")

        # Validate upgrade (new tier should be more expensive)
        current_price = current_subscription.tier.price_monthly
        new_price = new_tier.price_monthly

        if new_price <= current_price:
            raise ValueError("Can only upgrade to higher-tier subscriptions")

        # Update subscription in payment processor
        external_subscription_id = current_subscription.external_subscription_id

        # Calculate prorated amount
        days_remaining = (
            current_subscription.current_period_end - datetime.utcnow()
        ).days
        proration_credit = (current_price * days_remaining) // 30  # Rough proration

        # Update subscription
        current_subscription.tier_id = new_tier.id
        if billing_cycle:
            current_subscription.billing_cycle = billing_cycle
        current_subscription.updated_at = datetime.utcnow()

        # Enable Purple featuring if upgrading to Purple/Kingmaker
        if new_tier_slug in ["purple", "kingmaker"]:
            current_subscription.home_featuring_enabled = True
            await self.featuring_service.enable_user_featuring(user_id)

        self.db.commit()

        return {
            "success": True,
            "new_tier": new_tier.name,
            "proration_credit": proration_credit,
            "next_billing_amount": current_subscription.get_price_paid(),
            "effective_date": datetime.utcnow().isoformat(),
        }

    async def cancel_subscription(
        self, user_id: str, immediate: bool = False, reason: Optional[str] = None
    ) -> Dict:
        """Cancel user's subscription"""

        subscription = (
            self.db.query(UserSubscription)
            .filter(
                UserSubscription.user_id == user_id,
                UserSubscription.status == SubscriptionStatus.ACTIVE,
            )
            .first()
        )

        if not subscription:
            raise ValueError("No active subscription found")

        # Cancel in payment processor
        await self.payment_client.cancel_subscription(
            subscription.external_subscription_id
        )

        # Update local subscription
        subscription.canceled_at = datetime.utcnow()

        if immediate:
            subscription.status = SubscriptionStatus.CANCELED
            subscription.current_period_end = datetime.utcnow()
            subscription.home_featuring_enabled = False

            # Disable Purple featuring immediately
            await self.featuring_service.disable_user_featuring(user_id)
        else:
            # Cancel at end of billing period
            subscription.home_featuring_enabled = False  # Disable featuring immediately

        self.db.commit()

        return {
            "success": True,
            "canceled_at": subscription.canceled_at.isoformat(),
            "ends_at": subscription.current_period_end.isoformat(),
            "immediate": immediate,
            "reason": reason,
        }

    async def reactivate_subscription(self, user_id: str) -> Dict:
        """Reactivate a canceled subscription"""

        subscription = (
            self.db.query(UserSubscription)
            .filter(
                UserSubscription.user_id == user_id,
                UserSubscription.status == SubscriptionStatus.CANCELED,
                UserSubscription.current_period_end
                > datetime.utcnow(),  # Still in grace period
            )
            .first()
        )

        if not subscription:
            raise ValueError("No reactivatable subscription found")

        # Reactivate in payment processor
        await self.payment_client.update_subscription(
            subscription.external_subscription_id, {"cancelled": False}
        )

        # Update local subscription
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.canceled_at = None
        subscription.updated_at = datetime.utcnow()

        # Re-enable Purple featuring if applicable
        if subscription.tier.slug in ["purple", "kingmaker"]:
            subscription.home_featuring_enabled = True
            await self.featuring_service.enable_user_featuring(user_id)

        self.db.commit()

        return {
            "success": True,
            "reactivated_at": datetime.utcnow().isoformat(),
            "next_billing_date": subscription.current_period_end.isoformat(),
        }

    async def update_billing_cycle(self, user_id: str, new_billing_cycle: str) -> Dict:
        """Change billing cycle (monthly <-> annual)"""

        subscription = (
            self.db.query(UserSubscription)
            .filter(
                UserSubscription.user_id == user_id,
                UserSubscription.status == SubscriptionStatus.ACTIVE,
            )
            .first()
        )

        if not subscription:
            raise ValueError("No active subscription found")

        if subscription.billing_cycle == new_billing_cycle:
            return {"success": True, "message": "Billing cycle unchanged"}

        # Calculate price difference
        old_price = subscription.get_price_paid()
        subscription.billing_cycle = new_billing_cycle
        new_price = subscription.get_price_paid()

        # Update in payment processor
        await self.payment_client.update_subscription(
            subscription.external_subscription_id,
            {"billing_interval": new_billing_cycle},
        )

        subscription.updated_at = datetime.utcnow()
        self.db.commit()

        return {
            "success": True,
            "new_billing_cycle": new_billing_cycle,
            "old_price": old_price,
            "new_price": new_price,
            "savings": old_price - new_price if new_billing_cycle == "annual" else 0,
            "effective_date": subscription.current_period_end.isoformat(),
        }

    async def get_subscription_analytics(self, user_id: str, days: int = 30) -> Dict:
        """Get subscription and featuring analytics for user"""

        subscription = (
            self.db.query(UserSubscription)
            .filter(UserSubscription.user_id == user_id)
            .first()
        )

        if not subscription:
            return {"error": "No subscription found"}

        # Get featuring analytics
        start_date = datetime.utcnow() - timedelta(days=days)
        analytics = (
            self.db.query(FeaturingAnalytics)
            .filter(
                FeaturingAnalytics.user_id == user_id,
                FeaturingAnalytics.date >= start_date,
            )
            .all()
        )

        # Get featuring schedules
        featuring_schedules = (
            self.db.query(PurpleFeaturingSchedule)
            .filter(
                PurpleFeaturingSchedule.user_id == user_id,
                PurpleFeaturingSchedule.scheduled_start >= start_date,
            )
            .all()
        )

        # Aggregate metrics
        total_impressions = sum(a.home_impressions for a in analytics)
        total_clicks = sum(a.profile_clicks for a in analytics)
        total_connections = sum(a.connection_requests for a in analytics)
        total_opportunities = sum(a.opportunities_generated for a in analytics)

        featuring_hours = sum(f.duration_hours for f in featuring_schedules)

        return {
            "subscription": {
                "tier": subscription.tier.name,
                "status": subscription.status,
                "member_since": subscription.created_at.isoformat(),
                "total_paid": subscription.total_paid,
                "is_purple_tier": subscription.is_purple_tier,
            },
            "featuring_metrics": {
                "total_impressions": total_impressions,
                "total_clicks": total_clicks,
                "total_connections": total_connections,
                "total_opportunities": total_opportunities,
                "featuring_hours": featuring_hours,
                "click_through_rate": (
                    (total_clicks / total_impressions * 100)
                    if total_impressions > 0
                    else 0
                ),
                "conversion_rate": (
                    (total_connections / total_clicks * 100) if total_clicks > 0 else 0
                ),
            },
            "recent_featuring": [
                {
                    "type": f.featuring_type,
                    "start": f.scheduled_start.isoformat(),
                    "end": f.scheduled_end.isoformat(),
                    "impressions": f.impressions,
                    "clicks": f.clicks,
                    "engagement_score": f.engagement_score,
                }
                for f in featuring_schedules[-5:]  # Last 5 featuring sessions
            ],
            "period_days": days,
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def get_purple_featuring_queue(self, user_id: str) -> Dict:
        """Get user's Purple featuring queue and schedule"""

        subscription = (
            self.db.query(UserSubscription)
            .filter(
                UserSubscription.user_id == user_id,
                UserSubscription.status == SubscriptionStatus.ACTIVE,
            )
            .first()
        )

        if not subscription or not subscription.is_purple_tier:
            return {"error": "Purple tier subscription required"}

        # Get upcoming featuring schedules
        upcoming_schedules = (
            self.db.query(PurpleFeaturingSchedule)
            .filter(
                PurpleFeaturingSchedule.user_id == user_id,
                PurpleFeaturingSchedule.scheduled_start > datetime.utcnow(),
                PurpleFeaturingSchedule.status.in_(["scheduled", "active"]),
            )
            .order_by(PurpleFeaturingSchedule.scheduled_start)
            .all()
        )

        # Calculate queue position for hero featuring
        next_hero_slot = datetime.utcnow().replace(
            hour=0, minute=0, second=0
        ) + timedelta(days=1)

        hero_queue = (
            self.db.query(PurpleFeaturingSchedule)
            .filter(
                PurpleFeaturingSchedule.featuring_type == "hero",
                PurpleFeaturingSchedule.scheduled_start >= next_hero_slot,
                PurpleFeaturingSchedule.status == "scheduled",
            )
            .order_by(PurpleFeaturingSchedule.scheduled_start)
            .all()
        )

        user_hero_position = None
        for i, featuring in enumerate(hero_queue):
            if featuring.user_id == user_id:
                user_hero_position = i + 1
                break

        return {
            "featuring_enabled": subscription.home_featuring_enabled,
            "tier": subscription.tier.name,
            "queue_position": {
                "hero": user_hero_position,
                "estimated_hero_date": (
                    hero_queue[user_hero_position - 1].scheduled_start.isoformat()
                    if user_hero_position
                    else None
                ),
            },
            "upcoming_featuring": [
                {
                    "id": str(f.id),
                    "type": f.featuring_type,
                    "scheduled_start": f.scheduled_start.isoformat(),
                    "scheduled_end": f.scheduled_end.isoformat(),
                    "status": f.status,
                    "custom_bio": f.custom_bio,
                    "achievement_highlight": f.achievement_highlight,
                }
                for f in upcoming_schedules
            ],
            "last_featured": (
                subscription.last_featured_at.isoformat()
                if subscription.last_featured_at
                else None
            ),
            "total_featuring_hours": subscription.total_featuring_time,
        }

    async def update_featuring_content(
        self,
        user_id: str,
        featuring_id: str,
        custom_bio: Optional[str] = None,
        achievement_highlight: Optional[str] = None,
        cta_text: Optional[str] = None,
    ) -> Dict:
        """Update custom content for a scheduled featuring"""

        featuring = (
            self.db.query(PurpleFeaturingSchedule)
            .filter(
                PurpleFeaturingSchedule.id == featuring_id,
                PurpleFeaturingSchedule.user_id == user_id,
                PurpleFeaturingSchedule.status == "scheduled",
            )
            .first()
        )

        if not featuring:
            raise ValueError("Featuring not found or cannot be modified")

        # Update content
        if custom_bio is not None:
            featuring.custom_bio = custom_bio[:500]  # Limit length

        if achievement_highlight is not None:
            featuring.achievement_highlight = achievement_highlight[:200]

        if cta_text is not None:
            featuring.cta_text = cta_text[:100]

        featuring.updated_at = datetime.utcnow()
        self.db.commit()

        return {
            "success": True,
            "featuring_id": str(featuring.id),
            "updated_content": {
                "custom_bio": featuring.custom_bio,
                "achievement_highlight": featuring.achievement_highlight,
                "cta_text": featuring.cta_text,
            },
            "updated_at": featuring.updated_at.isoformat(),
        }

    async def get_subscription_metrics(self, admin_user_id: str) -> Dict:
        """Get platform-wide subscription metrics (admin only)"""

        # This would include admin authorization check

        total_subscriptions = self.db.query(UserSubscription).count()
        active_subscriptions = (
            self.db.query(UserSubscription)
            .filter(UserSubscription.status == SubscriptionStatus.ACTIVE)
            .count()
        )

        # Count by tier
        tier_counts = {}
        tiers = self.db.query(SubscriptionTier).all()

        for tier in tiers:
            count = (
                self.db.query(UserSubscription)
                .filter(
                    UserSubscription.tier_id == tier.id,
                    UserSubscription.status == SubscriptionStatus.ACTIVE,
                )
                .count()
            )
            tier_counts[tier.name] = count

        # Revenue metrics (last 30 days)
        last_30_days = datetime.utcnow() - timedelta(days=30)
        recent_subscriptions = (
            self.db.query(UserSubscription)
            .filter(UserSubscription.created_at >= last_30_days)
            .all()
        )

        monthly_revenue = sum(sub.get_price_paid() for sub in recent_subscriptions)

        return {
            "total_subscriptions": total_subscriptions,
            "active_subscriptions": active_subscriptions,
            "tier_distribution": tier_counts,
            "monthly_revenue": monthly_revenue,
            "purple_members": tier_counts.get("Purple", 0)
            + tier_counts.get("Kingmaker", 0),
            "featuring_enabled": self.db.query(UserSubscription)
            .filter(UserSubscription.home_featuring_enabled == True)
            .count(),
            "generated_at": datetime.utcnow().isoformat(),
        }
