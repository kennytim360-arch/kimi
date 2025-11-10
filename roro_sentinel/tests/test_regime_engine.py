"""
Tests for Regime Engine
"""

import pytest
import asyncio
from datetime import datetime
from roro_sentinel.core.regime_engine import RegimeEngine, RegimeType
from roro_sentinel.data.data_feed import MockDataFeed


@pytest.fixture
def config():
    """Test configuration"""
    return {
        'regime': {
            'base_threshold_percent': 0.2,
            'vix_levels': {
                'low': {'max': 15, 'threshold_multiplier': 1.0},
                'moderate': {'min': 15, 'max': 25, 'threshold_multiplier': 0.8},
                'high': {'min': 25, 'max': 40, 'threshold_multiplier': 0.6},
                'extreme': {'min': 40, 'threshold_multiplier': 0.4}
            },
            'score_classification': {
                'strong_risk_on': {'min': 3, 'max': 4},
                'weak_risk_on': {'min': 1.5, 'max': 3},
                'neutral': {'min': -1.5, 'max': 1.5},
                'weak_risk_off': {'min': -3, 'max': -1.5},
                'strong_risk_off': {'max': -3}
            }
        },
        'correlation': {
            'lookback_periods': 20,
            'min_periods_for_valid': 15,
            'healthy_threshold': 0.65,
            'critical_breakdown': 0.40,
            'volatility_limit': 0.15
        },
        'instruments': {
            'primary_gauges': [
                {'symbol': 'US500', 'weight': 0.35},
                {'symbol': 'USDJPY', 'weight': 0.30},
                {'symbol': 'VIX', 'weight': 0.20},
                {'symbol': 'US10Y', 'weight': 0.10}
            ]
        }
    }


@pytest.fixture
def data_feed():
    """Mock data feed"""
    return MockDataFeed(scenario="normal")


@pytest.mark.asyncio
async def test_regime_analysis_normal(config, data_feed):
    """Test regime analysis in normal conditions"""
    engine = RegimeEngine(config, data_feed)
    result = await engine.analyze_regime(current_session="US_OVERLAP")

    assert result is not None
    assert isinstance(result.regime_type, RegimeType)
    assert 0.0 <= result.confidence <= 1.0
    assert result.session == "US_OVERLAP"


@pytest.mark.asyncio
async def test_regime_detects_data_error(config):
    """Test regime handles data errors gracefully"""
    # Create a data feed that will fail
    class FailingDataFeed:
        async def get_history(self, *args, **kwargs):
            raise Exception("Data unavailable")

    engine = RegimeEngine(config, FailingDataFeed())
    result = await engine.analyze_regime()

    assert result.regime_type == RegimeType.DATA_ERROR
    assert result.status == "DATA_ERROR"


@pytest.mark.asyncio
async def test_vix_categorization(config, data_feed):
    """Test VIX level categorization"""
    engine = RegimeEngine(config, data_feed)

    # Test low VIX
    from roro_sentinel.core.regime_engine import VIXCategory
    assert engine._categorize_vix(12.0) == VIXCategory.LOW
    assert engine._categorize_vix(18.0) == VIXCategory.MODERATE
    assert engine._categorize_vix(30.0) == VIXCategory.HIGH
    assert engine._categorize_vix(50.0) == VIXCategory.EXTREME


def test_percent_change_calculation(config, data_feed):
    """Test percentage change calculation"""
    import pandas as pd
    import numpy as np

    engine = RegimeEngine(config, data_feed)

    # Create sample data
    df = pd.DataFrame({
        'close': [100, 101, 102, 103, 104]
    })

    change = engine._percent_change(df)
    assert change == pytest.approx(4.0, rel=0.01)  # 4% increase


def test_trend_direction(config, data_feed):
    """Test trend direction detection"""
    import pandas as pd

    engine = RegimeEngine(config, data_feed)

    # Rising trend
    df_rising = pd.DataFrame({'close': [100, 100.1, 100.2, 100.3]})
    assert engine._trend_direction(df_rising) == 'rising'

    # Falling trend
    df_falling = pd.DataFrame({'close': [100, 99.9, 99.8, 99.7]})
    assert engine._trend_direction(df_falling) == 'falling'

    # Flat
    df_flat = pd.DataFrame({'close': [100, 100.01, 100.02, 100.03]})
    assert engine._trend_direction(df_flat) == 'flat'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
