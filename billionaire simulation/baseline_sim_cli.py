"""
Baseline Simulation CLI - Simple investment interval analysis

Focuses on understanding how investment timing affects outcomes:
- Income invested on payday (weekly, biweekly, monthly)
- Expenses withdrawn on the 1st of each month
- No life events, just salary + market returns
- Compare different investment frequencies
"""

import json
import numpy as np
import csv
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Literal


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class BaselineConfig:
    """Configuration for baseline simulation."""

    # Personal Info
    current_age: int = 38
    life_expectancy: int = 90

    # Income
    annual_salary: float = 150_000
    tax_rate: float = 0.27
    salary_growth: float = 0.01  # Annual raise

    # Expenses (withdrawn 1st of month)
    monthly_expenses: float = 9_000
    expense_growth: float = 0.01  # Annual inflation

    # Investment Timing
    investment_frequency: Literal['weekly', 'biweekly', 'monthly'] = 'biweekly'

    # Market Parameters
    spy_mean_return: float = 0.10
    spy_volatility: float = 0.18

    # Initial Conditions
    initial_balance: float = 0.0
    initial_cash_buffer: float = 27_000

    # Simulation
    num_simulations: int = 1000
    random_seed: Optional[int] = None

    def save(self, filepath: str) -> None:
        """Save configuration to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> 'BaselineConfig':
        """Load configuration from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls(**data)


# ============================================================================
# SIMULATOR
# ============================================================================

class BaselineSimulator:
    """Simulates basic invest-on-payday, withdraw-on-1st strategy."""

    def __init__(self, config: BaselineConfig):
        self.config = config

        # Calculate periods per year based on frequency
        self.periods_per_year = {
            'weekly': 52,
            'biweekly': 26,
            'monthly': 12,
        }[config.investment_frequency]

    def _generate_returns(self, num_periods: int, seed: Optional[int] = None) -> np.ndarray:
        """Generate market returns for the specified frequency."""
        if seed is not None:
            np.random.seed(seed)

        period_mean = self.config.spy_mean_return / self.periods_per_year
        period_std = self.config.spy_volatility / np.sqrt(self.periods_per_year)

        return np.random.normal(period_mean, period_std, num_periods)

    def run_single_simulation(self, sim_number: int = 0) -> Dict:
        """Run single simulation with specified investment frequency."""
        years = self.config.life_expectancy - self.config.current_age
        total_periods = int(years * self.periods_per_year)

        # Accounts
        investment_balance = self.config.initial_balance
        cash_buffer = self.config.initial_cash_buffer

        # Income/Expenses
        annual_salary = self.config.annual_salary
        monthly_expenses = self.config.monthly_expenses

        # Tracking
        monthly_balances = []  # Track balance on 1st of each month
        total_invested = self.config.initial_balance
        total_withdrawn = 0.0
        last_withdrawal_month = -1  # Track last month we withdrew

        # Generate returns
        seed = (self.config.random_seed + sim_number) if self.config.random_seed else None
        returns = self._generate_returns(total_periods, seed)

        # Calculate investment amount per period
        after_tax_salary = annual_salary * (1 - self.config.tax_rate)
        investment_per_period = after_tax_salary / self.periods_per_year

        for period in range(total_periods):
            age = self.config.current_age + (period / self.periods_per_year)
            year_num = period // self.periods_per_year

            # Determine if it's the 1st of the month
            # Calculate which calendar month we're in (0-11 for each year)
            periods_per_month = self.periods_per_year / 12
            current_month = int(period / periods_per_month)
            is_first_of_month = (current_month != last_withdrawal_month)

            # STEP 1: INVEST (every period = payday)
            investment_balance += investment_per_period
            total_invested += investment_per_period

            # STEP 2: MARKET RETURNS
            investment_balance *= (1 + returns[period])

            # STEP 3: WITHDRAW EXPENSES (on 1st of month)
            if is_first_of_month:
                last_withdrawal_month = current_month  # Mark this month as withdrawn

                if investment_balance >= monthly_expenses:
                    investment_balance -= monthly_expenses
                    total_withdrawn += monthly_expenses
                else:
                    # Use cash buffer for shortfall
                    shortfall = monthly_expenses - investment_balance
                    total_withdrawn += investment_balance
                    investment_balance = 0

                    if cash_buffer >= shortfall:
                        cash_buffer -= shortfall
                        total_withdrawn += shortfall
                    else:
                        # Simulation fails - ran out of money
                        return {
                            'success': False,
                            'failure_age': age,
                            'final_balance': 0.0,
                            'total_invested': total_invested,
                            'total_withdrawn': total_withdrawn,
                            'monthly_balances': monthly_balances,
                        }

                # Record monthly balance
                monthly_balances.append({
                    'month': len(monthly_balances),
                    'age': age,
                    'balance': investment_balance,
                    'cash_buffer': cash_buffer,
                })

            # Annual adjustments (at year boundaries)
            if period > 0 and period % self.periods_per_year == 0:
                annual_salary *= (1 + self.config.salary_growth)
                monthly_expenses *= (1 + self.config.expense_growth)
                after_tax_salary = annual_salary * (1 - self.config.tax_rate)
                investment_per_period = after_tax_salary / self.periods_per_year

        # Success!
        final_balance = investment_balance + cash_buffer

        return {
            'success': True,
            'failure_age': None,
            'final_balance': final_balance,
            'total_invested': total_invested,
            'total_withdrawn': total_withdrawn,
            'monthly_balances': monthly_balances,
            'investment_only': investment_balance,
            'cash_buffer': cash_buffer,
        }

    def run_simulations(self) -> List[Dict]:
        """Run multiple simulations."""
        results = []
        for i in range(self.config.num_simulations):
            results.append(self.run_single_simulation(sim_number=i))
        return results


# ============================================================================
# CSV EXPORT
# ============================================================================

def export_results_to_csv(config: BaselineConfig, results: List[Dict], output_dir: str = '.') -> str:
    """Export simulation results to CSV with unique filename."""

    # Generate unique filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    frequency = config.investment_frequency
    filename = f'baseline_sim_{frequency}_{timestamp}.csv'
    filepath = Path(output_dir) / filename

    # Write summary statistics
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)

        # Header: Configuration
        writer.writerow(['BASELINE SIMULATION RESULTS'])
        writer.writerow(['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])

        # Configuration
        writer.writerow(['CONFIGURATION'])
        writer.writerow(['Investment Frequency', config.investment_frequency])
        writer.writerow(['Annual Salary', f'${config.annual_salary:,.0f}'])
        writer.writerow(['Tax Rate', f'{config.tax_rate*100:.1f}%'])
        writer.writerow(['Monthly Expenses', f'${config.monthly_expenses:,.0f}'])
        writer.writerow(['Age Range', f'{config.current_age} - {config.life_expectancy}'])
        writer.writerow(['Market Return (Mean)', f'{config.spy_mean_return*100:.1f}%'])
        writer.writerow(['Market Volatility (Std)', f'{config.spy_volatility*100:.1f}%'])
        writer.writerow(['Simulations', config.num_simulations])
        writer.writerow([])

        # Summary statistics
        writer.writerow(['SUMMARY STATISTICS'])
        writer.writerow(['Total Simulations', len(results)])
        writer.writerow(['Successful', len(successful)])
        writer.writerow(['Failed', len(failed)])
        writer.writerow(['Success Rate', f'{len(successful)/len(results)*100:.1f}%'])
        writer.writerow([])

        if successful:
            final_balances = [r['final_balance'] for r in successful]
            writer.writerow(['FINAL BALANCE STATISTICS'])
            writer.writerow(['Mean', f'${np.mean(final_balances):,.0f}'])
            writer.writerow(['Median', f'${np.median(final_balances):,.0f}'])
            writer.writerow(['Std Dev', f'${np.std(final_balances):,.0f}'])
            writer.writerow(['Min', f'${np.min(final_balances):,.0f}'])
            writer.writerow(['25th Percentile', f'${np.percentile(final_balances, 25):,.0f}'])
            writer.writerow(['75th Percentile', f'${np.percentile(final_balances, 75):,.0f}'])
            writer.writerow(['Max', f'${np.max(final_balances):,.0f}'])
            writer.writerow([])

        # Individual simulation results
        writer.writerow(['INDIVIDUAL SIMULATION RESULTS'])
        writer.writerow(['Sim #', 'Success', 'Final Balance', 'Investment Balance', 'Cash Buffer',
                        'Total Invested', 'Total Withdrawn', 'Net Gain', 'Failure Age'])

        for i, result in enumerate(results):
            if result['success']:
                net_gain = result['final_balance'] - result['total_invested']
                writer.writerow([
                    i + 1,
                    'Yes',
                    f'${result["final_balance"]:,.0f}',
                    f'${result["investment_only"]:,.0f}',
                    f'${result["cash_buffer"]:,.0f}',
                    f'${result["total_invested"]:,.0f}',
                    f'${result["total_withdrawn"]:,.0f}',
                    f'${net_gain:,.0f}',
                    ''
                ])
            else:
                writer.writerow([
                    i + 1,
                    'No',
                    '$0',
                    '$0',
                    '$0',
                    f'${result["total_invested"]:,.0f}',
                    f'${result["total_withdrawn"]:,.0f}',
                    f'${-result["total_invested"]:,.0f}',
                    f'{result["failure_age"]:.1f}'
                ])

    return str(filepath)


# ============================================================================
# CLI
# ============================================================================

def print_menu():
    """Display main menu."""
    print("\n" + "="*60)
    print("BASELINE SIMULATION CLI")
    print("="*60)
    print("1. Create new configuration")
    print("2. Load configuration from file")
    print("3. Edit current configuration")
    print("4. Run simulation")
    print("5. Compare investment frequencies")
    print("6. Save configuration")
    print("7. Exit")
    print("="*60)


def create_config() -> BaselineConfig:
    """Interactively create new configuration."""
    print("\n--- Create New Configuration ---")

    # Use defaults but allow overrides
    config = BaselineConfig()

    print(f"\nCurrent age [{config.current_age}]: ", end='')
    age_input = input().strip()
    if age_input:
        config.current_age = int(age_input)

    print(f"Life expectancy [{config.life_expectancy}]: ", end='')
    life_input = input().strip()
    if life_input:
        config.life_expectancy = int(life_input)

    print(f"Annual salary [${config.annual_salary:,.0f}]: ", end='')
    salary_input = input().strip()
    if salary_input:
        config.annual_salary = float(salary_input)

    print(f"Monthly expenses [${config.monthly_expenses:,.0f}]: ", end='')
    expense_input = input().strip()
    if expense_input:
        config.monthly_expenses = float(expense_input)

    print(f"\nInvestment frequency (weekly/biweekly/monthly) [{config.investment_frequency}]: ", end='')
    freq_input = input().strip().lower()
    if freq_input in ['weekly', 'biweekly', 'monthly']:
        config.investment_frequency = freq_input

    print(f"Number of simulations [{config.num_simulations}]: ", end='')
    num_input = input().strip()
    if num_input:
        config.num_simulations = int(num_input)

    return config


def edit_config(config: BaselineConfig) -> BaselineConfig:
    """Edit existing configuration."""
    print("\n--- Edit Configuration ---")
    print("Press Enter to keep current value")

    print(f"\nCurrent age [{config.current_age}]: ", end='')
    age_input = input().strip()
    if age_input:
        config.current_age = int(age_input)

    print(f"Annual salary [${config.annual_salary:,.0f}]: ", end='')
    salary_input = input().strip()
    if salary_input:
        config.annual_salary = float(salary_input)

    print(f"Monthly expenses [${config.monthly_expenses:,.0f}]: ", end='')
    expense_input = input().strip()
    if expense_input:
        config.monthly_expenses = float(expense_input)

    print(f"Investment frequency (weekly/biweekly/monthly) [{config.investment_frequency}]: ", end='')
    freq_input = input().strip().lower()
    if freq_input in ['weekly', 'biweekly', 'monthly']:
        config.investment_frequency = freq_input

    print(f"Number of simulations [{config.num_simulations}]: ", end='')
    num_input = input().strip()
    if num_input:
        config.num_simulations = int(num_input)

    return config


def display_config(config: BaselineConfig):
    """Display current configuration."""
    print("\n--- Current Configuration ---")
    print(f"Age: {config.current_age} - {config.life_expectancy} ({config.life_expectancy - config.current_age} years)")
    print(f"Annual Salary: ${config.annual_salary:,.0f} (after tax: ${config.annual_salary * (1-config.tax_rate):,.0f})")
    print(f"Monthly Expenses: ${config.monthly_expenses:,.0f}")
    print(f"Investment Frequency: {config.investment_frequency}")
    print(f"Market Return: {config.spy_mean_return*100:.1f}% ± {config.spy_volatility*100:.1f}%")
    print(f"Simulations: {config.num_simulations}")


def run_simulation(config: BaselineConfig):
    """Run simulation and display results."""
    print(f"\n--- Running {config.num_simulations} simulations ({config.investment_frequency}) ---")

    simulator = BaselineSimulator(config)
    results = simulator.run_simulations()

    # Calculate statistics
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    print(f"\nResults:")
    print(f"  Success Rate: {len(successful)}/{len(results)} ({len(successful)/len(results)*100:.1f}%)")

    if successful:
        final_balances = [r['final_balance'] for r in successful]
        print(f"\n  Final Balance Statistics:")
        print(f"    Mean:   ${np.mean(final_balances):>15,.0f}")
        print(f"    Median: ${np.median(final_balances):>15,.0f}")
        print(f"    Std:    ${np.std(final_balances):>15,.0f}")
        print(f"    Min:    ${np.min(final_balances):>15,.0f}")
        print(f"    Max:    ${np.max(final_balances):>15,.0f}")

    # Export to CSV
    print("\nExporting results to CSV...")
    filepath = export_results_to_csv(config, results)
    print(f"Results saved to: {filepath}")


def compare_frequencies(config: BaselineConfig):
    """Compare different investment frequencies."""
    print("\n--- Comparing Investment Frequencies ---")
    print(f"Running {config.num_simulations} simulations for each frequency...\n")

    frequencies = ['weekly', 'biweekly', 'monthly']
    all_results = {}

    for freq in frequencies:
        freq_config = BaselineConfig(
            current_age=config.current_age,
            life_expectancy=config.life_expectancy,
            annual_salary=config.annual_salary,
            tax_rate=config.tax_rate,
            salary_growth=config.salary_growth,
            monthly_expenses=config.monthly_expenses,
            expense_growth=config.expense_growth,
            investment_frequency=freq,
            spy_mean_return=config.spy_mean_return,
            spy_volatility=config.spy_volatility,
            num_simulations=config.num_simulations,
            random_seed=config.random_seed,
        )

        simulator = BaselineSimulator(freq_config)
        results = simulator.run_simulations()
        all_results[freq] = results

        # Export each to CSV
        filepath = export_results_to_csv(freq_config, results)
        print(f"{freq.capitalize():10} -> {filepath}")

    # Print comparison table
    print("\n" + "="*80)
    print("COMPARISON SUMMARY")
    print("="*80)
    print(f"{'Frequency':<12} {'Success Rate':<15} {'Mean Balance':<20} {'Median Balance':<20}")
    print("-"*80)

    for freq in frequencies:
        results = all_results[freq]
        successful = [r for r in results if r['success']]
        success_rate = len(successful) / len(results) * 100

        if successful:
            final_balances = [r['final_balance'] for r in successful]
            mean_balance = np.mean(final_balances)
            median_balance = np.median(final_balances)
            print(f"{freq.capitalize():<12} {success_rate:>6.1f}%        ${mean_balance:>15,.0f}     ${median_balance:>15,.0f}")
        else:
            print(f"{freq.capitalize():<12} {success_rate:>6.1f}%        $0                  $0")

    print("="*80)


def main():
    """Main CLI loop."""
    config = None

    while True:
        print_menu()

        if config:
            display_config(config)
        else:
            print("\nNo configuration loaded. Create or load one to get started.")

        choice = input("\nSelect option (1-7): ").strip()

        if choice == '1':
            config = create_config()
            print("\nConfiguration created!")

        elif choice == '2':
            filepath = input("Enter config file path: ").strip()
            try:
                config = BaselineConfig.load(filepath)
                print("Configuration loaded!")
            except Exception as e:
                print(f"Error loading config: {e}")

        elif choice == '3':
            if config:
                config = edit_config(config)
                print("Configuration updated!")
            else:
                print("No configuration loaded. Create or load one first.")

        elif choice == '4':
            if config:
                run_simulation(config)
            else:
                print("No configuration loaded. Create or load one first.")

        elif choice == '5':
            if config:
                compare_frequencies(config)
            else:
                print("No configuration loaded. Create or load one first.")

        elif choice == '6':
            if config:
                filepath = input("Enter save path (e.g., baseline_config.json): ").strip()
                config.save(filepath)
                print(f"Configuration saved to {filepath}")
            else:
                print("No configuration loaded. Create or load one first.")

        elif choice == '7':
            print("\nExiting. Goodbye!")
            break

        else:
            print("Invalid option. Please select 1-7.")


if __name__ == "__main__":
    main()
