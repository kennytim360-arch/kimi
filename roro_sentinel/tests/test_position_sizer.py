"""
Tests for Position Sizer
"""

import pytest
from roro_sentinel.risk.position_sizer import CFDRiskCalculator


@pytest.fixture
def config():
    """Test configuration"""
    return {
        'risk': {
            'max_daily_risk_percent': 3.0,
            'max_per_trade_risk_percent': 1.8,
            'divergence_penalty': 0.50,
            'correlation_break_penalty': 0.30,
            'max_leverage': 30,
            'swap_cost_threshold': -10
        }
    }


def test_basic_position_sizing(config):
    """Test basic position size calculation"""
    calculator = CFDRiskCalculator(config)

    result = calculator.calculate_position_size(
        account_equity=100000,
        instrument="US500",
        entry_price=4500,
        stop_loss_price=4488,  # 0.27% stop
        signal_confidence=0.75,
        regime_score=2.0,
        position_size_multiplier=1.0
    )

    assert result.risk_amount > 0
    assert result.position_size > 0
    assert result.margin_required > 0
    assert result.leverage_used <= config['risk']['max_leverage']


def test_low_confidence_reduces_size(config):
    """Test that low confidence reduces position size"""
    calculator = CFDRiskCalculator(config)

    result_high = calculator.calculate_position_size(
        account_equity=100000,
        instrument="US500",
        entry_price=4500,
        stop_loss_price=4488,
        signal_confidence=0.75,
        regime_score=2.0,
        position_size_multiplier=1.0
    )

    result_low = calculator.calculate_position_size(
        account_equity=100000,
        instrument="US500",
        entry_price=4500,
        stop_loss_price=4488,
        signal_confidence=0.50,  # Low confidence
        regime_score=2.0,
        position_size_multiplier=1.0
    )

    assert result_low.risk_amount < result_high.risk_amount


def test_divergence_penalty(config):
    """Test divergence penalty reduces position size"""
    calculator = CFDRiskCalculator(config)
    calculator.add_divergence_instrument("US500")

    result = calculator.calculate_position_size(
        account_equity=100000,
        instrument="US500",
        entry_price=4500,
        stop_loss_price=4488,
        signal_confidence=0.75,
        regime_score=2.0,
        position_size_multiplier=1.0
    )

    # Risk should be reduced by divergence penalty
    expected_max = 100000 * 0.018 * 0.5  # Max risk * divergence penalty
    assert result.risk_amount <= expected_max


def test_zero_position_on_zero_stop(config):
    """Test that zero stop distance returns zero position"""
    calculator = CFDRiskCalculator(config)

    result = calculator.calculate_position_size(
        account_equity=100000,
        instrument="US500",
        entry_price=4500,
        stop_loss_price=4500,  # Same as entry = zero stop
        signal_confidence=0.75,
        regime_score=2.0,
        position_size_multiplier=1.0
    )

    assert result.position_size == 0.0
    assert "zero" in result.reasoning.lower()


def test_daily_risk_limit(config):
    """Test daily risk limit enforcement"""
    calculator = CFDRiskCalculator(config)

    # Use up most of daily risk
    calculator.today_risk_used = 2.8  # 2.8% of 3% max

    result = calculator.calculate_position_size(
        account_equity=100000,
        instrument="US500",
        entry_price=4500,
        stop_loss_price=4488,
        signal_confidence=0.75,
        regime_score=2.0,
        position_size_multiplier=1.0
    )

    # Should only allow remaining 0.2%
    assert result.risk_amount <= 200  # 0.2% of 100k


def test_reset_daily_risk(config):
    """Test daily risk reset"""
    calculator = CFDRiskCalculator(config)

    calculator.today_risk_used = 2.5
    assert calculator.today_risk_used == 2.5

    calculator.reset_daily_risk()
    assert calculator.today_risk_used == 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
