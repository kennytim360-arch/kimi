"""
Liquidation Guard
Monitors margin levels and prevents liquidation/margin calls
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MarginLevel(Enum):
    SAFE = "safe"
    MONITOR = "monitor"
    WARNING = "warning"
    DANGER = "danger"
    CRITICAL = "critical"


@dataclass
class MarginStatus:
    """Current margin status"""
    level: MarginLevel
    margin_ratio: float  # Equity / Margin Used
    equity: float
    margin_used: float
    maintenance_margin: float
    max_adverse_move_percent: float  # How far market can move before margin call
    action_required: str
    message: str
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class LiquidationGuard:
    """Monitors margin level and prevents liquidation"""

    def __init__(self, config: Dict, broker_api):
        self.config = config
        self.broker_api = broker_api
        self.margin_history: List[MarginStatus] = []

    async def check_margin_safety(self) -> MarginStatus:
        """
        Check current margin safety level
        Returns MarginStatus with recommended actions
        """

        # Get account summary from broker
        account = await self.broker_api.get_account_summary()

        equity = account.equity
        margin_used = account.margin_used
        maintenance_margin = account.maintenance_margin

        # Calculate margin ratio (higher is better)
        margin_ratio = equity / margin_used if margin_used > 0 else float('inf')

        # Get all positions to calculate liquidation distance
        positions = await self.broker_api.get_positions()
        max_adverse_move = self._calculate_liquidation_distance(
            positions, equity, margin_used, maintenance_margin
        )

        # Determine margin level and action
        if margin_ratio < 1.25:  # Less than 125%
            status = MarginStatus(
                level=MarginLevel.CRITICAL,
                margin_ratio=margin_ratio,
                equity=equity,
                margin_used=margin_used,
                maintenance_margin=maintenance_margin,
                max_adverse_move_percent=max_adverse_move,
                action_required="LIQUIDATE_NOW",
                message=f"CRITICAL: Margin at {margin_ratio:.2f} - CLOSE ALL POSITIONS IMMEDIATELY"
            )
        elif margin_ratio < 1.5:  # Less than 150%
            status = MarginStatus(
                level=MarginLevel.DANGER,
                margin_ratio=margin_ratio,
                equity=equity,
                margin_used=margin_used,
                maintenance_margin=maintenance_margin,
                max_adverse_move_percent=max_adverse_move,
                action_required="IMMEDIATE_REDUCTION",
                message=f"DANGER: Margin at {margin_ratio:.2f} - Close 50% of positions NOW"
            )
        elif margin_ratio < 1.75:  # Less than 175%
            status = MarginStatus(
                level=MarginLevel.WARNING,
                margin_ratio=margin_ratio,
                equity=equity,
                margin_used=margin_used,
                maintenance_margin=maintenance_margin,
                max_adverse_move_percent=max_adverse_move,
                action_required="STOP_NEW_ENTRIES",
                message=f"WARNING: Margin at {margin_ratio:.2f} - No new trades, monitor closely"
            )
        elif margin_ratio < 2.5:  # Less than 250%
            status = MarginStatus(
                level=MarginLevel.MONITOR,
                margin_ratio=margin_ratio,
                equity=equity,
                margin_used=margin_used,
                maintenance_margin=maintenance_margin,
                max_adverse_move_percent=max_adverse_move,
                action_required="MONITOR",
                message=f"MONITOR: Margin at {margin_ratio:.2f} - Be cautious with new positions"
            )
        else:
            status = MarginStatus(
                level=MarginLevel.SAFE,
                margin_ratio=margin_ratio,
                equity=equity,
                margin_used=margin_used,
                maintenance_margin=maintenance_margin,
                max_adverse_move_percent=max_adverse_move,
                action_required="NONE",
                message=f"SAFE: Margin at {margin_ratio:.2f} - {max_adverse_move:.2f}% buffer to margin call"
            )

        # Log warnings
        if status.level in [MarginLevel.DANGER, MarginLevel.CRITICAL]:
            logger.critical(status.message)
        elif status.level == MarginLevel.WARNING:
            logger.warning(status.message)

        # Store history
        self.margin_history.append(status)
        if len(self.margin_history) > 1000:
            self.margin_history = self.margin_history[-1000:]

        return status

    def _calculate_liquidation_distance(self, positions: List, equity: float,
                                       margin_used: float, maintenance_margin: float) -> float:
        """
        Calculate how far the market can move adversely before margin call
        Returns percentage move
        """
        if not positions or margin_used == 0:
            return 100.0  # No positions = no liquidation risk

        # Simplified calculation
        # Real implementation would be more complex, considering each position's leverage

        # Margin call occurs when equity falls below maintenance margin
        # equity = initial_equity + unrealized_pnl
        # margin_call when: equity <= maintenance_margin

        buffer = equity - maintenance_margin

        if buffer <= 0:
            return 0.0  # Already at or below margin call level

        # Estimate total position value
        total_position_value = sum(abs(p.quantity * p.current_price) for p in positions)

        if total_position_value == 0:
            return 100.0

        # Percentage move to liquidation = buffer / total_position_value
        adverse_move_pct = (buffer / total_position_value) * 100

        return adverse_move_pct

    async def should_allow_new_position(self) -> bool:
        """Check if new positions should be allowed based on margin"""
        status = await self.check_margin_safety()

        # Don't allow new positions if margin is WARNING or worse
        return status.level in [MarginLevel.SAFE, MarginLevel.MONITOR]

    async def get_positions_to_close(self, target_reduction_pct: float = 0.5) -> List[str]:
        """
        Get list of positions to close to reduce margin usage
        Returns list of instrument symbols
        """
        positions = await self.broker_api.get_positions()

        if not positions:
            return []

        # Sort by unrealized PnL (close losers first, preserve winners)
        sorted_positions = sorted(positions, key=lambda p: p.unrealized_pnl)

        # Calculate how many to close
        target_count = max(1, int(len(sorted_positions) * target_reduction_pct))

        return [p.symbol for p in sorted_positions[:target_count]]

    def get_margin_report(self) -> Dict:
        """Generate margin safety report"""
        if not self.margin_history:
            return {"status": "NO_DATA"}

        recent = self.margin_history[-20:]  # Last 20 checks

        return {
            "timestamp": datetime.utcnow(),
            "current_level": recent[-1].level.value,
            "current_ratio": recent[-1].margin_ratio,
            "equity": recent[-1].equity,
            "margin_used": recent[-1].margin_used,
            "buffer_to_margin_call": recent[-1].max_adverse_move_percent,
            "action_required": recent[-1].action_required,
            "message": recent[-1].message,
            "historical_ratios": [s.margin_ratio for s in recent],
            "min_ratio_last_20": min(s.margin_ratio for s in recent),
            "max_ratio_last_20": max(s.margin_ratio for s in recent)
        }
