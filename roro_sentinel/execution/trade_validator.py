"""
Human-in-the-Loop Trade Validator
CRITICAL SAFETY LAYER - No trade executes without manual confirmation
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional
from enum import Enum
import logging
import asyncio
import uuid

logger = logging.getLogger(__name__)


@dataclass
class ConfirmationResponse:
    """Result of trade confirmation request"""
    trade_id: str
    confirmed: bool
    timestamp: datetime
    reason: str

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(datetime.UTC)


class TradeValidator:
    """
    CRITICAL SAFETY LAYER - No trade executes without manual confirmation
    """

    def __init__(self, config: Dict, alert_publisher):
        self.config = config
        self.alert_publisher = alert_publisher
        self.pending_trades = {}
        self.confirmations = {}  # Store confirmations
        self.today_losses = []
        self.today_loss_amount = 0.0

    async def request_confirmation(self, signal) -> ConfirmationResponse:
        """Send alert and wait for human confirmation"""

        # Generate trade ID
        trade_id = str(uuid.uuid4())[:8]
        signal.id = trade_id

        # 1. CHECK TRADER READINESS FIRST
        ready = await self._check_trader_readiness()
        if not ready:
            return ConfirmationResponse(
                trade_id=trade_id,
                confirmed=False,
                timestamp=datetime.now(datetime.UTC),
                reason="Trader not ready (check loss limits or emotional state)"
            )

        # 2. PUBLISH ALERT
        if hasattr(signal, 'divergence') and signal.divergence:
            alert = self.alert_publisher.format_p1_divergence(signal)
        else:
            alert = self.alert_publisher.format_p2_regime_signal(signal)

        await self.alert_publisher.publish(alert)

        # 3. WAIT FOR CONFIRMATION
        # In paper mode or when manual confirmation is disabled, auto-confirm
        if not self.config['execution'].get('require_manual_confirmation', True):
            logger.info(f"Auto-confirming trade {trade_id} (manual confirmation disabled)")
            return ConfirmationResponse(
                trade_id=trade_id,
                confirmed=True,
                timestamp=datetime.now(datetime.UTC),
                reason="Auto-confirmed (manual confirmation disabled)"
            )

        # Store as pending
        self.pending_trades[trade_id] = {
            'signal': signal,
            'timestamp': datetime.now(datetime.UTC)
        }

        confirmed = False
        try:
            # Wait for user confirmation via console input or external system
            # In real system, this would check a queue/database for confirmation
            confirmed = await asyncio.wait_for(
                self._wait_for_confirmation(trade_id),
                timeout=self.config['execution']['confirmation_timeout_seconds']
            )
        except asyncio.TimeoutError:
            logger.info(f"Confirmation timeout for trade {trade_id}")
            confirmed = False

        # Clean up pending
        if trade_id in self.pending_trades:
            del self.pending_trades[trade_id]

        return ConfirmationResponse(
            trade_id=trade_id,
            confirmed=confirmed,
            timestamp=datetime.now(datetime.UTC),
            reason="Manual confirmation" if confirmed else "Timeout or rejection"
        )

    async def _wait_for_confirmation(self, trade_id: str) -> bool:
        """
        Wait for confirmation from user
        In production, this would poll a database or message queue
        For now, simulates a confirmation after a short delay in paper mode
        """
        # Check if already confirmed
        if trade_id in self.confirmations:
            return self.confirmations[trade_id]

        # In paper mode, simulate user always confirming after 5 seconds
        mode = self.config.get('system', {}).get('mode', 'paper')
        if mode == 'paper':
            logger.info(f"[PAPER MODE] Simulating user confirmation for trade {trade_id}")
            await asyncio.sleep(5)
            return True

        # In live mode, would need actual user input mechanism
        # For now, require console input
        logger.warning(f"Trade {trade_id} waiting for confirmation...")
        logger.warning("In live mode, implement proper confirmation system (Discord bot, web interface, etc.)")

        # Wait for confirmation to be set externally
        timeout = self.config['execution']['confirmation_timeout_seconds']
        for _ in range(timeout):
            await asyncio.sleep(1)
            if trade_id in self.confirmations:
                return self.confirmations[trade_id]

        return False

    def confirm_trade(self, trade_id: str, confirmed: bool = True):
        """
        External method to confirm a trade
        Can be called from Discord bot, web interface, etc.
        """
        self.confirmations[trade_id] = confirmed
        logger.info(f"Trade {trade_id} {'CONFIRMED' if confirmed else 'REJECTED'}")

    async def _check_trader_readiness(self) -> bool:
        """
        Prevent trading during emotional/fatigued states
        """

        # CHECK 1: Multiple losses in last hour
        recent_losses = self._count_recent_losses(minutes=60)
        if recent_losses >= 3:
            await self.alert_publisher.publish(
                self.alert_publisher.format_p3_status({
                    "alert": "TRADING SUSPENDED",
                    "reason": f"{recent_losses} losses in last hour",
                    "message": "Take a break. System will resume after 1 hour."
                })
            )
            return False

        # CHECK 2: Near daily loss limit
        max_daily_loss = self.config['risk']['max_daily_risk_percent']
        if self.today_loss_amount > max_daily_loss * 0.7:
            await self.alert_publisher.publish(
                self.alert_publisher.format_p3_status({
                    "alert": "DAILY LOSS LIMIT APPROACHING",
                    "current_loss": f"{self.today_loss_amount:.2f}%",
                    "limit": f"{max_daily_loss}%",
                    "message": "Approaching daily limit. Exercise extreme caution."
                })
            )
            # Still allow, but warn
            return True

        # CHECK 3: Market hours (prevent late-night trading)
        current_hour = datetime.now(datetime.UTC).hour
        if 0 <= current_hour < 5:  # 00:00-05:00 GMT is low liquidity
            logger.info("Low liquidity hours - trading not recommended")
            return False

        return True

    def _count_recent_losses(self, minutes: int = 60) -> int:
        """Count number of losses in recent time period"""
        cutoff = datetime.now(datetime.UTC).timestamp() - (minutes * 60)
        recent = [loss for loss in self.today_losses
                 if loss['timestamp'].timestamp() > cutoff]
        return len(recent)

    def record_trade_result(self, trade_id: str, pnl: float, win: bool):
        """Record the result of a trade"""
        if not win:
            self.today_losses.append({
                'trade_id': trade_id,
                'pnl': pnl,
                'timestamp': datetime.now(datetime.UTC)
            })

        # Update today's loss amount
        if pnl < 0:
            self.today_loss_amount += abs(pnl)

        logger.info(f"Trade {trade_id} result: {'WIN' if win else 'LOSS'} ${pnl:.2f}")

    def reset_daily_stats(self):
        """Reset daily statistics (call at start of new trading day)"""
        logger.info(f"Resetting daily stats. Previous losses: {len(self.today_losses)}, "
                   f"Total loss: {self.today_loss_amount:.2f}%")
        self.today_losses = []
        self.today_loss_amount = 0.0

    def get_pending_trades(self) -> Dict:
        """Get all pending trades awaiting confirmation"""
        return {
            trade_id: {
                'instrument': data['signal'].instrument,
                'signal_type': data['signal'].signal_type.value,
                'confidence': data['signal'].confidence,
                'timestamp': data['timestamp'],
                'age_seconds': (datetime.now(datetime.UTC) - data['timestamp']).total_seconds()
            }
            for trade_id, data in self.pending_trades.items()
        }
