"""
LemonSqueezy Payment Processing Integration
Cost-optimized payment processing for subscription management
"""
import httpx
import hmac
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.api.config import settings
from src.api.database import get_db
from .models import UserSubscription, SubscriptionTier, SubscriptionStatus, BillingCycle


class LemonSqueezyClient:
    """LemonSqueezy API client for subscription management"""
    
    def __init__(self):
        self.api_key = settings.LEMONSQUEEZY_API_KEY
        self.store_id = settings.LEMONSQUEEZY_STORE_ID
        self.webhook_secret = settings.LEMONSQUEEZY_WEBHOOK_SECRET
        self.base_url = "https://api.lemonsqueezy.com/v1"
        
        # Product variant mapping (configured in LemonSqueezy dashboard)
        self.variant_mapping = {
            # Oracle tier
            "oracle_monthly": settings.LEMONSQUEEZY_ORACLE_MONTHLY_VARIANT,
            "oracle_annual": settings.LEMONSQUEEZY_ORACLE_ANNUAL_VARIANT,
            
            # Whale tier  
            "whale_monthly": settings.LEMONSQUEEZY_WHALE_MONTHLY_VARIANT,
            "whale_annual": settings.LEMONSQUEEZY_WHALE_ANNUAL_VARIANT,
            
            # Purple tier
            "purple_monthly": settings.LEMONSQUEEZY_PURPLE_MONTHLY_VARIANT,
            "purple_annual": settings.LEMONSQUEEZY_PURPLE_ANNUAL_VARIANT,
            
            # Kingmaker tier
            "kingmaker_monthly": settings.LEMONSQUEEZY_KINGMAKER_MONTHLY_VARIANT,
            "kingmaker_annual": settings.LEMONSQUEEZY_KINGMAKER_ANNUAL_VARIANT,
        }
    
    async def create_checkout_url(
        self,
        user_id: str,
        user_email: str,
        user_name: str,
        tier_slug: str,
        billing_cycle: str = "monthly",
        trial_days: int = 0
    ) -> str:
        """Create checkout URL for subscription with optimized conversion"""
        
        variant_key = f"{tier_slug}_{billing_cycle}"
        variant_id = self.variant_mapping.get(variant_key)
        
        if not variant_id:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown subscription tier/billing combination: {variant_key}"
            )
        
        # Checkout configuration optimized for conversion
        checkout_data = {
            "data": {
                "type": "checkouts",
                "attributes": {
                    "checkout_options": {
                        "embed": False,
                        "media": True,
                        "logo": True,
                        "desc": True,
                        "discount": True,
                        "dark": False,
                        "subscription_preview": True
                    },
                    "checkout_data": {
                        "email": user_email,
                        "name": user_name,
                        "billing_address": {
                            "country": "US"  # Default, user can change
                        },
                        "tax_number": "",
                        "discount_code": "",
                        "custom": {
                            "user_id": user_id,
                            "tier_slug": tier_slug,
                            "billing_cycle": billing_cycle,
                            "trial_days": trial_days,
                            "created_at": datetime.utcnow().isoformat()
                        }
                    },
                    "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
                },
                "relationships": {
                    "store": {
                        "data": {
                            "type": "stores",
                            "id": self.store_id
                        }
                    },
                    "variant": {
                        "data": {
                            "type": "variants",
                            "id": variant_id
                        }
                    }
                }
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/checkouts",
                json=checkout_data,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/vnd.api+json",
                    "Accept": "application/vnd.api+json"
                }
            )
        
        if response.status_code != 201:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create checkout: {response.text}"
            )
        
        checkout = response.json()
        checkout_url = checkout["data"]["attributes"]["url"]
        
        # Track checkout creation for analytics
        await self._track_checkout_created(user_id, tier_slug, billing_cycle, checkout_url)
        
        return checkout_url
    
    async def get_subscription_details(self, subscription_id: str) -> Dict:
        """Get subscription details from LemonSqueezy"""
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/subscriptions/{subscription_id}",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Accept": "application/vnd.api+json"
                }
            )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=404,
                detail=f"Subscription not found: {subscription_id}"
            )
        
        return response.json()
    
    async def cancel_subscription(self, subscription_id: str) -> Dict:
        """Cancel subscription in LemonSqueezy"""
        
        cancel_data = {
            "data": {
                "type": "subscriptions",
                "id": subscription_id,
                "attributes": {
                    "cancelled": True
                }
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.patch(
                f"{self.base_url}/subscriptions/{subscription_id}",
                json=cancel_data,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/vnd.api+json",
                    "Accept": "application/vnd.api+json"
                }
            )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to cancel subscription: {response.text}"
            )
        
        return response.json()
    
    async def update_subscription(self, subscription_id: str, updates: Dict) -> Dict:
        """Update subscription in LemonSqueezy"""
        
        update_data = {
            "data": {
                "type": "subscriptions",
                "id": subscription_id,
                "attributes": updates
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.patch(
                f"{self.base_url}/subscriptions/{subscription_id}",
                json=update_data,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/vnd.api+json",
                    "Accept": "application/vnd.api+json"
                }
            )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update subscription: {response.text}"
            )
        
        return response.json()
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature for security"""
        
        if not self.webhook_secret:
            return False
        
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={expected_signature}", signature)
    
    async def handle_webhook(self, event_type: str, event_data: Dict, db: Session):
        """Handle LemonSqueezy webhook events"""
        
        event_handlers = {
            "subscription_created": self._handle_subscription_created,
            "subscription_updated": self._handle_subscription_updated,
            "subscription_cancelled": self._handle_subscription_cancelled,
            "subscription_resumed": self._handle_subscription_resumed,
            "subscription_expired": self._handle_subscription_expired,
            "subscription_paused": self._handle_subscription_paused,
            "subscription_unpaused": self._handle_subscription_unpaused,
            "subscription_payment_success": self._handle_payment_success,
            "subscription_payment_failed": self._handle_payment_failed,
            "subscription_payment_recovered": self._handle_payment_recovered
        }
        
        handler = event_handlers.get(event_type)
        if handler:
            await handler(event_data, db)
        else:
            print(f"Unhandled webhook event type: {event_type}")
    
    async def _handle_subscription_created(self, event_data: Dict, db: Session):
        """Process new subscription creation"""
        
        attributes = event_data["data"]["attributes"]
        custom_data = attributes.get("custom_data", {})
        
        # Extract custom data
        user_id = custom_data.get("user_id")
        tier_slug = custom_data.get("tier_slug")
        billing_cycle = custom_data.get("billing_cycle", "monthly")
        
        if not user_id or not tier_slug:
            raise ValueError("Missing required custom data in subscription webhook")
        
        # Get tier info
        tier = db.query(SubscriptionTier).filter(
            SubscriptionTier.slug == tier_slug
        ).first()
        
        if not tier:
            raise ValueError(f"Unknown subscription tier: {tier_slug}")
        
        # Parse dates
        period_start = datetime.fromisoformat(attributes["renews_at"].replace("Z", "+00:00"))
        if billing_cycle == "annual":
            period_end = period_start + timedelta(days=365)
        else:
            period_end = period_start + timedelta(days=30)
        
        trial_end = None
        if attributes.get("trial_ends_at"):
            trial_end = datetime.fromisoformat(attributes["trial_ends_at"].replace("Z", "+00:00"))
        
        # Create subscription record
        subscription = UserSubscription(
            user_id=user_id,
            tier_id=tier.id,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=billing_cycle,
            current_period_start=period_start,
            current_period_end=period_end,
            trial_ends_at=trial_end,
            payment_provider="lemonsqueezy",
            external_subscription_id=str(attributes["id"]),
            external_customer_id=str(attributes.get("customer_id", "")),
            home_featuring_enabled=(tier_slug in ["purple", "kingmaker"])
        )
        
        db.add(subscription)
        db.commit()
        
        # Enable Purple featuring if applicable
        if tier_slug in ["purple", "kingmaker"]:
            await self._enable_purple_featuring(user_id, db)
        
        # Track conversion for analytics
        await self._track_subscription_created(user_id, tier_slug, billing_cycle)
    
    async def _handle_subscription_updated(self, event_data: Dict, db: Session):
        """Process subscription updates"""
        
        attributes = event_data["data"]["attributes"]
        external_id = str(attributes["id"])
        
        subscription = db.query(UserSubscription).filter(
            UserSubscription.external_subscription_id == external_id
        ).first()
        
        if not subscription:
            print(f"Subscription not found for external ID: {external_id}")
            return
        
        # Update subscription details
        subscription.current_period_start = datetime.fromisoformat(
            attributes["renews_at"].replace("Z", "+00:00")
        )
        
        if subscription.billing_cycle == BillingCycle.ANNUAL:
            subscription.current_period_end = subscription.current_period_start + timedelta(days=365)
        else:
            subscription.current_period_end = subscription.current_period_start + timedelta(days=30)
        
        # Update status based on LemonSqueezy status
        ls_status = attributes.get("status", "active")
        status_mapping = {
            "active": SubscriptionStatus.ACTIVE,
            "cancelled": SubscriptionStatus.CANCELED,
            "expired": SubscriptionStatus.CANCELED,
            "past_due": SubscriptionStatus.PAST_DUE,
            "paused": SubscriptionStatus.PAUSED
        }
        
        subscription.status = status_mapping.get(ls_status, SubscriptionStatus.ACTIVE)
        subscription.updated_at = datetime.utcnow()
        
        db.commit()
    
    async def _handle_subscription_cancelled(self, event_data: Dict, db: Session):
        """Process subscription cancellation"""
        
        attributes = event_data["data"]["attributes"]
        external_id = str(attributes["id"])
        
        subscription = db.query(UserSubscription).filter(
            UserSubscription.external_subscription_id == external_id
        ).first()
        
        if subscription:
            subscription.status = SubscriptionStatus.CANCELED
            subscription.canceled_at = datetime.utcnow()
            subscription.home_featuring_enabled = False  # Disable featuring
            db.commit()
            
            # Disable Purple featuring
            await self._disable_purple_featuring(subscription.user_id, db)
    
    async def _handle_payment_success(self, event_data: Dict, db: Session):
        """Process successful payment"""
        
        attributes = event_data["data"]["attributes"]
        subscription_id = str(attributes.get("subscription_id"))
        amount = int(attributes.get("subtotal", 0))  # In cents
        
        subscription = db.query(UserSubscription).filter(
            UserSubscription.external_subscription_id == subscription_id
        ).first()
        
        if subscription:
            subscription.total_paid += amount
            subscription.payment_failures = 0  # Reset failure count
            subscription.updated_at = datetime.utcnow()
            db.commit()
    
    async def _handle_payment_failed(self, event_data: Dict, db: Session):
        """Process failed payment"""
        
        attributes = event_data["data"]["attributes"]
        subscription_id = str(attributes.get("subscription_id"))
        
        subscription = db.query(UserSubscription).filter(
            UserSubscription.external_subscription_id == subscription_id
        ).first()
        
        if subscription:
            subscription.payment_failures += 1
            subscription.status = SubscriptionStatus.PAST_DUE
            
            # Disable featuring after 3 failed payments
            if subscription.payment_failures >= 3:
                subscription.home_featuring_enabled = False
            
            subscription.updated_at = datetime.utcnow()
            db.commit()
            
            # Send payment failure notification
            await self._notify_payment_failure(subscription)
    
    async def _enable_purple_featuring(self, user_id: str, db: Session):
        """Enable Purple tier featuring for user"""
        from .featuring import PurpleFeaturingService
        
        featuring_service = PurpleFeaturingService(db)
        await featuring_service.enable_user_featuring(user_id)
    
    async def _disable_purple_featuring(self, user_id: str, db: Session):
        """Disable Purple tier featuring for user"""
        from .featuring import PurpleFeaturingService
        
        featuring_service = PurpleFeaturingService(db)
        await featuring_service.disable_user_featuring(user_id)
    
    async def _track_checkout_created(self, user_id: str, tier_slug: str, billing_cycle: str, checkout_url: str):
        """Track checkout creation for analytics"""
        # Implementation would integrate with analytics service
        print(f"Checkout created: {user_id} -> {tier_slug} {billing_cycle}")
    
    async def _track_subscription_created(self, user_id: str, tier_slug: str, billing_cycle: str):
        """Track successful subscription conversion"""
        # Implementation would integrate with analytics service  
        print(f"Subscription created: {user_id} -> {tier_slug} {billing_cycle}")
    
    async def _notify_payment_failure(self, subscription: UserSubscription):
        """Send payment failure notification to user"""
        # Implementation would integrate with email service
        print(f"Payment failed for subscription: {subscription.id}")


class SubscriptionPricing:
    """Helper class for subscription pricing calculations"""
    
    @staticmethod
    def calculate_savings(monthly_price: int, annual_price: int) -> Dict:
        """Calculate savings for annual billing"""
        
        monthly_annual_cost = monthly_price * 12
        annual_savings = monthly_annual_cost - annual_price
        savings_percentage = int((annual_savings / monthly_annual_cost) * 100)
        
        return {
            "monthly_cost_per_year": monthly_annual_cost,
            "annual_cost": annual_price,
            "savings_amount": annual_savings,
            "savings_percentage": savings_percentage,
            "effective_monthly_price": annual_price // 12
        }
    
    @staticmethod
    def get_tier_comparison(tiers: List[SubscriptionTier]) -> List[Dict]:
        """Generate tier comparison data for frontend"""
        
        comparison = []
        for tier in sorted(tiers, key=lambda t: t.display_order):
            
            annual_savings = None
            if tier.price_annual:
                annual_savings = SubscriptionPricing.calculate_savings(
                    tier.price_monthly, 
                    tier.price_annual
                )
            
            comparison.append({
                "id": str(tier.id),
                "name": tier.name,
                "slug": tier.slug,
                "tagline": tier.marketing_tagline,
                "monthly_price": tier.price_monthly,
                "annual_price": tier.price_annual,
                "monthly_price_display": f"${tier.monthly_price_dollars:.0f}",
                "annual_price_display": f"${tier.annual_price_dollars:.0f}" if tier.price_annual else None,
                "annual_savings": annual_savings,
                "features": tier.features,
                "highlight_features": tier.highlight_features or [],
                "max_position_size": tier.max_position_size,
                "is_featured": tier.is_featured,
                "is_purple_tier": tier.slug in ["purple", "kingmaker"]
            })
        
        return comparison