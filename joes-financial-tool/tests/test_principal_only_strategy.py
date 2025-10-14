#!/usr/bin/env python3
"""
Test and compare principal_only strategy vs monthly_liquidation.

Shows the tax savings and wealth accumulation benefits of only selling principal
while letting gains compound.
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


def run_comparison():
    """Compare monthly_liquidation vs principal_only strategies."""
    print("=" * 80)
    print("  STRATEGY COMPARISON: monthly_liquidation vs principal_only")
    print("=" * 80)
    print()

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
                amount=1500.00,  # $1500 every 2 weeks = 26 paychecks/year
                frequency=Frequency.BIWEEKLY,
                next_date=date(2025, 10, 17),
                deposit_account="checking",
            )
        ],
        bills=[],
        credit_cards=[],
        settings=Settings(),
    )

    print("📊 SCENARIO:")
    print(f"   Income: ${config.income[0].amount:,.2f} every 2 weeks (26 paychecks/year)")
    print(f"   Initial balance: $5,000")
    print(f"   Simulation period: 2 years (age 38 → 40)")
    print(f"   Liquidation day: 1st of each month")
    print()

    # Disable Rust for detailed events
    import simulation_engine
    original_rust = simulation_engine.RUST_AVAILABLE
    simulation_engine.RUST_AVAILABLE = False

    results = {}

    try:
        # Test 1: Monthly liquidation (current strategy)
        print("=" * 80)
        print("TEST 1: Monthly Liquidation Strategy")
        print("=" * 80)
        print("Strategy: Sell all shares (principal + gains) on the 1st of each month")
        print()

        sim_monthly = InvestmentSimulation(
            id="test_monthly",
            name="Monthly Liquidation Test",
            enabled=True,
            current_age=38,
            target_ages=[40],
            strategy_type="monthly_liquidation",
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
            num_simulations=1,
            random_seed=42,
        )

        engine_monthly = SimulationEngine(config, sim_monthly)
        results_monthly = engine_monthly.run_monte_carlo(target_age=40)
        run_monthly = results_monthly.runs[0]

        print(f"✓ Simulation complete")
        print()
        print(f"Results:")
        print(f"  Total invested:      ${run_monthly.total_invested:>12,.2f}")
        print(f"  Total withdrawn:     ${run_monthly.total_withdrawn:>12,.2f}")
        print(f"  Final account value: ${run_monthly.final_account_value:>12,.2f}")
        print(f"  Total taxes paid:    ${run_monthly.total_taxes_paid:>12,.2f}  ⚠️")
        print(f"  Net gain:            ${run_monthly.net_gain:>12,.2f}")
        print()

        results["monthly"] = run_monthly

        # Test 2: Principal-only strategy
        print("=" * 80)
        print("TEST 2: Principal-Only Strategy 🆕")
        print("=" * 80)
        print("Strategy: Sell only enough shares to recover paycheck amounts")
        print("          Let all gains stay invested and compound!")
        print()

        sim_principal = InvestmentSimulation(
            id="test_principal",
            name="Principal-Only Test",
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
            num_simulations=1,
            random_seed=42,
        )

        engine_principal = SimulationEngine(config, sim_principal)
        results_principal = engine_principal.run_monte_carlo(target_age=40)
        run_principal = results_principal.runs[0]

        print(f"✓ Simulation complete")
        print()
        print(f"Results:")
        print(f"  Total invested:      ${run_principal.total_invested:>12,.2f}")
        print(f"  Total withdrawn:     ${run_principal.total_withdrawn:>12,.2f}")
        print(f"  Final account value: ${run_principal.final_account_value:>12,.2f}  ⬆️")
        print(f"  Total taxes paid:    ${run_principal.total_taxes_paid:>12,.2f}  ⬇️")
        print(f"  Net gain:            ${run_principal.net_gain:>12,.2f}")
        print()

        results["principal"] = run_principal

        # Comparison
        print("=" * 80)
        print("COMPARISON & ANALYSIS")
        print("=" * 80)
        print()

        tax_savings = run_monthly.total_taxes_paid - run_principal.total_taxes_paid
        tax_savings_pct = (tax_savings / run_monthly.total_taxes_paid) * 100 if run_monthly.total_taxes_paid > 0 else 0

        final_value_increase = run_principal.final_account_value - run_monthly.final_account_value
        net_gain_increase = run_principal.net_gain - run_monthly.net_gain

        print(f"💰 TAX SAVINGS:")
        print(f"   Monthly liquidation taxes: ${run_monthly.total_taxes_paid:,.2f}")
        print(f"   Principal-only taxes:      ${run_principal.total_taxes_paid:,.2f}")
        print(f"   {'─' * 50}")
        print(f"   TAX SAVINGS:               ${tax_savings:,.2f} ({tax_savings_pct:.1f}% reduction)")
        print()

        print(f"📈 WEALTH ACCUMULATION:")
        print(f"   Monthly liquidation final value: ${run_monthly.final_account_value:,.2f}")
        print(f"   Principal-only final value:      ${run_principal.final_account_value:,.2f}")
        print(f"   {'─' * 50}")
        print(f"   ADDITIONAL WEALTH:               ${final_value_increase:,.2f}")
        print()

        print(f"🎯 NET GAIN COMPARISON:")
        print(f"   Monthly liquidation net gain: ${run_monthly.net_gain:,.2f}")
        print(f"   Principal-only net gain:      ${run_principal.net_gain:,.2f}")
        print(f"   {'─' * 50}")
        print(f"   IMPROVEMENT:                  ${net_gain_increase:,.2f} ({(net_gain_increase/run_monthly.net_gain)*100:.1f}% better)")
        print()

        # ROI comparison
        roi_monthly = (run_monthly.net_gain / run_monthly.total_invested) * 100
        roi_principal = (run_principal.net_gain / run_principal.total_invested) * 100

        print(f"📊 RETURN ON INVESTMENT:")
        print(f"   Monthly liquidation ROI: {roi_monthly:.2f}%")
        print(f"   Principal-only ROI:      {roi_principal:.2f}%")
        print(f"   Improvement:             {roi_principal - roi_monthly:.2f} percentage points")
        print()

        print("=" * 80)
        print("WHY PRINCIPAL-ONLY IS BETTER")
        print("=" * 80)
        print()
        print("1. 📉 LOWER TAX DRAG:")
        print("   • You only pay taxes on gains when you sell principal")
        print("   • Most gains stay invested and untaxed")
        print("   • Accumulated gains may eventually qualify for long-term rates (15% vs 22%)")
        print()
        print("2. 📈 BETTER COMPOUNDING:")
        print("   • Gains stay in the market and generate returns")
        print("   • You're investing \"free money\" (market gains)")
        print("   • The longer you run this, the bigger the advantage")
        print()
        print("3. 💵 SAME LIQUIDITY:")
        print("   • You still get your paycheck amount back each month")
        print("   • Can pay bills and expenses as planned")
        print("   • But you're building wealth on the side")
        print()
        print("4. 🎯 PERFECT FOR YOUR USE CASE:")
        print("   • You said: 'I am investing money I wouldn't have been able to invest'")
        print("   • Principal-only lets you use money for expenses AND build wealth")
        print(f"   • After 2 years, you have ${final_value_increase:,.0f} more invested!")
        print()

        # Show some sample events
        print("=" * 80)
        print("SAMPLE TRANSACTIONS (First 10 Events)")
        print("=" * 80)
        print()
        print("PRINCIPAL-ONLY STRATEGY:")
        for i, event in enumerate(run_principal.events[:10], 1):
            print(f"{i}. {event.date.strftime('%Y-%m-%d')} - {event.event_type.upper()}")
            print(f"   Amount: ${abs(event.amount):,.2f}")
            if event.tax_owed > 0:
                print(f"   Tax: ${event.tax_owed:.2f}")
            if event.notes:
                print(f"   {event.notes}")
            print()

    finally:
        simulation_engine.RUST_AVAILABLE = original_rust

    print("=" * 80)
    print("BOTTOM LINE")
    print("=" * 80)
    print()
    print(f"✅ Principal-only strategy saves you ${tax_savings:,.2f} in taxes")
    print(f"✅ You end up with ${final_value_increase:,.2f} more wealth")
    print(f"✅ Same liquidity - you still get your money back for expenses")
    print(f"✅ Better for long-term wealth building")
    print()
    print("🎯 RECOMMENDATION: Use 'principal_only' strategy for the float approach!")
    print()


if __name__ == "__main__":
    run_comparison()
