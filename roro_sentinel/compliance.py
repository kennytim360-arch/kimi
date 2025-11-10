"""
RORO SENTINEL - SIGNAL GENERATION & ANALYSIS SYSTEM
====================================================
LEGAL DISCLAIMER: This is market analysis software, NOT financial advice.
This system generates trading signals for educational and informational purposes only.

⚠️  SIGNAL-ONLY SYSTEM: This software does NOT execute trades automatically.
All trading decisions and executions are YOUR responsibility.

IMPORTANT NOTICES:
- Signals are generated using historical correlations which may break down
- Past performance does not guarantee future results
- CFDs are complex instruments with high risk of rapid loss due to leverage
- You must hold valid CFD trading licenses where required by your jurisdiction
- Markets exhibit regime changes that can invalidate correlation-based strategies

RISK ACKNOWLEDGMENT:
Trading CFDs and forex carries a high level of risk and may not be suitable for all
investors. The high degree of leverage can work against you as well as for you.
Before deciding to trade, you should carefully consider your investment objectives,
level of experience, and risk appetite.

USER RESPONSIBILITY:
"I understand this system generates signals that may be false or inaccurate.
I am solely responsible for:
- Deciding whether to act on any signal
- Verifying all analysis before trading
- Managing my own risk and position sizing
- All trading decisions and their outcomes"
"""

SYSTEM_TYPE = "SIGNAL_GENERATION"  # Do not modify
SYSTEM_RISK_LEVEL = "INFORMATIONAL"  # This is an analysis tool
RECOMMENDED_EXPERIENCE_YEARS = 3  # Minimum recommended trader experience

def display_compliance_warning():
    """Display compliance warning on startup"""
    print("=" * 80)
    print("RORO SENTINEL - SIGNAL GENERATION & ANALYSIS SYSTEM")
    print("=" * 80)
    print(__doc__)
    print("=" * 80)
    print(f"SYSTEM TYPE: {SYSTEM_TYPE}")
    print(f"SYSTEM LEVEL: {SYSTEM_RISK_LEVEL}")
    print(f"RECOMMENDED EXPERIENCE: {RECOMMENDED_EXPERIENCE_YEARS} years minimum")
    print("=" * 80)

def require_acknowledgment() -> bool:
    """Require trader acknowledgment before system start"""
    print("\nTo proceed, you must acknowledge the risks:")
    print('Type "I ACKNOWLEDGE" to continue or "EXIT" to quit')
    response = input("> ").strip().upper()
    return response == "I ACKNOWLEDGE"
