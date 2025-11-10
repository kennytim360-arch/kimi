"""
Real-time Correlation Monitor
Tracks correlation health between key instruments
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List
from enum import Enum
import logging
import numpy as np

logger = logging.getLogger(__name__)


class CorrelationHealth(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    BROKEN = "broken"


@dataclass
class CorrelationStatus:
    """Correlation status between two instruments"""
    instrument1: str
    instrument2: str
    correlation: float
    volatility: float
    health: CorrelationHealth
    timestamp: datetime
    lookback_periods: int

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class CorrelationMonitor:
    """
    Monitors correlation health between key instruments
    Critical for detecting regime changes and false signals
    """

    def __init__(self, config: Dict, data_feed):
        self.config = config
        self.data_feed = data_feed
        self.correlation_history = []

    async def check_correlation_health(self) -> List[CorrelationStatus]:
        """
        Check correlation health for all key instrument pairs
        """
        statuses = []

        # Key pairs to monitor
        pairs = [
            ("US500", "USDJPY"),
            ("US500", "VIX"),
            ("USDJPY", "DXY"),
            ("US500", "US10Y"),
        ]

        lookback = self.config['correlation']['lookback_periods']

        for inst1, inst2 in pairs:
            try:
                status = await self._check_pair_correlation(inst1, inst2, lookback)
                if status:
                    statuses.append(status)
                    self._log_correlation_status(status)
            except Exception as e:
                logger.error(f"Error checking correlation {inst1}/{inst2}: {e}")

        # Store history
        self.correlation_history.extend(statuses)

        # Keep only last 1000 entries
        if len(self.correlation_history) > 1000:
            self.correlation_history = self.correlation_history[-1000:]

        return statuses

    async def _check_pair_correlation(self, inst1: str, inst2: str,
                                     lookback: int) -> CorrelationStatus:
        """Check correlation between a specific pair"""
        try:
            data1 = await self.data_feed.get_history(inst1, lookback, "1min")
            data2 = await self.data_feed.get_history(inst2, lookback, "1min")

            corr, corr_vol = self.data_feed.calculate_correlation(data1, data2, lookback)

            # Determine health status
            health = self._assess_health(corr, corr_vol)

            return CorrelationStatus(
                instrument1=inst1,
                instrument2=inst2,
                correlation=corr,
                volatility=corr_vol,
                health=health,
                timestamp=datetime.now(timezone.utc),
                lookback_periods=lookback
            )

        except Exception as e:
            logger.error(f"Error calculating correlation {inst1}/{inst2}: {e}")
            return None

    def _assess_health(self, correlation: float, volatility: float) -> CorrelationHealth:
        """Assess correlation health based on value and volatility"""
        healthy_threshold = self.config['correlation']['healthy_threshold']
        critical_threshold = self.config['correlation']['critical_breakdown']
        volatility_limit = self.config['correlation']['volatility_limit']

        # High volatility = unreliable
        if volatility > volatility_limit:
            return CorrelationHealth.WARNING

        # Check correlation value
        if abs(correlation) >= healthy_threshold:
            return CorrelationHealth.HEALTHY
        elif abs(correlation) >= critical_threshold:
            return CorrelationHealth.WARNING
        elif abs(correlation) >= critical_threshold * 0.75:
            return CorrelationHealth.CRITICAL
        else:
            return CorrelationHealth.BROKEN

    def _log_correlation_status(self, status: CorrelationStatus):
        """Log correlation status"""
        if status.health in [CorrelationHealth.CRITICAL, CorrelationHealth.BROKEN]:
            logger.warning(
                f"CORRELATION {status.health.value.upper()}: "
                f"{status.instrument1}/{status.instrument2} = {status.correlation:.3f} "
                f"(vol: {status.volatility:.3f})"
            )
        elif status.health == CorrelationHealth.WARNING:
            logger.info(
                f"Correlation warning: {status.instrument1}/{status.instrument2} = "
                f"{status.correlation:.3f} (vol: {status.volatility:.3f})"
            )

    def get_core_correlation(self) -> float:
        """Get the most recent SPX/USDJPY correlation"""
        for status in reversed(self.correlation_history):
            if (status.instrument1 == "US500" and status.instrument2 == "USDJPY") or \
               (status.instrument1 == "USDJPY" and status.instrument2 == "US500"):
                return status.correlation
        return 0.0

    def is_correlation_healthy(self) -> bool:
        """Check if core correlations are healthy"""
        recent_statuses = [s for s in self.correlation_history[-10:]
                          if (s.instrument1 == "US500" and s.instrument2 == "USDJPY") or
                             (s.instrument1 == "USDJPY" and s.instrument2 == "US500")]

        if not recent_statuses:
            return False

        # All recent checks must be healthy or warning (not critical/broken)
        return all(s.health in [CorrelationHealth.HEALTHY, CorrelationHealth.WARNING]
                  for s in recent_statuses)

    def get_correlation_report(self) -> Dict:
        """Generate correlation health report"""
        if not self.correlation_history:
            return {"status": "NO_DATA"}

        recent = self.correlation_history[-20:]  # Last 20 checks

        report = {
            "timestamp": datetime.now(timezone.utc),
            "overall_health": "HEALTHY",
            "pairs": {}
        }

        # Group by pair
        pairs = set((s.instrument1, s.instrument2) for s in recent)

        for pair in pairs:
            pair_statuses = [s for s in recent
                           if (s.instrument1, s.instrument2) == pair or
                              (s.instrument2, s.instrument1) == pair]

            if pair_statuses:
                latest = pair_statuses[-1]
                avg_corr = np.mean([s.correlation for s in pair_statuses])
                avg_vol = np.mean([s.volatility for s in pair_statuses])

                report["pairs"][f"{pair[0]}/{pair[1]}"] = {
                    "current_correlation": latest.correlation,
                    "avg_correlation": avg_corr,
                    "avg_volatility": avg_vol,
                    "health": latest.health.value
                }

                # Update overall health if any pair is critical
                if latest.health in [CorrelationHealth.CRITICAL, CorrelationHealth.BROKEN]:
                    report["overall_health"] = "CRITICAL"
                elif latest.health == CorrelationHealth.WARNING and report["overall_health"] == "HEALTHY":
                    report["overall_health"] = "WARNING"

        return report
