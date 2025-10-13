"""Compare weekly, biweekly, and monthly investment frequencies."""

from baseline_sim_cli import BaselineConfig, BaselineSimulator, export_results_to_csv
import numpy as np

# Base configuration
base_config = {
    'current_age': 38,
    'life_expectancy': 90,
    'annual_salary': 150_000,
    'tax_rate': 0.27,
    'monthly_expenses': 9_000,
    'num_simulations': 1000,
    'random_seed': 42,  # For reproducibility
}

frequencies = ['weekly', 'biweekly', 'monthly']
results_by_freq = {}

print("="*80)
print("INVESTMENT FREQUENCY COMPARISON")
print("="*80)
print(f"Salary: ${base_config['annual_salary']:,.0f}/year")
print(f"Expenses: ${base_config['monthly_expenses']:,.0f}/month")
print(f"Age: {base_config['current_age']} - {base_config['life_expectancy']} ({base_config['life_expectancy'] - base_config['current_age']} years)")
print(f"Simulations: {base_config['num_simulations']}\n")

for freq in frequencies:
    print(f"Running {freq} simulations...")

    config = BaselineConfig(**{**base_config, 'investment_frequency': freq})
    simulator = BaselineSimulator(config)
    results = simulator.run_simulations()

    successful = [r for r in results if r['success']]
    final_balances = [r['final_balance'] for r in successful]

    results_by_freq[freq] = {
        'results': results,
        'config': config,
        'success_rate': len(successful) / len(results) * 100,
        'mean': np.mean(final_balances) if successful else 0,
        'median': np.median(final_balances) if successful else 0,
        'std': np.std(final_balances) if successful else 0,
        'min': np.min(final_balances) if successful else 0,
        'max': np.max(final_balances) if successful else 0,
    }

    # Export to CSV
    filepath = export_results_to_csv(config, results)
    print(f"  Saved to: {filepath}")

# Print comparison table
print("\n" + "="*80)
print("RESULTS COMPARISON")
print("="*80)
print(f"{'Frequency':<12} {'Success':<10} {'Mean Balance':<18} {'Median Balance':<18} {'Std Dev':<15}")
print("-"*80)

for freq in frequencies:
    stats = results_by_freq[freq]
    print(f"{freq.capitalize():<12} {stats['success_rate']:>6.1f}%    ${stats['mean']:>14,.0f}    ${stats['median']:>14,.0f}    ${stats['std']:>12,.0f}")

print("="*80)

# Analysis
print("\nKEY INSIGHTS:")
print("-"*80)

mean_values = {freq: results_by_freq[freq]['mean'] for freq in frequencies}
median_values = {freq: results_by_freq[freq]['median'] for freq in frequencies}

best_mean = max(mean_values, key=mean_values.get)
best_median = max(median_values, key=median_values.get)

print(f"1. Highest mean balance: {best_mean.capitalize()} (${mean_values[best_mean]:,.0f})")
print(f"2. Highest median balance: {best_median.capitalize()} (${median_values[best_median]:,.0f})")

# Calculate differences
weekly_mean = mean_values['weekly']
monthly_mean = mean_values['monthly']
diff_pct = ((weekly_mean - monthly_mean) / monthly_mean) * 100

print(f"3. Difference (weekly vs monthly): {diff_pct:+.2f}%")

print("\nWHY THE DIFFERENCE?")
print("-"*80)
print("More frequent investing (weekly) provides:")
print("  - Better dollar-cost averaging (more opportunities to buy dips)")
print("  - More consistent market exposure throughout the month")
print("  - Less timing risk from single large deposits")
print("\nLess frequent investing (monthly) means:")
print("  - Larger lump sums exposed to market volatility")
print("  - Higher timing risk (one bad day affects entire month's investment)")
print("  - But fewer transactions in real-world scenarios")
print("="*80)
