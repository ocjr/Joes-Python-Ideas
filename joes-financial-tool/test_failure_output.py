#!/usr/bin/env python3
"""Test the improved failure output in CLI."""

from config_loader import load_config
from optimizer import FinancialOptimizer
from cli import print_optimal_simulation
from models import Bill

# Load config and create a cash-strapped scenario
config = load_config("example_config.json")

# Reduce checking balance to create potential violations
config.accounts[0].balance = 600  # Was 2500, now only 600 in checking (min 500)

# Add a large bill to trigger failure
large_bill = Bill(
    id="large_expense",
    name="Large One-Time Expense",
    amount=5000.00,
    due_day=11,
    frequency="monthly",
    autopay=False,
    payment_account="checking_main",
    category="other",
    paid_by_credit=False,
)
config.bills.append(large_bill)

optimizer = FinancialOptimizer(config)

print("Testing improved failure output...")
print(f"Initial checking: ${config.accounts[0].balance:.2f}")
print(f"Minimum balance: ${config.accounts[0].minimum_balance:.2f}")
print(f"Large bill on day 11: ${large_bill.amount:.2f}\n")

# This will print the failure details using the improved output
print_optimal_simulation(optimizer, days=30)
