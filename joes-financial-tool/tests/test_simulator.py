#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
"""Test script for the financial simulator."""

from config_loader import load_config
from optimizer import FinancialOptimizer

# Load the example config
config = load_config("example_config.json")

# Create optimizer
optimizer = FinancialOptimizer(config)

# Run optimal simulation
print("Running optimal simulation...")
optimal = optimizer.get_optimal_simulation(days_ahead=30)

print(f"\n✅ Optimal Strategy: {optimal.strategy.value}")
print(f"💰 Total Interest Cost: ${optimal.total_interest_paid:.2f}")
print(f"📉 Total Debt Reduction: ${optimal.get_total_debt_reduction():.2f}")

if optimal.warnings:
    print(f"\n⚠️  Warnings: {len(optimal.warnings)}")
    for w in optimal.warnings[:5]:
        print(f"   - {w}")
else:
    print("\n✅ No warnings - all constraints satisfied")

print(f"\n📊 Final State:")
print(f"   Total Checking: ${optimal.final_state.get_total_checking():.2f}")
print(f"   Total Savings:  ${optimal.final_state.get_total_savings():.2f}")
print(f"   Total Debt:     ${optimal.final_state.get_total_debt():.2f}")

# Show first few days of transactions
print(f"\n📋 Detailed Transactions (first 7 days):")
for i, day in enumerate(optimal.days[:7]):
    if day.transactions:
        print(f"\n{day.date.strftime('%a %m/%d')}:")
        print(
            f"  Starting: Checking=${day.starting_state.get_total_checking():.2f}, Debt=${day.starting_state.get_total_debt():.2f}"
        )

        for txn, decision in day.transactions:
            if abs(txn.amount) > 0:
                amount_str = f"${abs(txn.amount):.2f}"
                if txn.amount > 0:
                    print(f"    ✓ {txn.description}: +{amount_str}")
                    if txn.preferred_account:
                        print(f"      → Deposited to: {txn.preferred_account}")
                else:
                    print(f"    • {txn.description}: -{amount_str}")
                    if decision.method.value == "checking":
                        print(f"      → Paid from checking")
                    elif decision.method.value == "credit_card":
                        print(f"      → Charged to credit card")
                    elif decision.method.value == "split":
                        print(
                            f"      → Split: ${decision.checking_amount:.2f} checking + ${decision.credit_amount:.2f} credit"
                        )

                    # Show if this is a CC payment (reduces debt)
                    if "cc_payment" in txn.category or "cc_extra" in txn.category:
                        print(f"      → Reduces credit card debt")

        print(
            f"  Ending: Checking=${day.ending_state.get_total_checking():.2f}, Debt=${day.ending_state.get_total_debt():.2f}"
        )
        print(f"  Interest accrued today: ${day.interest_accrued:.2f}")
