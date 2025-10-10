#!/usr/bin/env python3
"""Test that cards starting over limit don't cause immediate failure."""

from config_loader import load_config
from optimizer import FinancialOptimizer
from simulator import FinancialSimulator, OptimizationStrategy

# Load config and modify it so a card starts over limit
config = load_config("example_config.json")

# Set Visa card over its limit (limit is 5000, set balance to 5200)
visa_card = next(cc for cc in config.credit_cards if cc.id == "cc_visa")
visa_card.balance = 5200.00  # Over the $5000 limit
print(f"Initial Visa balance: ${visa_card.balance:.2f}")
print(f"Visa limit: ${visa_card.credit_limit:.2f}")
print(f"Over limit by: ${visa_card.balance - visa_card.credit_limit:.2f}")

optimizer = FinancialOptimizer(config)
simulator = FinancialSimulator(config, optimizer.today)

print("\nRunning simulation with card over limit...")
result = simulator.run_simulation(OptimizationStrategy.AGGRESSIVE_DEBT, days_ahead=30)

print(f"\n{'='*60}")
if result.failed:
    print(f"❌ Simulation failed")
    print(f"  Days completed: {len(result.days)}")
    print(f"  Violations:")
    for warning in result.warnings:
        print(f"    - {warning}")
else:
    print(f"✓ Simulation succeeded")
    print(f"  Days completed: {len(result.days)}")
    print(f"  Total interest: ${result.total_interest_paid:.2f}")

    # Check final Visa balance
    final_visa_balance = result.final_state.credit_card_balances.get("cc_visa", 0)
    print(f"\n  Visa Card:")
    print(f"    Starting: ${visa_card.balance:.2f} (over limit)")
    print(f"    Ending: ${final_visa_balance:.2f}")
    print(f"    Change: ${final_visa_balance - visa_card.balance:.2f}")

    if final_visa_balance < visa_card.balance:
        print(f"    ✓ Balance decreased - simulation correctly allowed this")
    elif final_visa_balance == visa_card.balance:
        print(f"    ✓ Balance stayed same - simulation correctly allowed this")
    else:
        print(f"    ✗ Balance increased - this should have failed!")
