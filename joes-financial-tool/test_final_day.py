#!/usr/bin/env python3
"""Check final day of simulation."""

from config_loader import load_config
from optimizer import FinancialOptimizer
from simulator import FinancialSimulator, OptimizationStrategy

config = load_config("example_config.json")
optimizer = FinancialOptimizer(config)
simulator = FinancialSimulator(config, optimizer.today)

# Run simulation
result = simulator.run_simulation(OptimizationStrategy.AGGRESSIVE_DEBT, days_ahead=30)

print(f"Total days: {len(result.days)}")
print(f"\nFinal day: {result.final_state.date}")
print(f"Final checking: ${result.final_state.get_total_checking():.2f}")
print(f"Final debt: ${result.final_state.get_total_debt():.2f}")
print(f"\nCC Balances:")
for cc_id, balance in result.final_state.credit_card_balances.items():
    cc = next((c for c in config.credit_cards if c.id == cc_id), None)
    if cc:
        print(f"  {cc.name}: ${balance:.2f}")

# Check days after 10/22
print(f"\n\nDays after 10/22 with transactions:")
from datetime import date
for day_sim in result.days:
    if day_sim.date > date(2025, 10, 22) and day_sim.transactions:
        print(f"\n{day_sim.date}:")
        for txn, decision in day_sim.transactions:
            print(f"  {txn.description}: ${abs(txn.amount):.2f} ({txn.category})")
        print(f"  Ending debt: ${day_sim.ending_state.get_total_debt():.2f}")
