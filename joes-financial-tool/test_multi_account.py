#!/usr/bin/env python3
"""Test that the simulator intelligently selects between multiple checking accounts."""

from config_loader import load_config
from optimizer import FinancialOptimizer
from simulator import FinancialSimulator, OptimizationStrategy
from models import Account, AccountType

# Load config
config = load_config("example_config.json")

# Modify to have two checking accounts:
# - Main checking: $550 (min $500) = only $50 available
# - Secondary checking: $1500 (min $200) = $1300 available
config.accounts[0].balance = 550.00  # Main Checking
config.accounts[0].minimum_balance = 500.00

# Add a secondary checking account
secondary_checking = Account(
    id="checking_secondary",
    name="Secondary Checking",
    type=AccountType.CHECKING,
    balance=1500.00,
    minimum_balance=200.00,
)
config.accounts.append(secondary_checking)

print("Account Setup:")
print(f"  Main Checking: ${config.accounts[0].balance:.2f} (min ${config.accounts[0].minimum_balance:.2f}) = ${config.accounts[0].balance - config.accounts[0].minimum_balance:.2f} available")
print(f"  Secondary Checking: ${secondary_checking.balance:.2f} (min ${secondary_checking.minimum_balance:.2f}) = ${secondary_checking.balance - secondary_checking.minimum_balance:.2f} available")

optimizer = FinancialOptimizer(config)
simulator = FinancialSimulator(config, optimizer.today)

print("\nRunning simulation...")
print("Expected: Should use Secondary Checking for large payments since Main only has $50 available")

result = simulator.run_simulation(OptimizationStrategy.AGGRESSIVE_DEBT, days_ahead=30)

print(f"\n{'='*60}")
if result.failed:
    print(f"❌ Simulation failed")
    print(f"  Days completed: {len(result.days)}")
    print(f"  Violations:")
    for warning in result.warnings[:5]:
        print(f"    - {warning}")
else:
    print(f"✓ Simulation succeeded!")
    print(f"  Completed all {len(result.days)} days")
    print(f"  Total interest: ${result.total_interest_paid:.2f}")

    # Check which accounts were used
    main_final = result.final_state.account_balances.get("checking_main", 0)
    secondary_final = result.final_state.account_balances.get("checking_secondary", 0)

    main_change = main_final - config.accounts[0].balance
    secondary_change = secondary_final - secondary_checking.balance

    print(f"\n  Account Changes:")
    print(f"    Main Checking: ${config.accounts[0].balance:.2f} → ${main_final:.2f} (change: ${main_change:+.2f})")
    print(f"    Secondary Checking: ${secondary_checking.balance:.2f} → ${secondary_final:.2f} (change: ${secondary_change:+.2f})")

    # Both accounts should stay above minimums
    if main_final >= config.accounts[0].minimum_balance:
        print(f"    ✓ Main Checking stayed above minimum (${main_final:.2f} >= ${config.accounts[0].minimum_balance:.2f})")
    else:
        print(f"    ✗ Main Checking went below minimum! (${main_final:.2f} < ${config.accounts[0].minimum_balance:.2f})")

    if secondary_final >= secondary_checking.minimum_balance:
        print(f"    ✓ Secondary Checking stayed above minimum (${secondary_final:.2f} >= ${secondary_checking.minimum_balance:.2f})")
    else:
        print(f"    ✗ Secondary Checking went below minimum! (${secondary_final:.2f} < ${secondary_checking.minimum_balance:.2f})")

    # The secondary account should have been used more (since main has limited availability)
    if abs(secondary_change) > abs(main_change):
        print(f"\n    ✓ Correctly used Secondary Checking more (higher available balance)")
    else:
        print(f"\n    ℹ️  Main Checking used more than Secondary")
