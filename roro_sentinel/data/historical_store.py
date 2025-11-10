"""
Historical data storage and caching
Supports local cache for faster backtesting and offline operation
"""

import pandas as pd
import pickle
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict
import json

logger = logging.getLogger(__name__)


class HistoricalStore:
    """Manages local storage of historical market data"""

    def __init__(self, data_dir: str = "./data/cache"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.data_dir / "metadata.json"
        self.metadata = self._load_metadata()
        logger.info(f"HistoricalStore initialized at {self.data_dir}")

    def _load_metadata(self) -> Dict:
        """Load metadata about cached data"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_metadata(self):
        """Save metadata"""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2, default=str)

    def save_history(self, symbol: str, interval: str, df: pd.DataFrame):
        """Save historical data to disk"""
        filename = self._get_filename(symbol, interval)
        filepath = self.data_dir / filename

        # Save as parquet for efficiency
        df.to_parquet(filepath)

        # Update metadata
        self.metadata[f"{symbol}_{interval}"] = {
            "symbol": symbol,
            "interval": interval,
            "last_updated": datetime.utcnow().isoformat(),
            "num_bars": len(df),
            "start_date": df.index.min().isoformat() if len(df) > 0 else None,
            "end_date": df.index.max().isoformat() if len(df) > 0 else None
        }
        self._save_metadata()

        logger.info(f"Saved {len(df)} bars for {symbol} ({interval})")

    def load_history(self, symbol: str, interval: str) -> Optional[pd.DataFrame]:
        """Load historical data from disk"""
        filename = self._get_filename(symbol, interval)
        filepath = self.data_dir / filename

        if not filepath.exists():
            logger.warning(f"No cached data for {symbol} ({interval})")
            return None

        try:
            df = pd.read_parquet(filepath)
            logger.info(f"Loaded {len(df)} bars for {symbol} ({interval})")
            return df
        except Exception as e:
            logger.error(f"Error loading cached data: {e}")
            return None

    def is_data_stale(self, symbol: str, interval: str, max_age_hours: int = 24) -> bool:
        """Check if cached data is too old"""
        key = f"{symbol}_{interval}"
        if key not in self.metadata:
            return True

        last_updated = datetime.fromisoformat(self.metadata[key]["last_updated"])
        age = datetime.utcnow() - last_updated

        return age > timedelta(hours=max_age_hours)

    def _get_filename(self, symbol: str, interval: str) -> str:
        """Generate filename for symbol and interval"""
        return f"{symbol}_{interval}.parquet"

    def clear_cache(self, symbol: Optional[str] = None):
        """Clear cached data"""
        if symbol:
            # Clear specific symbol
            for interval in ["1min", "5min", "1h", "1d"]:
                filename = self._get_filename(symbol, interval)
                filepath = self.data_dir / filename
                if filepath.exists():
                    filepath.unlink()
                    logger.info(f"Cleared cache for {symbol} ({interval})")
                key = f"{symbol}_{interval}"
                if key in self.metadata:
                    del self.metadata[key]
        else:
            # Clear all
            for file in self.data_dir.glob("*.parquet"):
                file.unlink()
            self.metadata = {}
            logger.info("Cleared all cached data")

        self._save_metadata()

    def get_cache_info(self) -> Dict:
        """Get information about cached data"""
        return {
            "num_symbols": len(set(m["symbol"] for m in self.metadata.values())),
            "total_bars": sum(m["num_bars"] for m in self.metadata.values()),
            "symbols": self.metadata
        }


class TradeHistoryStore:
    """Store trade history and performance metrics"""

    def __init__(self, data_dir: str = "./data/trades"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.trades_file = self.data_dir / "trade_history.csv"
        logger.info(f"TradeHistoryStore initialized at {self.data_dir}")

    def save_trade(self, trade_data: Dict):
        """Save a trade to history"""
        df = pd.DataFrame([trade_data])

        if self.trades_file.exists():
            # Append to existing
            existing = pd.read_csv(self.trades_file)
            df = pd.concat([existing, df], ignore_index=True)

        df.to_csv(self.trades_file, index=False)
        logger.info(f"Trade saved: {trade_data.get('symbol')} {trade_data.get('side')}")

    def load_trades(self, start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None) -> pd.DataFrame:
        """Load trade history"""
        if not self.trades_file.exists():
            return pd.DataFrame()

        df = pd.read_csv(self.trades_file)

        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            if start_date:
                df = df[df['timestamp'] >= start_date]
            if end_date:
                df = df[df['timestamp'] <= end_date]

        return df

    def get_performance_metrics(self) -> Dict:
        """Calculate performance metrics from trade history"""
        df = self.load_trades()

        if len(df) == 0:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "avg_profit": 0.0,
                "avg_loss": 0.0,
                "profit_factor": 0.0,
                "total_pnl": 0.0
            }

        wins = df[df['pnl'] > 0]
        losses = df[df['pnl'] < 0]

        return {
            "total_trades": len(df),
            "win_rate": len(wins) / len(df) if len(df) > 0 else 0.0,
            "avg_profit": wins['pnl'].mean() if len(wins) > 0 else 0.0,
            "avg_loss": losses['pnl'].mean() if len(losses) > 0 else 0.0,
            "profit_factor": abs(wins['pnl'].sum() / losses['pnl'].sum()) if len(losses) > 0 and losses['pnl'].sum() != 0 else 0.0,
            "total_pnl": df['pnl'].sum()
        }
