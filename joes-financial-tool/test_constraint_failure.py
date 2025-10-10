#!/usr/bin/env python3
"""Test that simulations properly fail when constraints are violated."""

from config_loader import load_config
from optimizer import FinancialOptimizer
from simulator import FinancialSimulator, OptimizationStrategy

# Load config and modify it to create a cash-strapped scenario
config = load_config("example_config.json")

# Reduce checking balance to create potential violations
config.accounts[0].balance = 600  # Was 2500, now only 600 in checking (min 500)

# Add a large bill to trigger failure
from models import Bill

large_bill = Bill(
    id="large_expense",
    name="Large One-Time Expense",
    amount=5000.00,  # Huge expense we can't afford
    due_day=11,
    frequency="monthly",
    autopay=False,
    payment_account="checking_main",
    category="other",
    paid_by_credit=False,
)
config.bills.append(large_bill)

optimizer = FinancialOptimizer(config)
simulator = FinancialSimulator(config, optimizer.today)

print("Testing constraint violation detection...")
print(f"Initial checking: ${config.accounts[0].balance:.2f}")
print(f"Minimum balance: ${config.accounts[0].minimum_balance:.2f}")
print(f"Large bill on day 11: ${large_bill.amount:.2f}")

# Try to run aggressive_debt strategy
result = simulator.run_simulation(OptimizationStrategy.AGGRESSIVE_DEBT, days_ahead=30)

print(f"\n{'='*60}")
if result.failed:
    print(f"✓ CORRECTLY DETECTED FAILURE")
    print(f"  Days completed before failure: {len(result.days)}")
    print(f"  Violations:")
    for warning in result.warnings:
        print(f"    - {warning}")
else:
    print(f"✗ FAILED TO DETECT CONSTRAINT VIOLATION")
    print(f"  This should have failed but didn't!")
    print(f"  Final checking: ${result.final_state.get_total_checking():.2f}")
