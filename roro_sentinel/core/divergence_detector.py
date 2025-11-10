"""
Divergence Detector with False Positive Filters
Detects price-correlation divergences with robustness checks
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Callable
from enum import Enum
import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class DivergenceType(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    FALSE_POSITIVE = "invalid"


@dataclass
class DivergenceSignal:
    """Represents a detected divergence"""
    type: DivergenceType
    instrument: str
    confidence: float
    magnitude: float
    timestamp: datetime
    correlation: float = 0.0
    details: Dict = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(datetime.UTC)
        if self.details is None:
            self.details = {}


class DivergenceEngine:
    """
    Detects price-correlation divergences with robustness checks
    """

    def __init__(self, config: Dict, data_feed):
        self.config = config
        self.data_feed = data_feed
        self.false_positive_filters = [
            self._filter_vix_spike,
            self._filter_low_volatility,
            self._filter_correlation_decay
        ]

    async def scan_divergences(self) -> List[DivergenceSignal]:
        """
        Returns validated divergence signals only
        """
        signals = []

        # 1. CHECK CORE DIVERGENCE (SPX vs USDJPY)
        core_signal = await self._check_spx_usdjpy_divergence()
        if core_signal and await self._validate_divergence(core_signal):
            signals.append(core_signal)
            logger.info(f"CORE DIVERGENCE DETECTED: {core_signal.type.value} on {core_signal.instrument}")

        # 2. CHECK SATELLITE DIVERGENCES
        for satellite in ["DAX", "NAS100", "AUDJPY"]:
            try:
                sat_signal = await self._check_satellite_divergence(satellite)
                if sat_signal and await self._validate_divergence(sat_signal):
                    signals.append(sat_signal)
                    logger.info(f"SATELLITE DIVERGENCE: {sat_signal.type.value} on {satellite}")
            except Exception as e:
                logger.warning(f"Error checking {satellite} divergence: {e}")

        return signals

    async def _validate_divergence(self, signal: DivergenceSignal) -> bool:
        """
        Run all false positive filters. If ANY filter fails, reject signal.
        """
        for filter_func in self.false_positive_filters:
            try:
                if not await filter_func(signal):
                    logger.info(f"Divergence rejected by filter: {filter_func.__name__}")
                    return False
            except Exception as e:
                logger.warning(f"Filter {filter_func.__name__} failed: {e}")
                # If filter fails, be conservative and reject signal
                return False
        return True

    async def _filter_vix_spike(self, signal: DivergenceSignal) -> bool:
        """Reject if VIX spiking (potential panic conditions)"""
        try:
            vix_data = await self.data_feed.get_history("VIX", 10, "1min")
            vix_change = ((vix_data['close'].iloc[-1] - vix_data['close'].iloc[0]) /
                         vix_data['close'].iloc[0]) * 100

            if vix_change > 10:  # VIX up 10% = reject
                logger.warning(f"VIX spike detected: +{vix_change:.1f}%")
                return False
            return True
        except Exception as e:
            logger.warning(f"VIX filter error: {e}")
            return False

    async def _filter_low_volatility(self, signal: DivergenceSignal) -> bool:
        """Reject if SPX 30-min range < 0.3% (noise)"""
        try:
            spx_data = await self.data_feed.get_history("US500", 30, "1min")
            price_range = (spx_data['high'].max() - spx_data['low'].min()) / spx_data['low'].min()

            if price_range < 0.003:  # Less than 0.3% range
                logger.info(f"Low volatility: {price_range:.4f} - potential noise")
                return False
            return True
        except Exception as e:
            logger.warning(f"Volatility filter error: {e}")
            return False

    async def _filter_correlation_decay(self, signal: DivergenceSignal) -> bool:
        """Reject if correlation is decaying (relationship breaking down)"""
        try:
            spx_data = await self.data_feed.get_history("US500", 30, "1min")
            usdjpy_data = await self.data_feed.get_history("USDJPY", 30, "1min")

            # Check recent correlation vs longer-term
            recent_corr, _ = self.data_feed.calculate_correlation(spx_data, usdjpy_data, 10)
            longer_corr, _ = self.data_feed.calculate_correlation(spx_data, usdjpy_data, 20)

            if recent_corr < longer_corr * 0.7:  # Recent corr dropped 30%
                logger.warning(f"Correlation decay: {longer_corr:.2f} -> {recent_corr:.2f}")
                return False
            return True
        except Exception as e:
            logger.warning(f"Correlation filter error: {e}")
            return False

    async def _check_spx_usdjpy_divergence(self) -> Optional[DivergenceSignal]:
        """
        Bullish: SPX new low, USDJPY higher low, VIX declining
        Bearish: SPX new high, USDJPY lower high, VIX rising
        """
        try:
            spx_30m = await self.data_feed.get_history("US500", 30, "1min")
            usdjpy_30m = await self.data_feed.get_history("USDJPY", 30, "1min")
            vix_10m = await self.data_feed.get_history("VIX", 10, "1min")

            # Find significant peaks/troughs using fractals
            spx_lows = self._find_fractal_lows(spx_30m, period=5)
            usdjpy_lows = self._find_fractal_lows(usdjpy_30m, period=5)

            if len(spx_lows) < 2 or len(usdjpy_lows) < 2:
                return None

            # Get correlation for confidence calculation
            corr, _ = self.data_feed.calculate_correlation(spx_30m, usdjpy_30m, 20)

            # BULLISH DIVERGENCE
            if spx_lows[-1] < spx_lows[-2] * 0.9995:  # SPX new low
                if usdjpy_lows[-1] > usdjpy_lows[-2] * 1.0002:  # USDJPY higher low
                    if vix_10m['close'].iloc[-1] < vix_10m['close'].iloc[0]:  # VIX declining
                        magnitude = abs((spx_lows[-2] - spx_lows[-1]) / spx_lows[-2])
                        return DivergenceSignal(
                            type=DivergenceType.BULLISH,
                            instrument="US500",
                            confidence=self._calculate_divergence_strength(magnitude, corr),
                            magnitude=magnitude,
                            correlation=corr,
                            timestamp=datetime.now(datetime.UTC),
                            details={
                                "spx_low_1": spx_lows[-2],
                                "spx_low_2": spx_lows[-1],
                                "usdjpy_low_1": usdjpy_lows[-2],
                                "usdjpy_low_2": usdjpy_lows[-1]
                            }
                        )

            # BEARISH DIVERGENCE (inverse logic)
            spx_highs = self._find_fractal_highs(spx_30m, period=5)
            usdjpy_highs = self._find_fractal_highs(usdjpy_30m, period=5)

            if len(spx_highs) < 2 or len(usdjpy_highs) < 2:
                return None

            if spx_highs[-1] > spx_highs[-2] * 1.0005:  # SPX new high
                if usdjpy_highs[-1] < usdjpy_highs[-2] * 0.9998:  # USDJPY lower high
                    if vix_10m['close'].iloc[-1] > vix_10m['close'].iloc[0]:  # VIX rising
                        magnitude = abs((spx_highs[-1] - spx_highs[-2]) / spx_highs[-2])
                        return DivergenceSignal(
                            type=DivergenceType.BEARISH,
                            instrument="US500",
                            confidence=self._calculate_divergence_strength(magnitude, corr),
                            magnitude=magnitude,
                            correlation=corr,
                            timestamp=datetime.now(datetime.UTC),
                            details={
                                "spx_high_1": spx_highs[-2],
                                "spx_high_2": spx_highs[-1],
                                "usdjpy_high_1": usdjpy_highs[-2],
                                "usdjpy_high_2": usdjpy_highs[-1]
                            }
                        )

            return None

        except Exception as e:
            logger.error(f"Error checking SPX/USDJPY divergence: {e}")
            return None

    async def _check_satellite_divergence(self, satellite: str) -> Optional[DivergenceSignal]:
        """Check divergence between satellite instrument and SPX"""
        try:
            spx_data = await self.data_feed.get_history("US500", 30, "1min")
            sat_data = await self.data_feed.get_history(satellite, 30, "1min")

            # Simple divergence check
            spx_change = (spx_data['close'].iloc[-1] - spx_data['close'].iloc[0]) / spx_data['close'].iloc[0]
            sat_change = (sat_data['close'].iloc[-1] - sat_data['close'].iloc[0]) / sat_data['close'].iloc[0]

            # Divergence: SPX and satellite moving in opposite directions
            if abs(spx_change) > 0.002 and abs(sat_change) > 0.002:  # Both moving significantly
                if spx_change * sat_change < 0:  # Opposite signs
                    corr, _ = self.data_feed.calculate_correlation(spx_data, sat_data, 20)
                    magnitude = abs(spx_change - sat_change)

                    div_type = DivergenceType.BULLISH if spx_change < 0 else DivergenceType.BEARISH

                    return DivergenceSignal(
                        type=div_type,
                        instrument=satellite,
                        confidence=self._calculate_divergence_strength(magnitude, corr),
                        magnitude=magnitude,
                        correlation=corr,
                        timestamp=datetime.now(datetime.UTC)
                    )

            return None

        except Exception as e:
            logger.warning(f"Error checking {satellite} divergence: {e}")
            return None

    def _find_fractal_lows(self, df: pd.DataFrame, period: int = 5) -> List[float]:
        """Find fractal lows (local minima)"""
        lows = []
        closes = df['close'].values

        for i in range(period, len(closes) - period):
            is_low = True
            for j in range(1, period + 1):
                if closes[i] >= closes[i - j] or closes[i] >= closes[i + j]:
                    is_low = False
                    break
            if is_low:
                lows.append(closes[i])

        # If no fractals found, use rolling min
        if len(lows) == 0:
            lows = [closes.min()]

        return lows

    def _find_fractal_highs(self, df: pd.DataFrame, period: int = 5) -> List[float]:
        """Find fractal highs (local maxima)"""
        highs = []
        closes = df['close'].values

        for i in range(period, len(closes) - period):
            is_high = True
            for j in range(1, period + 1):
                if closes[i] <= closes[i - j] or closes[i] <= closes[i + j]:
                    is_high = False
                    break
            if is_high:
                highs.append(closes[i])

        # If no fractals found, use rolling max
        if len(highs) == 0:
            highs = [closes.max()]

        return highs

    def _calculate_divergence_strength(self, magnitude: float, correlation: float) -> float:
        """Calculate confidence score for divergence"""
        # Base confidence on magnitude and correlation health
        magnitude_score = min(1.0, magnitude / 0.01)  # 1% magnitude = max score
        correlation_score = max(0.3, min(1.0, correlation / 0.7))  # 0.7 corr = max score

        return (magnitude_score * 0.6 + correlation_score * 0.4)
