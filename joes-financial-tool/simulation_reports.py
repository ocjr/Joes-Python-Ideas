#!/usr/bin/env python3
"""
Simulation report generation for Monte Carlo results.

Formats and displays simulation results with percentile statistics,
charts, and detailed breakdowns.
"""

from simulation_engine import MonteCarloResults, SingleRunResult
from datetime import timedelta


def generate_instructions_run(config, simulation_config, months: int = 6):
    """
    Generate a deterministic single run for actionable instructions.

    This always uses Python with seed=0 to produce consistent instructions
    regardless of which engine was used for the main simulation.

    Args:
        config: FinancialConfig
        simulation_config: InvestmentSimulation
        months: Number of months to simulate (default 6)

    Returns:
        SingleRunResult with events for the specified period
    """
    from simulation_engine import SimulationEngine
    from models import InvestmentSimulation
    from datetime import date

    # Create a short-term version of the simulation (just for instructions)
    years_for_months = months / 12.0
    instruction_age = simulation_config.current_age + int(years_for_months) + (1 if years_for_months % 1 > 0 else 0)

    # Copy simulation config but with fixed seed and single run
    instruction_sim = InvestmentSimulation(
        id=simulation_config.id,
        name=f"{simulation_config.name} (Instructions)",
        enabled=True,
        current_age=simulation_config.current_age,
        target_ages=[instruction_age],
        strategy_type=simulation_config.strategy_type,
        hold_days=simulation_config.hold_days,
        liquidation_day=simulation_config.liquidation_day,
        income_source_ids=simulation_config.income_source_ids,
        income_growth_rate=simulation_config.income_growth_rate,
        income_growth_frequency=simulation_config.income_growth_frequency,
        ticker=simulation_config.ticker,
        initial_balance=simulation_config.initial_balance,
        expected_annual_return=simulation_config.expected_annual_return,
        annual_volatility=simulation_config.annual_volatility,
        annual_dividend_yield=simulation_config.annual_dividend_yield,
        expense_ratio=simulation_config.expense_ratio,
        short_term_cap_gains_rate=simulation_config.short_term_cap_gains_rate,
        long_term_cap_gains_rate=simulation_config.long_term_cap_gains_rate,
        dividend_tax_rate=simulation_config.dividend_tax_rate,
        num_simulations=1,
        random_seed=0,  # Fixed seed for deterministic instructions
    )

    engine = SimulationEngine(config, instruction_sim)
    results = engine.run_monte_carlo(target_age=instruction_age, force_python=True)

    return results.runs[0]


def print_actionable_instructions(results: MonteCarloResults, max_instructions: int = 50, config=None):
    """
    Print actionable buy/sell instructions based on a representative run.

    If the results don't have events (Rust run), generates a new deterministic
    Python run with the same configuration to provide instructions.

    Args:
        results: MonteCarloResults from main simulation
        max_instructions: Maximum number of instructions to show
        config: FinancialConfig (required if results have no events)
    """
    print("\n" + "=" * 80)
    print(f"  ACTIONABLE INVESTMENT INSTRUCTIONS")
    print("=" * 80)

    # Check if we need to generate instructions
    sample_run = None
    if not results.runs or len(results.runs[0].events) == 0:
        if config is None:
            print("\n⚠️  No transaction events available and no config provided.")
            print("   Pass config parameter to generate instructions.")
            print("\n" + "=" * 80)
            return

        print("\n📊 Generating deterministic instruction schedule...")
        print("   (Running 6-month Python simulation for transaction details)")
        print()

        sample_run = generate_instructions_run(config, results.simulation_config, months=6)
    else:
        sample_run = results.runs[0]

    ticker = results.simulation_config.ticker

    print(f"\nThese instructions are based on a sample simulation run.")
    print(f"Actual prices and amounts will vary based on market conditions.\n")

    print(f"Strategy: {results.simulation_config.strategy_type}")
    if results.simulation_config.strategy_type == "monthly_liquidation":
        print(f"Liquidation schedule: Day {results.simulation_config.liquidation_day} of each month\n")

    # Display income growth info if applicable
    if results.simulation_config.income_growth_rate > 0:
        print(f"📈 Income Growth: {results.simulation_config.income_growth_rate*100:.1f}% every {results.simulation_config.income_growth_frequency} year(s)")
        print(f"   Your income will increase over time in the simulation.\n")

    print("-" * 80)

    # Group events by type and limit display
    events_to_show = sample_run.events[:max_instructions]

    current_year = None
    current_month = None
    for i, event in enumerate(events_to_show, 1):
        # Year separator
        if current_year != event.date.year:
            if current_year is not None:
                print()
            current_year = event.date.year
            print(f"\n{'='*80}")
            print(f"YEAR {current_year} (Age {results.simulation_config.current_age + (current_year - sample_run.events[0].date.year)})")
            print(f"{'='*80}\n")
            current_month = None

        # Month separator (less prominent)
        if current_month != event.date.month:
            if current_month is not None:
                print()
            current_month = event.date.month
            print(f"{event.date.strftime('%B %Y')}")
            print("-" * 40)

        # Format instruction based on event type - simple and direct
        day_str = event.date.strftime("%d").lstrip('0')  # Remove leading zero (e.g., "3" instead of "03")
        day_of_week = event.date.strftime("%a")  # Mon, Tue, etc.

        if event.event_type == 'buy':
            if "Initial" in event.notes:
                print(f"  {day_str} ({day_of_week}): Buy ${abs(event.amount):,.0f} worth of {ticker} (initial investment)")
            else:
                print(f"  {day_str} ({day_of_week}): Buy ${abs(event.amount):,.0f} worth of {ticker}")

        elif event.event_type == 'sell':
            if event.tax_owed > 0:
                print(f"  {day_str} ({day_of_week}): Sell ${event.amount:,.0f} worth of {ticker} (tax: ${event.tax_owed:.2f})")
            else:
                print(f"  {day_str} ({day_of_week}): Sell ${event.amount:,.0f} worth of {ticker}")

        elif event.event_type == 'dividend':
            net = event.amount - event.tax_owed
            print(f"  {day_str} ({day_of_week}): Receive dividend ${net:.2f} (auto-reinvest)")

    if len(sample_run.events) > max_instructions:
        remaining = len(sample_run.events) - max_instructions
        print(f"\n... and {remaining} more transactions over the remaining years")

    # Summary
    print("\n" + "=" * 80)
    print("NOTES")
    print("=" * 80)
    print(f"""
• Set calendar reminders for each buy/sell date
• Keep records of all transactions for taxes (you'll need basis tracking)
• These are projections - actual prices will vary
• Consider setting up automatic investments if your broker supports it

""")

    print("=" * 80)


def print_simulation_summary(results: MonteCarloResults):
    """Print a comprehensive summary of simulation results."""
    stats = results.get_statistics()

    print("\n" + "=" * 80)
    print(f"  SIMULATION RESULTS: {results.simulation_config.name}")
    print("=" * 80)

    # Check if this is a partial result (interrupted)
    if results.num_runs < results.simulation_config.num_simulations:
        print(f"\n⚠️  PARTIAL RESULTS: {results.num_runs} of {results.simulation_config.num_simulations} runs completed")
        print(f"   Results may be less reliable with fewer simulations\n")

    print(f"\nConfiguration:")
    print(f"  Strategy: {results.simulation_config.strategy_type}")
    if results.simulation_config.strategy_type == "monthly_liquidation":
        print(f"  Liquidation day: {results.simulation_config.liquidation_day}")
    else:
        print(f"  Hold period: {results.simulation_config.hold_days} days")
    print(f"  Current age: {results.simulation_config.current_age}")
    print(f"  Target age: {results.target_age}")
    print(f"  Years simulated: {results.target_age - results.simulation_config.current_age}")
    print(f"  Number of runs: {results.num_runs}")
    print(f"  Expected return: {results.simulation_config.expected_annual_return*100:.1f}%")
    print(f"  Volatility: {results.simulation_config.annual_volatility*100:.1f}%")

    print(f"\n" + "-" * 80)
    print("FINAL ACCOUNT VALUE AT AGE", results.target_age)
    print("-" * 80)

    print(f"\n  {'Percentile':<15} {'Value':>15}")
    print(f"  {'-'*15} {'-'*15}")
    print(f"  {'Worst case':<15} ${stats['final_value']['min']:>14,.2f}")
    print(f"  {'10th':<15} ${stats['final_value']['p10']:>14,.2f}")
    print(f"  {'25th':<15} ${stats['final_value']['p25']:>14,.2f}")
    print(f"  {'Median (50th)':<15} ${stats['final_value']['median']:>14,.2f}")
    print(f"  {'75th':<15} ${stats['final_value']['p75']:>14,.2f}")
    print(f"  {'90th':<15} ${stats['final_value']['p90']:>14,.2f}")
    print(f"  {'Best case':<15} ${stats['final_value']['max']:>14,.2f}")
    print(f"  {'-'*15} {'-'*15}")
    print(f"  {'Mean':<15} ${stats['final_value']['mean']:>14,.2f}")

    print(f"\n" + "-" * 80)
    print("NET GAIN/LOSS FROM STRATEGY")
    print("-" * 80)

    print(f"\n  {'Percentile':<15} {'Value':>15}")
    print(f"  {'-'*15} {'-'*15}")
    print(f"  {'Worst case':<15} ${stats['net_gain']['min']:>14,.2f}")
    print(f"  {'10th':<15} ${stats['net_gain']['p10']:>14,.2f}")
    print(f"  {'Median (50th)':<15} ${stats['net_gain']['median']:>14,.2f}")
    print(f"  {'90th':<15} ${stats['net_gain']['p90']:>14,.2f}")
    print(f"  {'Best case':<15} ${stats['net_gain']['max']:>14,.2f}")
    print(f"  {'-'*15} {'-'*15}")
    print(f"  {'Mean':<15} ${stats['net_gain']['mean']:>14,.2f}")

    print(f"\n" + "-" * 80)
    print("CASH FLOW SUMMARY (Average Across All Runs)")
    print("-" * 80)

    print(f"\n  Total invested:  ${stats['total_invested']['mean']:>14,.2f}")
    print(f"  Total withdrawn: ${stats['total_withdrawn']['mean']:>14,.2f}")
    print(f"  Total taxes:     ${stats['total_taxes']['mean']:>14,.2f}")

    # Calculate probability of positive gain
    positive_gains = sum(1 for run in results.runs if run.net_gain > 0)
    prob_positive = (positive_gains / results.num_runs) * 100

    print(f"\n" + "-" * 80)
    print("RISK ANALYSIS")
    print("-" * 80)
    print(f"\n  Probability of positive gain: {prob_positive:.1f}%")
    print(f"  Probability of loss:          {100-prob_positive:.1f}%")

    # Show distribution
    print(f"\n  Distribution of outcomes:")
    ranges = [
        ("Significant loss (< -$500)", lambda x: x.net_gain < -500),
        ("Small loss ($-500 to $0)", lambda x: -500 <= x.net_gain < 0),
        ("Small gain ($0 to $1,000)", lambda x: 0 <= x.net_gain < 1000),
        ("Moderate gain ($1,000 to $5,000)", lambda x: 1000 <= x.net_gain < 5000),
        ("Large gain (>= $5,000)", lambda x: x.net_gain >= 5000),
    ]

    for label, condition in ranges:
        count = sum(1 for run in results.runs if condition(run))
        pct = (count / results.num_runs) * 100
        bar = "█" * int(pct / 2)
        print(f"    {label:<35} {pct:>5.1f}% {bar}")

    print("\n" + "=" * 80)


def print_sample_run(run: SingleRunResult, max_events: int = 20):
    """Print details from a single simulation run."""
    print("\n" + "=" * 80)
    print(f"  SAMPLE RUN #{run.run_number}")
    print("=" * 80)

    print(f"\nFinal Results:")
    print(f"  Final age:           {run.final_age}")
    print(f"  Final account value: ${run.final_account_value:,.2f}")
    print(f"  Total invested:      ${run.total_invested:,.2f}")
    print(f"  Total withdrawn:     ${run.total_withdrawn:,.2f}")
    print(f"  Total dividends:     ${run.total_dividends:,.2f}")
    print(f"  Total taxes paid:    ${run.total_taxes_paid:,.2f}")
    print(f"  Net gain:            ${run.net_gain:,.2f}")

    # Count event types
    buy_events = [e for e in run.events if e.event_type == 'buy']
    sell_events = [e for e in run.events if e.event_type == 'sell']
    dividend_events = [e for e in run.events if e.event_type == 'dividend']

    print(f"\nEvent Summary:")
    print(f"  Total events:    {len(run.events)}")
    print(f"  Buy events:      {len(buy_events)}")
    print(f"  Sell events:     {len(sell_events)}")
    print(f"  Dividend events: {len(dividend_events)}")

    if len(run.events) > 0:
        print(f"\nFirst {min(max_events, len(run.events))} Events:")
        for i, event in enumerate(run.events[:max_events]):
            print(f"\n  {i+1}. {event.date.strftime('%Y-%m-%d')} - {event.event_type.upper()}")
            print(f"     Shares: {event.shares:.4f} @ ${event.price_per_share:.2f}")
            if event.amount < 0:
                print(f"     Cost: ${abs(event.amount):,.2f}")
            else:
                print(f"     Proceeds: ${event.amount:,.2f}")
            if event.tax_owed > 0:
                print(f"     Tax owed: ${event.tax_owed:.2f}")
            if event.notes:
                print(f"     Note: {event.notes}")

    print("\n" + "=" * 80)


def compare_strategies(results_list: list[MonteCarloResults]):
    """Compare multiple simulation results side by side."""
    if len(results_list) < 2:
        print("Need at least 2 simulations to compare.")
        return

    print("\n" + "=" * 80)
    print("  STRATEGY COMPARISON")
    print("=" * 80)

    # Header
    print(f"\n{'Metric':<30}", end="")
    for result in results_list:
        print(f"{result.simulation_config.name[:20]:>22}", end="")
    print()
    print("-" * (30 + 22 * len(results_list)))

    # Compare key metrics
    metrics = [
        ("Strategy", lambda r: r.simulation_config.strategy_type),
        ("Target Age", lambda r: r.target_age),
        ("Num Runs", lambda r: r.num_runs),
        ("", lambda r: ""),  # Separator
        ("Median Final Value", lambda r: f"${r.get_statistics()['final_value']['median']:,.2f}"),
        ("Mean Final Value", lambda r: f"${r.get_statistics()['final_value']['mean']:,.2f}"),
        ("90th Percentile Value", lambda r: f"${r.get_statistics()['final_value']['p90']:,.2f}"),
        ("10th Percentile Value", lambda r: f"${r.get_statistics()['final_value']['p10']:,.2f}"),
        ("", lambda r: ""),  # Separator
        ("Median Net Gain", lambda r: f"${r.get_statistics()['net_gain']['median']:,.2f}"),
        ("Mean Net Gain", lambda r: f"${r.get_statistics()['net_gain']['mean']:,.2f}"),
        ("90th Percentile Gain", lambda r: f"${r.get_statistics()['net_gain']['p90']:,.2f}"),
        ("10th Percentile Gain", lambda r: f"${r.get_statistics()['net_gain']['p10']:,.2f}"),
        ("", lambda r: ""),  # Separator
        ("Prob. Positive Gain", lambda r: f"{(sum(1 for run in r.runs if run.net_gain > 0) / r.num_runs * 100):.1f}%"),
        ("Avg Taxes Paid", lambda r: f"${r.get_statistics()['total_taxes']['mean']:,.2f}"),
    ]

    for label, func in metrics:
        if label == "":
            print()
            continue
        print(f"{label:<30}", end="")
        for result in results_list:
            value = func(result)
            print(f"{str(value):>22}", end="")
        print()

    print("\n" + "=" * 80)


def export_results_to_csv(results: MonteCarloResults, filename: str):
    """Export simulation results to CSV for further analysis."""
    import csv

    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)

        # Header
        writer.writerow([
            'run_number', 'final_age', 'final_account_value',
            'total_invested', 'total_withdrawn', 'total_taxes_paid',
            'total_dividends', 'net_gain'
        ])

        # Data rows
        for run in results.runs:
            writer.writerow([
                run.run_number,
                run.final_age,
                run.final_account_value,
                run.total_invested,
                run.total_withdrawn,
                run.total_taxes_paid,
                run.total_dividends,
                run.net_gain,
            ])

    print(f"✅ Exported {len(results.runs)} simulation runs to {filename}")
