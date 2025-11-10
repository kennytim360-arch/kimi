"""
Regime Classification Engine
VIX-adaptive regime detection with false positive filters
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional
from enum import Enum
import logging
import numpy as np

logger = logging.getLogger(__name__)


class RegimeType(Enum):
    STRONG_RISK_ON = "strong_risk_on"
    WEAK_RISK_ON = "weak_risk_on"
    NEUTRAL = "neutral"
    WEAK_RISK_OFF = "weak_risk_off"
    STRONG_RISK_OFF = "strong_risk_off"
    UNRELIABLE = "unreliable"
    DATA_ERROR = "data_error"


class VIXCategory(Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class RegimeClassification:
    """Result of regime analysis"""
    regime_type: RegimeType
    score: float
    correlation_health: float
    vix_level: float
    threshold_used: float
    confidence: float
    timestamp: datetime
    session: str
    status: str = "OK"
    reason: str = ""

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class RegimeEngine:
    """VIX-adaptive regime detection with false positive filters"""

    def __init__(self, config: Dict, data_feed):
        self.config = config
        self.data_feed = data_feed
        self.last_regime = None

    async def analyze_regime(self, current_session: str = "UNKNOWN") -> RegimeClassification:
        """
        Core regime analysis with multiple validation layers
        Returns: RegimeClassification object
        """

        # 1. FETCH DATA WITH ERROR HANDLING
        try:
            spx_data = await self.data_feed.get_history("US500", 15, "1min")
            usdjpy_data = await self.data_feed.get_history("USDJPY", 15, "1min")
            vix_data = await self.data_feed.get_history("VIX", 15, "1min")
            us10y_data = await self.data_feed.get_history("US10Y", 3, "5min")
        except Exception as e:
            logger.error(f"Data feed error: {e}")
            return RegimeClassification(
                regime_type=RegimeType.DATA_ERROR,
                score=0.0,
                correlation_health=0.0,
                vix_level=0.0,
                threshold_used=0.0,
                confidence=0.0,
                timestamp=datetime.now(timezone.utc),
                session=current_session,
                status="DATA_ERROR",
                reason=str(e)
            )

        # 2. CALCULATE PERCENTAGE CHANGES
        spx_change = self._percent_change(spx_data)
        usdjpy_change = self._percent_change(usdjpy_data)
        vix_change = self._percent_change(vix_data)
        us10y_trend = self._trend_direction(us10y_data)

        # 3. VIX-ADAPTIVE THRESHOLD
        vix_level = vix_data['close'].iloc[-1]
        vix_category = self._categorize_vix(vix_level)
        base_threshold = self.config['regime']['base_threshold_percent']
        threshold_multiplier = self.config['regime']['vix_levels'][vix_category.value]['threshold_multiplier']
        threshold = base_threshold * threshold_multiplier

        # 4. CORRELATION HEALTH CHECK
        core_corr, corr_vol = self.data_feed.calculate_correlation(
            spx_data, usdjpy_data, self.config['correlation']['lookback_periods']
        )

        # FALSE POSITIVE FILTER: High correlation volatility = unreliable regime
        if corr_vol > self.config['correlation']['volatility_limit']:
            logger.warning(f"Correlation volatile: {corr_vol:.3f}. Regime unreliable.")
            return RegimeClassification(
                regime_type=RegimeType.UNRELIABLE,
                score=0.0,
                correlation_health=core_corr,
                vix_level=vix_level,
                threshold_used=threshold,
                confidence=0.0,
                timestamp=datetime.now(timezone.utc),
                session=current_session,
                status="UNRELIABLE",
                reason="Correlation instability"
            )

        # 5. SCORE COMPONENTS (weighted)
        risk_on_score = 0.0
        weights = {g['symbol']: g['weight'] for g in self.config['instruments']['primary_gauges']}

        if spx_change > threshold:
            risk_on_score += weights.get('US500', 0)
            logger.debug(f"SPX positive: +{spx_change:.3f}%")
        elif spx_change < -threshold:
            risk_on_score -= weights.get('US500', 0)
            logger.debug(f"SPX negative: {spx_change:.3f}%")

        if usdjpy_change > threshold:
            risk_on_score += weights.get('USDJPY', 0)
            logger.debug(f"USDJPY positive: +{usdjpy_change:.3f}%")
        elif usdjpy_change < -threshold:
            risk_on_score -= weights.get('USDJPY', 0)
            logger.debug(f"USDJPY negative: {usdjpy_change:.3f}%")

        if vix_change < -5:  # VIX declining = risk-on
            risk_on_score += weights.get('VIX', 0)
            logger.debug(f"VIX declining: {vix_change:.1f}%")
        elif vix_change > 5:  # VIX rising = risk-off
            risk_on_score -= weights.get('VIX', 0)
            logger.debug(f"VIX rising: +{vix_change:.1f}%")

        if us10y_trend == 'rising':
            risk_on_score += weights.get('US10Y', 0)
        elif us10y_trend == 'falling':
            risk_on_score -= weights.get('US10Y', 0)

        # 6. CLASSIFY REGIME
        regime_type = self._classify_score(risk_on_score)

        # 7. SESSION ADJUSTMENTS
        if current_session == "ASIAN":
            risk_on_score *= 1.4  # Reduced thresholds = higher relative scores
        elif current_session == "US_OVERLAP":
            pass  # Full power - no adjustment
        elif current_session in ["US_ONLY", "US_LATE"]:
            risk_on_score *= 0.9

        # 8. CALCULATE CONFIDENCE
        confidence = self._calculate_confidence(core_corr, corr_vol, vix_level)

        result = RegimeClassification(
            regime_type=regime_type,
            score=risk_on_score,
            correlation_health=core_corr,
            vix_level=vix_level,
            threshold_used=threshold,
            confidence=confidence,
            timestamp=datetime.now(timezone.utc),
            session=current_session,
            status="OK"
        )

        # Log regime changes
        if self.last_regime and self.last_regime.regime_type != result.regime_type:
            logger.warning(f"REGIME SHIFT: {self.last_regime.regime_type.value} -> {result.regime_type.value}")
            logger.warning(f"  Score: {self.last_regime.score:.2f} -> {result.score:.2f}")
            logger.warning(f"  Correlation: {self.last_regime.correlation_health:.2f} -> {result.correlation_health:.2f}")

        self.last_regime = result
        return result

    def _percent_change(self, df) -> float:
        """Calculate percentage change from first to last"""
        if len(df) < 2:
            return 0.0
        return ((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]) * 100

    def _trend_direction(self, df) -> str:
        """Determine if trend is rising, falling, or flat"""
        if len(df) < 2:
            return 'flat'

        first = df['close'].iloc[0]
        last = df['close'].iloc[-1]
        change_pct = ((last - first) / first) * 100

        if change_pct > 0.05:
            return 'rising'
        elif change_pct < -0.05:
            return 'falling'
        else:
            return 'flat'

    def _categorize_vix(self, vix_level: float) -> VIXCategory:
        """Categorize VIX level"""
        vix_config = self.config['regime']['vix_levels']

        if vix_level < vix_config['low']['max']:
            return VIXCategory.LOW
        elif vix_level < vix_config['moderate']['max']:
            return VIXCategory.MODERATE
        elif vix_level < vix_config['high']['max']:
            return VIXCategory.HIGH
        else:
            return VIXCategory.EXTREME

    def _classify_score(self, score: float) -> RegimeType:
        """Classify regime based on score"""
        classification = self.config['regime']['score_classification']

        if score >= classification['strong_risk_on']['min']:
            return RegimeType.STRONG_RISK_ON
        elif score >= classification['weak_risk_on']['min']:
            return RegimeType.WEAK_RISK_ON
        elif score >= classification['neutral']['min']:
            return RegimeType.NEUTRAL
        elif score >= classification['weak_risk_off']['min']:
            return RegimeType.WEAK_RISK_OFF
        else:
            return RegimeType.STRONG_RISK_OFF

    def _calculate_confidence(self, corr: float, corr_vol: float, vix: float) -> float:
        """Multi-factor confidence score 0-1.0"""
        factors = [
            min(1.0, corr / 0.7),  # Higher correlation = higher confidence
            max(0.0, 1.0 - (corr_vol / 0.2)),  # Lower vol = higher confidence
            max(0.0, 1.0 - (max(0, vix - 15) / 25)),  # Lower VIX = higher confidence
        ]
        return np.mean(factors)
