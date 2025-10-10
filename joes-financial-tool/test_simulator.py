#!/usr/bin/env python3
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
print(f"\n📋 Sample Transactions (first 3 days with activity):")
days_shown = 0
for day in optimal.days:
    if day.transactions and days_shown < 3:
        print(f"\n{day.date.strftime('%a %m/%d')}:")
        for txn, decision in day.transactions:
            if abs(txn.amount) > 0:
                amount_str = f"${abs(txn.amount):.2f}"
                if txn.amount > 0:
                    print(f"  + {txn.description}: {amount_str}")
                else:
                    print(f"  - {txn.description}: {amount_str}")
                    print(f"    Method: {decision.method.value}, Reason: {decision.reason}")
        days_shown += 1
