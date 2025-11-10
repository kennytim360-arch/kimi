"""
Trading Session Manager
Dynamic parameter adjustment based on market session
"""

from enum import Enum
from datetime import datetime, time
from typing import Dict
from copy import deepcopy
import logging
import yaml

logger = logging.getLogger(__name__)


class TradingSession(Enum):
    ASIAN = "ASIAN"  # 00:00-08:00 GMT
    EUROPEAN = "EUROPEAN"  # 08:00-13:00 GMT
    US_OVERLAP = "US_OVERLAP"  # 13:00-16:00 GMT
    US_ONLY = "US_ONLY"  # 16:00-21:00 GMT
    CLOSED = "CLOSED"  # 21:00-00:00 GMT


class SessionManager:
    """Dynamic parameter adjustment based on session"""

    def __init__(self, config: Dict):
        self.config = config
        self.session_rules = self._load_session_rules()
        self.current_session = None

    def _load_session_rules(self) -> Dict:
        """Load session-specific rules from config"""
        try:
            with open('roro_sentinel/config/session_rules.yaml', 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Could not load session_rules.yaml: {e}")
            return {'sessions': {}}

    def get_current_session(self) -> TradingSession:
        """Determine current trading session based on GMT time"""
        now = datetime.now(datetime.UTC).time()

        # Define session boundaries
        if time(0, 0) <= now < time(8, 0):
            session = TradingSession.ASIAN
        elif time(8, 0) <= now < time(13, 0):
            session = TradingSession.EUROPEAN
        elif time(13, 0) <= now < time(16, 0):
            session = TradingSession.US_OVERLAP
        elif time(16, 0) <= now < time(21, 0):
            session = TradingSession.US_ONLY
        else:  # 21:00-00:00
            session = TradingSession.CLOSED

        # Log session changes
        if self.current_session != session:
            logger.info(f"Session changed: {self.current_session} -> {session.value}")
            self.current_session = session

        return session

    def get_active_config(self) -> Dict:
        """Return session-modified configuration"""
        session = self.get_current_session()
        base_config = deepcopy(self.config)

        # Get session-specific rules
        session_config = self.session_rules.get('sessions', {}).get(session.value, {})

        if not session_config:
            logger.warning(f"No session config found for {session.value}")
            return base_config

        # Apply session adjustments
        if session == TradingSession.ASIAN:
            # Reduce thresholds by 40%
            base_config['regime']['base_threshold_percent'] *= \
                session_config.get('threshold_multiplier', 0.6)

            # Increase USDJPY weight
            for gauge in base_config['instruments']['primary_gauges']:
                if gauge['symbol'] == 'USDJPY':
                    gauge['weight'] = session_config.get('usdjpy_weight', 0.35)

            # Max 50% position size
            base_config['risk']['max_per_trade_risk_percent'] *= \
                session_config.get('max_position_size_multiplier', 0.5)

        elif session == TradingSession.EUROPEAN:
            # Moderate adjustments
            base_config['regime']['base_threshold_percent'] *= \
                session_config.get('threshold_multiplier', 0.85)
            base_config['risk']['max_per_trade_risk_percent'] *= \
                session_config.get('max_position_size_multiplier', 0.75)

        elif session == TradingSession.US_OVERLAP:
            # Full power - optimal trading window
            # No changes needed, but apply multiplier for consistency
            threshold_mult = session_config.get('threshold_multiplier', 1.0)
            base_config['regime']['base_threshold_percent'] *= threshold_mult

        elif session == TradingSession.US_ONLY:
            # Late US session - slightly reduced
            base_config['regime']['base_threshold_percent'] *= \
                session_config.get('threshold_multiplier', 0.9)
            base_config['risk']['max_per_trade_risk_percent'] *= \
                session_config.get('max_position_size_multiplier', 0.8)

            # Increase VIX weight for late session volatility
            for gauge in base_config['instruments']['primary_gauges']:
                if gauge['symbol'] == 'VIX':
                    gauge['weight'] = session_config.get('vix_weight', 0.30)

        elif session == TradingSession.CLOSED:
            # No new positions
            base_config['risk']['max_per_trade_risk_percent'] = 0.0
            logger.info("CLOSED session - no new positions allowed")

        return base_config

    def is_position_closure_required(self) -> bool:
        """US late session: Must close positions by 20:55 GMT"""
        current_time = datetime.now(datetime.UTC).time()
        session = self.get_current_session()

        # Force close before low liquidity period
        if session == TradingSession.US_ONLY and current_time >= time(20, 55):
            return True

        # Force close during CLOSED session
        if session == TradingSession.CLOSED:
            return True

        return False

    def should_allow_new_positions(self) -> bool:
        """Check if new positions should be allowed"""
        session = self.get_current_session()

        # Don't allow new positions during CLOSED session
        if session == TradingSession.CLOSED:
            return False

        # Don't allow new positions in last 5 minutes of US session
        if self.is_position_closure_required():
            return False

        return True

    def get_session_info(self) -> Dict:
        """Get current session information"""
        session = self.get_current_session()
        session_config = self.session_rules.get('sessions', {}).get(session.value, {})

        return {
            "current_session": session.value,
            "hours": session_config.get('hours', 'Unknown'),
            "description": session_config.get('description', ''),
            "threshold_multiplier": session_config.get('threshold_multiplier', 1.0),
            "max_position_size_multiplier": session_config.get('max_position_size_multiplier', 1.0),
            "allow_new_positions": self.should_allow_new_positions(),
            "closure_required": self.is_position_closure_required(),
            "current_time_gmt": datetime.now(datetime.UTC).strftime('%H:%M:%S')
        }

    def is_holiday(self, date: datetime = None) -> bool:
        """Check if current date is a holiday"""
        if date is None:
            date = datetime.now(datetime.UTC)

        holidays = self.session_rules.get('holidays', [])

        for holiday in holidays:
            holiday_date = holiday.get('date', '')
            if holiday_date == date.strftime('%Y-%m-%d'):
                logger.info(f"Holiday detected: {holiday.get('description', '')}")
                return True

        return False

    def get_session_multipliers(self) -> Dict[str, float]:
        """Get all multipliers for current session"""
        session = self.get_current_session()
        session_config = self.session_rules.get('sessions', {}).get(session.value, {})

        return {
            'threshold': session_config.get('threshold_multiplier', 1.0),
            'position_size': session_config.get('max_position_size_multiplier', 1.0),
            'usdjpy_weight': session_config.get('usdjpy_weight', None),
            'vix_weight': session_config.get('vix_weight', None),
            'dax_weight': session_config.get('dax_weight', None)
        }
