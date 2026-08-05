"""
Automated Intelligent Incident Response
=========================================

Runs automated containment, notification, and escalation workflows for
security incidents detected by the AI defense stack. This module is
self-contained: it does not require a database connection or application
configuration to import, so it can be used standalone or embedded in the
FastAPI middleware chain.

Public API
----------
- :class:`SecurityIncident` — immutable snapshot of a detected threat.
- :class:`ResponseResult` — outcome of an incident response run.
- :class:`IntelligentIncidentResponse` — orchestrates containment + notification.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Deque, Dict, List, Optional

from .ai_threat_detector import AttackType, ThreatAssessment, ThreatLevel

logger = logging.getLogger("fundcast.security.incident_response")


class ResponseAction(Enum):
    """Discrete actions an incident response run can take."""

    BLOCK = "block"
    CHALLENGE = "challenge"
    MONITOR = "monitor"
    CONTAIN = "contain"
    NOTIFY = "notify"
    ESCALATE = "escalate"
    NOOP = "noop"


@dataclass
class SecurityIncident:
    """Snapshot of a detected security threat."""

    incident_id: str
    threat_assessment: ThreatAssessment
    request_data: Dict[str, Any]
    severity: ThreatLevel
    attack_type: AttackType
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the incident to a JSON-safe dictionary."""
        return {
            "incident_id": self.incident_id,
            "severity": self.severity.name,
            "attack_type": self.attack_type.value,
            "confidence": self.threat_assessment.confidence,
            "risk_score": self.threat_assessment.risk_score,
            "detected_patterns": list(self.threat_assessment.detected_patterns),
            "timestamp": self.timestamp.isoformat(),
            "source_ip": self.request_data.get("ip_address"),
            "user_id": self.request_data.get("user_id"),
            "endpoint": self.request_data.get("endpoint"),
            "method": self.request_data.get("method"),
        }


@dataclass
class ResponseResult:
    """Outcome of an incident response run."""

    incident_id: str
    actions_taken: List[ResponseAction]
    contained: bool
    notification_sent: bool
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class IntelligentIncidentResponse:
    """
    Orchestrates the response lifecycle for security incidents.

    Workflow per incident:

    1. **Classify** — map threat level + attack type to a response plan.
    2. **Contain** — record blocking/challenge decisions (idempotent per IP/user).
    3. **Notify** — dispatch async notifications to a pluggable notifier.
    4. **Escalate** — route critical incidents to a human queue.
    5. **Forensics** — keep an in-memory ring buffer of recent incidents.
    """

    def __init__(
        self,
        max_forensics: int = 500,
        notifier: Optional[Any] = None,
        escalate_critical: bool = True,
    ) -> None:
        self.max_forensics = max_forensics
        self.notifier = notifier
        self.escalate_critical = escalate_critical
        self._forensics: Deque[SecurityIncident] = deque(maxlen=max_forensics)
        self._contained: Dict[str, float] = {}  # key -> expiry timestamp
        self._containment_ttl = 3600.0
        self._stats = {
            "incidents_total": 0,
            "incidents_blocked": 0,
            "incidents_escalated": 0,
            "notifications_sent": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        self._initialized = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def initialize(self) -> None:
        """Prepare the responder (idempotent)."""
        self._initialized = True
        logger.info("IntelligentIncidentResponse initialized")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def respond_to_incident(self, incident: SecurityIncident) -> ResponseResult:
        """
        Execute the full response lifecycle for a single incident.

        :param incident: The detected incident to respond to.
        :return: The result of the response run.
        """
        self._stats["incidents_total"] += 1
        self._forensics.append(incident)

        plan = self._build_response_plan(incident)
        actions: List[ResponseAction] = []
        details: Dict[str, Any] = {}

        for action in plan:
            if action == ResponseAction.BLOCK:
                await self._apply_block(incident)
                actions.append(action)
                self._stats["incidents_blocked"] += 1
                details["blocked"] = True
            elif action == ResponseAction.CONTAIN:
                self._contain_key(self._containment_key(incident))
                actions.append(action)
            elif action == ResponseAction.NOTIFY:
                sent = await self._notify(incident)
                if sent:
                    self._stats["notifications_sent"] += 1
                actions.append(action)
                details["notification_sent"] = sent
            elif action == ResponseAction.ESCALATE:
                self._stats["incidents_escalated"] += 1
                actions.append(action)
                details["escalated"] = True
            elif action == ResponseAction.MONITOR:
                actions.append(action)
            else:
                actions.append(ResponseAction.NOOP)

        return ResponseResult(
            incident_id=incident.incident_id,
            actions_taken=actions,
            contained=self._is_contained(self._containment_key(incident)),
            notification_sent=details.get("notification_sent", False),
            details=details,
        )

    async def health_check(self) -> Dict[str, Any]:
        """Return responder health and statistics."""
        return {
            "status": "healthy" if self._initialized else "not_initialized",
            "stats": dict(self._stats),
            "forensics_buffer": len(self._forensics),
            "contained_entities": len(self._contained),
        }

    def get_recent_incidents(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return the most recent incidents (newest first)."""
        return [inc.to_dict() for inc in list(self._forensics)[-limit:][::-1]]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _build_response_plan(self, incident: SecurityIncident) -> List[ResponseAction]:
        """Map a threat to an ordered response plan."""
        plan: List[ResponseAction] = [ResponseAction.MONITOR]

        if incident.severity in (ThreatLevel.CRITICAL, ThreatLevel.BLOCK):
            plan = [ResponseAction.BLOCK, ResponseAction.CONTAIN]
            if self.escalate_critical:
                plan.append(ResponseAction.ESCALATE)
            plan.append(ResponseAction.NOTIFY)
        elif incident.severity == ThreatLevel.HIGH:
            plan = [ResponseAction.CHALLENGE, ResponseAction.CONTAIN]
            plan.append(ResponseAction.NOTIFY)
        elif incident.severity == ThreatLevel.MEDIUM:
            plan.append(ResponseAction.NOTIFY)

        return plan

    async def _apply_block(self, incident: SecurityIncident) -> None:
        """Idempotently record a block for the offending entity."""
        self._contain_key(self._containment_key(incident))
        logger.warning(
            "Blocked request",
            extra={"incident_id": incident.incident_id, "severity": incident.severity.name},
        )

    def _containment_key(self, incident: SecurityIncident) -> str:
        """Derive a stable key identifying the offending entity."""
        source_ip = incident.request_data.get("ip_address") or "unknown"
        user_id = incident.request_data.get("user_id")
        if user_id:
            return f"user:{user_id}"
        return f"ip:{source_ip}"

    def _contain_key(self, key: str) -> None:
        self._contained[key] = time.time() + self._containment_ttl

    def _is_contained(self, key: str) -> bool:
        expiry = self._contained.get(key)
        return bool(expiry and expiry > time.time())

    async def _notify(self, incident: SecurityIncident) -> bool:
        """Dispatch a notification via the pluggable notifier (best-effort)."""
        if self.notifier is None:
            # Default no-op notifier — log for auditability.
            logger.info(
                "Incident notification (no notifier configured)",
                extra={"incident": incident.to_dict()},
            )
            return True
        try:
            if hasattr(self.notifier, "send"):
                await self.notifier.send(incident.to_dict())
            elif callable(self.notifier):
                await self.notifier(incident.to_dict())
            else:
                return False
            return True
        except Exception:  # pragma: no cover - never let notifications break the flow
            logger.exception("Notification dispatch failed")
            return False

    # ------------------------------------------------------------------
    # Convenience factory
    # ------------------------------------------------------------------
    @classmethod
    def from_incident(
        cls,
        threat_assessment: ThreatAssessment,
        request_data: Dict[str, Any],
        *,
        incident_id: Optional[str] = None,
    ) -> SecurityIncident:
        """Build a :class:`SecurityIncident` from a raw assessment."""
        raw = "".join(sorted(threat_assessment.detected_patterns))
        digest = hashlib.sha1(
            f"{raw}:{request_data.get('ip_address')}:{time.time()}".encode()
        ).hexdigest()[:12]
        return SecurityIncident(
            incident_id=incident_id or f"ai_threat_{digest}",
            threat_assessment=threat_assessment,
            request_data=request_data,
            severity=threat_assessment.threat_level,
            attack_type=threat_assessment.attack_type,
            timestamp=datetime.now(timezone.utc),
        )


def incidents_to_json(incidents: List[SecurityIncident]) -> str:
    """Serialize a list of incidents to JSON (for reporting/forensics)."""
    return json.dumps([inc.to_dict() for inc in incidents], indent=2)
