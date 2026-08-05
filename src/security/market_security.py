"""
Prediction Market Security Framework
====================================

Detects manipulation and integrity threats in prediction markets:
wash trading, spoofing, pump-and-dump patterns, cornering, position
concentration, and anomalous order-flow signatures. Purely analytical —
it consumes order/trade streams and produces integrity assessments.

Public API
----------
- :class:`IntegrityAssessment` — integrity verdict for a market window.
- :class:`PredictionMarketSecurityFramework` — the analyzer.
"""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, DefaultDict, Deque, Dict, List, Optional


class IntegrityLevel(Enum):
    """Market integrity verdict."""

    HEALTHY = "healthy"
    WATCH = "watch"        # elevated risk signals present
    SUSPICIOUS = "suspicious"
    COMPROMISED = "compromised"
    INSUFFICIENT_DATA = "insufficient_data"


class ManipulationType(Enum):
    """Manipulation techniques the framework looks for."""

    WASH_TRADING = "wash_trading"
    SPOOFING = "spoofing"
    PUMP_AND_DUMP = "pump_and_dump"
    CORNERING = "cornering"
    POSITION_CONCENTRATION = "position_concentration"
    LAYERING = "layering"
    NONE = "none"


@dataclass
class IntegrityAssessment:
    """Integrity assessment for a single market over a lookback window."""

    market_id: str
    level: IntegrityLevel
    manipulation_flags: List[ManipulationType] = field(default_factory=list)
    signals: Dict[str, float] = field(default_factory=dict)
    detail: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-safe dictionary."""
        return {
            "market_id": self.market_id,
            "level": self.level.value,
            "manipulation_flags": [m.value for m in self.manipulation_flags],
            "signals": {k: round(v, 4) for k, v in self.signals.items()},
            "detail": self.detail,
            "timestamp": self.timestamp.isoformat(),
        }


# Event shape helpers -----------------------------------------------------
def order_fingerprint(order: Dict[str, Any]) -> str:
    """Stable fingerprint of an order (used for wash-trade matching)."""
    raw = hashlib.sha1(
        f"{order.get('side')}:{order.get('price')}:{order.get('quantity')}:{order.get('market_id')}".encode()
    ).hexdigest()
    return raw


class PredictionMarketSecurityFramework:
    """
    Streaming integrity monitor for prediction markets.

    Feed it orders and trades via :meth:`record_order` /
    :meth:`record_trade`, then query :meth:`assess_market` for a windowed
    integrity assessment. Retains only recent activity per market.
    """

    def __init__(
        self,
        *,
        window_size: int = 200,
        wash_similarity_threshold: float = 0.6,
        spoof_cancel_ratio: float = 0.6,
        concentration_threshold: float = 0.5,
        max_age_seconds: float = 3600.0,
    ) -> None:
        self.window_size = window_size
        self.wash_similarity_threshold = wash_similarity_threshold
        self.spoof_cancel_ratio = spoof_cancel_ratio
        self.concentration_threshold = concentration_threshold
        self.max_age_seconds = max_age_seconds

        # market_id -> deque of order dicts
        self._orders: DefaultDict[str, Deque[Dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=window_size * 4)
        )
        # market_id -> deque of trade dicts
        self._trades: DefaultDict[str, Deque[Dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=window_size)
        )
        self._stats = {
            "orders_seen": 0,
            "trades_seen": 0,
            "assessments": 0,
            "alerts": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------
    def record_order(self, order: Dict[str, Any]) -> None:
        """Record an order event (created/cancelled/filled)."""
        order.setdefault("ts", time.time())
        self._orders[order["market_id"]].append(order)
        self._stats["orders_seen"] += 1

    def record_trade(self, trade: Dict[str, Any]) -> None:
        """Record a matched trade."""
        trade.setdefault("ts", time.time())
        self._trades[trade["market_id"]].append(trade)
        self._stats["trades_seen"] += 1

    # ------------------------------------------------------------------
    # Assessment
    # ------------------------------------------------------------------
    async def assess_market(self, market_id: str) -> IntegrityAssessment:
        """Assess the integrity of a market over its recent activity."""
        self._stats["assessments"] += 1
        orders = self._recent(self._orders.get(market_id, []))
        trades = self._recent(self._trades.get(market_id, []))

        if len(orders) < 5 and len(trades) < 3:
            return IntegrityAssessment(market_id, IntegrityLevel.INSUFFICIENT_DATA)

        signals: Dict[str, float] = {}
        flags: List[ManipulationType] = []

        # 1. Wash trading: opposite-side near-identical orders/trades from
        #    the same entity or matching fingerprints within a short window.
        wash = self._detect_wash_trading(orders, trades)
        signals["wash_trade_score"] = wash
        if wash > 0.5:
            flags.append(ManipulationType.WASH_TRADING)

        # 2. Spoofing: large limit orders placed then cancelled without fill.
        spoof = self._detect_spoofing(orders)
        signals["spoofing_score"] = spoof
        if spoof > 0.5:
            flags.append(ManipulationType.SPOOFING)

        # 3. Pump & dump: sharp price spike followed by heavy sell volume.
        pump = self._detect_pump_and_dump(trades)
        signals["pump_dump_score"] = pump
        if pump > 0.5:
            flags.append(ManipulationType.PUMP_AND_DUMP)

        # 4. Position concentration: a single entity holding a dominant share.
        concentration = self._detect_concentration(trades)
        signals["concentration_score"] = concentration
        if concentration > self.concentration_threshold:
            flags.append(ManipulationType.POSITION_CONCENTRATION)

        # 5. Layering: multiple price levels quoted then removed together.
        layering = self._detect_layering(orders)
        signals["layering_score"] = layering
        if layering > 0.5:
            flags.append(ManipulationType.LAYERING)

        level = self._classify(signals)
        if level in (IntegrityLevel.SUSPICIOUS, IntegrityLevel.COMPROMISED):
            self._stats["alerts"] += 1

        detail = ", ".join(f.value for f in flags) if flags else "no manipulation flags"
        return IntegrityAssessment(
            market_id=market_id,
            level=level,
            manipulation_flags=flags,
            signals=signals,
            detail=detail,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Return framework statistics."""
        return dict(self._stats)

    # ------------------------------------------------------------------
    # Detectors
    # ------------------------------------------------------------------
    def _detect_wash_trading(
        self, orders: List[Dict[str, Any]], trades: List[Dict[str, Any]]
    ) -> float:
        if len(trades) < 3:
            return 0.0
        by_fingerprint: DefaultDict[str, int] = defaultdict(int)
        for t in trades:
            fp = order_fingerprint(t)
            by_fingerprint[fp] += 1
        max_repeats = max(by_fingerprint.values()) if by_fingerprint else 1
        ratio = (max_repeats - 1) / len(trades)
        # Same-entity opposite sides is a stronger signal.
        entity_pairs = 0
        total_pairs = 0
        for i, a in enumerate(trades):
            for b in trades[i + 1:]:
                total_pairs += 1
                if (
                    a.get("trader_id") == b.get("trader_id")
                    and a.get("side") != b.get("side")
                    and abs(a.get("price", 0) - b.get("price", 0)) < 1e-6
                ):
                    entity_pairs += 1
        entity_ratio = entity_pairs / total_pairs if total_pairs else 0.0
        return max(ratio, entity_ratio)

    def _detect_spoofing(self, orders: List[Dict[str, Any]]) -> float:
        created = [o for o in orders if o.get("event") in ("created", "placed")]
        cancelled = [o for o in orders if o.get("event") in ("cancelled", "canceled")]
        if not created:
            return 0.0
        cancelled_filled = [
            c for c in cancelled if c.get("filled_quantity", 0) == 0
        ]
        return len(cancelled_filled) / len(created)

    def _detect_pump_and_dump(self, trades: List[Dict[str, Any]]) -> float:
        if len(trades) < 6:
            return 0.0
        prices = [t.get("price", 0.0) for t in trades]
        vols = [t.get("quantity", 0.0) for t in trades]
        half = len(prices) // 2
        first_half = prices[:half]
        second_half = prices[half:]
        peak = max(prices)
        start = prices[0]
        if start <= 0:
            return 0.0
        spike = (peak - start) / start
        # Sell pressure in the second half.
        sell_vol = sum(v for t, v in zip(trades[half:], vols[half:]) if t.get("side") == "sell")
        total_vol = sum(vols)
        sell_pressure = sell_vol / total_vol if total_vol else 0.0
        return max(0.0, min(1.0, spike * 0.5 + sell_pressure * 0.5))

    def _detect_concentration(self, trades: List[Dict[str, Any]]) -> float:
        by_entity: DefaultDict[str, float] = defaultdict(float)
        for t in trades:
            by_entity[t.get("trader_id", "unknown")] += t.get("quantity", 0.0)
        if not by_entity:
            return 0.0
        total = sum(by_entity.values())
        if total <= 0:
            return 0.0
        return max(by_entity.values()) / total

    def _detect_layering(self, orders: List[Dict[str, Any]]) -> float:
        created = [o for o in orders if o.get("event") in ("created", "placed")]
        cancelled = [o for o in orders if o.get("event") in ("cancelled", "canceled")]
        if len(created) < 5 or not cancelled:
            return 0.0
        # Layering = many distinct price levels cancelled in a short burst.
        levels = {c.get("price") for c in cancelled}
        return min(1.0, len(levels) / max(len(cancelled), 1))

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------
    def _classify(self, signals: Dict[str, float]) -> IntegrityLevel:
        max_signal = max(signals.values(), default=0.0)
        if max_signal >= 0.8:
            return IntegrityLevel.COMPROMISED
        if max_signal >= 0.5:
            return IntegrityLevel.SUSPICIOUS
        if max_signal >= 0.3:
            return IntegrityLevel.WATCH
        return IntegrityLevel.HEALTHY

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _recent(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        now = time.time()
        return [i for i in items if now - i.get("ts", now) <= self.max_age_seconds]
