"""Service Level Objective (SLO) monitoring and error budget tracking."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog

from ..cache import CacheKey, get_cache

logger = structlog.get_logger(__name__)


class SLOType(str, Enum):
    """Types of Service Level Objectives."""

    AVAILABILITY = "availability"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"


class SLOStatus(str, Enum):
    """SLO compliance status."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class SLOTarget:
    """Service Level Objective target definition."""

    name: str
    slo_type: SLOType
    target_percentage: float  # e.g., 99.9 for 99.9%
    window_hours: int = 24  # Time window in hours
    description: str = ""

    # Latency-specific settings
    latency_threshold_ms: Optional[float] = None

    # Error rate settings
    error_codes: List[int] = field(default_factory=lambda: [500, 502, 503, 504])

    # Throughput settings
    min_requests_per_second: Optional[float] = None


@dataclass
class SLOMeasurement:
    """Individual SLO measurement."""

    timestamp: datetime
    value: float
    success: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SLOStatus:
    """Current SLO status and error budget."""

    slo_name: str
    current_percentage: float
    target_percentage: float
    error_budget_remaining: float  # Percentage of budget remaining
    status: SLOStatus
    measurements_count: int
    window_start: datetime
    window_end: datetime
    next_evaluation: datetime
    alerts_fired: int = 0


class ErrorBudget:
    """Error budget calculator and tracker."""

    def __init__(self, target_percentage: float, window_hours: int):
        self.target_percentage = target_percentage
        self.window_hours = window_hours
        self.error_rate_threshold = 100 - target_percentage

    def calculate_budget(self, total_requests: int) -> int:
        """Calculate total error budget for period."""
        return int(total_requests * (self.error_rate_threshold / 100))

    def calculate_remaining(self, total_requests: int, failed_requests: int) -> float:
        """Calculate remaining error budget as percentage."""
        if total_requests == 0:
            return 100.0

        budget = self.calculate_budget(total_requests)
        if budget == 0:
            return 0.0

        used_budget = min(failed_requests, budget)
        remaining = budget - used_budget
        return (remaining / budget) * 100

    def is_exhausted(
        self, total_requests: int, failed_requests: int, threshold: float = 0.0
    ) -> bool:
        """Check if error budget is exhausted."""
        remaining = self.calculate_remaining(total_requests, failed_requests)
        return remaining <= threshold


class SLOCollector:
    """Collects and stores SLO measurements."""

    def __init__(self):
        self.cache_key = CacheKey("slo_measurements")
        self.max_measurements = 10000  # Keep last 10k measurements

    async def record_measurement(
        self,
        slo_name: str,
        value: float,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record a new SLO measurement."""
        measurement = SLOMeasurement(
            timestamp=datetime.now(),
            value=value,
            success=success,
            metadata=metadata or {},
        )

        # Store in cache
        cache = await get_cache()
        measurements_key = self.cache_key.build(slo_name, "measurements")

        # Get existing measurements
        measurements = await cache.get(measurements_key) or []

        # Add new measurement
        measurements.append(
            {
                "timestamp": measurement.timestamp.isoformat(),
                "value": measurement.value,
                "success": measurement.success,
                "metadata": measurement.metadata,
            }
        )

        # Trim to max size
        if len(measurements) > self.max_measurements:
            measurements = measurements[-self.max_measurements :]

        # Store back
        await cache.set(measurements_key, measurements, ttl=86400)  # 24 hours

        logger.debug(
            "SLO measurement recorded", slo_name=slo_name, value=value, success=success
        )

    async def get_measurements(
        self, slo_name: str, start_time: datetime, end_time: datetime
    ) -> List[SLOMeasurement]:
        """Get measurements within time window."""
        cache = await get_cache()
        measurements_key = self.cache_key.build(slo_name, "measurements")

        raw_measurements = await cache.get(measurements_key) or []

        # Filter by time window
        filtered = []
        for raw in raw_measurements:
            timestamp = datetime.fromisoformat(raw["timestamp"])
            if start_time <= timestamp <= end_time:
                filtered.append(
                    SLOMeasurement(
                        timestamp=timestamp,
                        value=raw["value"],
                        success=raw["success"],
                        metadata=raw.get("metadata", {}),
                    )
                )

        return filtered

    async def cleanup_old_measurements(self, older_than_hours: int = 72):
        """Clean up measurements older than specified hours."""
        cutoff = datetime.now() - timedelta(hours=older_than_hours)

        # This would need implementation based on storage backend
        logger.info("SLO measurement cleanup completed", cutoff=cutoff.isoformat())


class SLOEvaluator:
    """Evaluates SLO compliance and error budgets."""

    def __init__(self, collector: SLOCollector):
        self.collector = collector

    async def evaluate_slo(self, target: SLOTarget) -> SLOStatus:
        """Evaluate current SLO status."""
        # Get measurement window
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=target.window_hours)

        measurements = await self.collector.get_measurements(
            target.name, start_time, end_time
        )

        if not measurements:
            return SLOStatus(
                slo_name=target.name,
                current_percentage=0.0,
                target_percentage=target.target_percentage,
                error_budget_remaining=100.0,
                status=SLOStatus.UNKNOWN,
                measurements_count=0,
                window_start=start_time,
                window_end=end_time,
                next_evaluation=end_time + timedelta(minutes=5),
            )

        # Calculate based on SLO type
        if target.slo_type == SLOType.AVAILABILITY:
            current_percentage = self._calculate_availability(measurements)
        elif target.slo_type == SLOType.LATENCY:
            current_percentage = self._calculate_latency_slo(
                measurements, target.latency_threshold_ms
            )
        elif target.slo_type == SLOType.ERROR_RATE:
            current_percentage = self._calculate_error_rate_slo(
                measurements, target.error_codes
            )
        elif target.slo_type == SLOType.THROUGHPUT:
            current_percentage = self._calculate_throughput_slo(
                measurements, target.min_requests_per_second, target.window_hours
            )
        else:
            current_percentage = 0.0

        # Calculate error budget
        error_budget = ErrorBudget(target.target_percentage, target.window_hours)
        total_requests = len(measurements)
        failed_requests = sum(1 for m in measurements if not m.success)
        error_budget_remaining = error_budget.calculate_remaining(
            total_requests, failed_requests
        )

        # Determine status
        if current_percentage >= target.target_percentage:
            status = SLOStatus.HEALTHY
        elif (
            current_percentage >= target.target_percentage * 0.95
        ):  # Within 5% of target
            status = SLOStatus.WARNING
        else:
            status = SLOStatus.CRITICAL

        return SLOStatus(
            slo_name=target.name,
            current_percentage=current_percentage,
            target_percentage=target.target_percentage,
            error_budget_remaining=error_budget_remaining,
            status=status,
            measurements_count=len(measurements),
            window_start=start_time,
            window_end=end_time,
            next_evaluation=end_time + timedelta(minutes=5),
        )

    def _calculate_availability(self, measurements: List[SLOMeasurement]) -> float:
        """Calculate availability percentage."""
        if not measurements:
            return 0.0

        successful = sum(1 for m in measurements if m.success)
        return (successful / len(measurements)) * 100

    def _calculate_latency_slo(
        self, measurements: List[SLOMeasurement], threshold_ms: Optional[float]
    ) -> float:
        """Calculate latency SLO (percentage of requests under threshold)."""
        if not measurements or threshold_ms is None:
            return 0.0

        under_threshold = sum(
            1 for m in measurements if m.success and m.value <= threshold_ms
        )
        return (under_threshold / len(measurements)) * 100

    def _calculate_error_rate_slo(
        self, measurements: List[SLOMeasurement], error_codes: List[int]
    ) -> float:
        """Calculate error rate SLO."""
        if not measurements:
            return 100.0  # No errors if no measurements

        # For error rate, success means NOT an error
        non_errors = sum(1 for m in measurements if m.success)
        return (non_errors / len(measurements)) * 100

    def _calculate_throughput_slo(
        self,
        measurements: List[SLOMeasurement],
        min_rps: Optional[float],
        window_hours: int,
    ) -> float:
        """Calculate throughput SLO."""
        if not measurements or min_rps is None:
            return 0.0

        window_seconds = window_hours * 3600
        actual_rps = len(measurements) / window_seconds

        if actual_rps >= min_rps:
            return 100.0
        else:
            return (actual_rps / min_rps) * 100


class AlertManager:
    """Manages SLO-based alerting."""

    def __init__(self):
        self.alert_cooldown = timedelta(minutes=15)  # Prevent alert spam
        self.last_alerts: Dict[str, datetime] = {}

    async def check_alerts(self, slo_status: SLOStatus) -> List[Dict[str, Any]]:
        """Check if alerts should be fired for SLO status."""
        alerts = []

        # Check if we're in cooldown
        last_alert = self.last_alerts.get(slo_status.slo_name)
        if last_alert and datetime.now() - last_alert < self.alert_cooldown:
            return alerts

        # Critical SLO breach
        if slo_status.status == SLOStatus.CRITICAL:
            alerts.append(
                {
                    "severity": "critical",
                    "title": f"SLO Critical: {slo_status.slo_name}",
                    "description": (
                        f"SLO {slo_status.slo_name} is at {slo_status.current_percentage:.2f}% "
                        f"(target: {slo_status.target_percentage:.2f}%). "
                        f"Error budget remaining: {slo_status.error_budget_remaining:.1f}%"
                    ),
                    "metadata": {
                        "slo_name": slo_status.slo_name,
                        "current_percentage": slo_status.current_percentage,
                        "target_percentage": slo_status.target_percentage,
                        "error_budget_remaining": slo_status.error_budget_remaining,
                    },
                }
            )

        # Error budget exhaustion warning
        elif slo_status.error_budget_remaining <= 10.0:
            alerts.append(
                {
                    "severity": "warning",
                    "title": f"Error Budget Low: {slo_status.slo_name}",
                    "description": (
                        f"Error budget for {slo_status.slo_name} is at "
                        f"{slo_status.error_budget_remaining:.1f}%. "
                        f"Current SLO: {slo_status.current_percentage:.2f}%"
                    ),
                    "metadata": {
                        "slo_name": slo_status.slo_name,
                        "error_budget_remaining": slo_status.error_budget_remaining,
                    },
                }
            )

        # Update last alert time
        if alerts:
            self.last_alerts[slo_status.slo_name] = datetime.now()

        return alerts

    async def send_alert(self, alert: Dict[str, Any]):
        """Send alert notification."""
        # Implementation depends on notification system
        # Could integrate with Slack, PagerDuty, email, etc.

        logger.warning(
            "SLO Alert",
            severity=alert["severity"],
            title=alert["title"],
            description=alert["description"],
            metadata=alert["metadata"],
        )

        # Store alert in cache for dashboard
        cache = await get_cache()
        alert_key = CacheKey("slo_alerts").build("recent")
        recent_alerts = await cache.get(alert_key) or []

        alert["timestamp"] = datetime.now().isoformat()
        recent_alerts.append(alert)

        # Keep last 100 alerts
        if len(recent_alerts) > 100:
            recent_alerts = recent_alerts[-100:]

        await cache.set(alert_key, recent_alerts, ttl=86400)


class SLOManager:
    """Main SLO monitoring and management system."""

    def __init__(self):
        self.targets: Dict[str, SLOTarget] = {}
        self.collector = SLOCollector()
        self.evaluator = SLOEvaluator(self.collector)
        self.alert_manager = AlertManager()
        self.monitoring_task: Optional[asyncio.Task] = None
        self.is_running = False

    def register_slo(self, target: SLOTarget):
        """Register a new SLO target."""
        self.targets[target.name] = target
        logger.info(
            "SLO target registered", name=target.name, type=target.slo_type.value
        )

    async def record_request(
        self,
        slo_name: str,
        success: bool,
        latency_ms: Optional[float] = None,
        status_code: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record a request for SLO measurement."""
        if slo_name not in self.targets:
            return

        target = self.targets[slo_name]

        # Determine value based on SLO type
        if target.slo_type == SLOType.LATENCY and latency_ms is not None:
            value = latency_ms
        elif target.slo_type == SLOType.ERROR_RATE and status_code is not None:
            value = status_code
        else:
            value = 1.0 if success else 0.0

        await self.collector.record_measurement(slo_name, value, success, metadata)

    async def get_slo_status(self, slo_name: str) -> Optional[SLOStatus]:
        """Get current status for an SLO."""
        if slo_name not in self.targets:
            return None

        return await self.evaluator.evaluate_slo(self.targets[slo_name])

    async def get_all_slo_status(self) -> Dict[str, SLOStatus]:
        """Get status for all registered SLOs."""
        status_dict = {}

        for slo_name in self.targets:
            status_dict[slo_name] = await self.get_slo_status(slo_name)

        return status_dict

    async def start_monitoring(self, interval_seconds: int = 60):
        """Start continuous SLO monitoring."""
        if self.is_running:
            return

        self.is_running = True
        self.monitoring_task = asyncio.create_task(
            self._monitoring_loop(interval_seconds)
        )
        logger.info("SLO monitoring started", interval=interval_seconds)

    async def stop_monitoring(self):
        """Stop SLO monitoring."""
        if not self.is_running:
            return

        self.is_running = False

        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("SLO monitoring stopped")

    async def _monitoring_loop(self, interval_seconds: int):
        """Main monitoring loop."""
        while self.is_running:
            try:
                # Evaluate all SLOs
                for slo_name in self.targets:
                    status = await self.get_slo_status(slo_name)
                    if status:
                        # Check for alerts
                        alerts = await self.alert_manager.check_alerts(status)

                        # Send alerts
                        for alert in alerts:
                            await self.alert_manager.send_alert(alert)

                        # Log status
                        logger.debug(
                            "SLO evaluation",
                            slo_name=slo_name,
                            current_percentage=status.current_percentage,
                            target_percentage=status.target_percentage,
                            status=status.status.value,
                            error_budget_remaining=status.error_budget_remaining,
                        )

                await asyncio.sleep(interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("SLO monitoring error", error=str(e), exc_info=True)
                await asyncio.sleep(min(interval_seconds, 60))  # Back off on error


# Global SLO manager instance
_slo_manager: Optional[SLOManager] = None


async def get_slo_manager() -> SLOManager:
    """Get or create SLO manager instance."""
    global _slo_manager
    if _slo_manager is None:
        _slo_manager = SLOManager()
    return _slo_manager


def setup_default_slos():
    """Setup default SLOs for FundCast."""

    async def _setup():
        slo_manager = await get_slo_manager()

        # API Availability SLO
        slo_manager.register_slo(
            SLOTarget(
                name="api_availability",
                slo_type=SLOType.AVAILABILITY,
                target_percentage=99.9,
                window_hours=24,
                description="API should be available 99.9% of the time",
            )
        )

        # API Latency SLO
        slo_manager.register_slo(
            SLOTarget(
                name="api_latency",
                slo_type=SLOType.LATENCY,
                target_percentage=95.0,
                latency_threshold_ms=200.0,
                window_hours=24,
                description="95% of API requests should complete within 200ms",
            )
        )

        # Error Rate SLO
        slo_manager.register_slo(
            SLOTarget(
                name="api_error_rate",
                slo_type=SLOType.ERROR_RATE,
                target_percentage=99.5,  # 0.5% error rate
                window_hours=24,
                error_codes=[500, 502, 503, 504],
                description="Error rate should be less than 0.5%",
            )
        )

        logger.info("Default SLOs configured")

    return asyncio.create_task(_setup())
