# RORO SENTINEL - Startup Checklist

## Pre-Deployment Verification

### 1. Environment Setup
- [ ] Python 3.11+ installed
- [ ] Virtual environment created and activated
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] Configuration files present in `config/` directory

### 2. Configuration Review

#### settings.yaml
- [ ] System mode set correctly (`paper` for testing, `live` for production)
- [ ] Data refresh rates appropriate for your needs
- [ ] Instrument symbols match your broker's naming convention
- [ ] Risk limits are appropriate for your capital
- [ ] Alert channels configured (Discord, Telegram, etc.)

#### session_rules.yaml
- [ ] Session hours match your trading timezone
- [ ] Session-specific multipliers reviewed
- [ ] Holiday calendar updated for current year

#### risk_limits.yaml
- [ ] Daily risk limit is acceptable (default 3%)
- [ ] Per-trade risk limit is conservative (default 1.8%)
- [ ] Leverage limits comply with regulations (ESMA/ASIC)

### 3. Risk Management Verification

- [ ] **CRITICAL**: Max daily loss limit set to 3% or less
- [ ] Position sizing uses appropriate leverage (≤30x ESMA, ≤50x ASIC)
- [ ] Stop loss percentages are reasonable (0.25%-0.5%)
- [ ] Margin buffer set to at least 25%
- [ ] Manual confirmation is ENABLED for live trading

### 4. Compliance Checks

- [ ] Read and understood all legal disclaimers
- [ ] Have 3+ years trading experience (recommended minimum)
- [ ] Understand CFD risks (76-90% retail loss rate)
- [ ] Have valid CFD trading license if required in your jurisdiction
- [ ] Understand correlation breakdown risks
- [ ] Acknowledge sole responsibility for all trades

### 5. Testing Requirements

Before going live:

- [ ] Run full test suite: `pytest roro_sentinel/tests/`
- [ ] Verify all tests pass
- [ ] Run in paper trading mode for AT LEAST 2 weeks
- [ ] Monitor correlation health during paper trading
- [ ] Verify alert system works correctly
- [ ] Test emergency stop procedures
- [ ] Validate position sizing calculations

### 6. Data Feed Setup

For IBKR (Interactive Brokers):
- [ ] TWS or Gateway running
- [ ] API enabled in TWS settings
- [ ] Correct host and port in configuration
- [ ] Test connection successful

For Paper Trading:
- [ ] MockDataFeed configured
- [ ] Historical data available if needed

### 7. Broker API Setup

- [ ] Broker credentials configured (if live mode)
- [ ] Test connection to broker API
- [ ] Verify order placement works (paper trading first!)
- [ ] Confirm position retrieval works
- [ ] Test account summary retrieval

### 8. Alert System Verification

- [ ] Discord webhook URL configured (if using)
- [ ] Telegram bot token and chat ID configured (if using)
- [ ] Test alerts send successfully
- [ ] P0 alerts reach you immediately
- [ ] Alert rate limiting tested

### 9. Monitoring Setup

- [ ] Understand how to check system logs
- [ ] Know how to monitor margin levels
- [ ] Have access to broker platform for manual intervention
- [ ] Emergency contact info available
- [ ] Backup plan if system fails

### 10. Launch Preparation

**Day Before Launch:**
- [ ] Verify sufficient margin in account
- [ ] Check economic calendar for major events
- [ ] Ensure VIX is not in extreme territory (>40)
- [ ] Verify market hours are normal (no holidays)
- [ ] Have exit plan ready

**Launch Day:**
- [ ] Start during US Overlap session (13:00-16:00 GMT) for best conditions
- [ ] Monitor first 2 hours continuously
- [ ] Verify correlation health is HEALTHY
- [ ] Check margin levels every 30 minutes initially
- [ ] Be ready to manually intervene

### 11. Emergency Procedures

Know how to:
- [ ] Emergency stop the system (Ctrl+C)
- [ ] Manually close all positions via broker
- [ ] Disable automatic trading
- [ ] Contact broker support
- [ ] Access system logs for troubleshooting

### 12. Performance Monitoring

Track daily:
- [ ] Win rate
- [ ] Average profit vs average loss
- [ ] Maximum drawdown
- [ ] Correlation health
- [ ] Daily risk used
- [ ] Margin utilization

## Critical Safety Reminders

### 🚨 NEVER:
- Disable manual confirmation in live mode
- Exceed 30x leverage (ESMA) or 50x (ASIC)
- Trade with more than 3% daily risk
- Trade during correlation breakdowns
- Ignore margin warnings
- Trade when fatigued or emotional
- Skip the paper trading phase

### ✅ ALWAYS:
- Keep manual confirmation enabled
- Monitor margin levels
- Respect daily loss limits
- Close positions before low liquidity hours
- Stay informed of major news events
- Have backup plan for system failure
- Keep broker platform accessible

## Final Acknowledgment

Before starting the system, confirm:

- [ ] I understand this is HIGH-RISK algorithmic trading
- [ ] I accept 100% responsibility for all trades
- [ ] I will NOT trade more than I can afford to lose
- [ ] I will follow all risk management rules
- [ ] I will stop trading at 3% daily loss
- [ ] I have read and understood all documentation
- [ ] I acknowledge CFDs have 76-90% retail loss rates

## System Start Command

Once all checks are complete:

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Run in paper mode first
python -m roro_sentinel.main

# Monitor the output carefully
# System will request acknowledgment before starting
```

## Post-Launch Checklist

First Week:
- [ ] Monitor system 2+ hours daily
- [ ] Review all trades
- [ ] Check correlation remained healthy
- [ ] Verify risk limits were respected
- [ ] Confirm alert system worked correctly
- [ ] Document any issues encountered

## Support and Issues

- Review logs in system output
- Check configuration files for errors
- Verify broker API connection
- Consult README.md for troubleshooting
- Join community forums (if available)

---

**Remember: Trading CFDs is extremely risky. This system is a tool, not a guarantee of profits. You are solely responsible for all trading decisions.**
