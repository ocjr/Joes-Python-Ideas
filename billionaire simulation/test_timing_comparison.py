"""Compare different timing scenarios to see impact of when income/expenses occur."""

from calendar_sim import CalendarConfig, CalendarSimulator, export_results_to_csv
import numpy as np

scenarios = {
    'example_scenarios.json': 'Income on 1st & 15th, Expenses on 1st',
    'scenario_optimal_timing.json': 'Income on 1st & 15th, Expenses on 5th',
    'scenario_poor_timing.json': 'Income on 1st & 15th, Expenses on 16th',
    'scenario_split_expenses.json': 'Income on 1st & 15th, Split expenses on 1st & 15th',
}

print("="*80)
print("TIMING COMPARISON - How payment dates affect outcomes")
print("="*80)
print("All scenarios: $9,125/month income, $9,000/month expenses, 52 years")
print("Question: Does it matter WHEN in the month you get paid vs. spend?\n")

results_by_scenario = {}

for filename, description in scenarios.items():
    print(f"Running: {description}...")

    try:
        config = CalendarConfig.load(filename)
        simulator = CalendarSimulator(config)
        results = simulator.run_simulations()

        successful = [r for r in results if r['success']]

        if successful:
            final_balances = [r['final_balance'] for r in successful]
            market_gains = [r['market_gain'] for r in successful]

            results_by_scenario[description] = {
                'success_rate': len(successful) / len(results) * 100,
                'mean_balance': np.mean(final_balances),
                'median_balance': np.median(final_balances),
                'mean_market_gain': np.mean(market_gains),
                'median_market_gain': np.median(market_gains),
            }

            # Export
            filepath = export_results_to_csv(config, results)
            print(f"  Saved to: {filepath}")
        else:
            print(f"  FAILED: All simulations went bankrupt")

    except FileNotFoundError:
        print(f"  Skipped (file not found): {filename}")

# Print comparison table
print("\n" + "="*80)
print("RESULTS COMPARISON")
print("="*80)
print(f"{'Scenario':<50} {'Mean Balance':<18} {'Median Market Gain':<20}")
print("-"*80)

baseline = None
for scenario, stats in results_by_scenario.items():
    if baseline is None:
        baseline = stats['median_market_gain']

    diff_pct = ((stats['median_market_gain'] - baseline) / baseline) * 100
    diff_str = f"({diff_pct:+.2f}%)" if scenario != list(results_by_scenario.keys())[0] else "(baseline)"

    print(f"{scenario:<50} ${stats['mean_balance']:>14,.0f}    ${stats['median_market_gain']:>12,.0f} {diff_str}")

print("="*80)

# Analysis
print("\nKEY INSIGHTS:")
print("-"*80)

best_scenario = max(results_by_scenario.items(), key=lambda x: x[1]['median_market_gain'])
worst_scenario = min(results_by_scenario.items(), key=lambda x: x[1]['median_market_gain'])

best_gain = best_scenario[1]['median_market_gain']
worst_gain = worst_scenario[1]['median_market_gain']
diff_amount = best_gain - worst_gain
diff_pct = (diff_amount / worst_gain) * 100

print(f"1. BEST timing: {best_scenario[0]}")
print(f"   Median market gain: ${best_gain:,.0f}")
print()
print(f"2. WORST timing: {worst_scenario[0]}")
print(f"   Median market gain: ${worst_gain:,.0f}")
print()
print(f"3. DIFFERENCE: ${diff_amount:,.0f} ({diff_pct:.2f}%)")
print()
print("WHY IT MATTERS:")
print("  - More time between payday and bills = more time for money to compound")
print("  - Getting paid right before bills means money sits invested longer")
print("  - Even small timing differences can compound to large amounts over decades")
print("="*80)
