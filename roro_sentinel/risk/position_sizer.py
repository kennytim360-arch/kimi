"""
CFD Position Sizing with Leverage Awareness
Calculates appropriate position sizes based on risk parameters
"""

from dataclasses import dataclass
from typing import Dict
import logging

logger = logging.getLogger(__name__)


@dataclass
class PositionSizingResult:
    """Result of position sizing calculation"""
    risk_amount: float  # Dollar amount at risk
    position_size: float  # Number of contracts/shares
    margin_required: float  # Margin needed
    swap_cost: float  # Estimated overnight cost
    leverage_used: float  # Actual leverage
    reasoning: str


class CFDRiskCalculator:
    """
    Leverage-aware position sizing with swap cost projection
    """

    def __init__(self, config: Dict):
        self.config = config
        self.active_divergences = set()
        self.today_risk_used = 0.0

    def calculate_position_size(self,
                               account_equity: float,
                               instrument: str,
                               entry_price: float,
                               stop_loss_price: float,
                               signal_confidence: float,
                               regime_score: float,
                               position_size_multiplier: float = 1.0) -> PositionSizingResult:
        """
        Calculate appropriate position size considering all risk factors
        """

        # 1. BASE RISK AMOUNT
        max_risk_pct = self.config['risk']['max_per_trade_risk_percent'] / 100
        base_risk = account_equity * max_risk_pct

        reasoning = []

        # 2. SIGNAL CONFIDENCE ADJUSTMENT
        if signal_confidence < 0.65:
            base_risk *= 0.5
            reasoning.append(f"Low confidence ({signal_confidence:.1%}): 50% size")

        # 3. REGIME ADJUSTMENT
        regime_adjustment = min(1.0, abs(regime_score) / 2.0)
        if regime_adjustment < 1.0:
            base_risk *= regime_adjustment
            reasoning.append(f"Regime adjustment: {regime_adjustment:.1%}")

        # 4. POSITION SIZE MULTIPLIER (from signal)
        base_risk *= position_size_multiplier
        if position_size_multiplier < 1.0:
            reasoning.append(f"Signal multiplier: {position_size_multiplier:.1%}")

        # 5. DIVERGENCE PENALTY (if applicable)
        if instrument in self.active_divergences:
            base_risk *= self.config['risk']['divergence_penalty']
            reasoning.append(f"Divergence penalty: {self.config['risk']['divergence_penalty']:.1%}")

        # 6. CALCULATE POSITION SIZE
        stop_distance = abs(entry_price - stop_loss_price)
        if stop_distance == 0:
            logger.error("Stop distance is zero!")
            return self._create_zero_position("Stop distance is zero")

        position_value = base_risk / (stop_distance / entry_price)

        # 7. CFD-SPECIFIC: SWAP COST PROJECTION
        swap_cost = self._project_overnight_cost(instrument, position_value, entry_price)
        if swap_cost < self.config['risk']['swap_cost_threshold']:
            logger.warning(f"Swap cost too high: ${swap_cost:.2f}. Reducing size.")
            base_risk *= 0.7
            position_value *= 0.7
            reasoning.append(f"Swap cost penalty: ${swap_cost:.2f}")

        # 8. LEVERAGE & MARGIN CHECK
        max_leverage = self.config['risk']['max_leverage']
        margin_required = position_value / max_leverage

        if margin_required > account_equity * 0.7:  # Max 70% margin utilization
            logger.warning("Margin limit reached. Reducing size.")
            scaling_factor = (account_equity * 0.7) / margin_required
            base_risk *= scaling_factor
            position_value *= scaling_factor
            margin_required = position_value / max_leverage
            reasoning.append(f"Margin limit: scaled by {scaling_factor:.1%}")

        # 9. DAILY RISK CAP
        max_daily_risk = account_equity * (self.config['risk']['max_daily_risk_percent'] / 100)
        if self.today_risk_used + base_risk > max_daily_risk:
            available_risk = max_daily_risk - self.today_risk_used
            if available_risk <= 0:
                return self._create_zero_position("Daily risk limit reached")

            scaling_factor = available_risk / base_risk
            base_risk = available_risk
            position_value *= scaling_factor
            margin_required = position_value / max_leverage
            reasoning.append(f"Daily risk cap: {available_risk:.2f} remaining")

        # 10. CALCULATE FINAL METRICS
        leverage_used = position_value / margin_required if margin_required > 0 else 0

        # Convert position value to contracts/shares
        # For CFDs, typically 1 contract = value of 1 unit
        position_size = position_value / entry_price

        return PositionSizingResult(
            risk_amount=base_risk,
            position_size=position_size,
            margin_required=margin_required,
            swap_cost=swap_cost,
            leverage_used=leverage_used,
            reasoning=" | ".join(reasoning) if reasoning else "Full size"
        )

    def _project_overnight_cost(self, instrument: str, position_value: float,
                               entry_price: float) -> float:
        """
        Project overnight swap/financing cost
        Simplified calculation - real implementation would use broker's swap rates
        """
        # Typical swap rates (annualized)
        swap_rates = {
            "US500": -0.03,  # -3% per year
            "USDJPY": -0.02,
            "DAX": -0.035,
            "NAS100": -0.03,
        }

        annual_rate = swap_rates.get(instrument, -0.03)
        daily_rate = annual_rate / 365

        # Calculate daily cost
        daily_cost = position_value * daily_rate

        return daily_cost

    def _create_zero_position(self, reason: str) -> PositionSizingResult:
        """Create a zero-sized position result"""
        return PositionSizingResult(
            risk_amount=0.0,
            position_size=0.0,
            margin_required=0.0,
            swap_cost=0.0,
            leverage_used=0.0,
            reasoning=reason
        )

    def update_daily_risk_used(self, risk_amount: float):
        """Update the amount of risk used today"""
        self.today_risk_used += risk_amount
        logger.info(f"Daily risk used: ${self.today_risk_used:.2f}")

    def reset_daily_risk(self):
        """Reset daily risk counter (call at start of new trading day)"""
        logger.info(f"Resetting daily risk. Previous: ${self.today_risk_used:.2f}")
        self.today_risk_used = 0.0

    def add_divergence_instrument(self, instrument: str):
        """Mark an instrument as having an active divergence"""
        self.active_divergences.add(instrument)
        logger.info(f"Divergence marked for {instrument}")

    def remove_divergence_instrument(self, instrument: str):
        """Remove divergence marker"""
        if instrument in self.active_divergences:
            self.active_divergences.remove(instrument)
            logger.info(f"Divergence cleared for {instrument}")
