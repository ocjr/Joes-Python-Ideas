#!/usr/bin/env python3
"""Test what happens on day 22 (first CC payment day)."""

from config_loader import load_config
from optimizer import FinancialOptimizer
from simulator import FinancialSimulator, OptimizationStrategy

config = load_config("example_config.json")
optimizer = FinancialOptimizer(config)
simulator = FinancialSimulator(config, optimizer.today)

# Run simulation
result = simulator.run_simulation(OptimizationStrategy.AGGRESSIVE_DEBT, days_ahead=30)

# Find day 10/22
from datetime import date
target_date = date(2025, 10, 22)

for day_sim in result.days:
    if day_sim.date == target_date:
        print(f"Day: {day_sim.date}")
        print(f"\nStarting State:")
        print(f"  Checking: ${day_sim.starting_state.get_total_checking():.2f}")
        print(f"  Debt: ${day_sim.starting_state.get_total_debt():.2f}")
        for cc_id, balance in day_sim.starting_state.credit_card_balances.items():
            cc = next((c for c in config.credit_cards if c.id == cc_id), None)
            if cc:
                print(f"    {cc.name}: ${balance:.2f}")

        print(f"\nTransactions:")
        for txn, decision in day_sim.transactions:
            print(f"  {txn.description}: ${abs(txn.amount):.2f}")
            print(f"    Category: {txn.category}")
            print(f"    Method: {decision.method.value}")
            if decision.checking_amount > 0:
                print(f"    Checking amount: ${decision.checking_amount:.2f}")

        print(f"\nEnding State:")
        print(f"  Checking: ${day_sim.ending_state.get_total_checking():.2f}")
        print(f"  Debt: ${day_sim.ending_state.get_total_debt():.2f}")
        for cc_id, balance in day_sim.ending_state.credit_card_balances.items():
            cc = next((c for c in config.credit_cards if c.id == cc_id), None)
            if cc:
                print(f"    {cc.name}: ${balance:.2f}")

        break
