"""Advanced monitoring and observability system."""

import asyncio
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

import psutil
import structlog

from ..cache import CacheKey, get_cache
from .circuit_breaker import _registry as circuit_breaker_registry
from .slo_monitoring import get_slo_manager

logger = structlog.get_logger(__name__)


@dataclass
class SystemMetrics:
    """System resource metrics."""

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_available: int
    disk_percent: float
    load_average: List[float]
    network_connections: int
    process_count: int


@dataclass
class ApplicationMetrics:
    """Application-specific metrics."""

    timestamp: datetime
    active_connections: int
    request_rate: float  # requests per second
    error_rate: float  # errors per second
    avg_response_time: float  # milliseconds
    p95_response_time: float
    p99_response_time: float
    cache_hit_rate: float
    database_connections: int
    task_queue_size: int
    memory_usage: int  # bytes


@dataclass
class AlertRule:
    """Alert rule configuration."""

    name: str
    condition: Callable[[Dict[str, Any]], bool]
    severity: str  # critical, warning, info
    message_template: str
    cooldown_minutes: int = 15
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Collects various system and application metrics."""

    def __init__(self):
        self.cache_key = CacheKey("monitoring_metrics")
        self.process = psutil.Process()

    async def collect_system_metrics(self) -> SystemMetrics:
        """Collect system resource metrics."""

        # Run CPU-intensive operations in thread pool
        def get_system_info():
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            load_avg = (
                psutil.getloadavg() if hasattr(psutil, "getloadavg") else [0, 0, 0]
            )
            network_connections = len(psutil.net_connections())
            process_count = len(psutil.pids())

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available": memory.available,
                "disk_percent": disk.percent,
                "load_average": list(load_avg),
                "network_connections": network_connections,
                "process_count": process_count,
            }

        system_info = await asyncio.to_thread(get_system_info)

        return SystemMetrics(timestamp=datetime.now(), **system_info)

    async def collect_application_metrics(self) -> ApplicationMetrics:
        """Collect application-specific metrics."""
        cache = await get_cache()

        # Get cached metrics
        metrics_key = self.cache_key.build("app_metrics", "recent")
        recent_metrics = await cache.get(metrics_key) or {}

        # Calculate rates from recent data
        request_rate = (
            recent_metrics.get("request_count", 0) / 60
        )  # per minute -> per second
        error_rate = recent_metrics.get("error_count", 0) / 60

        # Get response time percentiles from cached data
        response_times = recent_metrics.get("response_times", [])
        if response_times:
            avg_response_time = statistics.mean(response_times)
            sorted_times = sorted(response_times)
            p95_index = int(len(sorted_times) * 0.95)
            p99_index = int(len(sorted_times) * 0.99)
            p95_response_time = sorted_times[min(p95_index, len(sorted_times) - 1)]
            p99_response_time = sorted_times[min(p99_index, len(sorted_times) - 1)]
        else:
            avg_response_time = p95_response_time = p99_response_time = 0.0

        # Cache statistics
        cache_stats = await cache.get_stats()
        l1_stats = cache_stats.get("l1_cache", {})
        cache_hit_rate = l1_stats.get("hit_ratio", 0.0) * 100

        # Database connections (from pool stats)
        try:
            from ..database_optimization import pool_manager

            pool_stats = pool_manager.get_pool_stats()
            db_connections = sum(
                stats.get("checked_out", 0) for stats in pool_stats.values()
            )
        except Exception:
            db_connections = 0

        # Task queue size
        try:
            from ..async_tasks import get_task_manager

            task_manager = await get_task_manager()
            task_stats = task_manager.get_stats()
            task_queue_size = sum(task_stats.get("queue_sizes", {}).values())
        except Exception:
            task_queue_size = 0

        # Process memory usage
        memory_info = self.process.memory_info()

        return ApplicationMetrics(
            timestamp=datetime.now(),
            active_connections=recent_metrics.get("active_connections", 0),
            request_rate=request_rate,
            error_rate=error_rate,
            avg_response_time=avg_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            cache_hit_rate=cache_hit_rate,
            database_connections=db_connections,
            task_queue_size=task_queue_size,
            memory_usage=memory_info.rss,
        )

    async def record_request_metrics(
        self, response_time_ms: float, status_code: int, endpoint: str
    ):
        """Record individual request metrics."""
        cache = await get_cache()

        # Update real-time metrics
        metrics_key = self.cache_key.build("app_metrics", "recent")
        current_metrics = await cache.get(metrics_key) or {
            "request_count": 0,
            "error_count": 0,
            "response_times": [],
            "active_connections": 0,
            "timestamp": time.time(),
        }

        # Reset if metrics are more than 1 minute old
        if time.time() - current_metrics["timestamp"] > 60:
            current_metrics = {
                "request_count": 0,
                "error_count": 0,
                "response_times": [],
                "active_connections": 0,
                "timestamp": time.time(),
            }

        # Update metrics
        current_metrics["request_count"] += 1
        if status_code >= 400:
            current_metrics["error_count"] += 1

        # Keep last 1000 response times for percentile calculation
        response_times = current_metrics["response_times"]
        response_times.append(response_time_ms)
        if len(response_times) > 1000:
            response_times = response_times[-1000:]
        current_metrics["response_times"] = response_times

        await cache.set(metrics_key, current_metrics, ttl=120)


class AlertManager:
    """Manages monitoring alerts and notifications."""

    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.alert_history: Dict[str, List[datetime]] = defaultdict(list)
        self.cache_key = CacheKey("monitoring_alerts")

    def register_alert_rule(self, rule: AlertRule):
        """Register a new alert rule."""
        self.rules[rule.name] = rule
        logger.info(
            "Alert rule registered", rule_name=rule.name, severity=rule.severity
        )

    async def evaluate_alerts(
        self, metrics_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Evaluate all alert rules against current metrics."""
        alerts = []

        for rule_name, rule in self.rules.items():
            if not rule.enabled:
                continue

            try:
                # Check cooldown
                if self._is_in_cooldown(rule_name, rule.cooldown_minutes):
                    continue

                # Evaluate condition
                if rule.condition(metrics_data):
                    alert = {
                        "rule_name": rule_name,
                        "severity": rule.severity,
                        "message": rule.message_template.format(**metrics_data),
                        "timestamp": datetime.now().isoformat(),
                        "metadata": rule.metadata,
                    }

                    alerts.append(alert)

                    # Record alert firing
                    self.alert_history[rule_name].append(datetime.now())

                    logger.warning(
                        "Alert triggered",
                        rule_name=rule_name,
                        severity=rule.severity,
                        message=alert["message"],
                    )

            except Exception as e:
                logger.error(
                    "Error evaluating alert rule", rule_name=rule_name, error=str(e)
                )

        # Store alerts in cache for dashboard
        if alerts:
            await self._store_alerts(alerts)

        return alerts

    def _is_in_cooldown(self, rule_name: str, cooldown_minutes: int) -> bool:
        """Check if alert rule is in cooldown period."""
        if rule_name not in self.alert_history:
            return False

        last_alerts = self.alert_history[rule_name]
        if not last_alerts:
            return False

        last_alert_time = max(last_alerts)
        cooldown_end = last_alert_time + timedelta(minutes=cooldown_minutes)

        return datetime.now() < cooldown_end

    async def _store_alerts(self, alerts: List[Dict[str, Any]]):
        """Store alerts for dashboard display."""
        cache = await get_cache()
        alerts_key = self.cache_key.build("recent_alerts")

        # Get existing alerts
        existing_alerts = await cache.get(alerts_key) or []

        # Add new alerts
        existing_alerts.extend(alerts)

        # Keep only last 1000 alerts
        if len(existing_alerts) > 1000:
            existing_alerts = existing_alerts[-1000:]

        await cache.set(alerts_key, existing_alerts, ttl=86400)  # 24 hours

    async def get_recent_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent alerts for dashboard."""
        cache = await get_cache()
        alerts_key = self.cache_key.build("recent_alerts")

        all_alerts = await cache.get(alerts_key) or []

        # Filter by time
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_alerts = []

        for alert in all_alerts:
            alert_time = datetime.fromisoformat(alert["timestamp"])
            if alert_time >= cutoff:
                recent_alerts.append(alert)

        return recent_alerts


class MonitoringDashboard:
    """Provides monitoring dashboard data."""

    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
        self.cache_key = CacheKey("monitoring_dashboard")

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard data."""
        # Collect current metrics
        system_metrics = await self.metrics_collector.collect_system_metrics()
        app_metrics = await self.metrics_collector.collect_application_metrics()

        # Get SLO status
        slo_manager = await get_slo_manager()
        slo_status = await slo_manager.get_all_slo_status()

        # Get circuit breaker status
        circuit_breakers = circuit_breaker_registry.get_all_stats()

        # Get recent alerts
        recent_alerts = await self.alert_manager.get_recent_alerts(hours=24)

        # Get historical metrics
        historical_metrics = await self._get_historical_metrics()

        return {
            "timestamp": datetime.now().isoformat(),
            "system_metrics": {
                "cpu_percent": system_metrics.cpu_percent,
                "memory_percent": system_metrics.memory_percent,
                "disk_percent": system_metrics.disk_percent,
                "load_average": system_metrics.load_average,
                "network_connections": system_metrics.network_connections,
                "process_count": system_metrics.process_count,
            },
            "application_metrics": {
                "request_rate": app_metrics.request_rate,
                "error_rate": app_metrics.error_rate,
                "avg_response_time": app_metrics.avg_response_time,
                "p95_response_time": app_metrics.p95_response_time,
                "cache_hit_rate": app_metrics.cache_hit_rate,
                "database_connections": app_metrics.database_connections,
                "task_queue_size": app_metrics.task_queue_size,
                "memory_usage_mb": app_metrics.memory_usage / 1024 / 1024,
            },
            "slo_status": {
                name: {
                    "current_percentage": status.current_percentage,
                    "target_percentage": status.target_percentage,
                    "error_budget_remaining": status.error_budget_remaining,
                    "status": status.status.value,
                }
                for name, status in slo_status.items()
            },
            "circuit_breakers": {
                name: {
                    "state": stats.state.value,
                    "failure_rate": stats.failure_rate,
                    "total_requests": stats.total_requests,
                    "average_response_time": stats.average_response_time,
                }
                for name, stats in circuit_breakers.items()
            },
            "alerts": {
                "recent_count": len(recent_alerts),
                "critical_count": len(
                    [a for a in recent_alerts if a["severity"] == "critical"]
                ),
                "warning_count": len(
                    [a for a in recent_alerts if a["severity"] == "warning"]
                ),
                "recent_alerts": recent_alerts[-10:],  # Last 10 alerts
            },
            "historical_metrics": historical_metrics,
        }

    async def _get_historical_metrics(self) -> Dict[str, List[Any]]:
        """Get historical metrics for trending."""
        cache = await get_cache()
        historical_key = self.cache_key.build("historical")

        # Get stored historical data
        historical = await cache.get(historical_key) or {
            "timestamps": [],
            "cpu_percent": [],
            "memory_percent": [],
            "request_rate": [],
            "error_rate": [],
            "response_time": [],
        }

        return historical

    async def store_historical_metrics(
        self, system_metrics: SystemMetrics, app_metrics: ApplicationMetrics
    ):
        """Store metrics for historical trending."""
        cache = await get_cache()
        historical_key = self.cache_key.build("historical")

        # Get existing data
        historical = await cache.get(historical_key) or {
            "timestamps": [],
            "cpu_percent": [],
            "memory_percent": [],
            "request_rate": [],
            "error_rate": [],
            "response_time": [],
        }

        # Add new data point
        timestamp = system_metrics.timestamp.isoformat()
        historical["timestamps"].append(timestamp)
        historical["cpu_percent"].append(system_metrics.cpu_percent)
        historical["memory_percent"].append(system_metrics.memory_percent)
        historical["request_rate"].append(app_metrics.request_rate)
        historical["error_rate"].append(app_metrics.error_rate)
        historical["response_time"].append(app_metrics.avg_response_time)

        # Keep only last 24 hours of data (assuming 1 minute intervals)
        max_points = 24 * 60
        for key in historical:
            if len(historical[key]) > max_points:
                historical[key] = historical[key][-max_points:]

        await cache.set(historical_key, historical, ttl=86400 * 2)  # 48 hours


class MonitoringService:
    """Main monitoring service."""

    def __init__(self):
        self.dashboard = MonitoringDashboard()
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
        self.monitoring_task: Optional[asyncio.Task] = None
        self.is_running = False

        # Setup default alert rules
        self._setup_default_alerts()

    def _setup_default_alerts(self):
        """Setup default monitoring alert rules."""

        # High CPU usage
        self.alert_manager.register_alert_rule(
            AlertRule(
                name="high_cpu_usage",
                condition=lambda m: m.get("system_metrics", {}).get("cpu_percent", 0)
                > 80,
                severity="warning",
                message_template="High CPU usage: {system_metrics[cpu_percent]:.1f}%",
                cooldown_minutes=10,
            )
        )

        # High memory usage
        self.alert_manager.register_alert_rule(
            AlertRule(
                name="high_memory_usage",
                condition=lambda m: m.get("system_metrics", {}).get("memory_percent", 0)
                > 85,
                severity="critical",
                message_template="High memory usage: {system_metrics[memory_percent]:.1f}%",
                cooldown_minutes=5,
            )
        )

        # High error rate
        self.alert_manager.register_alert_rule(
            AlertRule(
                name="high_error_rate",
                condition=lambda m: m.get("application_metrics", {}).get(
                    "error_rate", 0
                )
                > 5,
                severity="critical",
                message_template="High error rate: {application_metrics[error_rate]:.2f} errors/sec",
                cooldown_minutes=5,
            )
        )

        # Slow response times
        self.alert_manager.register_alert_rule(
            AlertRule(
                name="slow_response_times",
                condition=lambda m: m.get("application_metrics", {}).get(
                    "p95_response_time", 0
                )
                > 2000,
                severity="warning",
                message_template="Slow response times: P95 = {application_metrics[p95_response_time]:.0f}ms",
                cooldown_minutes=15,
            )
        )

        # Low cache hit rate
        self.alert_manager.register_alert_rule(
            AlertRule(
                name="low_cache_hit_rate",
                condition=lambda m: m.get("application_metrics", {}).get(
                    "cache_hit_rate", 100
                )
                < 50,
                severity="warning",
                message_template="Low cache hit rate: {application_metrics[cache_hit_rate]:.1f}%",
                cooldown_minutes=30,
            )
        )

        # High task queue size
        self.alert_manager.register_alert_rule(
            AlertRule(
                name="high_task_queue_size",
                condition=lambda m: m.get("application_metrics", {}).get(
                    "task_queue_size", 0
                )
                > 1000,
                severity="warning",
                message_template="High task queue size: {application_metrics[task_queue_size]} tasks",
                cooldown_minutes=10,
            )
        )

    async def start_monitoring(self, interval_seconds: int = 60):
        """Start continuous monitoring."""
        if self.is_running:
            return

        self.is_running = True
        self.monitoring_task = asyncio.create_task(
            self._monitoring_loop(interval_seconds)
        )

        logger.info("Monitoring service started", interval=interval_seconds)

    async def stop_monitoring(self):
        """Stop monitoring service."""
        if not self.is_running:
            return

        self.is_running = False

        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("Monitoring service stopped")

    async def _monitoring_loop(self, interval_seconds: int):
        """Main monitoring loop."""
        while self.is_running:
            try:
                # Collect metrics
                system_metrics = await self.metrics_collector.collect_system_metrics()
                app_metrics = await self.metrics_collector.collect_application_metrics()

                # Store historical data
                await self.dashboard.store_historical_metrics(
                    system_metrics, app_metrics
                )

                # Get complete dashboard data for alert evaluation
                dashboard_data = await self.dashboard.get_dashboard_data()

                # Evaluate alerts
                alerts = await self.alert_manager.evaluate_alerts(dashboard_data)

                # Process any triggered alerts
                for alert in alerts:
                    await self._process_alert(alert)

                # Log health status
                await self._log_health_status(system_metrics, app_metrics)

                await asyncio.sleep(interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Monitoring loop error", error=str(e), exc_info=True)
                await asyncio.sleep(min(interval_seconds, 60))

    async def _process_alert(self, alert: Dict[str, Any]):
        """Process a triggered alert."""
        # This would integrate with notification systems
        # For now, just log structured alert data

        logger.warning(
            "Monitoring alert",
            rule_name=alert["rule_name"],
            severity=alert["severity"],
            message=alert["message"],
            timestamp=alert["timestamp"],
        )

        # Could add integrations here:
        # - Send to Slack/Discord
        # - Create PagerDuty incident
        # - Send email notification
        # - Update status page

    async def _log_health_status(
        self, system_metrics: SystemMetrics, app_metrics: ApplicationMetrics
    ):
        """Log periodic health status."""
        logger.info(
            "Health status",
            cpu_percent=system_metrics.cpu_percent,
            memory_percent=system_metrics.memory_percent,
            request_rate=app_metrics.request_rate,
            error_rate=app_metrics.error_rate,
            avg_response_time=app_metrics.avg_response_time,
            cache_hit_rate=app_metrics.cache_hit_rate,
        )


# Global monitoring service
_monitoring_service: Optional[MonitoringService] = None


async def get_monitoring_service() -> MonitoringService:
    """Get or create monitoring service instance."""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService()
    return _monitoring_service


# Middleware integration
async def record_request_metrics(
    response_time_ms: float, status_code: int, endpoint: str
):
    """Record request metrics from middleware."""
    monitoring_service = await get_monitoring_service()
    await monitoring_service.metrics_collector.record_request_metrics(
        response_time_ms, status_code, endpoint
    )
