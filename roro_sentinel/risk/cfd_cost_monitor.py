"""
CFD Cost Monitor
Tracks swap costs, spreads, and overall position costs
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


@dataclass
class CFDCostSnapshot:
    """Snapshot of CFD costs at a point in time"""
    instrument: str
    position_value: float
    swap_cost_daily: float
    spread_cost: float
    commission: float
    total_cost_daily: float
    timestamp: datetime

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(datetime.UTC)


class CFDCostMonitor:
    """
    Monitors CFD-specific costs: swaps, spreads, commissions
    Helps identify when positions are becoming too expensive to hold
    """

    def __init__(self, config: Dict):
        self.config = config
        self.cost_history: List[CFDCostSnapshot] = []

    async def calculate_position_costs(self, position, current_quote) -> CFDCostSnapshot:
        """
        Calculate all costs associated with a CFD position
        """

        instrument = position.symbol
        position_value = abs(position.quantity * position.current_price)

        # 1. SWAP/FINANCING COST
        swap_cost = self._calculate_swap_cost(instrument, position_value)

        # 2. SPREAD COST (entry cost - already paid, but tracked)
        spread = current_quote.spread if hasattr(current_quote, 'spread') else 0
        spread_cost = spread * abs(position.quantity)

        # 3. COMMISSION (if applicable)
        commission = self._calculate_commission(instrument, position_value)

        # 4. TOTAL DAILY COST
        total_cost = swap_cost + commission

        snapshot = CFDCostSnapshot(
            instrument=instrument,
            position_value=position_value,
            swap_cost_daily=swap_cost,
            spread_cost=spread_cost,
            commission=commission,
            total_cost_daily=total_cost,
            timestamp=datetime.now(datetime.UTC)
        )

        self.cost_history.append(snapshot)

        # Keep only last 1000 snapshots
        if len(self.cost_history) > 1000:
            self.cost_history = self.cost_history[-1000:]

        # Check if costs are excessive
        self._check_cost_warnings(snapshot, position)

        return snapshot

    def _calculate_swap_cost(self, instrument: str, position_value: float) -> float:
        """
        Calculate daily swap/financing cost
        Real implementation would fetch from broker API
        """
        # Typical swap rates (annualized, negative = cost to trader)
        swap_rates = {
            "US500": -0.03,  # -3% per year
            "USDJPY": -0.02,
            "DAX": -0.035,
            "NAS100": -0.03,
            "AUDJPY": -0.025,
            "XAUUSD": -0.04,
            "EURJPY": -0.02,
        }

        annual_rate = swap_rates.get(instrument, -0.03)
        daily_rate = annual_rate / 365

        return position_value * daily_rate

    def _calculate_commission(self, instrument: str, position_value: float) -> float:
        """
        Calculate commission (if applicable)
        Many CFD brokers don't charge commission, but some do
        """
        # Simplified: most CFDs have no commission, costs are in spread
        return 0.0

    def _check_cost_warnings(self, snapshot: CFDCostSnapshot, position):
        """Check if costs are becoming excessive"""

        # WARNING 1: High daily swap cost
        threshold = self.config['risk']['swap_cost_threshold']
        if snapshot.swap_cost_daily < threshold:  # Negative = cost
            logger.warning(
                f"HIGH SWAP COST: {snapshot.instrument} costing "
                f"${abs(snapshot.swap_cost_daily):.2f}/day"
            )

        # WARNING 2: Cost eating into profits
        if hasattr(position, 'unrealized_pnl') and position.unrealized_pnl > 0:
            if abs(snapshot.total_cost_daily) > position.unrealized_pnl * 0.5:
                logger.warning(
                    f"COSTS EATING PROFITS: {snapshot.instrument} daily cost "
                    f"${abs(snapshot.total_cost_daily):.2f} vs PnL ${position.unrealized_pnl:.2f}"
                )

    def get_cost_report(self, instrument: Optional[str] = None) -> Dict:
        """
        Generate cost report for instruments
        """
        if not self.cost_history:
            return {"status": "NO_DATA"}

        recent_snapshots = self.cost_history[-50:]  # Last 50

        if instrument:
            recent_snapshots = [s for s in recent_snapshots if s.instrument == instrument]

        if not recent_snapshots:
            return {"status": "NO_DATA", "instrument": instrument}

        # Group by instrument
        by_instrument = {}
        for snapshot in recent_snapshots:
            inst = snapshot.instrument
            if inst not in by_instrument:
                by_instrument[inst] = []
            by_instrument[inst].append(snapshot)

        report = {
            "timestamp": datetime.now(datetime.UTC),
            "instruments": {}
        }

        for inst, snapshots in by_instrument.items():
            latest = snapshots[-1]
            avg_daily_cost = sum(s.total_cost_daily for s in snapshots) / len(snapshots)

            report["instruments"][inst] = {
                "position_value": latest.position_value,
                "current_daily_cost": latest.total_cost_daily,
                "avg_daily_cost": avg_daily_cost,
                "swap_cost": latest.swap_cost_daily,
                "spread_cost": latest.spread_cost,
                "warning": latest.swap_cost_daily < self.config['risk']['swap_cost_threshold']
            }

        return report

    def get_total_daily_cost(self) -> float:
        """Get total daily cost across all positions"""
        if not self.cost_history:
            return 0.0

        # Get latest snapshot for each instrument
        latest_by_instrument = {}
        for snapshot in reversed(self.cost_history):
            if snapshot.instrument not in latest_by_instrument:
                latest_by_instrument[snapshot.instrument] = snapshot

        return sum(s.total_cost_daily for s in latest_by_instrument.values())
