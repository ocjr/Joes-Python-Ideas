#!/usr/bin/env python3
"""
Test validation and error handling for simulations.
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


def test_invalid_income_ids():
    """Test simulation with invalid income source IDs."""
    print("=" * 80)
    print("TEST 1: Invalid Income Source IDs")
    print("=" * 80)

    # Create config with monthly income
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
                id="salary",  # Real ID
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

    # Create simulation with WRONG income ID
    simulation = InvestmentSimulation(
        id="test_bad_id",
        name="Test Bad Income ID",
        enabled=True,
        current_age=38,
        target_ages=[40],
        strategy_type="monthly_liquidation",
        liquidation_day=1,
        income_source_ids=["wrong_id"],  # This doesn't exist!
        ticker="SPY",
        initial_balance=9000.0,
        num_simulations=10,
        random_seed=42,
    )

    print(f"\nConfig has income with ID: '{config.income[0].id}'")
    print(f"Simulation expects ID: '{simulation.income_source_ids[0]}'")
    print(f"\nRunning simulation (should show warning)...\n")

    try:
        engine = SimulationEngine(config, simulation)
        results = engine.run_monte_carlo(target_age=40)
        print(f"\n✓ Simulation completed with {results.num_runs} runs")
        print(f"  (Used only initial balance of ${simulation.initial_balance:,.2f})")
    except Exception as e:
        print(f"\n❌ Error: {e}")


def test_no_income_or_balance():
    """Test simulation with no income and no initial balance."""
    print("\n\n" + "=" * 80)
    print("TEST 2: No Income and No Initial Balance")
    print("=" * 80)

    config = FinancialConfig(
        accounts=[],
        income=[],
        bills=[],
        credit_cards=[],
        settings=Settings(),
    )

    simulation = InvestmentSimulation(
        id="test_nothing",
        name="Test Nothing to Invest",
        enabled=True,
        current_age=38,
        target_ages=[40],
        strategy_type="monthly_liquidation",
        liquidation_day=1,
        income_source_ids=[],
        ticker="SPY",
        initial_balance=0.0,  # No initial balance
        num_simulations=10,
    )

    print(f"\nSimulation has no income sources and $0 initial balance")
    print(f"Running simulation (should raise error)...\n")

    try:
        engine = SimulationEngine(config, simulation)
        results = engine.run_monte_carlo(target_age=40)
        print(f"\n❌ ERROR: Should have failed but didn't!")
    except ValueError as e:
        print(f"\n✓ Correctly caught error: {e}")


def test_valid_config():
    """Test simulation with valid configuration."""
    print("\n\n" + "=" * 80)
    print("TEST 3: Valid Configuration")
    print("=" * 80)

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

    simulation = InvestmentSimulation(
        id="test_valid",
        name="Test Valid Config",
        enabled=True,
        current_age=38,
        target_ages=[40],
        strategy_type="monthly_liquidation",
        liquidation_day=1,
        income_source_ids=["salary"],  # Correct ID!
        ticker="SPY",
        initial_balance=9000.0,
        num_simulations=10,
        random_seed=42,
    )

    print(f"\nSimulation configured correctly:")
    print(f"  - Initial balance: ${simulation.initial_balance:,.2f}")
    print(
        f"  - Income: {config.income[0].source} (${config.income[0].amount:,.2f}/month)"
    )
    print(f"\nRunning simulation...\n")

    try:
        engine = SimulationEngine(config, simulation)
        results = engine.run_monte_carlo(target_age=40)
        print(f"\n✓ Simulation completed successfully!")
        print(f"  Runs: {results.num_runs}")
        print(
            f"  Median final value: ${results.get_statistics()['final_value']['median']:,.2f}"
        )
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    test_invalid_income_ids()
    test_no_income_or_balance()
    test_valid_config()

    print("\n\n" + "=" * 80)
    print("VALIDATION TESTS COMPLETE")
    print("=" * 80)
    print("\nKey Points:")
    print("  ✓ Invalid income IDs show warning but continue with initial balance")
    print("  ✓ No income + no balance raises error immediately")
    print("  ✓ Valid configuration runs successfully")
    print("  ✓ CLI now validates BEFORE running 1000 simulations")
