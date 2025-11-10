# Example Signal Output

Here's what a trading signal from RORO Sentinel looks like:

```
================================================================================
🎯 TRADING SIGNAL GENERATED - FOR MANUAL REVIEW
================================================================================

📊 SIGNAL DETAILS:
  Action:      BUY
  Instrument:  US500
  Priority:    P1
  Confidence:  73.5%

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
  Daily Swap Cost:  -$3.15

📈 MARKET CONTEXT:
  Regime:       strong_risk_on
  Regime Score: 3.42
  Correlation:  0.73
  VIX Level:    14.2
  Session:      US_OVERLAP

🔍 DIVERGENCE DETECTED:
  Type:       bullish
  Magnitude:  0.54%
  Confidence: 68.2%

💡 REASONING:
  BULLISH divergence detected with 68.2% confidence. Regime: strong_risk_on

⚠️  RISK NOTES:
  Divergence penalty: 50.0% | Session multiplier: 100.0%

================================================================================
⚠️  MANUAL EXECUTION REQUIRED - This is a signal only, not an order
================================================================================
```

## Understanding the Signal

### Signal Details
- **Action**: Whether to BUY or SELL
- **Instrument**: Which instrument to trade (US500 = S&P 500)
- **Priority**: P0 (critical), P1 (high), P2 (medium), P3 (low)
- **Confidence**: System's confidence in the signal (0-100%)

### Trade Parameters
- **Entry Price**: Suggested entry level
- **Stop Loss**: Suggested stop loss level
- **Target**: Suggested profit target
- **Risk/Reward**: The risk/reward ratio of the trade

### Position Sizing
- **Suggested Size**: Number of contracts based on your account size
- **Risk Amount**: How much you'd risk at the stop loss
- **Margin Required**: Margin needed to open the position
- **Leverage Used**: The leverage multiplier
- **Daily Swap Cost**: Estimated overnight financing cost

### Market Context
- **Regime**: Current market regime classification
  - `strong_risk_on`: Stocks up, USDJPY up, VIX down
  - `weak_risk_on`: Mild risk-on conditions
  - `neutral`: Mixed signals
  - `weak_risk_off`: Mild risk-off conditions
  - `strong_risk_off`: Stocks down, USDJPY down, VIX up
- **Regime Score**: Strength of the regime reading
- **Correlation**: Health of SPX/USDJPY correlation (>0.65 is healthy)
- **VIX Level**: Current VIX reading
- **Session**: Trading session (ASIAN, EUROPEAN, US_OVERLAP, US_ONLY)

### Divergence (if detected)
- **Type**: Bullish or bearish divergence
- **Magnitude**: Size of the divergence
- **Confidence**: Confidence in the divergence signal

## What to Do with a Signal

1. **Don't trade blindly** - This is just one indicator
2. **Check the context** - Is correlation healthy? What's the VIX?
3. **Verify independently** - Look at charts yourself
4. **Assess your view** - Does this align with your market analysis?
5. **Manage risk** - The suggested size is based on configured parameters
6. **Execute manually** - If you choose to trade, place orders via your broker
7. **Track results** - Keep records to evaluate signal quality over time

## Signal Quality Factors

**High Quality Signals:**
- Confidence > 70%
- Correlation > 0.65
- Strong regime (score > 3.0)
- US Overlap session
- Divergence confirmed

**Lower Quality Signals:**
- Confidence < 60%
- Correlation < 0.50
- Weak/neutral regime
- CLOSED session
- No divergence

**Red Flags:**
- VIX > 30 (high volatility)
- Correlation < 0.40 (breakdown)
- Conflicting regime signals
- Late session (after 20:00 GMT)

## Remember

This system is a **tool**, not a crystal ball. Use it as:
- One input among many
- A way to identify potential setups
- A framework for analysis
- A learning tool

**Always make your own trading decisions!**
