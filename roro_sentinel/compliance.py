"""
RORO SENTINEL CFD TRADING SYSTEM
================================
LEGAL DISCLAIMER: This is algorithmic analysis software, NOT financial advice.
Users must hold valid CFD trading licenses where required.
CFDs are complex instruments with high risk of rapid loss due to leverage.
Past correlations do not guarantee future performance; markets exhibit regime changes.

REGULATORY COMPLIANCE:
- Maximum leverage: 1:30 (ESMA) or 1:50 (ASIC) - Configurable
- Position risk per trade: 0.25%-1.8% (hard-capped)
- Daily loss limit: 3.0% (mandatory shutdown)
- Manual confirmation required for all trades (human-in-the-loop)

TRADER ACKNOWLEDGMENT REQUIRED:
"I understand this system can generate false signals, correlation breakdowns,
and that I am solely responsible for execution decisions."
"""

SYSTEM_RISK_LEVEL = "EXTREME"  # Do not modify
REQUIRED_EXPERIENCE_YEARS = 3  # Minimum recommended trader experience

def display_compliance_warning():
    """Display compliance warning on startup"""
    print("=" * 80)
    print("RORO SENTINEL CFD TRADING SYSTEM")
    print("=" * 80)
    print(__doc__)
    print("=" * 80)
    print(f"SYSTEM RISK LEVEL: {SYSTEM_RISK_LEVEL}")
    print(f"REQUIRED EXPERIENCE: {REQUIRED_EXPERIENCE_YEARS} years minimum")
    print("=" * 80)

def require_acknowledgment() -> bool:
    """Require trader acknowledgment before system start"""
    print("\nTo proceed, you must acknowledge the risks:")
    print('Type "I ACKNOWLEDGE" to continue or "EXIT" to quit')
    response = input("> ").strip().upper()
    return response == "I ACKNOWLEDGE"
