# 💜 Purple Tier Strategy: Premium Home Screen Featuring
*Psychology-optimized subscription model for maximum revenue and status addiction*

## 🎯 Strategic Overview

**Purple Tier** is our ultra-premium subscription designed to exploit founder psychology around status, visibility, and network effects. By offering home screen featuring, we create an irresistible status symbol that founders will pay premium prices to access.

### 🧠 Psychology Behind Purple Tier

**Status Signal Addiction**: Successful founders are inherently status-conscious - they've built companies specifically to be recognized as "successful entrepreneurs." Home screen featuring feeds directly into this psychological need.

**Network Effects Amplification**: Being featured on the home screen creates a virtuous cycle:
1. **Visibility** → More connections and deal flow
2. **Credibility** → Higher-quality networking opportunities  
3. **FOMO** → Other founders want the same visibility
4. **Exclusivity** → Limited spots make it more desirable

**Price Anchoring**: At $999/month, Purple positions our other tiers as "affordable" while capturing maximum value from high-earners.

---

## 💰 Subscription Tier Architecture

### Complete Tier Structure (Optimized for Psychology)

```typescript
const SUBSCRIPTION_TIERS = {
  founder: {
    name: "Founder",
    price: 0,
    billing: "free",
    maxPosition: 1000,
    features: [
      "Basic prediction markets",
      "Standard market discovery", 
      "Community access",
      "Mobile app"
    ],
    psychology: "Gateway drug - get them addicted to platform"
  },
  
  oracle: {
    name: "Oracle", 
    price: 99,
    billing: "monthly", 
    annualDiscount: 20,
    maxPosition: 10000,
    features: [
      "All prediction markets",
      "Advanced analytics dashboard",
      "Priority market discovery",
      "Verified founder badge",
      "Email support"
    ],
    psychology: "Professional tier - feels legitimate and affordable"
  },
  
  whale: {
    name: "Whale",
    price: 299, 
    billing: "monthly",
    annualDiscount: 25,
    maxPosition: 100000,
    features: [
      "Everything in Oracle",
      "Exclusive whale-only markets", 
      "Market creation tools",
      "Advanced portfolio analytics",
      "Priority customer support",
      "API access (limited)"
    ],
    psychology: "Serious player tier - separates hobbyists from pros"
  },
  
  purple: {
    name: "Purple", 
    price: 999,
    billing: "monthly",
    annualDiscount: 30,
    maxPosition: 1000000,
    features: [
      "Everything in Whale",
      "🏠 HOME SCREEN FEATURING", // The key differentiator
      "Purple founder badge with custom bio",
      "Featured in founder spotlight rotation",
      "Priority placement in all discovery",
      "Exclusive Purple-only markets ($10K+ predictions)",
      "Advanced networking: direct Purple member directory",
      "Concierge onboarding and account management", 
      "Custom integrations and API access",
      "Early access to new features",
      "Quarterly exclusive Purple events (virtual/in-person)"
    ],
    psychology: "Ultimate status symbol - for founders who've 'made it'"
  },
  
  kingmaker: {
    name: "Kingmaker",
    price: 2999,
    billing: "monthly", 
    annualDiscount: 35,
    maxPosition: "unlimited",
    features: [
      "Everything in Purple",
      "Market maker privileges",
      "Revenue sharing on markets you create",
      "White-label platform access",
      "Direct influence on platform direction",
      "Investment opportunity deal flow",
      "Personal relationship manager"
    ],
    psychology: "Platform co-owner feeling - ultimate insider status"
  }
}
```

### 🎯 Purple Tier Positioning Strategy

**"The Founder's Spotlight"**
- **Tagline**: *"Your success deserves the spotlight"*
- **Value Prop**: *"Get discovered by the right investors, partners, and customers"*
- **Social Proof**: *"Join 247 successful founders already featured"*
- **Urgency**: *"Limited to 500 Purple members globally"*

---

## 🏠 Home Screen Featuring System

### Featured Founder Showcase Architecture

```typescript
interface PurpleFeaturing {
  // Rotation system for fairness and engagement
  rotationSchedule: {
    heroSpot: "24-hour rotations among Purple members",
    featuredGrid: "12 founders displayed simultaneously", 
    rotationAlgorithm: "Weighted by subscription length + engagement"
  },
  
  // Featuring formats
  showcaseFormats: {
    heroCarousel: {
      position: "Top of home screen",
      duration: "24 hours per founder",
      content: "Photo + bio + recent big win + CTA button"
    },
    
    featuredGrid: {
      position: "Featured Founders section", 
      count: "12 concurrent spots",
      content: "Profile photo + name + company + achievement"
    },
    
    successStories: {
      position: "Sidebar featured content",
      format: "Recent Purple member wins and achievements",
      frequency: "Updated daily"
    }
  },
  
  // Content optimization
  contentStrategy: {
    profileOptimization: "Professional photography + copywriter support",
    achievementHighlighting: "Recent funding, exits, major milestones", 
    callToAction: "Connect, Follow, or View Portfolio buttons",
    socialProof: "Verified founder badge + Purple member status"
  }
}
```

### Featuring Analytics & Optimization

```typescript
const FEATURING_ANALYTICS = {
  visibilityMetrics: [
    "Home screen impressions",
    "Profile clicks from featuring", 
    "Connection requests received",
    "Market participation increase",
    "Deal flow opportunities generated"
  ],
  
  optimizationFactors: [
    "Time of day for maximum founder traffic",
    "Most effective bio/achievement combinations",
    "Optimal rotation frequency",
    "Cross-promotion with other Purple members"
  ],
  
  roiTracking: [
    "Networking connections made",
    "Business opportunities generated", 
    "Investment meetings booked",
    "Revenue attributed to featuring"
  ]
}
```

---

## 💳 Cost-Optimized Payment Processing

### Payment Provider Strategy

#### **Primary: LemonSqueezy (Recommended)**
```typescript
const LEMONSQUEEZY_CONFIG = {
  advantages: [
    "5% flat rate (no per-transaction fees)", 
    "Handles global taxes/VAT automatically",
    "Merchant of record (reduces compliance burden)",
    "Excellent for SaaS subscriptions", 
    "Built-in dunning management",
    "Crypto payment support"
  ],
  
  costAnalysis: {
    purple999Monthly: "5% = $49.95 per subscription",
    whale299Monthly: "5% = $14.95 per subscription", 
    oracle99Monthly: "5% = $4.95 per subscription"
  },
  
  implementation: {
    webhooks: "Real-time subscription status updates",
    api: "Full subscription management API",
    embeddedCheckout: "Seamless payment experience",
    analytics: "Revenue reporting and churn analytics"
  }
}
```

#### **Alternative: Stripe (For Comparison)**
```typescript
const STRIPE_COMPARISON = {
  fees: "2.9% + $0.30 per transaction",
  
  costAnalysis: {
    purple999Monthly: "$29.27 per subscription (better than LS)",
    whale299Monthly: "$9.00 per subscription (better than LS)",
    oracle99Monthly: "$3.17 per subscription (better than LS)"
  },
  
  advantages: [
    "Lower fees for higher-value subscriptions",
    "More advanced features and integrations",
    "Better fraud protection", 
    "More payment methods"
  ],
  
  disadvantages: [
    "Manual tax/VAT handling",
    "More complex compliance",
    "No built-in merchant of record"
  ]
}
```

#### **Crypto Payments (Premium Option)**
```typescript
const CRYPTO_STRATEGY = {
  providers: ["Coinbase Commerce", "BitPay", "Paddle + Crypto"],
  
  advantages: [
    "~1% processing fees (vs 3-5% traditional)",
    "Appeal to tech-savvy founder demographic",
    "International payment simplification",
    "No chargeback risk"
  ],
  
  implementation: {
    acceptedTokens: ["BTC", "ETH", "USDC", "USDT"],
    annualDiscounts: "Additional 10% discount for crypto payments",
    targetSegment: "Tech founders and international users"
  }
}
```

### **Recommended Multi-Provider Strategy**

```typescript
const PAYMENT_ARCHITECTURE = {
  primary: "LemonSqueezy for all tiers (simplicity + global compliance)",
  alternative: "Stripe for enterprise customers wanting invoicing",
  premium: "Crypto payments for 20%+ additional discount",
  
  costOptimization: [
    "Annual billing default (reduces transaction volume)",
    "Volume discounts negotiation at $100K+ monthly volume",
    "Corporate/team plans for bulk subscriptions",
    "Referral credits to reduce churn and processing costs"
  ]
}
```

---

## 🏗️ Technical Implementation

### Database Schema for Subscription Management

```sql
-- Subscription tiers and pricing
CREATE TABLE subscription_tiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    slug VARCHAR(50) UNIQUE NOT NULL,
    price_monthly INTEGER NOT NULL, -- in cents
    price_annual INTEGER, -- in cents (with discount)
    max_position_size INTEGER,
    features JSONB NOT NULL,
    psychology_notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- User subscriptions
CREATE TABLE user_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    tier_id UUID NOT NULL REFERENCES subscription_tiers(id),
    
    -- Subscription details
    status VARCHAR(20) NOT NULL CHECK (status IN ('active', 'canceled', 'past_due', 'paused')),
    billing_cycle VARCHAR(10) NOT NULL CHECK (billing_cycle IN ('monthly', 'annual')),
    current_period_start TIMESTAMP NOT NULL,
    current_period_end TIMESTAMP NOT NULL,
    
    -- Payment processing
    payment_provider VARCHAR(50) NOT NULL, -- 'lemonsqueezy', 'stripe', 'crypto'
    external_subscription_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- Purple tier specific
    home_featuring_enabled BOOLEAN DEFAULT FALSE,
    featuring_weight INTEGER DEFAULT 1, -- For rotation algorithm
    last_featured_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Purple tier featuring schedule
CREATE TABLE purple_featuring_schedule (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    featuring_type VARCHAR(20) NOT NULL CHECK (featuring_type IN ('hero', 'grid', 'story')),
    scheduled_start TIMESTAMP NOT NULL,
    scheduled_end TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'active', 'completed')),
    
    -- Content for featuring
    custom_bio TEXT,
    achievement_highlight TEXT,
    cta_text VARCHAR(100),
    
    -- Analytics
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    connections_generated INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Featuring analytics
CREATE TABLE featuring_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    date DATE NOT NULL,
    
    -- Visibility metrics
    home_impressions INTEGER DEFAULT 0,
    profile_clicks INTEGER DEFAULT 0,
    connection_requests INTEGER DEFAULT 0,
    
    -- Engagement metrics  
    markets_participated INTEGER DEFAULT 0,
    new_followers INTEGER DEFAULT 0,
    messages_received INTEGER DEFAULT 0,
    
    -- Business metrics
    opportunities_generated INTEGER DEFAULT 0,
    meetings_booked INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, date)
);
```

### Subscription Management API

```python
# src/api/subscriptions/models.py
from enum import Enum
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from src.api.database import Base

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    CANCELED = "canceled" 
    PAST_DUE = "past_due"
    PAUSED = "paused"

class BillingCycle(str, Enum):
    MONTHLY = "monthly"
    ANNUAL = "annual"

class SubscriptionTier(Base):
    __tablename__ = "subscription_tiers"
    
    id = Column(UUID, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    slug = Column(String(50), unique=True, nullable=False) 
    price_monthly = Column(Integer, nullable=False)  # cents
    price_annual = Column(Integer)  # cents with discount
    max_position_size = Column(Integer)
    features = Column(JSONB, nullable=False)
    psychology_notes = Column(Text)
    
    subscriptions = relationship("UserSubscription", back_populates="tier")

class UserSubscription(Base):
    __tablename__ = "user_subscriptions"
    
    id = Column(UUID, primary_key=True)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    tier_id = Column(UUID, ForeignKey("subscription_tiers.id"), nullable=False)
    
    status = Column(String(20), nullable=False)
    billing_cycle = Column(String(10), nullable=False)
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    
    payment_provider = Column(String(50), nullable=False)
    external_subscription_id = Column(String(255), unique=True, nullable=False)
    
    # Purple tier features
    home_featuring_enabled = Column(Boolean, default=False)
    featuring_weight = Column(Integer, default=1)
    last_featured_at = Column(DateTime)
    
    user = relationship("User", back_populates="subscription")
    tier = relationship("SubscriptionTier", back_populates="subscriptions")
```

### LemonSqueezy Integration

```python
# src/api/subscriptions/lemonsqueezy.py
import httpx
from datetime import datetime, timedelta
from typing import Optional
from src.api.config import settings

class LemonSqueezyClient:
    def __init__(self):
        self.api_key = settings.LEMONSQUEEZY_API_KEY
        self.store_id = settings.LEMONSQUEEZY_STORE_ID
        self.base_url = "https://api.lemonsqueezy.com/v1"
        
    async def create_checkout_url(
        self,
        user_id: str,
        tier_slug: str,
        billing_cycle: str = "monthly"
    ) -> str:
        """Create checkout URL for subscription"""
        
        # Map our tiers to LemonSqueezy product variants
        variant_mapping = {
            "oracle_monthly": "oracle-monthly-variant-id",
            "oracle_annual": "oracle-annual-variant-id", 
            "whale_monthly": "whale-monthly-variant-id",
            "whale_annual": "whale-annual-variant-id",
            "purple_monthly": "purple-monthly-variant-id", 
            "purple_annual": "purple-annual-variant-id",
            "kingmaker_monthly": "kingmaker-monthly-variant-id",
            "kingmaker_annual": "kingmaker-annual-variant-id"
        }
        
        variant_key = f"{tier_slug}_{billing_cycle}"
        variant_id = variant_mapping.get(variant_key)
        
        if not variant_id:
            raise ValueError(f"Unknown tier/billing combination: {variant_key}")
        
        checkout_data = {
            "data": {
                "type": "checkouts",
                "attributes": {
                    "checkout_data": {
                        "custom": {
                            "user_id": user_id,
                            "tier_slug": tier_slug,
                            "billing_cycle": billing_cycle
                        }
                    }
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
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/checkouts",
                json=checkout_data,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/vnd.api+json"
                }
            )
            
        if response.status_code != 201:
            raise Exception(f"Failed to create checkout: {response.text}")
            
        checkout = response.json()
        return checkout["data"]["attributes"]["url"]
    
    async def handle_webhook(self, event_type: str, event_data: dict):
        """Handle LemonSqueezy webhook events"""
        
        if event_type == "subscription_created":
            await self._handle_subscription_created(event_data)
        elif event_type == "subscription_updated": 
            await self._handle_subscription_updated(event_data)
        elif event_type == "subscription_cancelled":
            await self._handle_subscription_cancelled(event_data)
        elif event_type == "subscription_payment_success":
            await self._handle_payment_success(event_data)
        elif event_type == "subscription_payment_failed":
            await self._handle_payment_failed(event_data)
    
    async def _handle_subscription_created(self, event_data: dict):
        """Process new subscription creation"""
        subscription_data = event_data["data"]["attributes"]
        custom_data = subscription_data.get("custom_data", {})
        
        # Extract our custom data
        user_id = custom_data.get("user_id")
        tier_slug = custom_data.get("tier_slug")
        
        if not user_id or not tier_slug:
            raise ValueError("Missing required custom data in subscription webhook")
        
        # Create subscription record in our database
        # This would integrate with our subscription service
        await self._create_user_subscription(
            user_id=user_id,
            tier_slug=tier_slug,
            external_id=subscription_data["id"],
            status="active",
            billing_cycle=custom_data.get("billing_cycle", "monthly")
        )
        
        # Enable Purple featuring if applicable
        if tier_slug in ["purple", "kingmaker"]:
            await self._enable_purple_featuring(user_id)
```

### Purple Featuring System

```python
# src/api/subscriptions/featuring.py
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from src.api.subscriptions.models import UserSubscription, PurpleFeaturingSchedule

class PurpleFeaturingService:
    """Manages home screen featuring for Purple tier members"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def schedule_featuring_rotation(self, days_ahead: int = 30):
        """Generate featuring schedule for Purple members"""
        
        # Get all active Purple+ members
        purple_members = self.db.query(UserSubscription).filter(
            UserSubscription.tier_id.in_(
                self.db.query(SubscriptionTier.id).filter(
                    SubscriptionTier.slug.in_(["purple", "kingmaker"])
                )
            ),
            UserSubscription.status == "active",
            UserSubscription.home_featuring_enabled == True
        ).all()
        
        if not purple_members:
            return []
        
        # Calculate rotation schedule
        start_date = datetime.now().replace(hour=0, minute=0, second=0)
        schedule = []
        
        # Hero carousel (24-hour rotations)
        hero_slots = days_ahead  # One hero per day
        for day in range(hero_slots):
            slot_start = start_date + timedelta(days=day)
            slot_end = slot_start + timedelta(days=1)
            
            # Weighted selection based on subscription length and engagement
            selected_member = self._select_weighted_member(purple_members, "hero")
            
            schedule.append(PurpleFeaturingSchedule(
                user_id=selected_member.user_id,
                featuring_type="hero",
                scheduled_start=slot_start,
                scheduled_end=slot_end,
                status="scheduled"
            ))
        
        # Featured grid (12 concurrent spots, weekly rotation)
        grid_slots = days_ahead // 7  # Weekly rotations
        for week in range(grid_slots):
            week_start = start_date + timedelta(weeks=week)
            week_end = week_start + timedelta(weeks=1)
            
            # Select 12 different members for the grid
            grid_members = self._select_grid_members(purple_members, 12)
            
            for member in grid_members:
                schedule.append(PurpleFeaturingSchedule(
                    user_id=member.user_id,
                    featuring_type="grid", 
                    scheduled_start=week_start,
                    scheduled_end=week_end,
                    status="scheduled"
                ))
        
        # Bulk insert schedule
        self.db.bulk_save_objects(schedule)
        self.db.commit()
        
        return schedule
    
    def _select_weighted_member(self, members: List[UserSubscription], featuring_type: str) -> UserSubscription:
        """Select member using weighted algorithm"""
        import random
        
        # Calculate weights based on:
        # 1. Subscription length (longer = higher weight)
        # 2. Last featured date (longer ago = higher weight) 
        # 3. Engagement score (more active = higher weight)
        # 4. Tier level (Kingmaker > Purple)
        
        weights = []
        for member in members:
            weight = 1.0
            
            # Subscription length bonus (max 2x)
            days_subscribed = (datetime.now() - member.created_at).days
            weight += min(days_subscribed / 365.0, 1.0)
            
            # Recency bonus (max 2x)
            if member.last_featured_at:
                days_since_featured = (datetime.now() - member.last_featured_at).days
                weight += min(days_since_featured / 30.0, 1.0)
            else:
                weight += 1.0  # Never featured gets bonus
            
            # Tier bonus
            if member.tier.slug == "kingmaker":
                weight *= 1.5
            
            weights.append(weight)
        
        # Weighted random selection
        selected = random.choices(members, weights=weights, k=1)[0]
        return selected
    
    async def get_current_featured_founders(self) -> dict:
        """Get currently featured founders for home screen display"""
        now = datetime.now()
        
        # Get hero founder
        hero = self.db.query(PurpleFeaturingSchedule).filter(
            PurpleFeaturingSchedule.featuring_type == "hero",
            PurpleFeaturingSchedule.scheduled_start <= now,
            PurpleFeaturingSchedule.scheduled_end > now,
            PurpleFeaturingSchedule.status == "active"
        ).first()
        
        # Get grid founders
        grid = self.db.query(PurpleFeaturingSchedule).filter(
            PurpleFeaturingSchedule.featuring_type == "grid",
            PurpleFeaturingSchedule.scheduled_start <= now,
            PurpleFeaturingSchedule.scheduled_end > now,
            PurpleFeaturingSchedule.status == "active"
        ).all()
        
        return {
            "hero": await self._format_featured_founder(hero) if hero else None,
            "grid": [await self._format_featured_founder(f) for f in grid],
            "updated_at": now.isoformat()
        }
    
    async def _format_featured_founder(self, featuring: PurpleFeaturingSchedule) -> dict:
        """Format founder data for featuring display"""
        user = featuring.user  # Assuming relationship is loaded
        
        return {
            "user_id": str(user.id),
            "name": user.full_name,
            "title": user.title,
            "company": user.company,
            "bio": featuring.custom_bio or user.bio,
            "achievement": featuring.achievement_highlight,
            "avatar_url": user.avatar_url,
            "profile_url": f"/founders/{user.username}",
            "badges": ["purple", "verified"],
            "cta": featuring.cta_text or "Connect",
            "featuring_type": featuring.featuring_type,
            "metrics": {
                "successful_predictions": user.successful_predictions_count,
                "portfolio_value": user.portfolio_value,
                "networks_connections": user.connections_count
            }
        }
```

---

## 📊 Revenue Impact & Projections

### Purple Tier Revenue Model

```typescript
const PURPLE_TIER_PROJECTIONS = {
  pricing: {
    monthly: 999, // $999/month
    annual: 8390,  // $839/month (30% discount)
    lifetime: 19999 // One-time payment option
  },
  
  targetAdoption: {
    month3: "50 Purple subscribers",
    month6: "150 Purple subscribers", 
    month12: "400 Purple subscribers",
    month24: "800 Purple subscribers"
  },
  
  revenueProjections: {
    month12: {
      purpleSubscribers: 400,
      monthlyRevenue: "$299,600", // 400 * $749 avg (factoring annual discounts)
      annualRevenue: "$3.6M from Purple tier alone"
    },
    
    month24: {
      purpleSubscribers: 800,
      monthlyRevenue: "$599,200",
      annualRevenue: "$7.2M from Purple tier alone"
    }
  },
  
  // Combined tier revenue
  totalSubscriptionRevenue: {
    month12: "$12M annual recurring revenue",
    month24: "$28M annual recurring revenue"
  }
}
```

### Cost-Benefit Analysis

```typescript
const COST_ANALYSIS = {
  paymentProcessing: {
    lemonSqueezy: "5% = $50/month per Purple subscriber",
    annualSavings: "Members prefer annual billing (30% more profitable)"
  },
  
  featuringCosts: {
    developmentTime: "80 hours initial build", 
    ongoingMaintenance: "10 hours/month",
    contentModeration: "5 hours/week",
    customerSuccess: "Dedicated Purple member manager"
  },
  
  roi: {
    grossMargin: "90%+ after payment processing",
    paybackPeriod: "2 months average",
    ltv: "$12,000+ per Purple subscriber"
  }
}
```

---

## 🚀 Implementation Timeline

### Phase 1: Foundation (Weeks 1-2)
- [ ] Database schema implementation
- [ ] LemonSqueezy integration and webhook handling
- [ ] Basic subscription management API
- [ ] Tier feature flagging system

### Phase 2: Purple Features (Weeks 3-4) 
- [ ] Home screen featuring system
- [ ] Purple member directory
- [ ] Enhanced analytics dashboard
- [ ] Exclusive Purple markets

### Phase 3: Psychology Optimization (Weeks 5-6)
- [ ] A/B testing framework for pricing
- [ ] Featuring rotation algorithm optimization
- [ ] Social proof and FOMO mechanics
- [ ] Referral program for Purple members

### Phase 4: Scale & Optimize (Weeks 7-8)
- [ ] Payment processing optimization
- [ ] International tax handling
- [ ] Corporate/team subscription options
- [ ] Advanced featuring analytics

---

## 🎯 Success Metrics

### Primary KPIs
- **Purple Tier Adoption**: Target 400 subscribers by month 12
- **Revenue per Purple User**: Target $10,000 annual LTV
- **Feature Engagement**: 80%+ of Purple members actively use featuring
- **Retention**: 95%+ Purple member retention (vs 85% other tiers)

### Psychology Metrics
- **Upgrade Conversion**: 25% of Whale members upgrade to Purple within 6 months
- **Social Proof Impact**: 40% of new signups mention seeing featured founders
- **Network Effects**: Purple members generate 300%+ more connections than other tiers
- **Status Satisfaction**: 90%+ Purple member satisfaction with featuring benefits

The Purple Tier creates an irresistible status symbol that transforms our platform into a premium networking and visibility engine for successful founders. 💜
