# Setting Up Live Market Data

## 🚀 Quick Start with Yahoo Finance (FREE)

Yahoo Finance provides free, near-real-time market data. Perfect for getting started!

### Step 1: Install yfinance

```powershell
pip install yfinance
```

### Step 2: Enable Live Mode

Edit `roro_sentinel/config/settings.yaml`:

```yaml
system:
  mode: "live"        # Change from "paper" to "live"
  data_source: "yahoo"  # Already set by default
```

### Step 3: Run the System

```powershell
python -m roro_sentinel.main
```

**That's it!** The system will now pull real market data from Yahoo Finance.

## 📊 What You'll Get

With Yahoo Finance live data:
- ✅ Real S&P 500 prices (^GSPC)
- ✅ Real USD/JPY forex rates
- ✅ Real VIX readings
- ✅ Real 10-Year Treasury yields
- ✅ **Actual correlations** between instruments
- ✅ **Real trading signals** based on current market conditions

## 🔄 Data Update Frequency

- **Yahoo Finance**: Updates every 1-15 minutes (delayed quotes)
- **Best for**: Testing the system with real market conditions
- **Good enough for**: Signal generation (not ultra-high-frequency trading)

## ⚙️ Configuration Options

### Data Refresh Rate

In `settings.yaml`:
```yaml
system:
  data_refresh_rate_ms: 60000  # Check every 60 seconds (1 minute)
```

**Recommendation**: Keep at 60 seconds (1 minute) for Yahoo Finance since data updates aren't instant.

### Supported Instruments

The system maps your symbols to Yahoo tickers:

| Your Symbol | Yahoo Ticker | Description |
|------------|--------------|-------------|
| US500 | ^GSPC | S&P 500 Index |
| USDJPY | USDJPY=X | USD/JPY Forex |
| VIX | ^VIX | Volatility Index |
| US10Y | ^TNX | 10-Year Treasury |
| DXY | DX-Y.NYB | US Dollar Index |
| DAX | ^GDAXI | German DAX |
| NAS100 | ^NDX | Nasdaq 100 |
| AUDJPY | AUDJPY=X | AUD/JPY |
| XAUUSD | GC=F | Gold Futures |
| EURJPY | EURJPY=X | EUR/JPY |

## 🎯 What to Expect

When running with live data, you should see:

### Healthy Correlations
```
Correlation: US500/USDJPY = 0.72 (healthy)
```

### Real Regime Classifications
```
Regime: strong_risk_on
Regime Score: 3.15
VIX Level: 14.2
```

### Actual Trading Signals
```
🎯 TRADING SIGNAL GENERATED
Action: BUY
Instrument: US500
Entry: 4525.50
Stop: 4514.25
Confidence: 73.5%
```

## ⚠️ Important Notes

### Yahoo Finance Limitations

1. **Delayed Data**: 15-minute delay on some quotes (fine for signal generation)
2. **Rate Limits**: Don't query too frequently (60-second refresh is safe)
3. **Data Quality**: Generally good, but occasional gaps or errors
4. **Not for HFT**: This is NOT high-frequency trading quality data

### When Signals Appear

Signals are **selective** - you won't see them every minute. Signals appear when:
- ✅ Correlation is healthy (> 0.65)
- ✅ Strong regime detected (score > 3.0 or < -3.0)
- ✅ Divergence confirmed with filters
- ✅ Market session is favorable

**This is GOOD!** Quality over quantity.

## 🔧 Troubleshooting

### "No module named 'yfinance'"

```powershell
pip install yfinance
```

### "Failed to get quote for US500"

- Check your internet connection
- Yahoo Finance may be temporarily unavailable
- System will log errors and continue

### Still seeing "CORRELATION BROKEN"

- This can happen during:
  - Market close / low liquidity hours
  - Major news events breaking normal correlations
  - System just started (needs a few minutes of data)

Give it 2-3 refresh cycles to build up correlation data.

## 📈 Monitoring Tips

### Watch for Good Signals

High quality signals have:
- Confidence > 70%
- Correlation > 0.70
- Strong regime (|score| > 3.0)
- US Overlap session (13:00-16:00 GMT)

### Best Trading Times

- **US Overlap** (13:00-16:00 GMT): Highest volume, best signals
- **US Only** (16:00-21:00 GMT): Good, but lower volume
- **Avoid**: CLOSED session (21:00-00:00 GMT) - low liquidity

## 🚀 Next Level: Interactive Brokers (Optional)

For professional-grade data (real-time, no delays):

1. Open IBKR account
2. Install TWS or Gateway
3. Edit settings:
   ```yaml
   system:
     mode: "live"
     data_source: "ibkr"
   ```
4. Install: `pip install ib-insync`

But for most users, **Yahoo Finance is perfect** to start! 🎯

## 📊 Example: Full Signal from Live Data

```
================================================================================
🎯 TRADING SIGNAL GENERATED - FOR MANUAL REVIEW
================================================================================

📊 SIGNAL DETAILS:
  Action:      BUY
  Instrument:  US500
  Priority:    P1
  Confidence:  78.3%

💰 TRADE PARAMETERS:
  Entry Price: 4525.50
  Stop Loss:   4514.25
  Target:      4547.75
  Risk/Reward: 1:1.98

📏 POSITION SIZING:
  Suggested Size:   2.35 contracts
  Risk Amount:      $1,250.00
  Margin Required:  $3,545.00
  Leverage Used:    15.3x

📈 MARKET CONTEXT:
  Regime:       strong_risk_on
  Regime Score: 3.42
  Correlation:  0.73 ✓ HEALTHY
  VIX Level:    14.2
  Session:      US_OVERLAP

💡 REASONING:
  Strong regime detected: stocks up, USDJPY up, VIX down
  Healthy correlation confirms setup

⚠️  MANUAL EXECUTION REQUIRED
================================================================================
```

Now you're ready to see REAL trading signals! 🎯
