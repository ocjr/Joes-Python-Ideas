#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
"""Test that payments to the same card on the same day are combined."""

from config_loader import load_config
from optimizer import FinancialOptimizer
from cli import print_optimal_simulation

config = load_config("example_config.json")
optimizer = FinancialOptimizer(config)

print("Testing payment combination")
print("Expect to see combined payments when multiple payments")
print("are made to the same credit card on the same day")
print()

# Get transactions before combining
from simulator import FinancialSimulator

sim = FinancialSimulator(config)
all_txns = sim.get_planned_transactions(30)

print("\nTransactions for Oct 22 BEFORE combining:")
print("=" * 60)
for txn in all_txns:
    if txn.date.day == 22 and "Payment" in txn.description and "Visa" in txn.description:
        print(f"  Category: {txn.category}")
        print(f"  Description: {txn.description}")
        print(f"  Amount: ${abs(txn.amount):,.2f}")
        print()

# Now combine
combined_txns = sim.combine_same_day_payments(all_txns)

print("\nTransactions for Oct 22 AFTER combining:")
print("=" * 60)
for txn in combined_txns:
    if txn.date.day == 22 and "Payment" in txn.description and "Visa" in txn.description:
        print(f"  Category: {txn.category}")
        print(f"  Description: {txn.description}")
        print(f"  Amount: ${abs(txn.amount):,.2f}")
        print()

# Run simulation to see if payments are combined
result = optimizer.get_optimal_simulation(days_ahead=30)

# Check day 22 (Oct 22) which should have combined Visa payments
print("\nChecking transactions for Oct 22:")
print("=" * 60)
for day in result.days:
    if day.date.day == 22:
        print(f"Date: {day.date}")
        print(f"Number of transactions: {len(day.transactions)}")
        for txn_tuple in day.transactions:
            # Unpack the tuple (transaction, decision)
            txn, decision = txn_tuple
            if "Payment" in txn.description and "Visa" in txn.description:
                print(f"  • {txn.description}: ${abs(txn.amount):,.2f}")
        break
