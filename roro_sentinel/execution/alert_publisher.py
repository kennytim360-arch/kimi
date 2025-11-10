"""
Alert System with Severity Levels
Publishes alerts to multiple channels (Discord, Telegram, Webhooks)
"""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from enum import Enum
import logging
import asyncio
import json
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    P0_CRITICAL = "P0"  # Immediate action required, forced close
    P1_HIGH = "P1"      # Entry/exit signal with 5-min confirmation
    P2_MEDIUM = "P2"    # Watchlist, monitor only
    P3_LOW = "P3"       # FYI/status update


@dataclass
class AlertMessage:
    """Alert message structure"""
    severity: AlertSeverity
    header: str
    body: Dict
    requires_acknowledgment: bool = False
    timeout_seconds: int = 300
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

    def format_for_channel(self) -> str:
        """Format message for display"""
        lines = [
            f"{'='*60}",
            f"[{self.severity.value}] {self.header}",
            f"Time: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"{'='*60}",
        ]

        for key, value in self.body.items():
            lines.append(f"{key}: {value}")

        if self.requires_acknowledgment:
            lines.append(f"\n⚠️ CONFIRMATION REQUIRED within {self.timeout_seconds}s")

        lines.append(f"{'='*60}")
        return "\n".join(lines)


class AlertChannel(ABC):
    """Abstract base class for alert channels"""

    def __init__(self, config: Dict):
        self.config = config
        self.name = "BaseChannel"

    @abstractmethod
    async def send(self, message: str) -> bool:
        """Send message to channel"""
        pass


class ConsoleChannel(AlertChannel):
    """Console/stdout alert channel"""

    def __init__(self, config: Dict):
        super().__init__(config)
        self.name = "Console"

    async def send(self, message: str) -> bool:
        """Print to console"""
        print(f"\n{message}\n")
        return True


class DiscordChannel(AlertChannel):
    """Discord webhook alert channel"""

    def __init__(self, config: Dict):
        super().__init__(config)
        self.name = "Discord"
        self.webhook_url = config.get('webhook_url', '')

    async def send(self, message: str) -> bool:
        """Send to Discord via webhook"""
        if not self.webhook_url or '${' in self.webhook_url:
            logger.warning("Discord webhook not configured")
            return False

        try:
            # In production, would use aiohttp to send webhook
            # For now, just log
            logger.info(f"[Discord] {message}")
            return True
        except Exception as e:
            logger.error(f"Discord send failed: {e}")
            return False


class TelegramChannel(AlertChannel):
    """Telegram bot alert channel"""

    def __init__(self, config: Dict):
        super().__init__(config)
        self.name = "Telegram"
        self.bot_token = config.get('bot_token', '')
        self.chat_id = config.get('chat_id', '')

    async def send(self, message: str) -> bool:
        """Send to Telegram"""
        if not self.bot_token or '${' in self.bot_token:
            logger.warning("Telegram bot not configured")
            return False

        try:
            # In production, would use Telegram Bot API
            # For now, just log
            logger.info(f"[Telegram] {message}")
            return True
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False


class WebhookChannel(AlertChannel):
    """Generic webhook alert channel"""

    def __init__(self, config: Dict):
        super().__init__(config)
        self.name = "Webhook"
        self.url = config.get('url', '')

    async def send(self, message: str) -> bool:
        """Send to webhook"""
        if not self.url or '${' in self.url:
            logger.warning("Webhook not configured")
            return False

        try:
            # In production, would use aiohttp to POST
            # For now, just log
            logger.info(f"[Webhook] {message}")
            return True
        except Exception as e:
            logger.error(f"Webhook send failed: {e}")
            return False


class AlertPublisher:
    """Main alert publishing system"""

    def __init__(self, config: Dict):
        self.config = config
        self.channels = self._initialize_channels()
        self.alert_history: List[AlertMessage] = []
        self.p0_alert_times: List[datetime] = []

    def _initialize_channels(self) -> List[AlertChannel]:
        """Initialize alert channels from config"""
        channels = [ConsoleChannel({})]  # Always include console

        alert_config = self.config.get('execution', {}).get('alert_channels', [])

        for channel_config in alert_config:
            channel_type = channel_config.get('type', '')

            if channel_type == 'discord':
                channels.append(DiscordChannel(channel_config))
            elif channel_type == 'telegram':
                channels.append(TelegramChannel(channel_config))
            elif channel_type == 'webhook':
                channels.append(WebhookChannel(channel_config))

        logger.info(f"Initialized {len(channels)} alert channels")
        return channels

    async def publish(self, alert: AlertMessage):
        """Publish alert to all applicable channels"""

        # Rate limiting: Max 3 P0 alerts per 15 minutes
        if alert.severity == AlertSeverity.P0_CRITICAL:
            if self._p0_alert_count_in_last_15min() >= 3:
                logger.warning("P0 alert rate limit reached. Queueing alert.")
                await asyncio.sleep(300)  # Wait 5 minutes

            self.p0_alert_times.append(datetime.now(timezone.utc))

        # Format message
        formatted_message = alert.format_for_channel()

        # Send to all channels
        for channel in self.channels:
            # Check if channel should receive this severity
            if self._should_send_to_channel(channel, alert.severity):
                try:
                    await channel.send(formatted_message)
                except Exception as e:
                    logger.error(f"Channel {channel.name} failed: {e}")

        # Store in history
        self.alert_history.append(alert)
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]

    def _should_send_to_channel(self, channel: AlertChannel,
                               severity: AlertSeverity) -> bool:
        """Check if severity level should be sent to channel"""
        # Console gets everything
        if channel.name == "Console":
            return True

        # Check config for channel's severity levels
        alert_config = self.config.get('execution', {}).get('alert_channels', [])
        for ch_config in alert_config:
            if ch_config.get('type', '').lower() in channel.name.lower():
                severity_levels = ch_config.get('severity_levels', [])
                return severity.value in severity_levels

        return False

    def _p0_alert_count_in_last_15min(self) -> int:
        """Count P0 alerts in last 15 minutes"""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
        self.p0_alert_times = [t for t in self.p0_alert_times if t > cutoff]
        return len(self.p0_alert_times)

    def format_p0_regime_shift(self, old_regime: str, new_regime: str,
                              triggers: Dict) -> AlertMessage:
        """Format P0 regime shift alert"""
        return AlertMessage(
            severity=AlertSeverity.P0_CRITICAL,
            header="🚨 REGIME SHIFT - IMMEDIATE ACTION",
            body={
                "old_regime": old_regime,
                "new_regime": new_regime,
                "triggers": json.dumps(triggers, indent=2),
                "action": "CLOSE ALL RISK POSITIONS IMMEDIATELY",
                "correlation_health": triggers.get('correlation', 'N/A')
            },
            requires_acknowledgment=True
        )

    def format_p1_divergence(self, signal) -> AlertMessage:
        """Format P1 divergence alert"""
        return AlertMessage(
            severity=AlertSeverity.P1_HIGH,
            header=f"⚠️ {signal.divergence.type.value.upper()} DIVERGENCE",
            body={
                "instrument": signal.instrument,
                "confidence": f"{signal.confidence:.1%}",
                "entry": f"{signal.suggested_entry:.2f}",
                "stop": f"{signal.suggested_stop:.2f}",
                "target": f"{signal.suggested_target:.2f}",
                "position_size": f"{signal.position_size_multiplier:.1%}",
                "time_window": "30-60 minutes expected",
                "manual_confirmation": "REQUIRED - Reply 'CONFIRM' to execute"
            },
            requires_acknowledgment=True,
            timeout_seconds=300  # 5 minute confirmation window
        )

    def format_p2_regime_signal(self, signal) -> AlertMessage:
        """Format P2 regime-based signal"""
        return AlertMessage(
            severity=AlertSeverity.P2_MEDIUM,
            header=f"📊 {signal.signal_type.value.upper()} Signal - Regime Based",
            body={
                "instrument": signal.instrument,
                "regime": signal.regime.regime_type.value,
                "confidence": f"{signal.confidence:.1%}",
                "entry": f"{signal.suggested_entry:.2f}",
                "stop": f"{signal.suggested_stop:.2f}",
                "target": f"{signal.suggested_target:.2f}",
                "reasoning": signal.reasoning
            },
            requires_acknowledgment=True,
            timeout_seconds=180
        )

    def format_p3_status(self, status_data: Dict) -> AlertMessage:
        """Format P3 status update"""
        return AlertMessage(
            severity=AlertSeverity.P3_LOW,
            header="ℹ️ System Status Update",
            body=status_data,
            requires_acknowledgment=False
        )
