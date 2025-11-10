# RORO SENTINEL - CFD Trading System

**High-Risk Algorithmic Trading System - For Experienced Traders Only**

## ⚠️ CRITICAL WARNING

This is a HIGH-RISK trading system designed for CFD (Contract for Difference) trading. CFDs have a 76-90% retail trader loss rate. This system:

- Can lose money rapidly due to leverage
- Requires manual confirmation for all trades
- Is NOT financial advice
- Should only be used by experienced traders (3+ years recommended)
- Requires valid CFD trading licenses where applicable

**You are solely responsible for all trading decisions.**

## Overview

RORO Sentinel is a Python-based algorithmic trading system that implements Risk-On/Risk-Off (RORO) regime detection combined with divergence trading strategies for CFD markets.

### Key Features

- **VIX-Adaptive Regime Detection**: Automatically adjusts to market volatility
- **Correlation Monitoring**: Tracks relationship health between key instruments
- **Divergence Detection**: Identifies price-correlation divergences with false positive filters
- **CFD-Specific Risk Management**: Leverage-aware position sizing with margin monitoring
- **Human-in-the-Loop**: Mandatory manual confirmation for all trades
- **Multi-Session Support**: Adapts to Asian, European, and US trading sessions
- **Comprehensive Alerting**: Discord, Telegram, and webhook support

## System Architecture

```
roro_sentinel/
├── config/           # Configuration files
├── core/            # Trading engine (regime, divergence, signals)
├── data/            # Data feeds and storage
├── risk/            # Risk management modules
├── execution/       # Alerts and trade validation
├── analysis/        # Performance analysis
├── tests/           # Unit tests
└── main.py          # Entry point
```

## Quick Start

### 1. Installation

```bash
# Clone repository
cd roro_sentinel

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Edit configuration files in `config/`:

- `settings.yaml` - Main system configuration
- `session_rules.yaml` - Session-specific parameters
- `risk_limits.yaml` - Risk management rules

**IMPORTANT**: Set `mode: "paper"` for testing!

### 3. Run Tests

```bash
pytest roro_sentinel/tests/ -v
```

### 4. Start System (Paper Mode)

```bash
python -m roro_sentinel.main
```

The system will:
1. Display legal disclaimers
2. Require your acknowledgment
3. Begin monitoring markets
4. Generate signals with manual confirmation

## Configuration

### Risk Limits (CRITICAL)

```yaml
risk:
  max_daily_risk_percent: 3.0      # Hard limit
  max_per_trade_risk_percent: 1.8  # Per trade
  max_leverage: 30                 # ESMA compliance
```

### Instrument Selection

Primary gauges:
- **US500** (S&P 500 CFD) - 35% weight
- **USDJPY** (USD/JPY Forex) - 30% weight
- **VIX** (Volatility Index) - 20% weight
- **US10Y** (10-Year Treasury) - 10% weight

### Alert Channels

Configure in `settings.yaml`:

```yaml
execution:
  alert_channels:
    - type: "discord"
      webhook_url: "YOUR_WEBHOOK_URL"
      severity_levels: ["P0", "P1"]
```

## Trading Logic

### Regime Detection

The system classifies market regimes:
- **Strong Risk-On**: Stocks up, USD/JPY up, VIX down
- **Strong Risk-Off**: Stocks down, USD/JPY down, VIX up
- **Neutral**: Mixed signals

Regime classification adapts to VIX levels (low/moderate/high/extreme).

### Divergence Trading

Detects divergences between:
- SPX vs USD/JPY price action
- Satellite instruments (DAX, NAS100, etc.)

False positive filters:
- VIX spike detection
- Low volatility rejection
- Correlation decay check

### Position Sizing

Factors considered:
- Account equity
- Signal confidence
- Regime strength
- Correlation health
- Swap costs
- Leverage limits
- Daily risk used

## Risk Management

### Automatic Safeguards

1. **Daily Loss Limit**: System stops at 3% daily loss
2. **Margin Monitoring**: Warns at low margin levels
3. **Correlation Breakdown**: Reduces trading when correlations weaken
4. **Session Management**: Closes positions before low liquidity hours
5. **Position Sizing**: Dynamically adjusts to risk conditions

### Manual Controls

- All trades require manual confirmation (configurable timeout)
- Emergency stop: Ctrl+C
- Manual position closure via broker platform

## Sessions

System adapts to trading sessions:

- **Asian** (00:00-08:00 GMT): Reduced thresholds, USDJPY focus
- **European** (08:00-13:00 GMT): Moderate activity
- **US Overlap** (13:00-16:00 GMT): **OPTIMAL** - Full power
- **US Only** (16:00-21:00 GMT): Late session, reduced size
- **Closed** (21:00-00:00 GMT): No new positions

## Monitoring

### Real-Time Metrics

- Regime type and score
- Correlation health
- VIX level
- Margin ratio
- Position P&L
- Daily risk used

### Alerts

- **P0 (Critical)**: Regime shifts, margin danger
- **P1 (High)**: Trade signals requiring confirmation
- **P2 (Medium)**: Watchlist items
- **P3 (Low)**: Status updates

## Testing

Run comprehensive tests:

```bash
# All tests
pytest roro_sentinel/tests/ -v

# Specific test
pytest roro_sentinel/tests/test_regime_engine.py -v

# With coverage
pytest --cov=roro_sentinel roro_sentinel/tests/
```

## Paper Trading

**MANDATORY before live trading:**

1. Run in paper mode for minimum 2 weeks
2. Monitor all signals and system behavior
3. Verify risk limits are enforced
4. Check alert system works correctly
5. Document any issues

## Going Live

⚠️ **ONLY after successful paper trading:**

1. Complete `startup_checklist.md`
2. Set `mode: "live"` in `settings.yaml`
3. Configure broker API credentials
4. **Keep manual confirmation ENABLED**
5. Start during US Overlap session
6. Monitor continuously for first 2 hours

## Troubleshooting

### Common Issues

**Data Feed Errors**
- Check broker API connection
- Verify instrument symbols match broker
- Ensure TWS/Gateway is running (if IBKR)

**No Signals Generated**
- Check correlation health (must be HEALTHY)
- Verify VIX is not extreme (>40)
- Ensure current session allows trading
- Check margin levels

**Alerts Not Sending**
- Verify webhook URLs in config
- Check channel severity levels
- Review logs for errors

## Performance Tracking

System tracks:
- Win rate
- Average profit/loss
- Maximum drawdown
- Correlation stability
- Risk utilization
- Trade frequency

Review `data/trades/trade_history.csv` for detailed records.

## Compliance

### Regulatory Requirements

- **ESMA (Europe)**: Max 30x leverage, negative balance protection
- **ASIC (Australia)**: Max 50x leverage for experienced traders
- **US**: CFD trading generally prohibited for retail traders

### Disclaimers

This system:
- Is for educational/research purposes
- Does not constitute financial advice
- Cannot guarantee profits
- Can result in significant losses
- Requires user to accept all trading risks

## Development

### Project Structure

- `core/`: Trading logic and analysis engines
- `data/`: Data feeds, broker APIs, storage
- `risk/`: Position sizing, margin monitoring
- `execution/`: Alerts, trade validation
- `tests/`: Unit and integration tests

### Adding New Features

1. Create feature branch
2. Implement with tests
3. Run full test suite
4. Paper trade extensively
5. Document thoroughly

## Support

- Review `startup_checklist.md` for deployment guide
- Check logs for detailed error messages
- Consult individual module documentation
- Test in paper mode first

## License

For educational and research purposes only. See LICENSE file.

## Acknowledgments

Based on RORO (Risk-On/Risk-Off) trading methodology with CFD-specific risk management adaptations.

---

**Remember: Past performance does not guarantee future results. Correlations can break down. Markets can remain irrational longer than you can remain solvent. Trade responsibly.**
