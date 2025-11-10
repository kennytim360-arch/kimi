"""
Yahoo Finance Data Feed
Free real-time(ish) market data using yfinance
"""

from datetime import datetime, timezone
from typing import Optional
import pandas as pd
import logging
from .data_feed import DataFeed, MarketQuote, DataFeedError

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

logger = logging.getLogger(__name__)


class YahooDataFeed(DataFeed):
    """Yahoo Finance data feed - Free real market data"""

    def __init__(self):
        if not YFINANCE_AVAILABLE:
            raise DataFeedError("yfinance library not installed. Run: pip install yfinance")

        # Map our symbols to Yahoo Finance tickers
        self.symbol_map = {
            "US500": "^GSPC",      # S&P 500
            "USDJPY": "USDJPY=X",  # USD/JPY Forex
            "VIX": "^VIX",         # VIX Index
            "US10Y": "^TNX",       # 10-Year Treasury Yield
            "DXY": "DX-Y.NYB",     # US Dollar Index
            "DAX": "^GDAXI",       # DAX
            "NAS100": "^NDX",      # Nasdaq 100
            "AUDJPY": "AUDJPY=X",  # AUD/JPY
            "XAUUSD": "GC=F",      # Gold
            "EURJPY": "EURJPY=X"   # EUR/JPY
        }

        logger.info("YahooDataFeed initialized - using real market data")

    async def get_quote(self, symbol: str) -> Optional[MarketQuote]:
        """Get current quote from Yahoo Finance"""
        ticker = self.symbol_map.get(symbol)
        if not ticker:
            raise DataFeedError(f"Symbol {symbol} not mapped to Yahoo ticker")

        try:
            data = yf.Ticker(ticker)
            info = data.info

            # Get the latest price
            price = info.get('regularMarketPrice') or info.get('previousClose', 0)

            # Get bid/ask if available
            bid = info.get('bid', price * 0.9999)
            ask = info.get('ask', price * 1.0001)
            spread = ask - bid if (bid and ask) else 0

            return MarketQuote(
                symbol=symbol,
                price=price,
                timestamp=datetime.now(timezone.utc),
                volume=info.get('volume', 0),
                bid=bid,
                ask=ask,
                spread=spread
            )
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {e}")
            raise DataFeedError(f"Failed to get quote for {symbol}: {e}")

    async def get_history(self, symbol: str, bars: int, interval: str) -> pd.DataFrame:
        """Get historical data from Yahoo Finance"""
        ticker = self.symbol_map.get(symbol)
        if not ticker:
            raise DataFeedError(f"Symbol {symbol} not mapped to Yahoo ticker")

        try:
            # Map our intervals to Yahoo intervals
            yahoo_interval = self._map_interval(interval)

            # Determine period based on bars and interval
            period = self._calculate_period(bars, interval)

            # Get data
            data = yf.Ticker(ticker)
            df = data.history(period=period, interval=yahoo_interval)

            if df.empty:
                raise DataFeedError(f"No data returned for {symbol}")

            # Rename columns to match our format
            df = df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })

            # Keep only the columns we need
            df = df[['open', 'high', 'low', 'close', 'volume']]

            # Take only the requested number of bars
            df = df.tail(bars)

            logger.debug(f"Retrieved {len(df)} bars for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Error getting history for {symbol}: {e}")
            raise DataFeedError(f"Failed to get history for {symbol}: {e}")

    def _map_interval(self, interval: str) -> str:
        """Map our interval to Yahoo Finance interval"""
        mapping = {
            "1min": "1m",
            "5min": "5m",
            "15min": "15m",
            "1h": "1h",
            "1d": "1d"
        }
        return mapping.get(interval, "1m")

    def _calculate_period(self, bars: int, interval: str) -> str:
        """Calculate the period string for Yahoo Finance"""
        # Yahoo Finance periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max

        if interval in ["1min", "5min", "15min"]:
            # Intraday data - limited to last 7 days
            if bars <= 390:  # 1 day of 1-min bars
                return "1d"
            elif bars <= 1950:  # 5 days
                return "5d"
            else:
                return "7d"  # Max for intraday
        elif interval == "1h":
            if bars <= 24:
                return "1d"
            elif bars <= 168:  # 1 week
                return "5d"
            else:
                return "1mo"
        else:  # Daily
            if bars <= 30:
                return "1mo"
            elif bars <= 90:
                return "3mo"
            elif bars <= 180:
                return "6mo"
            else:
                return "1y"
