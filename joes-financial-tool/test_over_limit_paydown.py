#!/usr/bin/env python3
"""Test that cards over limit can be paid down without failing."""

from config_loader import load_config
from optimizer import FinancialOptimizer
from simulator import FinancialSimulator, OptimizationStrategy

# Load config and set MasterCard slightly over limit
config = load_config("example_config.json")

# Set MasterCard just over its limit (limit is 2000, set balance to 2050)
mastercard = next(cc for cc in config.credit_cards if cc.id == "cc_mastercard")
mastercard.balance = 2050.00  # Over the $2000 limit by $50

# Remove bills charged to MasterCard to prevent increasing the balance
config.bills = [
    b
    for b in config.bills
    if not (b.paid_by_credit and b.payment_account == "cc_mastercard")
]

print(f"Initial MasterCard balance: ${mastercard.balance:.2f}")
print(f"MasterCard limit: ${mastercard.credit_limit:.2f}")
print(f"Over limit by: ${mastercard.balance - mastercard.credit_limit:.2f}")

optimizer = FinancialOptimizer(config)
simulator = FinancialSimulator(config, optimizer.today)

print("\nRunning simulation to pay down over-limit card...")
result = simulator.run_simulation(OptimizationStrategy.AGGRESSIVE_DEBT, days_ahead=30)

print(f"\n{'='*60}")
if result.failed:
    print(f"❌ Simulation failed")
    print(f"  Days completed: {len(result.days)}")
    if result.warnings:
        print(f"  Violations:")
        for warning in result.warnings[:3]:
            print(f"    - {warning}")
else:
    print(f"✓ Simulation succeeded!")
    print(f"  Completed all {len(result.days)} days")
    print(f"  Total interest: ${result.total_interest_paid:.2f}")

    # Check final MasterCard balance
    final_mc_balance = result.final_state.credit_card_balances.get("cc_mastercard", 0)
    print(f"\n  MasterCard:")
    print(
        f"    Starting: ${mastercard.balance:.2f} (over limit by ${mastercard.balance - mastercard.credit_limit:.2f})"
    )
    print(f"    Ending: ${final_mc_balance:.2f}")
    print(f"    Paid down: ${mastercard.balance - final_mc_balance:.2f}")

    if final_mc_balance < mastercard.balance:
        print(f"\n    ✓ Successfully paid down over-limit card!")
        if final_mc_balance <= mastercard.credit_limit:
            print(f"    ✓ Card is now under limit!")
    else:
        print(f"\n    ✗ Card balance didn't decrease")
