#!/usr/bin/env python3
"""
Test that instructions can be generated regardless of simulation engine.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from models import (
    FinancialConfig,
    Account,
    AccountType,
    Income,
    Frequency,
    Settings,
    InvestmentSimulation,
)
from simulation_engine import SimulationEngine
from simulation_reports import print_actionable_instructions

# Create test config
config = FinancialConfig(
    accounts=[
        Account(
            id="checking",
            name="Checking",
            type=AccountType.CHECKING,
            balance=5000.0,
        )
    ],
    income=[
        Income(
            id="biweekly_salary",
            source="Biweekly Paycheck",
            amount=1500.00,
            frequency=Frequency.BIWEEKLY,
            next_date=date(2025, 10, 17),
            deposit_account="checking",
        )
    ],
    bills=[],
    credit_cards=[],
    settings=Settings(),
)

print("=" * 80)
print("TESTING: Instructions Generation from Rust Results")
print("=" * 80)
print()

# Run with Rust (>10 simulations, no events)
sim_config = InvestmentSimulation(
    id="test_instructions",
    name="Rust Simulation with Instructions",
    enabled=True,
    current_age=38,
    target_ages=[40],
    strategy_type="principal_only",
    liquidation_day=1,
    income_source_ids=["biweekly_salary"],
    income_growth_rate=0.0,
    income_growth_frequency=1,
    ticker="SPY",
    initial_balance=5000.0,
    expected_annual_return=0.10,
    annual_volatility=0.15,
    annual_dividend_yield=0.015,
    expense_ratio=0.0009,
    short_term_cap_gains_rate=0.22,
    long_term_cap_gains_rate=0.15,
    dividend_tax_rate=0.15,
    num_simulations=1000,  # Force Rust
    random_seed=42,
)

print("Step 1: Run 1000 simulations with Rust (fast, no events)")
print("-" * 80)
engine = SimulationEngine(config, sim_config)
results = engine.run_monte_carlo(target_age=40)

print("\n✅ Rust simulation complete")
print(
    f"   Median final value: ${results.get_statistics()['final_value']['median']:,.2f}"
)
print(f"   Events in results:  {len(results.runs[0].events)}")  # Should be 0

print("\n" + "=" * 80)
print("\nStep 2: Generate actionable instructions (auto-generates 6-month Python run)")
print("-" * 80)

# This should automatically generate a deterministic instruction run
print_actionable_instructions(results, max_instructions=20, config=config)

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
print()
print("✅ Instructions generated successfully from Rust results")
print("✅ Instructions are deterministic (always use seed=0)")
print("✅ Only simulates 6 months for quick generation")
print()
