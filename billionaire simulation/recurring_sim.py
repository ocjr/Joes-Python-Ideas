"""
Recurring Cash Flow Simulation - Exact start dates with recurring schedules

Realistic modeling with:
- Income: "I get $3,000 biweekly starting 10-17-25"
- Expenses: "I withdraw $2,000 weekly starting 10-13-25"
- Day-by-day simulation with exact date matching
- Auto-load configuration if available
"""

import json
import numpy as np
import csv
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Literal


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class RecurringIncome:
    """Income that recurs at a specific frequency from a start date."""
    amount: float
    start_date: str  # Format: "YYYY-MM-DD"
    frequency: Literal['weekly', 'biweekly', 'monthly', 'quarterly', 'annual']
    description: str = "Income"
    annual_growth: float = 0.01

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'RecurringIncome':
        return cls(**data)


@dataclass
class RecurringExpense:
    """Expense that recurs at a specific frequency from a start date."""
    amount: float
    start_date: str  # Format: "YYYY-MM-DD"
    frequency: Literal['weekly', 'biweekly', 'monthly', 'quarterly', 'annual']
    description: str = "Expense"
    annual_growth: float = 0.01

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'RecurringExpense':
        return cls(**data)


@dataclass
class RecurringConfig:
    """Configuration for recurring cash flow simulation."""

    # Personal Info
    current_age: int = 38
    life_expectancy: int = 90
    simulation_start_date: str = "2025-01-01"  # When simulation begins

    # Schedules
    income_schedules: List[RecurringIncome] = field(default_factory=list)
    expense_schedules: List[RecurringExpense] = field(default_factory=list)

    # Market Parameters
    spy_mean_return: float = 0.10
    spy_volatility: float = 0.18

    # Initial Conditions
    initial_balance: float = 0.0
    initial_cash_buffer: float = 27_000

    # Simulation
    num_simulations: int = 1000
    random_seed: Optional[int] = None

    def save(self, filepath: str = 'recurring_config.json') -> None:
        """Save configuration to JSON file."""
        data = {
            'current_age': self.current_age,
            'life_expectancy': self.life_expectancy,
            'simulation_start_date': self.simulation_start_date,
            'income_schedules': [inc.to_dict() for inc in self.income_schedules],
            'expense_schedules': [exp.to_dict() for exp in self.expense_schedules],
            'spy_mean_return': self.spy_mean_return,
            'spy_volatility': self.spy_volatility,
            'initial_balance': self.initial_balance,
            'initial_cash_buffer': self.initial_cash_buffer,
            'num_simulations': self.num_simulations,
            'random_seed': self.random_seed,
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Configuration saved to {filepath}")

    @classmethod
    def load(cls, filepath: str = 'recurring_config.json') -> 'RecurringConfig':
        """Load configuration from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)

        income_schedules = [RecurringIncome.from_dict(inc) for inc in data.get('income_schedules', [])]
        expense_schedules = [RecurringExpense.from_dict(exp) for exp in data.get('expense_schedules', [])]

        return cls(
            current_age=data.get('current_age', 38),
            life_expectancy=data.get('life_expectancy', 90),
            simulation_start_date=data.get('simulation_start_date', '2025-01-01'),
            income_schedules=income_schedules,
            expense_schedules=expense_schedules,
            spy_mean_return=data.get('spy_mean_return', 0.10),
            spy_volatility=data.get('spy_volatility', 0.18),
            initial_balance=data.get('initial_balance', 0.0),
            initial_cash_buffer=data.get('initial_cash_buffer', 27_000),
            num_simulations=data.get('num_simulations', 1000),
            random_seed=data.get('random_seed'),
        )

    @classmethod
    def load_or_create(cls, filepath: str = 'recurring_config.json') -> 'RecurringConfig':
        """Load configuration if exists, otherwise return default."""
        if Path(filepath).exists():
            print(f"Loading configuration from {filepath}...")
            return cls.load(filepath)
        else:
            print(f"No configuration found at {filepath}, using defaults.")
            return cls()


# ============================================================================
# SIMULATOR
# ============================================================================

class RecurringSimulator:
    """Day-by-day simulation with recurring income and expenses."""

    # Days per frequency
    FREQUENCY_DAYS = {
        'weekly': 7,
        'biweekly': 14,
        'monthly': 30,  # Approximate, will adjust
        'quarterly': 91,  # Approximate
        'annual': 365,
    }

    def __init__(self, config: RecurringConfig):
        self.config = config

    def _generate_daily_returns(self, num_days: int, seed: Optional[int] = None) -> np.ndarray:
        """Generate daily market returns."""
        if seed is not None:
            np.random.seed(seed)

        daily_mean = self.config.spy_mean_return / 365
        daily_std = self.config.spy_volatility / np.sqrt(365)

        return np.random.normal(daily_mean, daily_std, num_days)

    def _is_recurring_date(self, current_date: datetime, start_date: datetime, frequency: str) -> bool:
        """Check if current_date matches a recurring schedule."""
        if current_date < start_date:
            return False

        if frequency == 'monthly':
            # Monthly: same day of month
            return current_date.day == start_date.day
        elif frequency == 'quarterly':
            # Quarterly: every 3 months on same day
            months_diff = (current_date.year - start_date.year) * 12 + (current_date.month - start_date.month)
            return months_diff % 3 == 0 and current_date.day == start_date.day
        elif frequency == 'annual':
            # Annual: same month and day
            return current_date.month == start_date.month and current_date.day == start_date.day
        else:
            # Weekly/biweekly: count days
            days_diff = (current_date - start_date).days
            return days_diff >= 0 and days_diff % self.FREQUENCY_DAYS[frequency] == 0

    def run_single_simulation(self, sim_number: int = 0) -> Dict:
        """Run single day-by-day simulation."""
        years = self.config.life_expectancy - self.config.current_age
        total_days = years * 365

        # Accounts
        investment_balance = self.config.initial_balance
        cash_buffer = self.config.initial_cash_buffer

        # Tracking
        total_income = self.config.initial_balance
        total_expenses = 0.0
        monthly_snapshots = []

        # Generate returns
        seed = (self.config.random_seed + sim_number) if self.config.random_seed else None
        returns = self._generate_daily_returns(total_days, seed)

        # Parse start dates
        sim_start = datetime.strptime(self.config.simulation_start_date, '%Y-%m-%d')

        # Create mutable copies with parsed dates
        income_schedules = [
            {
                'amount': inc.amount,
                'start_date': datetime.strptime(inc.start_date, '%Y-%m-%d'),
                'frequency': inc.frequency,
                'description': inc.description,
                'annual_growth': inc.annual_growth,
            }
            for inc in self.config.income_schedules
        ]
        expense_schedules = [
            {
                'amount': exp.amount,
                'start_date': datetime.strptime(exp.start_date, '%Y-%m-%d'),
                'frequency': exp.frequency,
                'description': exp.description,
                'annual_growth': exp.annual_growth,
            }
            for exp in self.config.expense_schedules
        ]

        last_snapshot_month = -1

        for day_num in range(total_days):
            current_date = sim_start + timedelta(days=day_num)
            age = self.config.current_age + (day_num / 365)

            # STEP 1: INCOME (deposit on recurring dates)
            for inc in income_schedules:
                if self._is_recurring_date(current_date, inc['start_date'], inc['frequency']):
                    investment_balance += inc['amount']
                    total_income += inc['amount']

            # STEP 2: MARKET RETURNS (daily)
            if investment_balance > 0:
                investment_balance *= (1 + returns[day_num])

            # STEP 3: EXPENSES (withdraw on recurring dates)
            for exp in expense_schedules:
                if self._is_recurring_date(current_date, exp['start_date'], exp['frequency']):
                    if investment_balance >= exp['amount']:
                        investment_balance -= exp['amount']
                        total_expenses += exp['amount']
                    else:
                        # Use cash buffer for shortfall
                        shortfall = exp['amount'] - investment_balance
                        total_expenses += investment_balance
                        investment_balance = 0

                        if cash_buffer >= shortfall:
                            cash_buffer -= shortfall
                            total_expenses += shortfall
                        else:
                            # Ran out of money
                            return {
                                'success': False,
                                'failure_age': age,
                                'failure_date': current_date.strftime('%Y-%m-%d'),
                                'final_balance': 0.0,
                                'total_income': total_income,
                                'total_expenses': total_expenses,
                                'net_contributed': total_income - total_expenses,
                                'market_gain': 0.0,
                                'monthly_snapshots': monthly_snapshots,
                            }

            # STEP 4: MONTHLY SNAPSHOT (on 1st of month)
            current_month = current_date.year * 12 + current_date.month
            if current_date.day == 1 and current_month != last_snapshot_month:
                monthly_snapshots.append({
                    'month': len(monthly_snapshots),
                    'date': current_date.strftime('%Y-%m-%d'),
                    'age': age,
                    'balance': investment_balance,
                    'cash_buffer': cash_buffer,
                })
                last_snapshot_month = current_month

            # STEP 5: ANNUAL ADJUSTMENTS (on simulation anniversary)
            if day_num > 0 and day_num % 365 == 0:
                for inc in income_schedules:
                    inc['amount'] *= (1 + inc['annual_growth'])
                for exp in expense_schedules:
                    exp['amount'] *= (1 + exp['annual_growth'])

        # Success!
        final_balance = investment_balance + cash_buffer
        net_contributed = total_income - total_expenses
        market_gain = final_balance - net_contributed

        return {
            'success': True,
            'failure_age': None,
            'failure_date': None,
            'final_balance': final_balance,
            'investment_balance': investment_balance,
            'cash_buffer': cash_buffer,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net_contributed': net_contributed,
            'market_gain': market_gain,
            'monthly_snapshots': monthly_snapshots,
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

def export_results_to_csv(config: RecurringConfig, results: List[Dict], output_dir: str = '.') -> str:
    """Export simulation results to CSV with unique filename."""

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'recurring_sim_{timestamp}.csv'
    filepath = Path(output_dir) / filename

    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)

        # Header
        writer.writerow(['RECURRING CASH FLOW SIMULATION RESULTS'])
        writer.writerow(['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])

        # Configuration
        writer.writerow(['CONFIGURATION'])
        writer.writerow(['Age Range', f'{config.current_age} - {config.life_expectancy}'])
        writer.writerow(['Simulation Start', config.simulation_start_date])
        writer.writerow(['Market Return (Mean)', f'{config.spy_mean_return*100:.1f}%'])
        writer.writerow(['Market Volatility', f'{config.spy_volatility*100:.1f}%'])
        writer.writerow(['Initial Balance', f'${config.initial_balance:,.0f}'])
        writer.writerow(['Initial Cash Buffer', f'${config.initial_cash_buffer:,.0f}'])
        writer.writerow(['Simulations', config.num_simulations])
        writer.writerow([])

        # Income schedules
        writer.writerow(['INCOME SCHEDULES'])
        for i, inc in enumerate(config.income_schedules, 1):
            writer.writerow([f'Income {i}', inc.description, f'${inc.amount:,.0f}',
                           inc.frequency, f'Starting {inc.start_date}', f'Growth: {inc.annual_growth*100:.1f}%'])
        writer.writerow([])

        # Expense schedules
        writer.writerow(['EXPENSE SCHEDULES'])
        for i, exp in enumerate(config.expense_schedules, 1):
            writer.writerow([f'Expense {i}', exp.description, f'${exp.amount:,.0f}',
                           exp.frequency, f'Starting {exp.start_date}', f'Growth: {exp.annual_growth*100:.1f}%'])
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
            market_gains = [r['market_gain'] for r in successful]

            writer.writerow(['FINAL BALANCE'])
            writer.writerow(['Mean', f'${np.mean(final_balances):,.0f}'])
            writer.writerow(['Median', f'${np.median(final_balances):,.0f}'])
            writer.writerow([])

            writer.writerow(['MARKET GAIN (Final - Net Contributed)'])
            writer.writerow(['Mean', f'${np.mean(market_gains):,.0f}'])
            writer.writerow(['Median', f'${np.median(market_gains):,.0f}'])
            writer.writerow([])

        # Individual simulation results
        writer.writerow(['INDIVIDUAL SIMULATION RESULTS'])
        writer.writerow(['Sim #', 'Success', 'Final Balance', 'Investment Balance', 'Cash Buffer',
                        'Total Income', 'Total Expenses', 'Net Contributed', 'Market Gain', 'Failure Age', 'Failure Date'])

        for i, result in enumerate(results):
            if result['success']:
                writer.writerow([
                    i + 1,
                    'Yes',
                    f'${result["final_balance"]:,.0f}',
                    f'${result["investment_balance"]:,.0f}',
                    f'${result["cash_buffer"]:,.0f}',
                    f'${result["total_income"]:,.0f}',
                    f'${result["total_expenses"]:,.0f}',
                    f'${result["net_contributed"]:,.0f}',
                    f'${result["market_gain"]:,.0f}',
                    '',
                    ''
                ])
            else:
                writer.writerow([
                    i + 1,
                    'No',
                    '$0',
                    '$0',
                    '$0',
                    f'${result["total_income"]:,.0f}',
                    f'${result["total_expenses"]:,.0f}',
                    f'${result["net_contributed"]:,.0f}',
                    '$0',
                    f'{result["failure_age"]:.1f}',
                    result["failure_date"]
                ])

    return str(filepath)


# ============================================================================
# WIZARD
# ============================================================================

def setup_wizard() -> RecurringConfig:
    """Interactive wizard to configure simulation."""
    print("\n" + "="*70)
    print("RECURRING CASH FLOW SIMULATION - SETUP WIZARD")
    print("="*70)

    config = RecurringConfig()

    # Basic info
    print("\n--- Personal Information ---")
    age_input = input(f"Current age [{config.current_age}]: ").strip()
    if age_input:
        config.current_age = int(age_input)

    life_input = input(f"Life expectancy [{config.life_expectancy}]: ").strip()
    if life_input:
        config.life_expectancy = int(life_input)

    start_date_input = input(f"Simulation start date (YYYY-MM-DD) [{config.simulation_start_date}]: ").strip()
    if start_date_input:
        config.simulation_start_date = start_date_input

    # Initial balances
    print("\n--- Initial Balances ---")
    balance_input = input(f"Starting investment balance [${config.initial_balance:,.0f}]: ").strip()
    if balance_input:
        config.initial_balance = float(balance_input)

    buffer_input = input(f"Starting cash buffer [${config.initial_cash_buffer:,.0f}]: ").strip()
    if buffer_input:
        config.initial_cash_buffer = float(buffer_input)

    # Income schedules
    print("\n--- Recurring Income ---")
    print("Examples:")
    print("  - $3,000 biweekly starting 2025-10-17")
    print("  - $5,000 monthly starting 2025-01-01")

    while True:
        print("\nAdd income source? (y/n): ", end='')
        if input().strip().lower() != 'y':
            break

        description = input("Description (e.g., 'Salary'): ").strip() or "Income"
        amount = float(input("Amount per occurrence: $").strip())
        start_date = input("Start date (YYYY-MM-DD): ").strip()
        print("Frequency: weekly, biweekly, monthly, quarterly, annual")
        frequency = input("Frequency: ").strip().lower()
        growth_input = input("Annual growth rate [1.0%]: ").strip()
        growth = float(growth_input) / 100 if growth_input else 0.01

        config.income_schedules.append(RecurringIncome(
            amount=amount,
            start_date=start_date,
            frequency=frequency,
            description=description,
            annual_growth=growth,
        ))

        print(f"✓ Added: {description} - ${amount:,.0f} {frequency} starting {start_date}")

    # Expense schedules
    print("\n--- Recurring Expenses ---")
    print("Examples:")
    print("  - $2,000 weekly starting 2025-10-13")
    print("  - $4,500 monthly starting 2025-01-01")

    while True:
        print("\nAdd expense? (y/n): ", end='')
        if input().strip().lower() != 'y':
            break

        description = input("Description (e.g., 'Living expenses'): ").strip() or "Expense"
        amount = float(input("Amount per occurrence: $").strip())
        start_date = input("Start date (YYYY-MM-DD): ").strip()
        print("Frequency: weekly, biweekly, monthly, quarterly, annual")
        frequency = input("Frequency: ").strip().lower()
        growth_input = input("Annual growth rate [1.0%]: ").strip()
        growth = float(growth_input) / 100 if growth_input else 0.01

        config.expense_schedules.append(RecurringExpense(
            amount=amount,
            start_date=start_date,
            frequency=frequency,
            description=description,
            annual_growth=growth,
        ))

        print(f"✓ Added: {description} - ${amount:,.0f} {frequency} starting {start_date}")

    # Simulation parameters
    print("\n--- Simulation Parameters ---")
    num_input = input(f"Number of simulations [{config.num_simulations}]: ").strip()
    if num_input:
        config.num_simulations = int(num_input)

    # Summary
    print_config_summary(config)

    return config


def print_config_summary(config: RecurringConfig):
    """Print configuration summary."""
    print("\n" + "="*70)
    print("CONFIGURATION SUMMARY")
    print("="*70)
    print(f"Age: {config.current_age} - {config.life_expectancy} ({config.life_expectancy - config.current_age} years)")
    print(f"Start Date: {config.simulation_start_date}")
    print(f"Initial Balance: ${config.initial_balance:,.0f}")
    print(f"Initial Cash Buffer: ${config.initial_cash_buffer:,.0f}")

    if config.income_schedules:
        print(f"\nIncome Schedules:")
        for inc in config.income_schedules:
            print(f"  • {inc.description}: ${inc.amount:,.0f} {inc.frequency} starting {inc.start_date}")

    if config.expense_schedules:
        print(f"\nExpense Schedules:")
        for exp in config.expense_schedules:
            print(f"  • {exp.description}: ${exp.amount:,.0f} {exp.frequency} starting {exp.start_date}")

    print(f"\nSimulations: {config.num_simulations}")
    print("="*70)


def run_simulation_from_config(config: RecurringConfig):
    """Run simulation and export results."""
    print(f"\nRunning {config.num_simulations} simulations...")

    simulator = RecurringSimulator(config)
    results = simulator.run_simulations()

    # Calculate statistics
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    print(f"\n{'='*70}")
    print("RESULTS")
    print(f"{'='*70}")
    print(f"Success Rate: {len(successful)}/{len(results)} ({len(successful)/len(results)*100:.1f}%)")

    if successful:
        final_balances = [r['final_balance'] for r in successful]
        market_gains = [r['market_gain'] for r in successful]

        print(f"\nFinal Balance:")
        print(f"  Mean:   ${np.mean(final_balances):>15,.0f}")
        print(f"  Median: ${np.median(final_balances):>15,.0f}")

        print(f"\nMarket Gain:")
        print(f"  Mean:   ${np.mean(market_gains):>15,.0f}")
        print(f"  Median: ${np.median(market_gains):>15,.0f}")

    # Export to CSV
    print(f"\n{'-'*70}")
    filepath = export_results_to_csv(config, results)
    print(f"Results saved to: {filepath}")
    print(f"{'='*70}")


# ============================================================================
# MAIN CLI
# ============================================================================

def main():
    """Main CLI."""
    print("\n" + "="*70)
    print("RECURRING CASH FLOW SIMULATION")
    print("="*70)

    # Try to auto-load configuration
    config = RecurringConfig.load_or_create()

    if config.income_schedules or config.expense_schedules:
        print_config_summary(config)

    print("\nOptions:")
    print("1. Run simulation with current configuration")
    print("2. Create new configuration (wizard)")
    print("3. Edit configuration file manually")
    print("4. Save current configuration")
    print("5. Exit")
    print("="*70)

    choice = input("\nSelect option (1-5): ").strip()

    if choice == '1':
        if not config.income_schedules and not config.expense_schedules:
            print("\nNo income or expense schedules configured!")
            print("Please create configuration first (option 2).")
        else:
            run_simulation_from_config(config)

    elif choice == '2':
        config = setup_wizard()
        print("\nSave this configuration? (y/n): ", end='')
        if input().strip().lower() == 'y':
            config.save()
        run_simulation_from_config(config)

    elif choice == '3':
        print(f"\nEdit the file: recurring_config.json")
        print("Then re-run this script to load it automatically.")

    elif choice == '4':
        config.save()

    elif choice == '5':
        print("\nExiting. Goodbye!")

    else:
        print("Invalid option.")


if __name__ == "__main__":
    main()
