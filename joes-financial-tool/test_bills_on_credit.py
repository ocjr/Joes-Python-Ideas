#!/usr/bin/env python3
"""Test bills charged to credit cards."""

from config_loader import load_config
from optimizer import FinancialOptimizer
from simulator import FinancialSimulator

config = load_config("example_config.json")
optimizer = FinancialOptimizer(config)
simulator = FinancialSimulator(config, optimizer.today)

transactions = simulator.get_planned_transactions(days_ahead=30)

print("Bills charged to credit cards in next 30 days:")
for txn in transactions:
    if txn.category == "bill_on_credit":
        print(f"  {txn.date}: {txn.description} - ${abs(txn.amount):.2f} to {txn.preferred_account}")
