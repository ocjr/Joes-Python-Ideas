#!/usr/bin/env python3
"""
Detailed explanation of net gain/loss calculation.

Shows exactly what the numbers mean in the float strategy.
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


def explain_net_gain():
    """Run a simple simulation and explain the net gain calculation."""
    print("=" * 80)
    print("  NET GAIN/LOSS CALCULATION EXPLAINED")
    print("=" * 80)
    print()

    # Create simple test config
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

    # Simple 1-year simulation
    simulation = InvestmentSimulation(
        id="test",
        name="Net Gain Test",
        enabled=True,
        current_age=38,
        target_ages=[39],  # Just 1 year
        strategy_type="monthly_liquidation",
        liquidation_day=1,
        income_source_ids=["salary"],
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
        num_simulations=1,  # Just 1 run for clarity
        random_seed=42,
    )

    # Disable Rust for detailed events
    import simulation_engine
    original_rust = simulation_engine.RUST_AVAILABLE
    simulation_engine.RUST_AVAILABLE = False

    try:
        engine = SimulationEngine(config, simulation)
        results = engine.run_monte_carlo(target_age=39)

        # Get the single run
        run = results.runs[0]

        print("\n" + "=" * 80)
        print("WHAT HAPPENED IN THE SIMULATION")
        print("=" * 80)
        print()

        print("📊 THE FLOAT STRATEGY:")
        print("   1. You invest your paycheck when it arrives")
        print("   2. You sell it ~1 month later to get cash for expenses")
        print("   3. Profit comes from market gains during the hold period")
        print("   4. You also keep shares from your initial balance")
        print()

        print("=" * 80)
        print("CASH FLOW BREAKDOWN")
        print("=" * 80)
        print()

        print(f"💰 MONEY IN (Total Invested):")
        print(f"   Initial balance:        ${simulation.initial_balance:>12,.2f}")
        print(f"   All paychecks invested: ${run.total_invested - simulation.initial_balance:>12,.2f}")
        print(f"   {'─' * 40}")
        print(f"   TOTAL INVESTED:         ${run.total_invested:>12,.2f}")
        print()

        print(f"💸 MONEY OUT:")
        print(f"   Sold for expenses:      ${run.total_withdrawn:>12,.2f}")
        print(f"   Taxes paid:             ${run.total_taxes_paid:>12,.2f}")
        print(f"   {'─' * 40}")
        print(f"   TOTAL OUT:              ${run.total_withdrawn + run.total_taxes_paid:>12,.2f}")
        print()

        print(f"📈 MONEY STILL IN MARKET:")
        print(f"   Final account value:    ${run.final_account_value:>12,.2f}")
        print(f"   (Shares you still own)")
        print()

        print("=" * 80)
        print("NET GAIN CALCULATION")
        print("=" * 80)
        print()

        print("Formula:")
        print("  Net Gain = (Final Value + Total Withdrawn) - Total Invested - Taxes")
        print()

        total_received = run.final_account_value + run.total_withdrawn
        total_spent = run.total_invested + run.total_taxes_paid
        net_gain = run.net_gain

        print(f"  Net Gain = (${run.final_account_value:,.2f} + ${run.total_withdrawn:,.2f}) - ${run.total_invested:,.2f} - ${run.total_taxes_paid:,.2f}")
        print(f"  Net Gain = ${total_received:,.2f} - ${total_spent:,.2f}")
        print(f"  Net Gain = ${net_gain:,.2f}")
        print()

        print("=" * 80)
        print("WHAT THIS MEANS")
        print("=" * 80)
        print()

        if net_gain > 0:
            print(f"✅ You're UP ${net_gain:,.2f}")
            print()
            print(f"   You put in:  ${run.total_invested:,.2f}")
            print(f"   You got out: ${total_received:,.2f} (withdrawals + remaining shares)")
            print(f"   After taxes: ${net_gain:,.2f} profit")
            print()
            gain_pct = (net_gain / run.total_invested) * 100
            print(f"   That's a {gain_pct:.2f}% return on invested capital")
        else:
            print(f"❌ You're DOWN ${abs(net_gain):,.2f}")
            print()
            print("   The market went down during your holding periods")

        print()
        print("=" * 80)
        print("WHY THE GAINS SEEM SMALL")
        print("=" * 80)
        print()

        print("The 'float strategy' doesn't make huge returns because:")
        print()
        print("  1. ⏱️  SHORT HOLDING PERIODS:")
        print("     You only hold each paycheck for ~1 month")
        print("     Even with 10% annual returns, that's ~0.83% per month")
        print()
        print("  2. 🔄 CONSTANT TURNOVER:")
        print("     You're constantly buying and selling (high tax drag)")
        print("     Most gains are short-term = higher tax rate (22% vs 15%)")
        print()
        print("  3. 💰 INITIAL BALANCE GAINS:")
        print("     Most of your profit comes from the initial $5,000")
        print("     That stays invested the whole time and compounds")
        print()
        print("  4. 📊 MARKET VOLATILITY:")
        print("     Sometimes the market is UP when you sell (gain)")
        print("     Sometimes it's DOWN when you sell (loss)")
        print()

        # Show the actual events
        print("=" * 80)
        print(f"TRANSACTION DETAIL (First 10 events)")
        print("=" * 80)
        print()

        for i, event in enumerate(run.events[:10], 1):
            print(f"{i}. {event.date.strftime('%Y-%m-%d')} - {event.event_type.upper()}")
            print(f"   Amount: ${abs(event.amount):,.2f}")
            if event.tax_owed > 0:
                print(f"   Tax: ${event.tax_owed:.2f}")
            print(f"   {event.notes}")
            print()

        # Calculate effective return
        print("=" * 80)
        print("EFFECTIVE RETURN ANALYSIS")
        print("=" * 80)
        print()

        # Time period
        years = 1.0
        effective_return = (net_gain / run.total_invested) * 100
        annualized_return = effective_return / years

        print(f"Period: {years:.1f} year(s)")
        print(f"Money at risk: ${run.total_invested:,.2f}")
        print(f"Profit: ${net_gain:,.2f}")
        print(f"Return: {effective_return:.2f}%")
        print(f"Annualized: {annualized_return:.2f}%")
        print()

        if annualized_return < simulation.expected_annual_return * 100:
            expected = simulation.expected_annual_return * 100
            print(f"⚠️  This is LESS than the expected {expected:.0f}% annual return because:")
            print(f"   - You're not fully invested the whole time")
            print(f"   - Short-term capital gains taxes eat into profits")
            print(f"   - Transaction costs and timing losses")

        print()
        print("=" * 80)
        print("BOTTOM LINE")
        print("=" * 80)
        print()
        print("The 'float strategy' is designed for:")
        print("  ✓ Earning *some* return on money that would otherwise sit idle")
        print("  ✓ Keeping liquidity - you get your cash back each month")
        print("  ✓ Low commitment - you're not locking money away long-term")
        print()
        print("It's NOT designed for:")
        print("  ✗ Maximizing returns (buy-and-hold is better for that)")
        print("  ✗ Tax efficiency (you pay short-term gains tax)")
        print("  ✗ Compounding growth (you keep withdrawing)")
        print()
        print("Think of it as 'better than a savings account, worse than investing'")
        print()

    finally:
        simulation_engine.RUST_AVAILABLE = original_rust


if __name__ == "__main__":
    explain_net_gain()
