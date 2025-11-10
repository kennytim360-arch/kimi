"""
Trade Signal Generator
Combines regime analysis, divergence detection, and correlation monitoring
to generate high-probability trade signals
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict
from enum import Enum
import logging
import uuid

from .regime_engine import RegimeType, RegimeClassification
from .divergence_detector import DivergenceSignal, DivergenceType
from .correlation_monitor import CorrelationHealth

logger = logging.getLogger(__name__)


class SignalType(Enum):
    BUY = "buy"
    SELL = "sell"
    CLOSE = "close"
    NO_TRADE = "no_trade"


class SignalPriority(Enum):
    P0_CRITICAL = "P0"  # Regime shift - immediate action
    P1_HIGH = "P1"      # Strong signal - confirm and execute
    P2_MEDIUM = "P2"    # Moderate signal - watch list
    P3_LOW = "P3"       # Weak signal - informational


@dataclass
class TradeSignal:
    """Complete trade signal with all context"""
    id: str
    signal_type: SignalType
    instrument: str
    priority: SignalPriority
    confidence: float
    regime: RegimeClassification
    divergence: Optional[DivergenceSignal]
    correlation_health: str
    suggested_entry: float
    suggested_stop: float
    suggested_target: float
    position_size_multiplier: float  # 0.0 - 1.0
    timestamp: datetime
    reasoning: str

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        if not self.id:
            self.id = str(uuid.uuid4())[:8]


class SignalGenerator:
    """
    Main signal generation engine
    Combines all analysis components to produce actionable signals
    """

    def __init__(self, config: Dict, regime_engine, divergence_engine, correlation_monitor, data_feed):
        self.config = config
        self.regime_engine = regime_engine
        self.divergence_engine = divergence_engine
        self.correlation_monitor = correlation_monitor
        self.data_feed = data_feed
        self.last_signal = None

    async def generate_signal(self, current_session: str = "UNKNOWN") -> TradeSignal:
        """
        Main signal generation logic
        Returns a TradeSignal with all relevant information
        """

        # 1. ANALYZE REGIME
        regime = await self.regime_engine.analyze_regime(current_session)

        # 2. CHECK CORRELATION HEALTH
        correlation_statuses = await self.correlation_monitor.check_correlation_health()
        correlation_healthy = self.correlation_monitor.is_correlation_healthy()
        correlation_report = self.correlation_monitor.get_correlation_report()

        # 3. SCAN FOR DIVERGENCES
        divergences = await self.divergence_engine.scan_divergences()

        # 4. GENERATE SIGNAL BASED ON CONDITIONS

        # PRIORITY 0: REGIME SHIFT (immediate action required)
        if self._is_regime_shift(regime):
            return self._generate_regime_shift_signal(regime, correlation_report)

        # PRIORITY 1: HIGH CONFIDENCE DIVERGENCE
        if divergences and correlation_healthy:
            best_divergence = max(divergences, key=lambda d: d.confidence)
            if best_divergence.confidence > 0.65:
                return await self._generate_divergence_signal(
                    best_divergence, regime, correlation_report
                )

        # PRIORITY 2: STRONG REGIME + HEALTHY CORRELATION
        if regime.regime_type in [RegimeType.STRONG_RISK_ON, RegimeType.STRONG_RISK_OFF]:
            if correlation_healthy and regime.confidence > 0.70:
                return await self._generate_regime_signal(regime, correlation_report)

        # DEFAULT: NO TRADE
        return TradeSignal(
            id="",
            signal_type=SignalType.NO_TRADE,
            instrument="US500",
            priority=SignalPriority.P3_LOW,
            confidence=0.0,
            regime=regime,
            divergence=None,
            correlation_health=correlation_report.get("overall_health", "UNKNOWN"),
            suggested_entry=0.0,
            suggested_stop=0.0,
            suggested_target=0.0,
            position_size_multiplier=0.0,
            timestamp=datetime.now(timezone.utc),
            reasoning="No high-probability setup detected"
        )

    def _is_regime_shift(self, regime: RegimeClassification) -> bool:
        """Detect if regime has significantly shifted"""
        if not self.last_signal or not self.last_signal.regime:
            return False

        old_regime = self.last_signal.regime.regime_type
        new_regime = regime.regime_type

        # Significant shifts
        significant_shifts = [
            (RegimeType.STRONG_RISK_ON, RegimeType.STRONG_RISK_OFF),
            (RegimeType.STRONG_RISK_OFF, RegimeType.STRONG_RISK_ON),
            (RegimeType.WEAK_RISK_ON, RegimeType.STRONG_RISK_OFF),
            (RegimeType.WEAK_RISK_OFF, RegimeType.STRONG_RISK_ON),
        ]

        return (old_regime, new_regime) in significant_shifts or \
               (new_regime, old_regime) in significant_shifts

    def _generate_regime_shift_signal(self, regime: RegimeClassification,
                                     correlation_report: Dict) -> TradeSignal:
        """Generate signal for regime shift"""
        return TradeSignal(
            id="",
            signal_type=SignalType.CLOSE,  # Close existing positions
            instrument="ALL",
            priority=SignalPriority.P0_CRITICAL,
            confidence=0.95,
            regime=regime,
            divergence=None,
            correlation_health=correlation_report.get("overall_health", "UNKNOWN"),
            suggested_entry=0.0,
            suggested_stop=0.0,
            suggested_target=0.0,
            position_size_multiplier=0.0,
            timestamp=datetime.now(timezone.utc),
            reasoning=f"REGIME SHIFT DETECTED: {regime.regime_type.value}"
        )

    async def _generate_divergence_signal(self, divergence: DivergenceSignal,
                                         regime: RegimeClassification,
                                         correlation_report: Dict) -> TradeSignal:
        """Generate signal based on divergence"""

        # Get current price
        quote = await self.data_feed.get_quote(divergence.instrument)
        entry_price = quote.price

        # Determine signal type
        if divergence.type == DivergenceType.BULLISH:
            signal_type = SignalType.BUY
            stop_price = entry_price * 0.9975  # 0.25% stop
            target_price = entry_price * 1.005  # 0.5% target
        else:  # BEARISH
            signal_type = SignalType.SELL
            stop_price = entry_price * 1.0025  # 0.25% stop
            target_price = entry_price * 0.995  # 0.5% target

        # Apply divergence penalty to position size
        size_multiplier = self.config['risk']['divergence_penalty']

        # Adjust confidence based on regime alignment
        final_confidence = divergence.confidence

        if (divergence.type == DivergenceType.BULLISH and
            regime.regime_type in [RegimeType.WEAK_RISK_ON, RegimeType.STRONG_RISK_ON]):
            final_confidence *= 1.2  # Boost confidence
        elif (divergence.type == DivergenceType.BEARISH and
              regime.regime_type in [RegimeType.WEAK_RISK_OFF, RegimeType.STRONG_RISK_OFF]):
            final_confidence *= 1.2

        final_confidence = min(0.95, final_confidence)  # Cap at 95%

        return TradeSignal(
            id="",
            signal_type=signal_type,
            instrument=divergence.instrument,
            priority=SignalPriority.P1_HIGH,
            confidence=final_confidence,
            regime=regime,
            divergence=divergence,
            correlation_health=correlation_report.get("overall_health", "UNKNOWN"),
            suggested_entry=entry_price,
            suggested_stop=stop_price,
            suggested_target=target_price,
            position_size_multiplier=size_multiplier,
            timestamp=datetime.now(timezone.utc),
            reasoning=f"{divergence.type.value.upper()} divergence detected with "
                     f"{divergence.confidence:.1%} confidence. Regime: {regime.regime_type.value}"
        )

    async def _generate_regime_signal(self, regime: RegimeClassification,
                                     correlation_report: Dict) -> TradeSignal:
        """Generate signal based purely on regime"""

        instrument = "US500"
        quote = await self.data_feed.get_quote(instrument)
        entry_price = quote.price

        if regime.regime_type == RegimeType.STRONG_RISK_ON:
            signal_type = SignalType.BUY
            stop_price = entry_price * 0.997  # 0.3% stop
            target_price = entry_price * 1.01  # 1.0% target
            size_multiplier = 0.8
        else:  # STRONG_RISK_OFF
            signal_type = SignalType.SELL
            stop_price = entry_price * 1.003  # 0.3% stop
            target_price = entry_price * 0.99  # 1.0% target
            size_multiplier = 0.8

        return TradeSignal(
            id="",
            signal_type=signal_type,
            instrument=instrument,
            priority=SignalPriority.P2_MEDIUM,
            confidence=regime.confidence,
            regime=regime,
            divergence=None,
            correlation_health=correlation_report.get("overall_health", "UNKNOWN"),
            suggested_entry=entry_price,
            suggested_stop=stop_price,
            suggested_target=target_price,
            position_size_multiplier=size_multiplier,
            timestamp=datetime.now(timezone.utc),
            reasoning=f"Strong regime: {regime.regime_type.value} with "
                     f"{regime.confidence:.1%} confidence"
        )
