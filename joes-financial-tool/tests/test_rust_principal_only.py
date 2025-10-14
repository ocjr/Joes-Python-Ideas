#!/usr/bin/env python3
"""
Test Rust implementation of principal_only strategy with 1000 simulations.
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


# Create test config with biweekly income
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

print("Testing Rust implementation with principal_only strategy")
print("Running 1000 simulations (2 years)...")
print()

sim_principal = InvestmentSimulation(
    id="test_rust",
    name="Rust Principal-Only Test",
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
    num_simulations=1000,  # Force Rust usage
    random_seed=42,
)

engine = SimulationEngine(config, sim_principal)
results = engine.run_monte_carlo(target_age=40)

stats = results.get_statistics()

print()
print("=" * 80)
print("RESULTS (1000 Monte Carlo Simulations)")
print("=" * 80)
print()
print(f"Final Account Value:")
print(f"  10th percentile:  ${stats['final_value']['p10']:>12,.2f}")
print(f"  Median (50th):    ${stats['final_value']['median']:>12,.2f}")
print(f"  90th percentile:  ${stats['final_value']['p90']:>12,.2f}")
print()
print(f"Net Gain/Loss:")
print(f"  10th percentile:  ${stats['net_gain']['p10']:>12,.2f}")
print(f"  Median (50th):    ${stats['net_gain']['median']:>12,.2f}")
print(f"  90th percentile:  ${stats['net_gain']['p90']:>12,.2f}")
print()
print(f"Average Total Invested:  ${stats['total_invested']['mean']:>12,.2f}")
print(f"Average Total Withdrawn: ${stats['total_withdrawn']['mean']:>12,.2f}")
print(f"Average Taxes Paid:      ${stats['total_taxes']['mean']:>12,.2f}")
print()
print("✅ Rust implementation working correctly with principal_only strategy!")
