"""
Wealth Simulation - Core Financial Path Simulator

Realistic financial journey modeling with:
- Bi-weekly salary deposits (dollar-cost averaging)
- Separate accounts: personal investments, cash buffer, business income
- Life events: windfalls, job changes, startups, investments
- Optional portfolio insurance
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from startup_simulation import StartupSimulator, StartupConfig

# ============================================================================
# SCENARIO CONFIGURATIONS
# Edit these to customize your simulation scenarios
# ============================================================================

SCENARIOS = {
    'baseline': {
        'name': 'Baseline - Salary + Market Only',
        'description': 'No windfall, just regular salary invested in market with DCA',
        'life_events': []
    },

    'windfall_conservative': {
        'name': 'Windfall - Keep Job',
        'description': '$1M windfall in 3 years, keep working, invest everything',
        'life_events': [
            {'years_from_now': 3, 'one_time_payment': 1_000_000},
        ]
    },

    'startup_sell': {
        'name': 'Startup - Sell Company',
        'description': '$1M windfall → invest $500k in startup → sell when profitable',
        'life_events': [
            {'years_from_now': 3, 'one_time_payment': 1_000_000},
            {
                'liquid_trigger': 900_000,
                'startup': {
                    'investment': 500_000,
                    'monthly_burn_rate': 20_000,
                    'revenue_growth_mean': 0.08,
                    'revenue_growth_std': 0.25,
                    'max_months': 48,
                    'force_exit': True,  # Sell when profitable
                }
            },
        ]
    },

    'startup_keep': {
        'name': 'Startup - Keep Operating',
        'description': '$1M windfall → invest $500k in startup → keep and take profits',
        'life_events': [
            {'years_from_now': 3, 'one_time_payment': 1_000_000},
            {
                'liquid_trigger': 900_000,
                'startup': {
                    'investment': 500_000,
                    'monthly_burn_rate': 20_000,
                    'revenue_growth_mean': 0.08,
                    'revenue_growth_std': 0.25,
                    'max_months': 48,
                    'force_exit': False,  # Keep operating
                    'profit_distribution': 0.50,  # Take 50% of profits
                }
            },
        ]
    },

    'real_estate': {
        'name': 'Real Estate Investment',
        'description': '$1M windfall → buy apartment complex when enough capital',
        'life_events': [
            {'years_from_now': 3, 'one_time_payment': 1_000_000},
            {
                'liquid_trigger': 5_000_000,
                'investment': {
                    'name': 'Apartment Complex',
                    'cost': 1_000_000,
                    'annual_profit': 60_000,  # 6% return
                    'growth_rate': 0.03,  # 3% annual growth
                }
            },
        ]
    },

    'franchise': {
        'name': 'McDonald\'s Franchise',
        'description': '$1M windfall → buy franchise when $9M+ in investments',
        'life_events': [
            {'years_from_now': 3, 'one_time_payment': 1_000_000},
            {
                'liquid_trigger': 9_000_000,
                'investment': {
                    'name': "McDonald's Franchise",
                    'cost': 2_500_000,
                    'annual_profit': 150_000,  # 6% return
                    'growth_rate': 0.02,  # 2% annual growth
                }
            },
        ]
    },
}


# ============================================================================
# BASE CONFIGURATION
# These are default values used across all scenarios
# ============================================================================

@dataclass
class WealthConfig:
    """Configuration for wealth simulation."""

    # Personal Info
    current_age: int = 38
    retirement_age: int = 68
    life_expectancy: int = 90

    # Employment
    starting_salary: float = 150_000
    tax_rate: float = 0.27
    base_salary_growth: float = 0.01
    job_change_years: int = 4
    job_change_raise_min: float = 0.10
    job_change_raise_max: float = 0.20

    # Living Expenses
    monthly_living_expenses: float = 9_000
    expense_growth: float = 0.01

    # Cash Buffer (Emergency Fund)
    initial_cash_buffer: float = 27_000
    cash_return_rate: float = 0.02
    target_buffer_months: int = 3

    # Investments
    spy_mean_return: float = 0.10
    spy_volatility: float = 0.18

    # Insurance (Optional)
    enable_insurance: bool = False
    insurance_annual_premium: float = 2_000
    insurance_base_deductible: float = 1_000
    insurance_deductible_pct: float = 0.10
    insurance_lifetime_cap: float = 500_000
    insurance_stop_net_worth: float = 5_000_000
    insurance_settlement_age: float = 70

    # Debt/Bankruptcy
    debt_interest_rate: float = 0.05
    debt_bankruptcy_threshold: float = 100_000

    # Life Events
    life_events: List[Dict] = field(default_factory=list)

    # Simulation
    random_seed: Optional[int] = 42


# ============================================================================
# SIMULATION ENGINE
# (Implementation details - usually don't need to edit this)
# ============================================================================

class WealthSimulator:
    def __init__(self, config: WealthConfig):
        self.config = config
        if config.random_seed is not None:
            np.random.seed(config.random_seed)

    def simulate_biweekly_returns(self, num_periods: int) -> np.ndarray:
        """Generate market returns for bi-weekly periods."""
        biweekly_mean = self.config.spy_mean_return / 26
        biweekly_std = self.config.spy_volatility / np.sqrt(26)
        return np.random.normal(biweekly_mean, biweekly_std, num_periods)

    def run_single_simulation(self, sim_number: int = 0) -> Dict:
        """Run single simulation with proper dollar-cost averaging."""
        years = self.config.life_expectancy - self.config.current_age
        total_periods = int(years * 26)

        # Separate Accounts
        investment_balance = 0.0
        cash_buffer = self.config.initial_cash_buffer
        debt = 0.0

        # Business accounts
        business_investments = {}
        business_income = 0.0
        active_startup = None
        startup_exit_month = None
        startup_monthly_income = 0.0  # For kept startups

        # Income/Expenses
        annual_salary = self.config.starting_salary
        monthly_expenses = self.config.monthly_living_expenses

        # Tracking
        max_debt = 0.0
        triggered_events = set()

        returns = self.simulate_biweekly_returns(total_periods)

        for period in range(total_periods):
            age = self.config.current_age + (period / 26)
            month_num = period // 2
            is_month_end = (period % 2 == 1)
            is_retired = age >= self.config.retirement_age

            # STEP 1: DEPOSIT
            if not is_retired:
                biweekly_pay = (annual_salary * (1 - self.config.tax_rate)) / 26
                investment_balance += biweekly_pay

            # STEP 2: MARKET MOVES
            investment_balance *= (1 + returns[period])

            # STEP 3: WITHDRAW EXPENSES
            biweekly_expenses = monthly_expenses / 2

            if investment_balance >= biweekly_expenses:
                investment_balance -= biweekly_expenses
            else:
                shortfall = biweekly_expenses - investment_balance
                investment_balance = 0

                if cash_buffer >= shortfall:
                    cash_buffer -= shortfall
                else:
                    debt += (shortfall - cash_buffer)
                    cash_buffer = 0

            # Cash buffer grows
            if cash_buffer > 0:
                cash_buffer *= (1 + self.config.cash_return_rate / 26)

            # MONTH-END MANAGEMENT
            if is_month_end:
                # Annual adjustments
                if month_num > 0 and month_num % 12 == 0:
                    monthly_expenses *= (1 + self.config.expense_growth)
                    annual_salary *= (1 + self.config.base_salary_growth)

                    # Job changes
                    years_elapsed = month_num / 12
                    if years_elapsed > 0 and years_elapsed % self.config.job_change_years < 1/12:
                        raise_pct = np.random.uniform(
                            self.config.job_change_raise_min,
                            self.config.job_change_raise_max
                        )
                        annual_salary *= (1 + raise_pct)

                # Debt interest
                if debt > 0:
                    debt *= (1 + self.config.debt_interest_rate / 12)
                    max_debt = max(max_debt, debt)

                # Pay down debt
                if debt > 0 and cash_buffer > 0:
                    payment = min(debt, cash_buffer)
                    debt -= payment
                    cash_buffer -= payment

                if debt > 0 and investment_balance > 0:
                    payment = min(debt, investment_balance * 0.10)
                    debt -= payment
                    investment_balance -= payment

                # Bankruptcy check
                if debt >= self.config.debt_bankruptcy_threshold:
                    can_pay = investment_balance + cash_buffer
                    if can_pay >= debt:
                        if investment_balance >= debt:
                            investment_balance -= debt
                        else:
                            cash_buffer -= (debt - investment_balance)
                            investment_balance = 0
                        debt = 0
                    else:
                        return {
                            'success': False,
                            'bankruptcy': True,
                            'bankruptcy_age': age,
                            'final_net_worth': can_pay - debt,
                        }

                # Refill buffer
                target_buffer = monthly_expenses * self.config.target_buffer_months
                if cash_buffer < target_buffer and investment_balance > 50000:
                    transfer = min(
                        (investment_balance - 50000) * 0.10,
                        target_buffer - cash_buffer
                    )
                    if transfer > 0:
                        investment_balance -= transfer
                        cash_buffer += transfer

                # Check life events
                years_elapsed = month_num / 12
                for idx, event in enumerate(self.config.life_events):
                    if idx in triggered_events:
                        continue

                    if idx > 0 and (idx - 1) not in triggered_events:
                        continue

                    time_trigger = 'years_from_now' in event and abs(years_elapsed - event['years_from_now']) < 1/12

                    if 'investment' in event:
                        total_liquid = investment_balance + cash_buffer
                        can_afford = total_liquid >= event['investment']['cost']
                        liquid_trigger = 'liquid_trigger' in event and investment_balance >= event['liquid_trigger'] and can_afford
                    else:
                        liquid_trigger = 'liquid_trigger' in event and investment_balance >= event['liquid_trigger']

                    if time_trigger or liquid_trigger:
                        triggered_events.add(idx)

                        if 'one_time_payment' in event:
                            investment_balance += event['one_time_payment']

                        if 'annual_salary' in event:
                            annual_salary = event['annual_salary']

                        if 'monthly_living_expenses' in event:
                            monthly_expenses = event['monthly_living_expenses']

                        # Business investment
                        if 'investment' in event:
                            inv = event['investment']
                            if investment_balance >= inv['cost']:
                                investment_balance -= inv['cost']
                            else:
                                shortfall = inv['cost'] - investment_balance
                                investment_balance = 0
                                if cash_buffer >= shortfall:
                                    cash_buffer -= shortfall
                                else:
                                    debt += (shortfall - cash_buffer)
                                    cash_buffer = 0

                            business_investments[idx] = {
                                'name': inv.get('name', f'Investment_{idx}'),
                                'initial_cost': inv['cost'],
                                'annual_profit': inv['annual_profit'],
                                'growth_rate': inv.get('growth_rate', 0),
                            }

                        # Startup
                        if 'startup' in event:
                            startup_params = event['startup']
                            initial_investment = startup_params.get('investment', 500_000)

                            if investment_balance >= initial_investment:
                                investment_balance -= initial_investment

                                startup_config = StartupConfig(
                                    initial_investment=initial_investment,
                                    monthly_burn_rate=startup_params.get('monthly_burn_rate', initial_investment / 24),
                                    revenue_growth_mean=startup_params.get('revenue_growth_mean', 0.08),
                                    revenue_growth_std=startup_params.get('revenue_growth_std', 0.25),
                                    max_months=startup_params.get('max_months', 48),
                                    force_exit=startup_params.get('force_exit', True),
                                    profit_distribution=startup_params.get('profit_distribution', 0.50),
                                )

                                # Use sim_number + period for unique random seed per simulation
                                startup_seed = sim_number * 10000 + period
                                startup_sim = StartupSimulator(startup_config, random_seed=startup_seed)
                                startup_result = startup_sim.simulate()

                                active_startup = {
                                    'start_month': month_num,
                                    'result': startup_result,
                                }
                                startup_exit_month = month_num + startup_result['months_duration']

                                # If keeping company, set up monthly income
                                if startup_result.get('keeps_company'):
                                    startup_monthly_income = startup_result['monthly_profit']

                # Monthly income from businesses
                business_income = 0
                for idx, biz in business_investments.items():
                    monthly_profit = biz['annual_profit'] / 12
                    business_income += monthly_profit

                    if 'growth_rate' in biz and month_num % 12 == 0 and month_num > 0:
                        biz['annual_profit'] *= (1 + biz['growth_rate'])

                # Add business income + startup income
                investment_balance += business_income + startup_monthly_income

                # Check if startup exits
                if active_startup and startup_exit_month == month_num:
                    exit_value = active_startup['result']['exit_value']
                    investment_balance += exit_value
                    if not active_startup['result'].get('keeps_company'):
                        active_startup = None
                        startup_exit_month = None
                        startup_monthly_income = 0

        # Survived!
        final_net_worth = investment_balance + cash_buffer - debt

        return {
            'success': True,
            'bankruptcy': False,
            'bankruptcy_age': None,
            'final_net_worth': final_net_worth,
            'final_investment_balance': investment_balance,
            'final_cash_buffer': cash_buffer,
            'final_debt': debt,
            'max_debt': max_debt,
        }

    def run_simulations(self, num_sims: int) -> List[Dict]:
        """Run multiple simulations."""
        results = []
        for i in range(num_sims):
            results.append(self.run_single_simulation(sim_number=i))
        return results


# ============================================================================
# RUN SCENARIOS
# ============================================================================

if __name__ == "__main__":
    NUM_SIMS = 1000

    print("="*80)
    print("WEALTH SIMULATION - SCENARIO COMPARISON")
    print("="*80)
    print(f"\nRunning {NUM_SIMS} simulations per scenario...\n")

    all_results = {}

    for scenario_key, scenario_config in SCENARIOS.items():
        print(f"Running: {scenario_config['name']}...")

        config = WealthConfig(
            enable_insurance=False,
            life_events=scenario_config['life_events'],
            random_seed=None,  # Use different random seed for each simulation
        )

        simulator = WealthSimulator(config)
        results = simulator.run_simulations(NUM_SIMS)
        all_results[scenario_key] = {
            'name': scenario_config['name'],
            'description': scenario_config['description'],
            'results': results,
        }

    # Print summary
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)

    for scenario_key, data in all_results.items():
        results = data['results']
        survived = [r for r in results if r['success']]
        bankruptcies = [r for r in results if r.get('bankruptcy', False)]

        if survived:
            nw_values = [r['final_net_worth'] for r in survived]

            print(f"\n{data['name']}")
            print(f"  {data['description']}")
            print(f"  Survival: {len(survived)}/{len(results)} ({len(survived)/len(results)*100:.1f}%)")
            print(f"  Mean NW:   ${np.mean(nw_values):>15,.0f}")
            print(f"  Median NW: ${np.median(nw_values):>15,.0f}")
            print(f"  Min NW:    ${np.min(nw_values):>15,.0f}")
            print(f"  Max NW:    ${np.max(nw_values):>15,.0f}")
        else:
            print(f"\n{data['name']}")
            print(f"  {data['description']}")
            print(f"  Survival: 0/{len(results)} (0.0%)")

    print("\n" + "="*80)
