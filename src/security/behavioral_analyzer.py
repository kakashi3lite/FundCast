"""
Behavioral Authenticity Analyzer
=================================

Detects automation vs. human interaction by analyzing behavioral signals:
request cadence, input pacing, error patterns, session geometry, and
payload characteristics. Designed to run inline in the request path with
pure-Python heuristics plus an optional ``sklearn`` isolation forest for
outlier scoring (gracefully degraded when sklearn is unavailable).

Public API
----------
- :class:`AuthenticityScore` — normalized authenticity assessment.
- :class:`BehavioralAuthenticityAnalyzer` — the analyzer.
"""

from __future__ import annotations

import hashlib
import math
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

try:  # Optional heavy dependency — analyzer works without it.
    import numpy as np
    from sklearn.ensemble import IsolationForest
except Exception:  # pragma: no cover - optional dependency
    np = None  # type: ignore[assignment]
    IsolationForest = None  # type: ignore[assignment,misc]


class AuthenticityLabel(Enum):
    """Final authenticity verdict."""

    HUMAN = "human"
    PROBABLY_HUMAN = "probably_human"
    SUSPICIOUS = "suspicious"
    AUTOMATION = "automation"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class AuthenticityScore:
    """Normalized authenticity assessment for a session/request stream."""

    score: float  # 0.0 (automation) -> 1.0 (human)
    label: AuthenticityLabel
    confidence: float
    signals: Dict[str, float] = field(default_factory=dict)
    flagged_indicators: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-safe dictionary."""
        return {
            "score": round(self.score, 4),
            "label": self.label.value,
            "confidence": round(self.confidence, 4),
            "signals": {k: round(v, 4) for k, v in self.signals.items()},
            "flagged_indicators": self.flagged_indicators,
            "timestamp": self.timestamp.isoformat(),
        }


# Timings (seconds) of human-like interaction patterns.
_HUMAN_MIN_INTERVAL = 0.08       # below this: unlikely a human round-trip
_HUMAN_TYPING_CPS_MIN = 2.0      # min characters per second for fast typists
_HUMAN_TYPING_CPS_MAX = 14.0     # above this: impossible sustained typing
_PERFECT_TIMING_EPSILON = 0.005  # identical intervals => automation


class BehavioralAuthenticityAnalyzer:
    """
    Scores how human a given behavioral sample looks.

    The analyzer consumes ``session_data`` dictionaries with optional keys:

    - ``timestamps``: list of datetime/float request timestamps
    - ``inputs``: list of user-supplied strings
    - ``endpoints``: list of visited endpoint paths
    - ``responses``: list of response dicts (status_code)
    - ``request_intervals_ms``: list of millisecond intervals (precomputed)
    - ``user_agent``: the UA string
    """

    def __init__(
        self,
        *,
        automation_threshold: float = 0.35,
        human_threshold: float = 0.7,
        suspicious_threshold: float = 0.5,
        use_isolation_forest: bool = True,
    ) -> None:
        self.automation_threshold = automation_threshold
        self.human_threshold = human_threshold
        self.suspicious_threshold = suspicious_threshold
        self.use_isolation_forest = use_isolation_forest and IsolationForest is not None
        self._forest: Optional[IsolationForest] = None
        self._trained = False
        self._training_buffer: List[List[float]] = []
        self._max_training_samples = 512

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def analyze_behavior(
        self, user_id: str, session_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze a behavioral sample and return a human-readable assessment.

        :param user_id: Identifier of the user (for baseline tracking).
        :param session_data: Behavioral sample (see class docstring).
        :return: Dict with ``authenticity`` (AuthenticityScore.to_dict()),
            ``feature_vector``, and ``anomaly_score``.
        """
        signals = self._extract_signals(session_data)
        indicator_flags: List[str] = []
        for name, value in signals.items():
            if value > 0 and self._indicator_is_flagged(name, value):
                indicator_flags.append(name)

        feature_vector = self._to_feature_vector(signals)
        forest_score = await self._forest_score(feature_vector)
        rule_score = self._rule_based_score(signals)

        # Blend rule-based (stable) and ML (adaptive) scores.
        if forest_score is not None:
            blended = 0.6 * rule_score + 0.4 * forest_score
        else:
            blended = rule_score

        score = max(0.0, min(1.0, blended))
        label = self._classify(score)
        confidence = self._estimate_confidence(signals, forest_score is not None)

        authenticity = AuthenticityScore(
            score=score,
            label=label,
            confidence=confidence,
            signals=signals,
            flagged_indicators=indicator_flags,
        )
        return {
            "authenticity": authenticity.to_dict(),
            "feature_vector": feature_vector,
            "forest_score": round(forest_score, 4) if forest_score is not None else None,
            "user_id": user_id,
        }

    # ------------------------------------------------------------------
    # Signal extraction
    # ------------------------------------------------------------------
    def _extract_signals(self, data: Dict[str, Any]) -> Dict[str, float]:
        timestamps = self._normalize_timestamps(data.get("timestamps", []))
        intervals = data.get("request_intervals_ms")
        if not intervals:
            intervals = self._compute_intervals(timestamps)

        inputs = [str(i) for i in data.get("inputs", [])]
        endpoints = data.get("endpoints", [])
        responses = data.get("responses", [])
        ua = str(data.get("user_agent", ""))

        signals: Dict[str, float] = {}
        signals["request_frequency"] = self._request_frequency(intervals)
        signals["interval_regularity"] = self._interval_regularity(intervals)
        signals["perfect_timing_ratio"] = self._perfect_timing_ratio(intervals)
        signals["avg_input_length"] = self._avg_input_length(inputs)
        signals["input_pacing"] = self._input_pacing(inputs, intervals)
        signals["typing_cadence"] = self._typing_cadence(inputs, intervals)
        signals["error_rate"] = self._error_rate(responses)
        signals["endpoint_diversity"] = self._endpoint_diversity(endpoints)
        signals["payload_repetitiveness"] = self._payload_repetitiveness(inputs)
        signals["bot_ua_indicators"] = self._bot_ua_indicators(ua)
        return signals

    @staticmethod
    def _normalize_timestamps(raw: List[Any]) -> List[float]:
        out: List[float] = []
        for item in raw:
            if isinstance(item, datetime):
                out.append(item.timestamp())
            elif isinstance(item, (int, float)):
                # Accept both epoch seconds and epoch millis.
                out.append(item / 1000.0 if item > 1e11 else float(item))
        return out

    @staticmethod
    def _compute_intervals(timestamps: List[float]) -> List[float]:
        if len(timestamps) < 2:
            return []
        return [timestamps[i] - timestamps[i - 1] for i in range(1, len(timestamps))]

    @staticmethod
    def _request_frequency(intervals: List[float]) -> float:
        if not intervals:
            return 0.0
        positive = [i for i in intervals if i > 0]
        if not positive:
            return 1.0
        mean = sum(positive) / len(positive)
        # Normalize: ~30s between requests => 0.5, sub-second => 1.0
        return max(0.0, min(1.0, 1.0 - math.log10(max(mean, 0.05)) / 3.0))

    @staticmethod
    def _interval_regularity(intervals: List[float]) -> float:
        """High regularity (identical cadence) => automation."""
        if len(intervals) < 3:
            return 0.0
        mean = sum(intervals) / len(intervals)
        if mean == 0:
            return 1.0
        variance = sum((i - mean) ** 2 for i in intervals) / len(intervals)
        cv = math.sqrt(variance) / mean  # coefficient of variation
        # Humans are irregular: CV < 0.05 => very regular.
        return max(0.0, min(1.0, 1.0 - cv / 0.5))

    @staticmethod
    def _perfect_timing_ratio(intervals: List[float]) -> float:
        """Fraction of intervals that are suspiciously identical."""
        if len(intervals) < 3:
            return 0.0
        close = 0
        for a, b in zip(intervals, intervals[1:]):
            if abs(a - b) <= _PERFECT_TIMING_EPSILON:
                close += 1
        return close / (len(intervals) - 1)

    @staticmethod
    def _avg_input_length(inputs: List[str]) -> float:
        if not inputs:
            return 0.0
        return sum(len(i) for i in inputs) / len(inputs)

    @staticmethod
    def _input_pacing(inputs: List[str], intervals: List[float]) -> float:
        """Estimate whether inputs arrive with human-like pacing."""
        if not inputs or not intervals:
            return 0.0
        # Reconstruct keystroke stream length and elapsed wall time.
        total_chars = sum(len(i) for i in inputs)
        elapsed = sum(max(i, 0) for i in intervals)
        if elapsed <= 0:
            return 0.5
        cps = total_chars / elapsed
        if _HUMAN_TYPING_CPS_MIN <= cps <= _HUMAN_TYPING_CPS_MAX:
            return 1.0
        if cps > _HUMAN_TYPING_CPS_MAX * 2.5:  # clearly automated
            return 0.0
        return 0.3

    @staticmethod
    def _typing_cadence(inputs: List[str], intervals: List[float]) -> float:
        """Proportion of pauses consistent with human typing gaps."""
        if not inputs or not intervals:
            return 0.0
        human_gaps = sum(1 for i in intervals if _HUMAN_MIN_INTERVAL < i < 5.0)
        return human_gaps / len(intervals)

    @staticmethod
    def _error_rate(responses: List[Dict[str, Any]]) -> float:
        if not responses:
            return 0.0
        errors = sum(1 for r in responses if r.get("status_code", 200) >= 400)
        return errors / len(responses)

    @staticmethod
    def _endpoint_diversity(endpoints: List[str]) -> float:
        if not endpoints:
            return 0.0
        unique = len(set(endpoints))
        return max(0.0, min(1.0, unique / 10.0))

    @staticmethod
    def _payload_repetitiveness(inputs: List[str]) -> float:
        """Fraction of near-duplicate payloads (bots repeat payloads)."""
        if len(inputs) < 2:
            return 0.0
        hashes = {hashlib.md5(i.encode()).hexdigest() for i in inputs}
        return 1.0 - (len(hashes) / len(inputs))

    @staticmethod
    def _bot_ua_indicators(ua: str) -> float:
        """Score presence of known automation UA markers."""
        markers = re.compile(
            r"(?i)(python-requests|curl/|wget|httpie|scrapy|selenium|headless|"
            r"phantomjs|puppeteer|playwright|postmanruntime|bot|crawl|spider)"
        )
        return 1.0 if markers.search(ua) else 0.0

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------
    def _rule_based_score(self, signals: Dict[str, float]) -> float:
        # Base human-ish prior.
        score = 0.6
        weights = {
            "perfect_timing_ratio": -0.35,
            "interval_regularity": -0.15,
            "bot_ua_indicators": -0.30,
            "payload_repetitiveness": -0.20,
            "input_pacing": 0.10,
            "typing_cadence": 0.10,
            "endpoint_diversity": 0.05,
            "error_rate": 0.03,
            "avg_input_length": 0.02,
        }
        for name, weight in weights.items():
            score += signals.get(name, 0.0) * weight
        return max(0.0, min(1.0, score))

    def _to_feature_vector(self, signals: Dict[str, float]) -> List[float]:
        order = [
            "request_frequency",
            "interval_regularity",
            "perfect_timing_ratio",
            "avg_input_length",
            "input_pacing",
            "error_rate",
            "endpoint_diversity",
            "payload_repetitiveness",
            "bot_ua_indicators",
        ]
        return [signals.get(k, 0.0) for k in order]

    async def _forest_score(self, feature_vector: List[float]) -> Optional[float]:
        """Adaptive anomaly score using a lightweight isolation forest."""
        if not self.use_isolation_forest or np is None:
            return None
        try:
            await self._maybe_train(feature_vector)
            if not self._trained:
                return None
            sample = np.array([feature_vector], dtype=float).reshape(1, -1)
            # isolation score in [-0.5, 0.5]; positive => anomalous.
            iso = float(self._forest.score_samples(sample)[0])  # type: ignore[union-attr]
            anomaly = max(0.0, min(1.0, (0.5 - iso) * 2.0))
            return 1.0 - anomaly
        except Exception:  # pragma: no cover - ML is best-effort
            return None

    async def _maybe_train(self, feature_vector: List[float]) -> None:
        if self._trained:
            return
        self._training_buffer.append(feature_vector)
        if len(self._training_buffer) >= max(24, self._max_training_samples // 8):
            try:
                X = np.array(self._training_buffer, dtype=float)
                self._forest = IsolationForest(
                    contamination=0.1, random_state=42, n_estimators=32
                )
                self._forest.fit(X)
                self._trained = True
            except Exception:  # pragma: no cover
                self._forest = None
                self._trained = False

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------
    def _classify(self, score: float) -> AuthenticityLabel:
        if score >= self.human_threshold:
            return AuthenticityLabel.HUMAN
        if score >= self.suspicious_threshold:
            return AuthenticityLabel.PROBABLY_HUMAN
        if score >= self.automation_threshold:
            return AuthenticityLabel.SUSPICIOUS
        return AuthenticityLabel.AUTOMATION

    @staticmethod
    def _estimate_confidence(signals: Dict[str, float], has_ml: bool) -> float:
        observed = sum(1 for v in signals.values() if v != 0.0)
        base = min(1.0, observed / 8.0)
        return round(min(1.0, base + (0.2 if has_ml else 0.0)), 4)

    @staticmethod
    def _indicator_is_flagged(name: str, value: float) -> bool:
        return {
            "perfect_timing_ratio": value > 0.8,
            "bot_ua_indicators": value >= 1.0,
            "payload_repetitiveness": value > 0.9,
            "interval_regularity": value > 0.95,
        }.get(name, False)
