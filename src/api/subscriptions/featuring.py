"""
Purple Tier Home Screen Featuring System
Manages the rotation and display of Purple tier members on the home screen
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from .models import (
    FeaturingAnalytics,
    FeaturingStatus,
    FeaturingType,
    PurpleFeaturingSchedule,
    SubscriptionTier,
    UserSubscription,
)


class PurpleFeaturingService:
    """Service for managing Purple tier home screen featuring"""

    def __init__(self, db: Session):
        self.db = db

        # Featuring configuration
        self.config = {
            "hero_slots_per_day": 1,  # One hero per day
            "grid_slots_concurrent": 12,  # 12 founders in grid simultaneously
            "grid_rotation_days": 7,  # Weekly grid rotation
            "story_slots_per_week": 5,  # 5 success stories per week
            # Algorithm weights
            "subscription_length_weight": 0.3,
            "last_featured_weight": 0.4,
            "engagement_weight": 0.2,
            "tier_bonus_weight": 0.1,
            # Featuring limits
            "max_hero_per_month": 4,  # Prevent overexposure
            "min_days_between_hero": 7,
            "max_grid_per_month": 8,
        }

    async def schedule_featuring_rotation(
        self, days_ahead: int = 30
    ) -> List[PurpleFeaturingSchedule]:
        """Generate optimal featuring schedule for Purple members"""

        # Get eligible Purple+ members
        purple_members = self._get_eligible_purple_members()

        if not purple_members:
            return []

        schedule = []
        start_date = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Schedule hero rotations (24-hour slots)
        hero_schedule = await self._schedule_hero_rotations(
            purple_members, start_date, days_ahead
        )
        schedule.extend(hero_schedule)

        # Schedule grid rotations (weekly slots)
        grid_schedule = await self._schedule_grid_rotations(
            purple_members, start_date, days_ahead
        )
        schedule.extend(grid_schedule)

        # Schedule success stories (weekly featured content)
        story_schedule = await self._schedule_success_stories(
            purple_members, start_date, days_ahead
        )
        schedule.extend(story_schedule)

        # Bulk insert all schedules
        self.db.bulk_save_objects(schedule)
        self.db.commit()

        return schedule

    async def _schedule_hero_rotations(
        self, members: List[UserSubscription], start_date: datetime, days: int
    ) -> List[PurpleFeaturingSchedule]:
        """Schedule hero carousel rotations"""

        schedule = []

        for day in range(days):
            slot_start = start_date + timedelta(days=day)
            slot_end = slot_start + timedelta(days=1)

            # Select member using weighted algorithm
            selected_member = self._select_weighted_member(
                members, FeaturingType.HERO, slot_start
            )

            if selected_member:
                featuring = PurpleFeaturingSchedule(
                    user_id=selected_member.user_id,
                    subscription_id=selected_member.id,
                    featuring_type=FeaturingType.HERO,
                    scheduled_start=slot_start,
                    scheduled_end=slot_end,
                    status=FeaturingStatus.SCHEDULED,
                    algorithm_weight=self._calculate_member_weight(
                        selected_member, FeaturingType.HERO
                    ),
                )
                schedule.append(featuring)

                # Update member's last featured time for future calculations
                selected_member.last_featured_at = slot_start

        return schedule

    async def _schedule_grid_rotations(
        self, members: List[UserSubscription], start_date: datetime, days: int
    ) -> List[PurpleFeaturingSchedule]:
        """Schedule featured grid rotations"""

        schedule = []
        weeks = days // 7

        for week in range(weeks):
            week_start = start_date + timedelta(weeks=week)
            week_end = week_start + timedelta(weeks=1)

            # Select 12 different members for the grid
            grid_members = self._select_grid_members(
                members, self.config["grid_slots_concurrent"]
            )

            for i, member in enumerate(grid_members):
                featuring = PurpleFeaturingSchedule(
                    user_id=member.user_id,
                    subscription_id=member.id,
                    featuring_type=FeaturingType.GRID,
                    scheduled_start=week_start,
                    scheduled_end=week_end,
                    status=FeaturingStatus.SCHEDULED,
                    algorithm_weight=self._calculate_member_weight(
                        member, FeaturingType.GRID
                    ),
                    boost_factor=1 + (i // 4),  # Slight boost for variety
                )
                schedule.append(featuring)

        return schedule

    async def _schedule_success_stories(
        self, members: List[UserSubscription], start_date: datetime, days: int
    ) -> List[PurpleFeaturingSchedule]:
        """Schedule success story features"""

        schedule = []
        weeks = days // 7

        # Get members with notable achievements
        story_candidates = [
            member for member in members if self._has_recent_achievements(member)
        ]

        for week in range(weeks):
            week_start = start_date + timedelta(weeks=week)
            week_end = week_start + timedelta(weeks=1)

            # Select up to 5 members for success stories
            selected_stories = random.sample(
                story_candidates,
                min(self.config["story_slots_per_week"], len(story_candidates)),
            )

            for member in selected_stories:
                featuring = PurpleFeaturingSchedule(
                    user_id=member.user_id,
                    subscription_id=member.id,
                    featuring_type=FeaturingType.STORY,
                    scheduled_start=week_start,
                    scheduled_end=week_end,
                    status=FeaturingStatus.SCHEDULED,
                    achievement_highlight=self._generate_achievement_highlight(member),
                )
                schedule.append(featuring)

        return schedule

    def _get_eligible_purple_members(self) -> List[UserSubscription]:
        """Get active Purple/Kingmaker members eligible for featuring"""

        return (
            self.db.query(UserSubscription)
            .join(SubscriptionTier)
            .filter(
                SubscriptionTier.slug.in_(["purple", "kingmaker"]),
                UserSubscription.status == "active",
                UserSubscription.home_featuring_enabled == True,
                UserSubscription.current_period_end > datetime.utcnow(),
            )
            .all()
        )

    def _select_weighted_member(
        self,
        members: List[UserSubscription],
        featuring_type: FeaturingType,
        target_date: datetime,
    ) -> Optional[UserSubscription]:
        """Select member using weighted algorithm"""

        if not members:
            return None

        # Filter members based on featuring constraints
        eligible_members = []
        for member in members:
            if self._is_member_eligible(member, featuring_type, target_date):
                eligible_members.append(member)

        if not eligible_members:
            return None

        # Calculate weights for each eligible member
        weights = []
        for member in eligible_members:
            weight = self._calculate_member_weight(member, featuring_type)
            weights.append(weight)

        # Weighted random selection
        selected = random.choices(eligible_members, weights=weights, k=1)[0]
        return selected

    def _select_grid_members(
        self, members: List[UserSubscription], count: int
    ) -> List[UserSubscription]:
        """Select diverse set of members for grid featuring"""

        if len(members) <= count:
            return members

        # Ensure diversity by company stage, industry, etc.
        selected = []
        remaining = list(members)

        # First, ensure we have variety in tiers (Kingmaker vs Purple)
        kingmakers = [m for m in remaining if m.tier.slug == "kingmaker"]
        purples = [m for m in remaining if m.tier.slug == "purple"]

        # Aim for 30% Kingmaker, 70% Purple ratio if possible
        kingmaker_slots = min(len(kingmakers), max(1, count // 3))
        purple_slots = count - kingmaker_slots

        # Add Kingmakers first (weighted selection)
        if kingmakers:
            kingmaker_weights = [
                self._calculate_member_weight(m, FeaturingType.GRID) for m in kingmakers
            ]
            selected_kingmakers = random.choices(
                kingmakers, weights=kingmaker_weights, k=kingmaker_slots
            )
            selected.extend(selected_kingmakers)

            # Remove selected from remaining
            for m in selected_kingmakers:
                remaining.remove(m)

        # Add Purples
        if purples and len(selected) < count:
            needed = count - len(selected)
            purple_candidates = [m for m in remaining if m.tier.slug == "purple"]

            if purple_candidates:
                purple_weights = [
                    self._calculate_member_weight(m, FeaturingType.GRID)
                    for m in purple_candidates
                ]
                selected_purples = random.choices(
                    purple_candidates,
                    weights=purple_weights,
                    k=min(needed, len(purple_candidates)),
                )
                selected.extend(selected_purples)

        return selected

    def _calculate_member_weight(
        self, member: UserSubscription, featuring_type: FeaturingType
    ) -> float:
        """Calculate algorithm weight for member selection"""

        weight = 1.0
        config = self.config

        # Subscription length bonus (longer subscription = higher weight)
        days_subscribed = (datetime.utcnow() - member.created_at).days
        subscription_bonus = min(days_subscribed / 365.0, 2.0)  # Max 2x bonus
        weight += subscription_bonus * config["subscription_length_weight"]

        # Recency bonus (longer since last featured = higher weight)
        if member.last_featured_at:
            days_since_featured = (datetime.utcnow() - member.last_featured_at).days
            recency_bonus = min(days_since_featured / 30.0, 3.0)  # Max 3x bonus
        else:
            recency_bonus = 2.0  # Never featured gets good bonus

        weight += recency_bonus * config["last_featured_weight"]

        # Engagement bonus (more active users get priority)
        engagement_score = self._calculate_engagement_score(member)
        weight += engagement_score * config["engagement_weight"]

        # Tier bonus (Kingmaker > Purple)
        if member.tier.slug == "kingmaker":
            weight += 1.5 * config["tier_bonus_weight"]
        elif member.tier.slug == "purple":
            weight += 1.0 * config["tier_bonus_weight"]

        # Featuring type specific adjustments
        if featuring_type == FeaturingType.HERO:
            # Hero needs more engaged, established members
            weight *= 1.2 if engagement_score > 0.7 else 0.8

        return max(weight, 0.1)  # Minimum weight

    def _is_member_eligible(
        self,
        member: UserSubscription,
        featuring_type: FeaturingType,
        target_date: datetime,
    ) -> bool:
        """Check if member is eligible for featuring at target date"""

        # Check if already scheduled around target date
        existing_featuring = (
            self.db.query(PurpleFeaturingSchedule)
            .filter(
                PurpleFeaturingSchedule.user_id == member.user_id,
                PurpleFeaturingSchedule.featuring_type == featuring_type,
                PurpleFeaturingSchedule.scheduled_start
                <= target_date + timedelta(days=1),
                PurpleFeaturingSchedule.scheduled_end
                >= target_date - timedelta(days=1),
                PurpleFeaturingSchedule.status.in_(
                    [FeaturingStatus.SCHEDULED, FeaturingStatus.ACTIVE]
                ),
            )
            .first()
        )

        if existing_featuring:
            return False

        # Check monthly limits
        if featuring_type == FeaturingType.HERO:
            month_start = target_date.replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1)

            monthly_hero_count = (
                self.db.query(PurpleFeaturingSchedule)
                .filter(
                    PurpleFeaturingSchedule.user_id == member.user_id,
                    PurpleFeaturingSchedule.featuring_type == FeaturingType.HERO,
                    PurpleFeaturingSchedule.scheduled_start >= month_start,
                    PurpleFeaturingSchedule.scheduled_start < month_end,
                )
                .count()
            )

            if monthly_hero_count >= self.config["max_hero_per_month"]:
                return False

        # Check minimum days between hero features
        if featuring_type == FeaturingType.HERO and member.last_featured_at:
            days_since_last = (target_date - member.last_featured_at).days
            if days_since_last < self.config["min_days_between_hero"]:
                return False

        return True

    def _calculate_engagement_score(self, member: UserSubscription) -> float:
        """Calculate engagement score for member (0.0 to 1.0)"""

        # Get recent analytics (last 30 days)
        recent_analytics = (
            self.db.query(FeaturingAnalytics)
            .filter(
                FeaturingAnalytics.user_id == member.user_id,
                FeaturingAnalytics.date >= datetime.utcnow() - timedelta(days=30),
            )
            .all()
        )

        if not recent_analytics:
            return 0.5  # Default score for new members

        # Calculate aggregate metrics
        total_predictions = sum(a.predictions_made for a in recent_analytics)
        total_markets = sum(a.markets_participated for a in recent_analytics)
        total_connections = sum(a.connection_requests for a in recent_analytics)
        total_opportunities = sum(a.opportunities_generated for a in recent_analytics)

        # Normalize to 0-1 scale
        engagement_score = min(
            (
                total_predictions * 0.1
                + total_markets * 0.3
                + total_connections * 0.4
                + total_opportunities * 0.2
            )
            / 100.0,
            1.0,
        )

        return engagement_score

    def _has_recent_achievements(self, member: UserSubscription) -> bool:
        """Check if member has recent achievements worth highlighting"""

        # This would integrate with user achievements system
        # For now, return True for members with good engagement
        engagement_score = self._calculate_engagement_score(member)
        return engagement_score > 0.6

    def _generate_achievement_highlight(self, member: UserSubscription) -> str:
        """Generate achievement highlight text for member"""

        # This would integrate with user achievements system
        # For now, generate based on available data
        achievements = []

        if member.tier.slug == "kingmaker":
            achievements.append("Kingmaker tier member")

        # Get recent prediction success rate
        recent_analytics = (
            self.db.query(FeaturingAnalytics)
            .filter(
                FeaturingAnalytics.user_id == member.user_id,
                FeaturingAnalytics.date >= datetime.utcnow() - timedelta(days=30),
            )
            .all()
        )

        if recent_analytics:
            total_predictions = sum(a.predictions_made for a in recent_analytics)
            total_opportunities = sum(
                a.opportunities_generated for a in recent_analytics
            )

            if total_predictions > 20:
                achievements.append(f"Made {total_predictions} successful predictions")

            if total_opportunities > 5:
                achievements.append(
                    f"Generated {total_opportunities} business opportunities"
                )

        return (
            " • ".join(achievements)
            if achievements
            else "Active FundCast community member"
        )

    async def get_current_featured_founders(self) -> Dict:
        """Get currently featured founders for home screen display"""

        now = datetime.utcnow()

        # Get active hero founder
        hero_featuring = (
            self.db.query(PurpleFeaturingSchedule)
            .filter(
                PurpleFeaturingSchedule.featuring_type == FeaturingType.HERO,
                PurpleFeaturingSchedule.scheduled_start <= now,
                PurpleFeaturingSchedule.scheduled_end > now,
                PurpleFeaturingSchedule.status == FeaturingStatus.SCHEDULED,
            )
            .first()
        )

        # Get active grid founders
        grid_featuring = (
            self.db.query(PurpleFeaturingSchedule)
            .filter(
                PurpleFeaturingSchedule.featuring_type == FeaturingType.GRID,
                PurpleFeaturingSchedule.scheduled_start <= now,
                PurpleFeaturingSchedule.scheduled_end > now,
                PurpleFeaturingSchedule.status == FeaturingStatus.SCHEDULED,
            )
            .limit(12)
            .all()
        )

        # Get active success stories
        story_featuring = (
            self.db.query(PurpleFeaturingSchedule)
            .filter(
                PurpleFeaturingSchedule.featuring_type == FeaturingType.STORY,
                PurpleFeaturingSchedule.scheduled_start <= now,
                PurpleFeaturingSchedule.scheduled_end > now,
                PurpleFeaturingSchedule.status == FeaturingStatus.SCHEDULED,
            )
            .limit(5)
            .all()
        )

        # Format for frontend
        featured_data = {
            "hero": (
                await self._format_featured_founder(hero_featuring)
                if hero_featuring
                else None
            ),
            "grid": [await self._format_featured_founder(f) for f in grid_featuring],
            "stories": [
                await self._format_featured_founder(f) for f in story_featuring
            ],
            "updated_at": now.isoformat(),
            "next_rotation": self._get_next_rotation_time(now),
        }

        # Mark as active (for analytics tracking)
        for featuring in [hero_featuring] + grid_featuring + story_featuring:
            if featuring and featuring.status == FeaturingStatus.SCHEDULED:
                featuring.status = FeaturingStatus.ACTIVE

        self.db.commit()

        return featured_data

    async def _format_featured_founder(
        self, featuring: PurpleFeaturingSchedule
    ) -> Dict:
        """Format founder data for frontend display"""

        # This would join with User table in real implementation
        user_data = {
            "user_id": str(featuring.user_id),
            "subscription_id": str(featuring.subscription_id),
            "name": "John Doe",  # From User table
            "title": "CEO & Co-Founder",  # From User table
            "company": "TechCorp Inc.",  # From User table
            "bio": featuring.custom_bio or "Building the future of SaaS",
            "achievement": featuring.achievement_highlight,
            "avatar_url": "/api/avatars/placeholder.jpg",
            "cover_url": "/api/covers/placeholder.jpg",
            "profile_url": f"/founders/{featuring.user_id}",
            # Status and badges
            "badges": [
                (
                    "purple"
                    if featuring.subscription.tier.slug == "purple"
                    else "kingmaker"
                ),
                "verified",
            ],
            "tier": featuring.subscription.tier.name,
            "member_since": featuring.subscription.created_at.isoformat(),
            # CTA
            "cta": featuring.cta_text or "Connect",
            "cta_url": f"/founders/{featuring.user_id}/connect",
            # Featuring metadata
            "featuring_id": str(featuring.id),
            "featuring_type": featuring.featuring_type,
            "featured_until": featuring.scheduled_end.isoformat(),
            # Metrics (if available)
            "metrics": {
                "successful_predictions": 47,  # From user analytics
                "portfolio_value": "$25,000",  # From user portfolio
                "network_connections": 156,  # From user network
                "achievements_count": 8,  # From user achievements
            },
        }

        return user_data

    def _get_next_rotation_time(self, current_time: datetime) -> str:
        """Get next rotation time for frontend countdown"""

        # Next hero rotation (daily at midnight)
        next_hero = (current_time + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Next grid rotation (weekly on Sundays)
        days_ahead = (6 - current_time.weekday()) % 7
        if days_ahead == 0:  # Today is Sunday
            days_ahead = 7
        next_grid = (current_time + timedelta(days=days_ahead)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        return min(next_hero, next_grid).isoformat()

    async def track_featuring_impression(
        self, featuring_id: str, impression_type: str = "view"
    ):
        """Track impression/interaction with featuring"""

        featuring = (
            self.db.query(PurpleFeaturingSchedule)
            .filter(PurpleFeaturingSchedule.id == featuring_id)
            .first()
        )

        if featuring:
            if impression_type == "view":
                featuring.impressions += 1
            elif impression_type == "click":
                featuring.clicks += 1
            elif impression_type == "profile":
                featuring.profile_views += 1
            elif impression_type == "connect":
                featuring.connections_generated += 1

            self.db.commit()

    async def enable_user_featuring(self, user_id: str):
        """Enable featuring for a user (when they upgrade to Purple)"""

        subscription = (
            self.db.query(UserSubscription)
            .filter(
                UserSubscription.user_id == user_id, UserSubscription.status == "active"
            )
            .first()
        )

        if subscription and subscription.tier.slug in ["purple", "kingmaker"]:
            subscription.home_featuring_enabled = True
            subscription.featuring_weight = 1
            self.db.commit()

    async def disable_user_featuring(self, user_id: str):
        """Disable featuring for a user (when they downgrade/cancel)"""

        # Disable future featuring
        subscription = (
            self.db.query(UserSubscription)
            .filter(UserSubscription.user_id == user_id)
            .first()
        )

        if subscription:
            subscription.home_featuring_enabled = False

            # Cancel future scheduled featuring
            future_featuring = (
                self.db.query(PurpleFeaturingSchedule)
                .filter(
                    PurpleFeaturingSchedule.user_id == user_id,
                    PurpleFeaturingSchedule.scheduled_start > datetime.utcnow(),
                    PurpleFeaturingSchedule.status == FeaturingStatus.SCHEDULED,
                )
                .all()
            )

            for featuring in future_featuring:
                featuring.status = FeaturingStatus.CANCELLED

            self.db.commit()
