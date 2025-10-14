#!/usr/bin/env python3
"""
Test income growth and actionable instructions features.
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
from simulation_reports import print_simulation_summary, print_actionable_instructions


def test_income_growth():
    """Test simulation with income growth."""
    print("=" * 80)
    print("  TESTING INCOME GROWTH & ACTIONABLE INSTRUCTIONS")
    print("=" * 80)
    print()

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
                id="salary",
                source="Monthly Salary",
                amount=3000.00,
                frequency=Frequency.MONTHLY,
                next_date=date(2025, 10, 15),
                deposit_account="checking",
            )
        ],
        bills=[],
        credit_cards=[],
        settings=Settings(),
    )

    # Create simulation with 10% income growth every 2 years
    simulation = InvestmentSimulation(
        id="growth_test",
        name="Income Growth Test",
        enabled=True,
        current_age=38,
        target_ages=[42],  # 4 years = 2 growth periods
        strategy_type="monthly_liquidation",
        liquidation_day=1,
        income_source_ids=["salary"],
        income_growth_rate=0.10,  # 10% growth
        income_growth_frequency=2,  # Every 2 years
        ticker="SPY",
        initial_balance=5000.0,
        expected_annual_return=0.10,
        annual_volatility=0.15,
        annual_dividend_yield=0.015,
        expense_ratio=0.0009,
        short_term_cap_gains_rate=0.22,
        long_term_cap_gains_rate=0.15,
        dividend_tax_rate=0.15,
        num_simulations=10,  # Small number for quick test
        random_seed=42,
    )

    # Disable Rust for this test to get detailed events
    import simulation_engine
    original_rust = simulation_engine.RUST_AVAILABLE
    simulation_engine.RUST_AVAILABLE = False

    try:
        engine = SimulationEngine(config, simulation)
        results = engine.run_monte_carlo(target_age=42)

        # Display results
        print_simulation_summary(results)

        # Show actionable instructions
        print_actionable_instructions(results, max_instructions=30)

        # Verify income growth in events
        print("\n" + "=" * 80)
        print("  INCOME GROWTH VERIFICATION")
        print("=" * 80)
        print()

        # Check events from first run
        buy_events = [e for e in results.runs[0].events if e.event_type == 'buy' and 'paycheck' in e.notes.lower()]
        if buy_events:
            print(f"Found {len(buy_events)} income investment events")
            print("\nSample income amounts over time:")
            for i, event in enumerate(buy_events[:12]):  # Show first year
                print(f"  {event.date.strftime('%Y-%m-%d')}: ${abs(event.amount):,.2f}")

            # Check if growth is applied
            year_0_amount = abs(buy_events[0].amount)
            if len(buy_events) >= 24:  # After 2 years
                year_2_amount = abs(buy_events[24].amount)
                growth_factor = year_2_amount / year_0_amount
                print(f"\nGrowth factor after 2 years: {growth_factor:.4f}")
                print(f"Expected: 1.10 (10% growth)")
                if 1.08 <= growth_factor <= 1.12:
                    print("✅ Income growth working correctly!")
                else:
                    print("⚠️  Growth factor seems off")

        print("\n" + "=" * 80)
        print("✅ TEST COMPLETE!")
        print("=" * 80)

    finally:
        # Restore Rust availability
        simulation_engine.RUST_AVAILABLE = original_rust


if __name__ == "__main__":
    test_income_growth()
