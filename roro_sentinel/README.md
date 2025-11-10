# RORO SENTINEL - Signal Generation & Analysis System

**⚠️ THIS SYSTEM GENERATES TRADING SIGNALS - IT DOES NOT EXECUTE TRADES**

## 🎯 What This System Does

**RORO Sentinel is a SIGNAL GENERATOR, not an automated trader.**

This system:
- ✅ **Analyzes** market regime (Risk-On/Risk-Off)
- ✅ **Detects** divergences between correlated instruments
- ✅ **Generates** trading signals with entry, stop, and target levels
- ✅ **Calculates** suggested position sizes based on risk parameters
- ✅ **Displays** complete trade analysis for your review
- ❌ **DOES NOT** place orders or execute trades automatically
- ❌ **DOES NOT** connect to broker for order execution

**YOU must manually execute any trades you choose to take.**

## ⚠️ IMPORTANT DISCLAIMER

This is market analysis software, NOT financial advice:

- Signals may be false or inaccurate
- Past correlations do not guarantee future results
- CFDs have a 76-90% retail trader loss rate
- You must verify all analysis before trading
- You are solely responsible for ALL trading decisions
- Recommended for traders with 3+ years experience

## Overview

RORO Sentinel implements Risk-On/Risk-Off (RORO) regime detection combined with divergence trading strategies to generate trading signals for CFD markets.

### Key Features

- **VIX-Adaptive Regime Detection**: Automatically adjusts thresholds based on market volatility
- **Correlation Monitoring**: Tracks relationship health between key instruments (SPX/USDJPY)
- **Divergence Detection**: Identifies price-correlation divergences with false positive filters
- **Position Size Calculator**: Suggests leverage-aware position sizing based on risk parameters
- **Multi-Session Awareness**: Adapts signal criteria to Asian, European, and US trading sessions
- **Comprehensive Signal Display**: Shows entry, stop, target, risk/reward, and market context
- **Alert System**: Optional Discord, Telegram, and webhook notifications for signals

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

## Using the Signals

**How to use this system:**

1. **Run the System**: Start the signal generator in paper mode (uses mock data)
2. **Review Signals**: When a signal is generated, review all the details provided
3. **Verify Analysis**: Check the regime, correlation health, and market context
4. **Make Your Decision**: Decide whether to take the trade based on your own analysis
5. **Execute Manually**: If you choose to trade, place orders manually through your broker
6. **Track Results**: Keep your own record of which signals you took and their outcomes

**Recommended Practice:**

- Run the system for 2+ weeks to understand the types of signals it generates
- Track signal quality by paper trading or noting signals without trading
- Only trade signals that align with your own market view
- Always verify the market context before executing
- Never blindly follow signals - use them as one input in your decision-making

## Operational Modes

The system has two data modes:

1. **Paper Mode** (`mode: "paper"` in settings.yaml) - Uses mock data for testing
2. **Live Mode** (`mode: "live"`) - Would connect to real data feeds (IBKR, etc.)

**Note**: Regardless of mode, the system ONLY generates signals. It never places trades.

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
