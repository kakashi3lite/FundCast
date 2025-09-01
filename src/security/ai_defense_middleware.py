"""
AI Defense Middleware for FastAPI
Real-time threat detection and automated response
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..config import settings
from .ai_threat_detector import AIThreatDetector, ThreatLevel
from .incident_response import IntelligentIncidentResponse


class AIDefenseMiddleware(BaseHTTPMiddleware):
    """
    Advanced AI Defense Middleware
    Provides real-time protection against AI-powered attacks
    """

    def __init__(
        self,
        app: ASGIApp,
        threat_detector_config: Optional[Dict[str, Any]] = None,
        response_config: Optional[Dict[str, Any]] = None,
        enabled: bool = True,
    ):
        super().__init__(app)
        self.enabled = enabled
        self.threat_detector: Optional[AIThreatDetector] = None
        self.incident_responder: Optional[IntelligentIncidentResponse] = None

        # Configuration
        self.config = {
            "prompt_injection_threshold": 0.8,
            "behavioral_anomaly_threshold": 0.7,
            "adversarial_input_threshold": 0.9,
            "auto_block_critical": True,
            "auto_challenge_high": True,
            "detailed_logging": True,
            "performance_monitoring": True,
            **(threat_detector_config or {}),
        }

        self.response_config = {
            "auto_containment": True,
            "forensics_enabled": True,
            "threat_hunting_enabled": False,  # Disabled by default for performance
            "notification_enabled": True,
            **(response_config or {}),
        }

        # Performance metrics
        self.metrics = {
            "requests_processed": 0,
            "threats_detected": 0,
            "threats_blocked": 0,
            "false_positives": 0,
            "avg_processing_time": 0.0,
            "last_reset": datetime.now(),
        }

        # Initialize components
        asyncio.create_task(self._initialize_components())

    async def _initialize_components(self):
        """Initialize AI defense components"""
        if not self.enabled:
            return

        try:
            # Initialize threat detector
            self.threat_detector = AIThreatDetector()
            await self.threat_detector.initialize()

            # Initialize incident responder
            from .incident_response import IntelligentIncidentResponse

            self.incident_responder = IntelligentIncidentResponse()
            await self.incident_responder.initialize()

            print("✅ AI Defense Middleware initialized successfully")

        except Exception as e:
            print(f"❌ AI Defense Middleware initialization failed: {e}")
            self.enabled = False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Main middleware dispatch method"""

        if not self.enabled or not self.threat_detector:
            return await call_next(request)

        start_time = time.time()

        try:
            # Extract request data
            request_data = await self._extract_request_data(request)

            # Analyze threat level
            threat_assessment = await self.threat_detector.analyze_request(request_data)

            # Log security event
            await self._log_security_event(request, threat_assessment)

            # Apply security response
            security_response = await self._apply_security_response(
                request, threat_assessment
            )

            if security_response:
                return security_response

            # Process request normally
            response = await call_next(request)

            # Post-process response
            await self._post_process_response(request, response, threat_assessment)

            return response

        except Exception as e:
            print(f"AI Defense Middleware error: {e}")
            # Fail open - allow request to proceed
            return await call_next(request)

        finally:
            # Update performance metrics
            processing_time = time.time() - start_time
            await self._update_metrics(processing_time)

    async def _extract_request_data(self, request: Request) -> Dict[str, Any]:
        """Extract relevant data from request for analysis"""

        # Basic request info
        request_data = {
            "method": request.method,
            "url": str(request.url),
            "endpoint": request.url.path,
            "headers": dict(request.headers),
            "user_agent": request.headers.get("user-agent", ""),
            "ip_address": self._get_client_ip(request),
            "timestamp": datetime.now().isoformat(),
        }

        # Extract user ID from headers or auth
        user_id = request.headers.get("user-id")
        if not user_id and hasattr(request.state, "user"):
            user_id = getattr(request.state.user, "id", None)
        request_data["user_id"] = user_id

        # Extract query parameters and body
        request_data["query_params"] = dict(request.query_params)

        try:
            # Attempt to read body for POST requests
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await self._read_request_body(request)
                if body:
                    request_data["body"] = body

                    # Extract common fields that might contain prompts
                    if isinstance(body, dict):
                        for field in ["query", "prompt", "message", "content", "text"]:
                            if field in body:
                                request_data[field] = body[field]

        except Exception as e:
            # Don't fail if we can't read the body
            pass

        # Extract session data (mock for now)
        request_data["session_data"] = await self._extract_session_data(request)

        return request_data

    async def _read_request_body(self, request: Request) -> Optional[Dict[str, Any]]:
        """Safely read request body"""
        try:
            body = await request.body()
            if not body:
                return None

            # Try to parse as JSON
            try:
                return json.loads(body.decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Return raw body for non-JSON content
                return {"raw_body": body.decode(errors="ignore")}

        except Exception:
            return None

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        # Check for forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fallback to client host
        return getattr(request.client, "host", "unknown")

    async def _extract_session_data(self, request: Request) -> Dict[str, Any]:
        """Extract session-level behavioral data"""
        # This would integrate with session management system
        # For now, return mock data based on headers

        session_data = {
            "requests": [],
            "timestamps": [datetime.now()],
            "endpoints": [request.url.path],
            "inputs": [],
            "responses": [],
        }

        # Extract from headers if available
        session_id = request.headers.get("session-id")
        if session_id:
            session_data["session_id"] = session_id

        return session_data

    async def _apply_security_response(
        self, request: Request, threat_assessment
    ) -> Optional[Response]:
        """Apply security response based on threat level"""

        threat_level = threat_assessment.threat_level

        # Critical threats - block immediately
        if threat_level >= ThreatLevel.CRITICAL and self.config["auto_block_critical"]:
            await self._trigger_incident_response(request, threat_assessment)

            return JSONResponse(
                status_code=403,
                content={
                    "error": "security_violation",
                    "message": "Request blocked due to security policy",
                    "incident_id": threat_assessment.timestamp.isoformat(),
                    "support_contact": "security@fundcast.ai",
                },
            )

        # High threats - challenge user
        elif threat_level >= ThreatLevel.HIGH and self.config["auto_challenge_high"]:
            # For now, add security headers and continue
            # In production, this could trigger CAPTCHA or MFA
            return JSONResponse(
                status_code=429,
                content={
                    "error": "security_challenge",
                    "message": "Additional verification required",
                    "challenge_type": "rate_limit",
                    "retry_after": 60,
                },
                headers={"Retry-After": "60"},
            )

        # Medium threats - log and monitor
        elif threat_level >= ThreatLevel.MEDIUM:
            # Add monitoring headers but allow request
            pass

        return None  # Allow request to proceed

    async def _trigger_incident_response(self, request: Request, threat_assessment):
        """Trigger automated incident response"""

        if not self.incident_responder or not self.response_config["auto_containment"]:
            return

        try:
            # Create security incident
            from .incident_response import SecurityIncident

            incident = SecurityIncident(
                incident_id=f"ai_threat_{int(time.time())}",
                threat_assessment=threat_assessment,
                request_data=await self._extract_request_data(request),
                severity=threat_assessment.threat_level,
                attack_type=threat_assessment.attack_type,
                timestamp=datetime.now(),
            )

            # Execute incident response asynchronously
            asyncio.create_task(self.incident_responder.respond_to_incident(incident))

        except Exception as e:
            print(f"Incident response trigger failed: {e}")

    async def _log_security_event(self, request: Request, threat_assessment):
        """Log security event for monitoring and analysis"""

        if not self.config["detailed_logging"]:
            return

        # Prepare log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "ai_threat_analysis",
            "threat_level": threat_assessment.threat_level.name,
            "attack_type": threat_assessment.attack_type.name,
            "confidence": threat_assessment.confidence,
            "risk_score": threat_assessment.risk_score,
            "patterns": threat_assessment.detected_patterns,
            "ip_address": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", ""),
            "endpoint": request.url.path,
            "method": request.method,
            "user_id": request.headers.get("user-id"),
            "evidence": threat_assessment.evidence,
        }

        # Log to structured logging system
        try:
            # This would integrate with your logging infrastructure
            print(f"Security Event: {json.dumps(log_entry, indent=2)}")

        except Exception as e:
            print(f"Security logging failed: {e}")

    async def _post_process_response(
        self, request: Request, response: Response, threat_assessment
    ):
        """Post-process response based on threat assessment"""

        # Add security headers for suspicious requests
        if threat_assessment.threat_level >= ThreatLevel.MEDIUM:
            response.headers["X-Security-Scan"] = "performed"
            response.headers["X-Threat-Level"] = threat_assessment.threat_level.name
            response.headers["X-Risk-Score"] = str(
                round(threat_assessment.risk_score, 2)
            )

    async def _update_metrics(self, processing_time: float):
        """Update performance metrics"""

        self.metrics["requests_processed"] += 1

        # Update average processing time
        current_avg = self.metrics["avg_processing_time"]
        request_count = self.metrics["requests_processed"]

        new_avg = (
            (current_avg * (request_count - 1)) + processing_time
        ) / request_count
        self.metrics["avg_processing_time"] = new_avg

        # Reset metrics daily
        if (datetime.now() - self.metrics["last_reset"]).days >= 1:
            await self._reset_daily_metrics()

    async def _reset_daily_metrics(self):
        """Reset daily metrics"""

        # Store historical data before reset
        daily_report = {
            "date": self.metrics["last_reset"].date().isoformat(),
            "requests_processed": self.metrics["requests_processed"],
            "threats_detected": self.metrics["threats_detected"],
            "threats_blocked": self.metrics["threats_blocked"],
            "avg_processing_time": self.metrics["avg_processing_time"],
        }

        # Reset counters
        self.metrics.update(
            {
                "requests_processed": 0,
                "threats_detected": 0,
                "threats_blocked": 0,
                "false_positives": 0,
                "avg_processing_time": 0.0,
                "last_reset": datetime.now(),
            }
        )

        print(f"Daily AI Defense Report: {json.dumps(daily_report, indent=2)}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""

        uptime = (datetime.now() - self.metrics["last_reset"]).total_seconds()

        return {
            **self.metrics,
            "uptime_seconds": uptime,
            "requests_per_second": self.metrics["requests_processed"] / max(uptime, 1),
            "threat_detection_rate": self.metrics["threats_detected"]
            / max(self.metrics["requests_processed"], 1),
            "block_rate": self.metrics["threats_blocked"]
            / max(self.metrics["threats_detected"], 1),
            "false_positive_rate": self.metrics["false_positives"]
            / max(self.metrics["requests_processed"], 1),
            "avg_latency_ms": self.metrics["avg_processing_time"] * 1000,
        }

    async def health_check(self) -> Dict[str, Any]:
        """Health check for AI defense system"""

        health_status = {
            "status": "healthy" if self.enabled else "disabled",
            "threat_detector": "online" if self.threat_detector else "offline",
            "incident_responder": "online" if self.incident_responder else "offline",
            "metrics": self.get_metrics(),
            "last_health_check": datetime.now().isoformat(),
        }

        # Check component health
        if self.threat_detector:
            try:
                # Test with benign input
                test_data = {"query": "test health check", "user_id": "health_check"}
                await self.threat_detector.analyze_request(test_data)
                health_status["threat_detector_status"] = "healthy"
            except Exception as e:
                health_status["threat_detector_status"] = f"unhealthy: {e}"

        return health_status


# Convenience functions for FastAPI integration


def setup_ai_defense_middleware(app, config: Optional[Dict] = None):
    """Setup AI Defense Middleware with configuration"""

    default_config = {
        "enabled": getattr(settings, "AI_DEFENSE_ENABLED", True),
        "threat_detector_config": {
            "prompt_injection_threshold": 0.8,
            "behavioral_anomaly_threshold": 0.7,
            "adversarial_input_threshold": 0.9,
        },
        "response_config": {
            "auto_containment": True,
            "forensics_enabled": True,
            "notification_enabled": True,
        },
    }

    # Merge with provided config
    if config:
        default_config.update(config)

    # Add middleware
    app.add_middleware(AIDefenseMiddleware, **default_config)

    return app
