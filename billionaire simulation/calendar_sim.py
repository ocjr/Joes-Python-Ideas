"""
Calendar-Based Simulation - Exact payday and withdrawal date modeling

Realistic cash flow with specific dates:
- Income deposits on specific days of month (e.g., 1st and 15th)
- Expense withdrawals on specific days of month (e.g., 1st)
- Day-by-day simulation shows exact time money is invested
- Optimize timing by seeing how long deposits compound before withdrawals
"""

import json
import numpy as np
import csv
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from calendar import monthrange


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class IncomeSchedule:
    """Income that arrives on specific days of the month."""
    amount: float  # After-tax amount per occurrence
    days_of_month: List[int]  # Days when income arrives (e.g., [1, 15])
    description: str = "Salary"
    annual_growth: float = 0.01  # Annual raise

    def to_dict(self) -> Dict:
        return {
            'amount': self.amount,
            'days_of_month': self.days_of_month,
            'description': self.description,
            'annual_growth': self.annual_growth,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'IncomeSchedule':
        return cls(**data)


@dataclass
class ExpenseSchedule:
    """Expenses that are withdrawn on specific days of the month."""
    amount: float  # Amount per occurrence
    days_of_month: List[int]  # Days when expenses are withdrawn
    description: str = "Living expenses"
    annual_growth: float = 0.01  # Annual inflation

    def to_dict(self) -> Dict:
        return {
            'amount': self.amount,
            'days_of_month': self.days_of_month,
            'description': self.description,
            'annual_growth': self.annual_growth,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ExpenseSchedule':
        return cls(**data)


@dataclass
class CalendarConfig:
    """Configuration for calendar-based simulation."""

    # Personal Info
    current_age: int = 38
    life_expectancy: int = 90

    # Schedules
    income_schedules: List[IncomeSchedule] = field(default_factory=list)
    expense_schedules: List[ExpenseSchedule] = field(default_factory=list)

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
        data = {
            'current_age': self.current_age,
            'life_expectancy': self.life_expectancy,
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

    @classmethod
    def load(cls, filepath: str) -> 'CalendarConfig':
        """Load configuration from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)

        income_schedules = [IncomeSchedule.from_dict(inc) for inc in data.get('income_schedules', [])]
        expense_schedules = [ExpenseSchedule.from_dict(exp) for exp in data.get('expense_schedules', [])]

        return cls(
            current_age=data.get('current_age', 38),
            life_expectancy=data.get('life_expectancy', 90),
            income_schedules=income_schedules,
            expense_schedules=expense_schedules,
            spy_mean_return=data.get('spy_mean_return', 0.10),
            spy_volatility=data.get('spy_volatility', 0.18),
            initial_balance=data.get('initial_balance', 0.0),
            initial_cash_buffer=data.get('initial_cash_buffer', 27_000),
            num_simulations=data.get('num_simulations', 1000),
            random_seed=data.get('random_seed'),
        )


# ============================================================================
# SIMULATOR
# ============================================================================

class CalendarSimulator:
    """Day-by-day simulation with exact payday and withdrawal dates."""

    def __init__(self, config: CalendarConfig):
        self.config = config

    def _generate_daily_returns(self, num_days: int, seed: Optional[int] = None) -> np.ndarray:
        """Generate daily market returns."""
        if seed is not None:
            np.random.seed(seed)

        daily_mean = self.config.spy_mean_return / 365
        daily_std = self.config.spy_volatility / np.sqrt(365)

        return np.random.normal(daily_mean, daily_std, num_days)

    def _is_income_day(self, day_of_month: int, income_schedule: IncomeSchedule) -> bool:
        """Check if this day matches an income schedule."""
        return day_of_month in income_schedule.days_of_month

    def _is_expense_day(self, day_of_month: int, expense_schedule: ExpenseSchedule) -> bool:
        """Check if this day matches an expense schedule."""
        return day_of_month in expense_schedule.days_of_month

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
        monthly_snapshots = []  # Snapshot on 1st of each month

        # Generate returns
        seed = (self.config.random_seed + sim_number) if self.config.random_seed else None
        returns = self._generate_daily_returns(total_days, seed)

        # Create mutable copies of schedules (for annual growth)
        income_schedules = [
            IncomeSchedule(
                amount=inc.amount,
                days_of_month=inc.days_of_month,
                description=inc.description,
                annual_growth=inc.annual_growth,
            )
            for inc in self.config.income_schedules
        ]
        expense_schedules = [
            ExpenseSchedule(
                amount=exp.amount,
                days_of_month=exp.days_of_month,
                description=exp.description,
                annual_growth=exp.annual_growth,
            )
            for exp in self.config.expense_schedules
        ]

        # Start date (arbitrary, but use current date for realism)
        start_date = datetime(2025, 1, 1)

        for day_num in range(total_days):
            current_date = start_date + timedelta(days=day_num)
            day_of_month = current_date.day
            age = self.config.current_age + (day_num / 365)

            # STEP 1: INCOME (deposit on payday)
            for inc_schedule in income_schedules:
                if self._is_income_day(day_of_month, inc_schedule):
                    investment_balance += inc_schedule.amount
                    total_income += inc_schedule.amount

            # STEP 2: MARKET RETURNS (daily)
            if investment_balance > 0:
                investment_balance *= (1 + returns[day_num])

            # STEP 3: EXPENSES (withdraw on expense day)
            for exp_schedule in expense_schedules:
                if self._is_expense_day(day_of_month, exp_schedule):
                    if investment_balance >= exp_schedule.amount:
                        investment_balance -= exp_schedule.amount
                        total_expenses += exp_schedule.amount
                    else:
                        # Use cash buffer for shortfall
                        shortfall = exp_schedule.amount - investment_balance
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
                                'monthly_snapshots': monthly_snapshots,
                            }

            # STEP 4: MONTHLY SNAPSHOT (on 1st of month)
            if day_of_month == 1:
                monthly_snapshots.append({
                    'month': len(monthly_snapshots),
                    'date': current_date.strftime('%Y-%m-%d'),
                    'age': age,
                    'balance': investment_balance,
                    'cash_buffer': cash_buffer,
                })

            # STEP 5: ANNUAL ADJUSTMENTS (on anniversary)
            if day_num > 0 and day_num % 365 == 0:
                for inc_schedule in income_schedules:
                    inc_schedule.amount *= (1 + inc_schedule.annual_growth)
                for exp_schedule in expense_schedules:
                    exp_schedule.amount *= (1 + exp_schedule.annual_growth)

        # Success!
        final_balance = investment_balance + cash_buffer
        net_contributed = total_income - total_expenses  # Net money we put in
        market_gain = final_balance - net_contributed  # What the market gave us

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

def export_results_to_csv(config: CalendarConfig, results: List[Dict], output_dir: str = '.') -> str:
    """Export simulation results to CSV with unique filename."""

    # Generate unique filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'calendar_sim_{timestamp}.csv'
    filepath = Path(output_dir) / filename

    # Write summary statistics
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)

        # Header
        writer.writerow(['CALENDAR-BASED SIMULATION RESULTS'])
        writer.writerow(['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])

        # Configuration
        writer.writerow(['CONFIGURATION'])
        writer.writerow(['Age Range', f'{config.current_age} - {config.life_expectancy}'])
        writer.writerow(['Market Return (Mean)', f'{config.spy_mean_return*100:.1f}%'])
        writer.writerow(['Market Volatility (Std)', f'{config.spy_volatility*100:.1f}%'])
        writer.writerow(['Initial Balance', f'${config.initial_balance:,.0f}'])
        writer.writerow(['Initial Cash Buffer', f'${config.initial_cash_buffer:,.0f}'])
        writer.writerow(['Simulations', config.num_simulations])
        writer.writerow([])

        # Income schedules
        writer.writerow(['INCOME SCHEDULES'])
        for i, inc in enumerate(config.income_schedules, 1):
            days_str = ', '.join([str(d) for d in sorted(inc.days_of_month)])
            writer.writerow([f'Income {i}', inc.description, f'${inc.amount:,.0f}',
                           f'Days: {days_str}', f'Growth: {inc.annual_growth*100:.1f}%'])
        writer.writerow([])

        # Expense schedules
        writer.writerow(['EXPENSE SCHEDULES'])
        for i, exp in enumerate(config.expense_schedules, 1):
            days_str = ', '.join([str(d) for d in sorted(exp.days_of_month)])
            writer.writerow([f'Expense {i}', exp.description, f'${exp.amount:,.0f}',
                           f'Days: {days_str}', f'Growth: {exp.annual_growth*100:.1f}%'])
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
            net_contributed = [r['net_contributed'] for r in successful]
            market_gains = [r['market_gain'] for r in successful]

            writer.writerow(['FINAL BALANCE STATISTICS'])
            writer.writerow(['Mean', f'${np.mean(final_balances):,.0f}'])
            writer.writerow(['Median', f'${np.median(final_balances):,.0f}'])
            writer.writerow(['Std Dev', f'${np.std(final_balances):,.0f}'])
            writer.writerow(['Min', f'${np.min(final_balances):,.0f}'])
            writer.writerow(['25th Percentile', f'${np.percentile(final_balances, 25):,.0f}'])
            writer.writerow(['75th Percentile', f'${np.percentile(final_balances, 75):,.0f}'])
            writer.writerow(['Max', f'${np.max(final_balances):,.0f}'])
            writer.writerow([])

            writer.writerow(['NET CONTRIBUTED (Income - Expenses)'])
            writer.writerow(['Mean', f'${np.mean(net_contributed):,.0f}'])
            writer.writerow(['Median', f'${np.median(net_contributed):,.0f}'])
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
                    f'${result.get("net_contributed", 0):,.0f}',
                    '$0',
                    f'{result["failure_age"]:.1f}',
                    result["failure_date"]
                ])

    return str(filepath)


# ============================================================================
# WIZARD
# ============================================================================

def setup_wizard() -> CalendarConfig:
    """Interactive wizard to configure simulation."""
    print("\n" + "="*60)
    print("CALENDAR SIMULATION SETUP WIZARD")
    print("="*60)

    config = CalendarConfig()

    # Basic info
    print("\n--- Personal Information ---")
    age_input = input(f"Current age [{config.current_age}]: ").strip()
    if age_input:
        config.current_age = int(age_input)

    life_input = input(f"Life expectancy [{config.life_expectancy}]: ").strip()
    if life_input:
        config.life_expectancy = int(life_input)

    # Initial balances
    print("\n--- Initial Balances ---")
    balance_input = input(f"Starting investment balance [${config.initial_balance:,.0f}]: ").strip()
    if balance_input:
        config.initial_balance = float(balance_input)

    buffer_input = input(f"Starting cash buffer [${config.initial_cash_buffer:,.0f}]: ").strip()
    if buffer_input:
        config.initial_cash_buffer = float(buffer_input)

    # Income schedules
    print("\n--- Income Schedules ---")
    print("Enter income sources (paydays). Examples:")
    print("  - Biweekly: days 1 and 15")
    print("  - Monthly: day 1")
    print("  - Weekly: days 1, 8, 15, 22")

    while True:
        print("\nAdd income source? (y/n): ", end='')
        if input().strip().lower() != 'y':
            break

        description = input("Description (e.g., 'Salary'): ").strip() or "Income"

        amount_input = input("Amount per occurrence (after-tax): $").strip()
        amount = float(amount_input)

        days_input = input("Days of month (comma-separated, e.g., '1,15'): ").strip()
        days = [int(d.strip()) for d in days_input.split(',')]

        growth_input = input("Annual growth rate [1.0%]: ").strip()
        growth = float(growth_input) / 100 if growth_input else 0.01

        config.income_schedules.append(IncomeSchedule(
            amount=amount,
            days_of_month=days,
            description=description,
            annual_growth=growth,
        ))

        print(f"Added: {description} - ${amount:,.0f} on days {days}")

    # Expense schedules
    print("\n--- Expense Schedules ---")
    print("Enter expense withdrawals. Examples:")
    print("  - Rent on 1st: day 1")
    print("  - Bills on 5th and 20th: days 5, 20")

    while True:
        print("\nAdd expense? (y/n): ", end='')
        if input().strip().lower() != 'y':
            break

        description = input("Description (e.g., 'Living expenses'): ").strip() or "Expense"

        amount_input = input("Amount per occurrence: $").strip()
        amount = float(amount_input)

        days_input = input("Days of month (comma-separated, e.g., '1'): ").strip()
        days = [int(d.strip()) for d in days_input.split(',')]

        growth_input = input("Annual growth rate [1.0%]: ").strip()
        growth = float(growth_input) / 100 if growth_input else 0.01

        config.expense_schedules.append(ExpenseSchedule(
            amount=amount,
            days_of_month=days,
            description=description,
            annual_growth=growth,
        ))

        print(f"Added: {description} - ${amount:,.0f} on days {days}")

    # Simulation parameters
    print("\n--- Simulation Parameters ---")
    num_input = input(f"Number of simulations [{config.num_simulations}]: ").strip()
    if num_input:
        config.num_simulations = int(num_input)

    # Summary
    print("\n" + "="*60)
    print("CONFIGURATION SUMMARY")
    print("="*60)
    print(f"Age: {config.current_age} - {config.life_expectancy} ({config.life_expectancy - config.current_age} years)")
    print(f"Initial Balance: ${config.initial_balance:,.0f}")
    print(f"Initial Cash Buffer: ${config.initial_cash_buffer:,.0f}")
    print(f"\nIncome Schedules:")
    for inc in config.income_schedules:
        days_str = ', '.join([str(d) for d in sorted(inc.days_of_month)])
        print(f"  - {inc.description}: ${inc.amount:,.0f} on days {days_str}")
    print(f"\nExpense Schedules:")
    for exp in config.expense_schedules:
        days_str = ', '.join([str(d) for d in sorted(exp.days_of_month)])
        print(f"  - {exp.description}: ${exp.amount:,.0f} on days {days_str}")
    print(f"\nSimulations: {config.num_simulations}")
    print("="*60)

    return config


def run_simulation_from_config(config: CalendarConfig):
    """Run simulation and export results."""
    print(f"\nRunning {config.num_simulations} simulations...")

    simulator = CalendarSimulator(config)
    results = simulator.run_simulations()

    # Calculate statistics
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    print(f"\nResults:")
    print(f"  Success Rate: {len(successful)}/{len(results)} ({len(successful)/len(results)*100:.1f}%)")

    if successful:
        final_balances = [r['final_balance'] for r in successful]
        net_contributed = [r['net_contributed'] for r in successful]
        market_gains = [r['market_gain'] for r in successful]

        print(f"\n  Final Balance Statistics:")
        print(f"    Mean:   ${np.mean(final_balances):>15,.0f}")
        print(f"    Median: ${np.median(final_balances):>15,.0f}")
        print(f"    Min:    ${np.min(final_balances):>15,.0f}")
        print(f"    Max:    ${np.max(final_balances):>15,.0f}")

        print(f"\n  Net Contributed (Income - Expenses):")
        print(f"    Mean:   ${np.mean(net_contributed):>15,.0f}")

        print(f"\n  Market Gain:")
        print(f"    Mean:   ${np.mean(market_gains):>15,.0f}")
        print(f"    Median: ${np.median(market_gains):>15,.0f}")

    # Export to CSV
    print("\nExporting results to CSV...")
    filepath = export_results_to_csv(config, results)
    print(f"Results saved to: {filepath}")

    # Offer to save config
    print("\nSave this configuration? (y/n): ", end='')
    if input().strip().lower() == 'y':
        save_path = input("Enter filename (e.g., my_scenario.json): ").strip()
        config.save(save_path)
        print(f"Configuration saved to {save_path}")


# ============================================================================
# MAIN CLI
# ============================================================================

def main():
    """Main CLI."""
    print("\n" + "="*60)
    print("CALENDAR-BASED SIMULATION")
    print("="*60)
    print("1. Run setup wizard (create new scenario)")
    print("2. Load scenario from file")
    print("3. Quick test with default values")
    print("4. Exit")
    print("="*60)

    choice = input("\nSelect option (1-4): ").strip()

    if choice == '1':
        config = setup_wizard()
        run_simulation_from_config(config)

    elif choice == '2':
        filepath = input("Enter scenario file path: ").strip()
        try:
            config = CalendarConfig.load(filepath)
            print("Scenario loaded!")

            # Show summary
            print("\n" + "="*60)
            print("LOADED SCENARIO")
            print("="*60)
            print(f"Age: {config.current_age} - {config.life_expectancy}")
            for inc in config.income_schedules:
                days_str = ', '.join([str(d) for d in sorted(inc.days_of_month)])
                print(f"Income: {inc.description} - ${inc.amount:,.0f} on days {days_str}")
            for exp in config.expense_schedules:
                days_str = ', '.join([str(d) for d in sorted(exp.days_of_month)])
                print(f"Expense: {exp.description} - ${exp.amount:,.0f} on days {days_str}")
            print("="*60)

            run_simulation_from_config(config)
        except Exception as e:
            print(f"Error loading scenario: {e}")

    elif choice == '3':
        # Quick test with semi-monthly income, monthly expenses
        print("\nRunning quick test scenario:")
        print("  - Income: $4,562.50 on 1st and 15th (semi-monthly, ~$109.5k/year after-tax)")
        print("  - Expenses: $9,000 on 1st of month")
        print("  - Age: 38 - 90")

        config = CalendarConfig(
            current_age=38,
            life_expectancy=90,
            income_schedules=[
                IncomeSchedule(amount=4_562.50, days_of_month=[1, 15], description="Semi-monthly salary")
            ],
            expense_schedules=[
                ExpenseSchedule(amount=9_000, days_of_month=[1], description="Monthly expenses")
            ],
            num_simulations=1000,
        )

        run_simulation_from_config(config)

    elif choice == '4':
        print("\nExiting. Goodbye!")
    else:
        print("Invalid option.")


if __name__ == "__main__":
    main()
