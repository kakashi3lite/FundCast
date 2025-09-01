"""
Subscription Management API Endpoints
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.auth import get_admin_user, get_current_user
from src.api.database import get_db

from .lemonsqueezy import LemonSqueezyClient
from .service import SubscriptionService

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


# ═══════════════════════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════════════════


class CheckoutRequest(BaseModel):
    tier_slug: str = Field(..., description="Subscription tier slug")
    billing_cycle: str = Field(default="monthly", description="monthly or annual")
    trial_days: int = Field(default=0, description="Trial period in days")
    referral_code: Optional[str] = Field(None, description="Referral code")


class UpgradeRequest(BaseModel):
    new_tier_slug: str = Field(..., description="Target tier slug")
    billing_cycle: Optional[str] = Field(
        None, description="Optional billing cycle change"
    )


class CancelRequest(BaseModel):
    immediate: bool = Field(
        default=False, description="Cancel immediately vs end of period"
    )
    reason: Optional[str] = Field(None, description="Cancellation reason")


class BillingCycleRequest(BaseModel):
    billing_cycle: str = Field(..., description="monthly or annual")


class FeaturingContentRequest(BaseModel):
    custom_bio: Optional[str] = Field(
        None, max_length=500, description="Custom bio for featuring"
    )
    achievement_highlight: Optional[str] = Field(
        None, max_length=200, description="Achievement to highlight"
    )
    cta_text: Optional[str] = Field(
        None, max_length=100, description="Call-to-action text"
    )


# ═══════════════════════════════════════════════════════════════════════════════════
# SUBSCRIPTION TIER ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════════


@router.get("/tiers", response_model=List[Dict])
async def get_subscription_tiers(db: Session = Depends(get_db)):
    """Get all available subscription tiers with pricing"""

    service = SubscriptionService(db)
    tiers = await service.get_available_tiers()

    return tiers


@router.get("/tiers/comparison", response_model=Dict)
async def get_tier_comparison(db: Session = Depends(get_db)):
    """Get tier comparison data optimized for pricing page"""

    service = SubscriptionService(db)
    tiers = await service.get_available_tiers()

    # Add psychology-optimized presentation data
    comparison_data = {
        "tiers": tiers,
        "recommended_tier": "purple",  # Highlight Purple tier
        "popular_tier": "whale",  # Show as "most popular"
        "annual_discount_message": "Save up to 30% with annual billing",
        "purple_spotlight": {
            "tagline": "Get featured on the home screen",
            "benefit": "Maximum visibility in the founder community",
            "social_proof": "Join 247 successful founders already featured",
        },
        "upgrade_incentives": {
            "oracle_to_whale": "Unlock exclusive markets and advanced analytics",
            "whale_to_purple": "Get the ultimate founder visibility and networking",
            "purple_to_kingmaker": "Become a platform co-owner with revenue sharing",
        },
    }

    return comparison_data


# ═══════════════════════════════════════════════════════════════════════════════════
# USER SUBSCRIPTION MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════════


@router.get("/my-subscription", response_model=Dict)
async def get_my_subscription(
    current_user: Dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get current user's subscription details"""

    service = SubscriptionService(db)
    subscription = await service.get_user_subscription(current_user["id"])

    if not subscription:
        return {"subscription": None, "is_subscribed": False}

    return {
        "subscription": subscription,
        "is_subscribed": True,
        "can_upgrade": subscription["tier"]["slug"] not in ["kingmaker"],
        "can_cancel": subscription["status"] == "active",
    }


@router.post("/checkout", response_model=Dict)
async def create_checkout_session(
    request: CheckoutRequest,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create checkout session for new subscription"""

    service = SubscriptionService(db)

    try:
        checkout_data = await service.create_checkout_session(
            user_id=current_user["id"],
            user_email=current_user["email"],
            user_name=current_user["full_name"],
            tier_slug=request.tier_slug,
            billing_cycle=request.billing_cycle,
            trial_days=request.trial_days,
            referral_code=request.referral_code,
        )

        return {
            "success": True,
            "checkout_url": checkout_data["checkout_url"],
            "tier_info": checkout_data["tier"],
            "billing_cycle": checkout_data["billing_cycle"],
            "trial_days": checkout_data["trial_days"],
            "expires_at": checkout_data["expires_at"],
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/upgrade", response_model=Dict)
async def upgrade_subscription(
    request: UpgradeRequest,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upgrade current subscription to higher tier"""

    service = SubscriptionService(db)

    try:
        result = await service.upgrade_subscription(
            user_id=current_user["id"],
            new_tier_slug=request.new_tier_slug,
            billing_cycle=request.billing_cycle,
        )

        # Track upgrade for analytics
        # analytics.track_event(current_user["id"], "subscription_upgraded", {
        #     "new_tier": request.new_tier_slug,
        #     "billing_cycle": request.billing_cycle
        # })

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to upgrade subscription")


@router.post("/cancel", response_model=Dict)
async def cancel_subscription(
    request: CancelRequest,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel current subscription"""

    service = SubscriptionService(db)

    try:
        result = await service.cancel_subscription(
            user_id=current_user["id"],
            immediate=request.immediate,
            reason=request.reason,
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")


@router.post("/reactivate", response_model=Dict)
async def reactivate_subscription(
    current_user: Dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Reactivate a canceled subscription"""

    service = SubscriptionService(db)

    try:
        result = await service.reactivate_subscription(current_user["id"])
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to reactivate subscription")


@router.post("/billing-cycle", response_model=Dict)
async def update_billing_cycle(
    request: BillingCycleRequest,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update subscription billing cycle"""

    service = SubscriptionService(db)

    try:
        result = await service.update_billing_cycle(
            user_id=current_user["id"], new_billing_cycle=request.billing_cycle
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update billing cycle")


# ═══════════════════════════════════════════════════════════════════════════════════
# PURPLE TIER FEATURING
# ═══════════════════════════════════════════════════════════════════════════════════


@router.get("/purple-featuring/queue", response_model=Dict)
async def get_featuring_queue(
    current_user: Dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get user's Purple featuring queue and schedule"""

    service = SubscriptionService(db)

    try:
        queue_data = await service.get_purple_featuring_queue(current_user["id"])
        return queue_data

    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get featuring queue")


@router.post("/purple-featuring/{featuring_id}/content", response_model=Dict)
async def update_featuring_content(
    featuring_id: str,
    request: FeaturingContentRequest,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update custom content for scheduled featuring"""

    service = SubscriptionService(db)

    try:
        result = await service.update_featuring_content(
            user_id=current_user["id"],
            featuring_id=featuring_id,
            custom_bio=request.custom_bio,
            achievement_highlight=request.achievement_highlight,
            cta_text=request.cta_text,
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Failed to update featuring content"
        )


@router.get("/purple-featuring/current", response_model=Dict)
async def get_current_featured_founders(db: Session = Depends(get_db)):
    """Get currently featured founders for home screen display"""

    from .featuring import PurpleFeaturingService

    featuring_service = PurpleFeaturingService(db)
    featured_data = await featuring_service.get_current_featured_founders()

    return featured_data


@router.post("/purple-featuring/{featuring_id}/track", response_model=Dict)
async def track_featuring_interaction(
    featuring_id: str,
    interaction_type: str,  # view, click, profile, connect
    db: Session = Depends(get_db),
):
    """Track interaction with featuring (for analytics)"""

    from .featuring import PurpleFeaturingService

    featuring_service = PurpleFeaturingService(db)

    try:
        await featuring_service.track_featuring_impression(
            featuring_id, interaction_type
        )
        return {"success": True, "tracked": interaction_type}

    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════════
# ANALYTICS & REPORTING
# ═══════════════════════════════════════════════════════════════════════════════════


@router.get("/analytics", response_model=Dict)
async def get_subscription_analytics(
    days: int = 30,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get subscription and featuring analytics"""

    service = SubscriptionService(db)
    analytics = await service.get_subscription_analytics(current_user["id"], days)

    return analytics


@router.get("/admin/metrics", response_model=Dict)
async def get_platform_metrics(
    admin_user: Dict = Depends(get_admin_user), db: Session = Depends(get_db)
):
    """Get platform-wide subscription metrics (admin only)"""

    service = SubscriptionService(db)
    metrics = await service.get_subscription_metrics(admin_user["id"])

    return metrics


# ═══════════════════════════════════════════════════════════════════════════════════
# WEBHOOK ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════════


@router.post("/webhooks/lemonsqueezy")
async def lemonsqueezy_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle LemonSqueezy webhook events"""

    # Get raw body and signature
    body = await request.body()
    signature = request.headers.get("X-Signature")

    if not signature:
        raise HTTPException(status_code=401, detail="Missing signature")

    # Initialize client and verify signature
    client = LemonSqueezyClient()

    if not client.verify_webhook_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse webhook data
    try:
        webhook_data = await request.json()
        event_type = webhook_data.get("meta", {}).get("event_name")

        if not event_type:
            raise HTTPException(status_code=400, detail="Missing event type")

        # Process webhook
        await client.handle_webhook(event_type, webhook_data, db)

        return {"success": True, "processed": event_type}

    except Exception as e:
        print(f"Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


# ═══════════════════════════════════════════════════════════════════════════════════
# UTILITY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════════


@router.get("/features/{tier_slug}", response_model=Dict)
async def get_tier_features(tier_slug: str, db: Session = Depends(get_db)):
    """Get detailed features for a specific tier"""

    service = SubscriptionService(db)
    tiers = await service.get_available_tiers()

    tier_data = None
    for tier in tiers:
        if tier["slug"] == tier_slug:
            tier_data = tier
            break

    if not tier_data:
        raise HTTPException(status_code=404, detail="Tier not found")

    # Add detailed feature descriptions
    feature_descriptions = {
        "basic_markets": "Access to standard prediction markets",
        "advanced_analytics": "Detailed portfolio and performance analytics",
        "exclusive_markets": "Access to high-stakes founder-only markets",
        "home_featuring": "Featured placement on home screen for maximum visibility",
        "priority_discovery": "Priority placement in market and founder discovery",
        "verified_badge": "Verified founder badge on profile",
        "api_access": "API access for custom integrations",
        "concierge_support": "Dedicated account manager and priority support",
        "market_creation": "Tools to create your own prediction markets",
        "revenue_sharing": "Earn revenue from markets you create",
        "networking_tools": "Advanced networking and connection tools",
    }

    detailed_features = []
    for feature in tier_data["features"]:
        detailed_features.append(
            {
                "name": feature,
                "description": feature_descriptions.get(
                    feature, "Premium platform feature"
                ),
                "included": True,
            }
        )

    return {
        "tier": tier_data,
        "detailed_features": detailed_features,
        "use_cases": {
            "oracle": [
                "Professional market participation",
                "Advanced analytics",
                "Verified status",
            ],
            "whale": [
                "Exclusive high-stakes markets",
                "Market creation",
                "Priority support",
            ],
            "purple": [
                "Maximum founder visibility",
                "Home screen featuring",
                "Premium networking",
            ],
            "kingmaker": [
                "Platform co-ownership",
                "Revenue generation",
                "Market making",
            ],
        }.get(tier_slug, []),
    }


@router.get("/referral/{referral_code}", response_model=Dict)
async def validate_referral_code(referral_code: str, db: Session = Depends(get_db)):
    """Validate referral code and get referrer info"""

    # This would integrate with referral system
    # For now, return mock validation

    return {
        "valid": True,
        "referrer": {
            "name": "Sarah K.",
            "title": "Oracle member",
            "discount": "First month free",
        },
        "discount": {"type": "percentage", "value": 100, "duration": "first_month"},
    }
