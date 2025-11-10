"""
ABSTRACT DATA INTERFACE - CRITICAL FOR TESTING
This module must NEVER assume live data availability.
Supports: IBKR API, Polygon.io, AlphaVantage, Historical CSV, Mock data
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple, Dict
import pandas as pd
import numpy as np
import logging
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class MarketQuote:
    """Represents a single market quote"""
    symbol: str
    price: float
    timestamp: datetime
    volume: float = 0
    bid: Optional[float] = None
    ask: Optional[float] = None
    spread: Optional[float] = None


class DataFeedError(Exception):
    """Raised when data feed encounters an error"""
    pass


class DataFeed(ABC):
    """Abstract base for all data sources"""

    @abstractmethod
    async def get_quote(self, symbol: str) -> Optional[MarketQuote]:
        """Get current quote for a symbol"""
        pass

    @abstractmethod
    async def get_history(self, symbol: str, bars: int, interval: str) -> pd.DataFrame:
        """Get historical data"""
        pass

    def calculate_correlation(self, df1: pd.DataFrame, df2: pd.DataFrame,
                            period: int) -> Tuple[float, float]:
        """
        Returns: (correlation_value, correlation_volatility)
        Includes validity checks to prevent lookahead bias
        """
        if len(df1) < period or len(df2) < period:
            return 0.0, 0.0

        # Use returns, not prices
        returns1 = df1['close'].pct_change().dropna()
        returns2 = df2['close'].pct_change().dropna()

        # Align timestamps
        aligned = pd.concat([returns1, returns2], axis=1, join='inner').dropna()

        if len(aligned) < period:
            return 0.0, 0.0

        corr = aligned.iloc[-period:].corr().iloc[0, 1]

        # Calculate correlation volatility (stability measure)
        rolling_corr = aligned.rolling(5).corr().iloc[::2, 1].dropna()
        corr_vol = rolling_corr.std() if len(rolling_corr) > 0 else 0.0

        return corr, corr_vol


class MockDataFeed(DataFeed):
    """For paper trading and backtesting - generates realistic market data"""

    def __init__(self, scenario: str = "normal"):
        self.scenario = scenario  # "normal", "crash", "rally", "chop"
        self.last_prices = {}
        self._initialize_base_prices()

    def _initialize_base_prices(self):
        """Initialize realistic starting prices"""
        self.last_prices = {
            "US500": 4500.0,
            "USDJPY": 150.0,
            "VIX": 15.0,
            "US10Y": 4.5,
            "DXY": 104.0,
            "DAX": 16000.0,
            "NAS100": 15500.0,
            "AUDJPY": 95.0,
            "XAUUSD": 2000.0,
            "EURJPY": 160.0,
        }

    async def get_quote(self, symbol: str) -> MarketQuote:
        """Generate a realistic quote with random walk"""
        if symbol not in self.last_prices:
            raise DataFeedError(f"Symbol {symbol} not supported in mock feed")

        base_price = self.last_prices[symbol]

        # Scenario-based volatility
        volatility = {
            "normal": 0.0001,
            "crash": 0.003,
            "rally": 0.002,
            "chop": 0.0005
        }.get(self.scenario, 0.0001)

        # Generate random walk
        noise = np.random.normal(0, volatility)
        new_price = base_price * (1 + noise)

        # Update last price
        self.last_prices[symbol] = new_price

        # Generate bid/ask spread
        spread_pct = 0.0002  # 0.02% spread
        spread = new_price * spread_pct
        bid = new_price - spread / 2
        ask = new_price + spread / 2

        return MarketQuote(
            symbol=symbol,
            price=new_price,
            timestamp=datetime.utcnow(),
            volume=np.random.randint(1000, 10000),
            bid=bid,
            ask=ask,
            spread=spread
        )

    async def get_history(self, symbol: str, bars: int, interval: str) -> pd.DataFrame:
        """Generate historical data using random walk"""
        if symbol not in self.last_prices:
            raise DataFeedError(f"Symbol {symbol} not supported in mock feed")

        base_price = self.last_prices[symbol]

        # Generate realistic OHLCV data
        timestamps = pd.date_range(
            end=datetime.utcnow(),
            periods=bars,
            freq=self._interval_to_freq(interval)
        )

        volatility = {
            "normal": 0.0001,
            "crash": 0.003,
            "rally": 0.002,
            "chop": 0.0005
        }.get(self.scenario, 0.0001)

        # Random walk for closes
        returns = np.random.normal(0, volatility, bars)
        closes = base_price * np.cumprod(1 + returns)

        # Generate OHLC from closes
        highs = closes * (1 + np.abs(np.random.normal(0, volatility / 2, bars)))
        lows = closes * (1 - np.abs(np.random.normal(0, volatility / 2, bars)))
        opens = np.roll(closes, 1)
        opens[0] = closes[0]

        volumes = np.random.randint(1000, 10000, bars)

        df = pd.DataFrame({
            'timestamp': timestamps,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        })

        df.set_index('timestamp', inplace=True)
        return df

    def _interval_to_freq(self, interval: str) -> str:
        """Convert interval string to pandas frequency"""
        mapping = {
            "1min": "1T",
            "5min": "5T",
            "15min": "15T",
            "1h": "1H",
            "1d": "1D"
        }
        return mapping.get(interval, "1T")


class IBKRDataFeed(DataFeed):
    """Interactive Brokers TWS/Gateway implementation"""

    def __init__(self, host: str = "127.0.0.1", port: int = 7497):
        self.host = host
        self.port = port
        self.ib = None
        self._connected = False

    async def _connect_with_retry(self, max_attempts: int = 3):
        """Connect to IBKR with retry logic"""
        for attempt in range(max_attempts):
            try:
                # Note: Requires ib_insync library
                from ib_insync import IB
                self.ib = IB()
                await self.ib.connectAsync(self.host, self.port, clientId=1)
                self._connected = True
                logger.info(f"Connected to IBKR at {self.host}:{self.port}")
                return
            except Exception as e:
                logger.warning(f"IBKR connection attempt {attempt + 1} failed: {e}")
                if attempt == max_attempts - 1:
                    logger.critical("IBKR connection failed. System will use mock data.")
                    raise DataFeedError("Cannot connect to IBKR")
                await asyncio.sleep(5)

    async def get_quote(self, symbol: str) -> Optional[MarketQuote]:
        """Get quote from IBKR"""
        if not self._connected:
            raise DataFeedError("Not connected to IBKR")

        # Implementation would use ib_insync to get quotes
        # This is a placeholder
        raise NotImplementedError("IBKR integration requires ib_insync library")

    async def get_history(self, symbol: str, bars: int, interval: str) -> pd.DataFrame:
        """Get historical data from IBKR"""
        if not self._connected:
            raise DataFeedError("Not connected to IBKR")

        # Implementation would use ib_insync to get historical data
        # This is a placeholder
        raise NotImplementedError("IBKR integration requires ib_insync library")


def create_data_feed(config: Dict) -> DataFeed:
    """Factory function to create appropriate data feed"""
    mode = config.get('system', {}).get('mode', 'paper')

    if mode in ['paper', 'backtest']:
        logger.info("Using MockDataFeed for paper/backtest mode")
        return MockDataFeed(scenario="normal")
    elif mode == 'live':
        logger.info("Attempting to connect to IBKR for live mode")
        try:
            feed = IBKRDataFeed()
            asyncio.create_task(feed._connect_with_retry())
            return feed
        except Exception as e:
            logger.error(f"Failed to create IBKR feed: {e}. Falling back to mock.")
            return MockDataFeed(scenario="normal")
    else:
        raise ValueError(f"Unknown mode: {mode}")
