#!/usr/bin/env python3
"""Test CC payment scheduling."""

from config_loader import load_config
from optimizer import FinancialOptimizer
from datetime import date

config = load_config("example_config.json")
optimizer = FinancialOptimizer(config)

print(f"Today: {optimizer.today}")
print(f"\nCredit Cards and Next Due Dates:")
for cc in config.credit_cards:
    next_due = optimizer.get_next_date(cc.due_day)
    print(f"  {cc.name}: Due day {cc.due_day}, balance ${cc.balance:.2f}, next due {next_due}")

# Check planned transactions
from simulator import FinancialSimulator
simulator = FinancialSimulator(config, optimizer.today)
transactions = simulator.get_planned_transactions(days_ahead=30)

print(f"\n\nCC Payment Transactions in next 30 days:")
for txn in transactions:
    if "CC Payment" in txn.description or "cc_payment" in txn.category:
        print(f"  {txn.date}: {txn.description} - ${abs(txn.amount):.2f}")
