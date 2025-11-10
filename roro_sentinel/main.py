"""
RORO SENTINEL CFD TRADING SYSTEM - Main Entry Point
High-frequency regime detection and divergence trading system
"""

import asyncio
import logging
import yaml
import sys
from datetime import datetime
from pathlib import Path

# Import compliance module first
sys.path.insert(0, str(Path(__file__).parent.parent))
from roro_sentinel import compliance

# Core modules
from roro_sentinel.core.regime_engine import RegimeEngine
from roro_sentinel.core.divergence_detector import DivergenceEngine
from roro_sentinel.core.correlation_monitor import CorrelationMonitor
from roro_sentinel.core.signal_generator import SignalGenerator
from roro_sentinel.core.session_manager import SessionManager

# Data modules
from roro_sentinel.data.data_feed import create_data_feed
from roro_sentinel.data.broker_api import create_broker_api
from roro_sentinel.data.historical_store import HistoricalStore, TradeHistoryStore

# Risk modules
from roro_sentinel.risk.position_sizer import CFDRiskCalculator
from roro_sentinel.risk.cfd_cost_monitor import CFDCostMonitor
from roro_sentinel.risk.liquidation_guard import LiquidationGuard

# Execution modules
from roro_sentinel.execution.alert_publisher import AlertPublisher
from roro_sentinel.execution.trade_validator import TradeValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class ROROSentinel:
    """Main trading system orchestrator"""

    def __init__(self, config_path: str = "roro_sentinel/config/settings.yaml"):
        self.config = self._load_config(config_path)
        self.running = False

        # Initialize components
        logger.info("Initializing RORO Sentinel components...")

        # Data layer
        self.data_feed = create_data_feed(self.config)
        self.broker_api = create_broker_api(self.config)
        self.historical_store = HistoricalStore()
        self.trade_history = TradeHistoryStore()

        # Core engine
        self.regime_engine = RegimeEngine(self.config, self.data_feed)
        self.divergence_engine = DivergenceEngine(self.config, self.data_feed)
        self.correlation_monitor = CorrelationMonitor(self.config, self.data_feed)
        self.signal_generator = SignalGenerator(
            self.config,
            self.regime_engine,
            self.divergence_engine,
            self.correlation_monitor,
            self.data_feed
        )

        # Session management
        self.session_manager = SessionManager(self.config)

        # Risk management
        self.position_sizer = CFDRiskCalculator(self.config)
        self.cost_monitor = CFDCostMonitor(self.config)
        self.liquidation_guard = LiquidationGuard(self.config, self.broker_api)

        # Execution
        self.alert_publisher = AlertPublisher(self.config)
        self.trade_validator = TradeValidator(self.config, self.alert_publisher)

        logger.info("✓ All components initialized successfully")

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Configuration loaded from {config_path}")
                return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            sys.exit(1)

    async def start(self):
        """Start the trading system"""
        # Display compliance warning
        compliance.display_compliance_warning()

        # Require acknowledgment
        if not compliance.require_acknowledgment():
            logger.info("User did not acknowledge. Exiting.")
            return

        logger.info("="*80)
        logger.info("RORO SENTINEL STARTING")
        logger.info(f"Mode: {self.config['system']['mode']}")
        logger.info(f"Data refresh rate: {self.config['system']['data_refresh_rate_ms']}ms")
        logger.info("="*80)

        self.running = True

        # Start main loop
        await self._main_loop()

    async def _main_loop(self):
        """Main trading loop"""
        iteration = 0

        try:
            while self.running:
                iteration += 1
                logger.info(f"\n{'='*80}")
                logger.info(f"ITERATION {iteration} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
                logger.info(f"{'='*80}")

                # 1. CHECK SESSION
                session_info = self.session_manager.get_session_info()
                logger.info(f"Session: {session_info['current_session']} - {session_info['description']}")

                # 2. CHECK MARGIN SAFETY
                margin_status = await self.liquidation_guard.check_margin_safety()
                if margin_status.level.value in ['danger', 'critical']:
                    logger.critical(f"MARGIN EMERGENCY: {margin_status.message}")
                    # Emergency position closure would go here
                    continue

                # 3. CHECK IF POSITION CLOSURE IS REQUIRED
                if self.session_manager.is_position_closure_required():
                    logger.warning("Position closure required - end of session")
                    # Close positions logic would go here
                    await asyncio.sleep(60)
                    continue

                # 4. GENERATE SIGNAL
                signal = await self.signal_generator.generate_signal(
                    current_session=session_info['current_session']
                )

                logger.info(f"Signal: {signal.signal_type.value} | "
                          f"Priority: {signal.priority.value} | "
                          f"Confidence: {signal.confidence:.1%}")
                logger.info(f"Reasoning: {signal.reasoning}")

                # 5. PROCESS SIGNAL
                if signal.signal_type.value != "no_trade":
                    await self._process_signal(signal)

                # 6. MONITOR EXISTING POSITIONS
                await self._monitor_positions()

                # 7. PUBLISH STATUS UPDATE
                await self._publish_status_update(signal, session_info, margin_status)

                # Wait for next iteration
                await asyncio.sleep(self.config['system']['data_refresh_rate_ms'] / 1000)

        except KeyboardInterrupt:
            logger.info("\nShutdown requested by user")
        except Exception as e:
            logger.error(f"Fatal error in main loop: {e}", exc_info=True)
        finally:
            await self._shutdown()

    async def _process_signal(self, signal):
        """Process a trading signal"""
        logger.info(f"\n{'='*60}")
        logger.info("PROCESSING TRADE SIGNAL")
        logger.info(f"{'='*60}")

        # 1. CHECK IF NEW POSITIONS ALLOWED
        if not self.session_manager.should_allow_new_positions():
            logger.warning("New positions not allowed in current session")
            return

        # 2. CHECK MARGIN SAFETY
        if not await self.liquidation_guard.should_allow_new_position():
            logger.warning("New positions blocked due to margin constraints")
            return

        # 3. REQUEST CONFIRMATION
        confirmation = await self.trade_validator.request_confirmation(signal)

        if not confirmation.confirmed:
            logger.info(f"Trade NOT confirmed: {confirmation.reason}")
            return

        logger.info("✓ Trade CONFIRMED")

        # 4. CALCULATE POSITION SIZE
        account = await self.broker_api.get_account_summary()
        position_result = self.position_sizer.calculate_position_size(
            account_equity=account.equity,
            instrument=signal.instrument,
            entry_price=signal.suggested_entry,
            stop_loss_price=signal.suggested_stop,
            signal_confidence=signal.confidence,
            regime_score=signal.regime.score,
            position_size_multiplier=signal.position_size_multiplier
        )

        logger.info(f"Position size: {position_result.position_size:.2f} contracts")
        logger.info(f"Risk amount: ${position_result.risk_amount:.2f}")
        logger.info(f"Margin required: ${position_result.margin_required:.2f}")
        logger.info(f"Reasoning: {position_result.reasoning}")

        # 5. EXECUTE TRADE (in paper mode, just log)
        logger.info("\n[TRADE EXECUTION]")
        logger.info(f"  {signal.signal_type.value.upper()} {signal.instrument}")
        logger.info(f"  Entry: {signal.suggested_entry:.2f}")
        logger.info(f"  Stop: {signal.suggested_stop:.2f}")
        logger.info(f"  Target: {signal.suggested_target:.2f}")
        logger.info(f"  Size: {position_result.position_size:.2f}")

        # In production, would place actual order here
        # order = await self.broker_api.place_order(...)

    async def _monitor_positions(self):
        """Monitor existing positions"""
        positions = await self.broker_api.get_positions()

        if not positions:
            return

        logger.info(f"\n[POSITIONS: {len(positions)}]")
        for pos in positions:
            logger.info(f"  {pos.symbol}: {pos.quantity:.2f} @ {pos.entry_price:.2f} "
                       f"| PnL: ${pos.unrealized_pnl:.2f}")

            # Calculate costs
            quote = await self.data_feed.get_quote(pos.symbol)
            costs = await self.cost_monitor.calculate_position_costs(pos, quote)
            if costs.total_cost_daily < -5:  # More than $5/day cost
                logger.warning(f"  ⚠️ High daily cost: ${abs(costs.total_cost_daily):.2f}")

    async def _publish_status_update(self, signal, session_info, margin_status):
        """Publish periodic status update"""
        # Only publish every 5 iterations (5 minutes if 1-min refresh)
        if hasattr(self, '_iteration_count'):
            self._iteration_count += 1
        else:
            self._iteration_count = 1

        if self._iteration_count % 5 == 0:
            status_data = {
                "session": session_info['current_session'],
                "regime": signal.regime.regime_type.value,
                "regime_score": f"{signal.regime.score:.2f}",
                "correlation": f"{signal.regime.correlation_health:.2f}",
                "vix": f"{signal.regime.vix_level:.1f}",
                "margin_ratio": f"{margin_status.margin_ratio:.2f}",
                "signal": signal.signal_type.value
            }
            alert = self.alert_publisher.format_p3_status(status_data)
            await self.alert_publisher.publish(alert)

    async def _shutdown(self):
        """Graceful shutdown"""
        logger.info("\n" + "="*80)
        logger.info("SHUTTING DOWN RORO SENTINEL")
        logger.info("="*80)

        self.running = False

        # Close any open positions if configured
        # Generate final reports
        # Save state

        logger.info("✓ Shutdown complete")


async def main():
    """Entry point"""
    sentinel = ROROSentinel()
    await sentinel.start()


if __name__ == "__main__":
    asyncio.run(main())
