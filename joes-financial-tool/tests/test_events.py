#!/usr/bin/env python3
"""
Demonstrate event tracking in Python implementation.
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
print("EVENT TRACKING DEMO (Python Implementation)")
print("=" * 80)
print()
print("This demonstrates the detailed event tracking available in Python.")
print("Events show every buy, sell, and dividend action in chronological order.")
print()

sim_config = InvestmentSimulation(
    id="test_events",
    name="Event Tracking Test",
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
    num_simulations=1,  # Single run for detailed events
    random_seed=42,
)

# Run with Python (force_python=True) to get detailed events
engine = SimulationEngine(config, sim_config)
results = engine.run_monte_carlo(target_age=40, force_python=True)

run = results.runs[0]

print(f"📊 RESULTS:")
print(f"  Total Invested:      ${run.total_invested:,.2f}")
print(f"  Total Withdrawn:     ${run.total_withdrawn:,.2f}")
print(f"  Final Account Value: ${run.final_account_value:,.2f}")
print(f"  Total Taxes:         ${run.total_taxes_paid:,.2f}")
print(f"  Net Gain:            ${run.net_gain:,.2f}")
print()

print(f"📋 DETAILED EVENTS (showing first 20 of {len(run.events)}):")
print("-" * 80)

for i, event in enumerate(run.events[:20], 1):
    symbol = (
        "📥"
        if event.event_type == "buy"
        else "📤" if event.event_type == "sell" else "💰"
    )
    print(
        f"{i:2d}. {event.date.strftime('%Y-%m-%d')} {symbol} {event.event_type.upper()}"
    )
    print(f"    {event.notes}")
    print(f"    Shares: {event.shares:.2f} @ ${event.price_per_share:.2f}")
    if event.event_type == "sell":
        print(f"    Sale proceeds: ${event.amount:,.2f}")
        if event.tax_owed > 0:
            print(f"    Tax owed: ${event.tax_owed:.2f}")
    print()

if len(run.events) > 20:
    print(f"... and {len(run.events) - 20} more events")
    print()

print("=" * 80)
print("NOTE:")
print("=" * 80)
print("• Events are only available with Python implementation")
print("• For large runs (>10 simulations), Rust is auto-selected for speed")
print("• Rust omits event tracking for performance (~500x faster)")
print("• Use force_python=True to get events for any simulation size")
print()
