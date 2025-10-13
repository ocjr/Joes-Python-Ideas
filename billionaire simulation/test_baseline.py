"""Quick test of baseline simulator."""

from baseline_sim_cli import BaselineConfig, BaselineSimulator, export_results_to_csv

# Load example config
config = BaselineConfig.load('example_baseline_config.json')

print("Configuration loaded:")
print(f"  Age: {config.current_age} - {config.life_expectancy}")
print(f"  Salary: ${config.annual_salary:,.0f}")
print(f"  Expenses: ${config.monthly_expenses:,.0f}/month")
print(f"  Frequency: {config.investment_frequency}")
print(f"  Simulations: {config.num_simulations}")

# Run simulation
print(f"\nRunning {config.num_simulations} simulations...")
simulator = BaselineSimulator(config)
results = simulator.run_simulations()

# Show results
successful = [r for r in results if r['success']]
print(f"\nSuccess Rate: {len(successful)}/{len(results)} ({len(successful)/len(results)*100:.1f}%)")

if successful:
    import numpy as np
    final_balances = [r['final_balance'] for r in successful]
    print(f"Mean Final Balance: ${np.mean(final_balances):,.0f}")
    print(f"Median Final Balance: ${np.median(final_balances):,.0f}")

# Export to CSV
print("\nExporting to CSV...")
filepath = export_results_to_csv(config, results)
print(f"Saved to: {filepath}")
