"""
Wealth Simulation - Core Financial Path Simulator

This is the main simulation engine that models a realistic financial journey with:
- Bi-weekly salary deposits (dollar-cost averaging)
- Monthly expense withdrawals
- Separate cash buffer (emergency fund)
- Optional portfolio insurance
- Life events (windfalls, job changes, startups, investments)

The simulation properly implements DCA where regular deposits buffer against
market volatility - you're constantly buying at different prices.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from startup_simulation import StartupSimulator, StartupConfig

# ============================================================================
# DEFAULT CONFIGURATION
# ============================================================================

@dataclass
class WealthConfig:
    """Configuration for wealth simulation."""

    # Personal Info
    current_age: int = 38
    retirement_age: int = 68
    life_expectancy: int = 90

    # Employment
    starting_salary: float = 150000
    tax_rate: float = 0.27
    base_salary_growth: float = 0.01  # 1% annual raises
    job_change_years: int = 4  # Change jobs every 4 years
    job_change_raise_min: float = 0.10  # 10-20% raise when changing jobs
    job_change_raise_max: float = 0.20

    # Living Expenses
    monthly_living_expenses: float = 9000
    expense_growth: float = 0.01  # 1% (mix of fixed mortgage/car + variable food)

    # Cash Buffer (Emergency Fund)
    initial_cash_buffer: float = 27000  # 3 months expenses
    cash_return_rate: float = 0.02  # 2% HYSA
    target_buffer_months: int = 3  # Maintain 3 months

    # Investments
    spy_mean_return: float = 0.10
    spy_volatility: float = 0.18

    # Insurance (Optional)
    enable_insurance: bool = False
    insurance_annual_premium: float = 2000
    insurance_base_deductible: float = 1000
    insurance_deductible_pct: float = 0.10  # 10% of balance
    insurance_lifetime_cap: float = 500000
    insurance_stop_net_worth: float = 5000000
    insurance_settlement_age: float = 70

    # Debt/Bankruptcy
    debt_interest_rate: float = 0.05
    debt_bankruptcy_threshold: float = 100000

    # Life Events
    life_events: List[Dict] = field(default_factory=list)

    # Simulation
    random_seed: Optional[int] = 42


# ============================================================================
# SIMULATION ENGINE
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

    def run_single_simulation(self) -> Dict:
        """
        Run single simulation with proper dollar-cost averaging.

        Key insight: Frequent compounding with deposits/withdrawals.
        - Bi-weekly: Add deposit, apply return, subtract half of monthly expenses
        - The balance fluctuates but frequent deposits during dips = accumulation
        - Like compound interest but with variable rates (market returns)

        Each bi-weekly period:
        1. Add paycheck deposit
        2. Apply market return: balance *= (1 + return)
        3. Subtract expenses (half of monthly on each period)
        4. If negative: use buffer → insurance → debt
        """
        years = self.config.life_expectancy - self.config.current_age
        total_periods = int(years * 26)  # 26 bi-weekly periods per year

        # Separate Accounts
        investment_balance = 0.0  # Market-invested funds (personal wealth)
        cash_buffer = self.config.initial_cash_buffer  # Emergency fund
        debt = 0.0  # Personal debt

        # Business accounts (separate from personal)
        business_investments = {}  # Track each business investment separately
        business_income = 0.0  # Monthly income from all businesses
        active_startup = None  # Track active startup if one is running
        startup_exit_month = None  # When startup exits

        # Income/Expenses
        annual_salary = self.config.starting_salary
        monthly_expenses = self.config.monthly_living_expenses

        # Insurance
        total_premiums = 0.0
        total_payouts = 0.0
        claims = 0
        lifetime_payout_remaining = self.config.insurance_lifetime_cap
        settlement = 0.0

        # Tracking
        max_debt = 0.0
        catastrophic_events = []
        peak_balance = 0.0
        in_drawdown = False
        triggered_events = set()
        investment_profits = {}  # Track investment profits per simulation

        # Generate returns
        returns = self.simulate_biweekly_returns(total_periods)

        for period in range(total_periods):
            age = self.config.current_age + (period / 26)
            month_num = period // 2
            is_month_end = (period % 2 == 1)
            is_retired = age >= self.config.retirement_age

            # ===== STEP 1: DEPOSIT =====
            if not is_retired:
                biweekly_pay = (annual_salary * (1 - self.config.tax_rate)) / 26
                investment_balance += biweekly_pay

            # ===== STEP 2: MARKET MOVES (compounding) =====
            investment_balance *= (1 + returns[period])

            # ===== STEP 3: WITHDRAW EXPENSES (bi-weekly, so half of monthly) =====
            biweekly_expenses = monthly_expenses / 2

            if investment_balance >= biweekly_expenses:
                investment_balance -= biweekly_expenses
            else:
                # Shortfall - need buffer/insurance/debt
                shortfall = biweekly_expenses - investment_balance
                investment_balance = 0

                # Use cash buffer first
                if cash_buffer >= shortfall:
                    cash_buffer -= shortfall
                else:
                    # Use all buffer, rest becomes debt
                    debt += (shortfall - cash_buffer)
                    cash_buffer = 0

            # Track catastrophic events
            if is_month_end and investment_balance > 10000:
                peak_balance = max(peak_balance, investment_balance)
                if peak_balance > 0:
                    drawdown = (peak_balance - investment_balance) / peak_balance
                    if drawdown >= 0.20 and not in_drawdown:
                        catastrophic_events.append({
                            'age': age,
                            'drawdown': drawdown
                        })
                        in_drawdown = True
                    elif drawdown < 0.10:
                        in_drawdown = False

            # Cash buffer grows
            if cash_buffer > 0:
                cash_buffer *= (1 + self.config.cash_return_rate / 26)

            # ===== MONTH-END: MANAGEMENT =====
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

                # Pay insurance premium (annually)
                if self.config.enable_insurance and month_num % 12 == 0:
                    net_worth = investment_balance + cash_buffer - debt
                    insurance_active = (
                        age < self.config.insurance_settlement_age and
                        net_worth < self.config.insurance_stop_net_worth and
                        lifetime_payout_remaining > 0
                    )

                    if insurance_active:
                        if cash_buffer >= self.config.insurance_annual_premium:
                            cash_buffer -= self.config.insurance_annual_premium
                            total_premiums += self.config.insurance_annual_premium

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
                    payment = min(debt, investment_balance * 0.10)  # Max 10% of investments
                    debt -= payment
                    investment_balance -= payment

                # Bankruptcy check
                if debt >= self.config.debt_bankruptcy_threshold:
                    can_pay = investment_balance + cash_buffer
                    if can_pay >= debt:
                        # Pay it off
                        if investment_balance >= debt:
                            investment_balance -= debt
                        else:
                            cash_buffer -= (debt - investment_balance)
                            investment_balance = 0
                        debt = 0
                    else:
                        # Bankruptcy
                        return {
                            'success': False,
                            'bankruptcy': True,
                            'bankruptcy_age': age,
                            'final_net_worth': can_pay - debt,
                            'insurance_premiums': total_premiums,
                            'insurance_payouts': total_payouts,
                            'insurance_claims': claims,
                            'insurance_settlement': settlement,
                            'catastrophic_events': catastrophic_events,
                            'max_debt': max_debt
                        }

                # Refill buffer if investments healthy
                target_buffer = monthly_expenses * self.config.target_buffer_months
                if cash_buffer < target_buffer and investment_balance > 50000:
                    transfer = min(
                        (investment_balance - 50000) * 0.10,
                        target_buffer - cash_buffer
                    )
                    if transfer > 0:
                        investment_balance -= transfer
                        cash_buffer += transfer

                # Settlement at age 70
                if (self.config.enable_insurance and
                    age >= self.config.insurance_settlement_age and
                    settlement == 0):
                    net_insurance = total_payouts - total_premiums
                    if net_insurance > 0:
                        settlement = net_insurance * 0.50
                        if cash_buffer >= settlement:
                            cash_buffer -= settlement
                        else:
                            settlement = cash_buffer
                            cash_buffer = 0

                # Check life events
                years_elapsed = month_num / 12
                for idx, event in enumerate(self.config.life_events):
                    if idx in triggered_events:
                        continue

                    # Sequential trigger
                    if idx > 0 and (idx - 1) not in triggered_events:
                        continue

                    time_trigger = 'years_from_now' in event and abs(years_elapsed - event['years_from_now']) < 1/12

                    # For investments, check if we can afford it
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

                        # Business investment (generates recurring income)
                        if 'investment' in event:
                            inv = event['investment']
                            # Deduct investment cost from personal wealth
                            if investment_balance >= inv['cost']:
                                investment_balance -= inv['cost']
                            else:
                                # Use buffer first, then debt
                                shortfall = inv['cost'] - investment_balance
                                investment_balance = 0
                                if cash_buffer >= shortfall:
                                    cash_buffer -= shortfall
                                else:
                                    debt += (shortfall - cash_buffer)
                                    cash_buffer = 0

                            # Track this business separately
                            business_investments[idx] = {
                                'name': inv.get('name', f'Investment_{idx}'),
                                'initial_cost': inv['cost'],
                                'annual_profit': inv['annual_profit'],
                                'growth_rate': inv.get('growth_rate', 0),
                            }

                        # Startup life event
                        if 'startup' in event:
                            startup_params = event['startup']
                            # Pull money from personal wealth for startup
                            initial_investment = startup_params.get('investment', 500000)

                            if investment_balance >= initial_investment:
                                investment_balance -= initial_investment

                                # Run startup simulation
                                startup_config = StartupConfig(
                                    initial_investment=initial_investment,
                                    monthly_burn_rate=startup_params.get('monthly_burn_rate', initial_investment / 24),
                                    revenue_growth_mean=startup_params.get('revenue_growth_mean', 0.15),
                                    revenue_growth_std=startup_params.get('revenue_growth_std', 0.30),
                                    max_months=startup_params.get('max_months', 48),
                                )

                                startup_sim = StartupSimulator(startup_config, random_seed=period)
                                startup_result = startup_sim.simulate()

                                # Track startup
                                active_startup = {
                                    'start_month': month_num,
                                    'result': startup_result,
                                }
                                startup_exit_month = month_num + startup_result['months_duration']

                # Monthly income from business investments (at month-end)
                business_income = 0
                for idx, biz in business_investments.items():
                    monthly_profit = biz['annual_profit'] / 12
                    business_income += monthly_profit

                    # Apply growth to the annual profit each year
                    if 'growth_rate' in biz and month_num % 12 == 0 and month_num > 0:
                        biz['annual_profit'] *= (1 + biz['growth_rate'])

                # Add business income to personal investment account
                investment_balance += business_income

                # Check if startup exits this month
                if active_startup and startup_exit_month == month_num:
                    exit_value = active_startup['result']['exit_value']
                    investment_balance += exit_value
                    active_startup = None  # Startup is done
                    startup_exit_month = None

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
            'insurance_premiums': total_premiums,
            'insurance_payouts': total_payouts,
            'insurance_claims': claims,
            'insurance_settlement': settlement,
            'catastrophic_events': catastrophic_events,
            'max_debt': max_debt
        }

    def run_simulations(self, num_sims: int) -> List[Dict]:
        """Run multiple simulations."""
        results = []
        for i in range(num_sims):
            if (i + 1) % 100 == 0:
                print(f"  Completed {i + 1}/{num_sims}")
            results.append(self.run_single_simulation())
        return results

    def analyze_results(self, results: List[Dict]) -> Dict:
        """Analyze and print results."""
        survived = sum(1 for r in results if r['success'])
        bankruptcies = sum(1 for r in results if r['bankruptcy'])

        final_nw = [r['final_net_worth'] for r in results if r['success']]

        # Insurance metrics
        if self.config.enable_insurance:
            premiums = [r['insurance_premiums'] for r in results]
            payouts = [r['insurance_payouts'] for r in results]
            claims = [r['insurance_claims'] for r in results]
            settlements = [r['insurance_settlement'] for r in results]
            profits = [(p + s - pay) for p, pay, s in zip(premiums, payouts, settlements)]

        # Catastrophic events
        all_catastrophic = []
        for r in results:
            all_catastrophic.extend(r['catastrophic_events'])
        scenarios_with_crash = sum(1 for r in results if len(r['catastrophic_events']) > 0)

        print("\n" + "="*70)
        print("WEALTH SIMULATION RESULTS")
        print("="*70)

        print(f"\nOutcomes:")
        print(f"  Survived: {survived}/{len(results)} ({survived/len(results)*100:.1f}%)")
        print(f"  Bankruptcies: {bankruptcies}/{len(results)} ({bankruptcies/len(results)*100:.1f}%)")

        if final_nw:
            print(f"\nFinal Net Worth:")
            print(f"  Mean: ${np.mean(final_nw):,.0f}")
            print(f"  Median: ${np.median(final_nw):,.0f}")
            print(f"  10th %ile: ${np.percentile(final_nw, 10):,.0f}")
            print(f"  90th %ile: ${np.percentile(final_nw, 90):,.0f}")

        if self.config.enable_insurance:
            print(f"\nInsurance Performance:")
            print(f"  Mean Premium: ${np.mean(premiums):,.0f}")
            print(f"  Mean Payout: ${np.mean(payouts):,.0f}")
            print(f"  Mean Claims: {np.mean(claims):.1f}")
            print(f"  Policies with Claims: {sum(1 for c in claims if c > 0)}/{len(claims)}")
            print(f"\n  Insurance Company:")
            print(f"    Mean Profit: ${np.mean(profits):,.0f}")
            print(f"    Profitable Policies: {sum(1 for p in profits if p > 0)}/{len(profits)}")
            loss_ratio = sum(payouts) / (sum(premiums) + sum(settlements)) * 100
            print(f"    Loss Ratio: {loss_ratio:.1f}%")

        if all_catastrophic:
            print(f"\nMarket Crashes (>20% drawdown):")
            print(f"  Scenarios with crash: {scenarios_with_crash}/{len(results)}")
            print(f"  Total crashes: {len(all_catastrophic)}")
            print(f"  Max drawdown: {max(e['drawdown'] for e in all_catastrophic)*100:.1f}%")

        print("\n" + "="*70)

        return {
            'survival_rate': survived / len(results),
            'bankruptcy_rate': bankruptcies / len(results),
            'mean_final_nw': np.mean(final_nw) if final_nw else 0,
        }


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("WEALTH SIMULATION SCENARIOS")
    print("="*80)

    # ========================================================================
    # SCENARIO 1: BASELINE - No windfall, no insurance
    # ========================================================================
    print("\n\n>>> SCENARIO 1: BASELINE (No windfall, just salary + market)")
    config1 = WealthConfig(
        enable_insurance=False,
        life_events=[]
    )
    simulator1 = WealthSimulator(config1)
    results1 = simulator1.run_simulations(1000)
    stats1 = simulator1.analyze_results(results1)

    # ========================================================================
    # SCENARIO 2: WINDFALL - $1M windfall in 3 years, no insurance
    # ========================================================================
    print("\n\n>>> SCENARIO 2: WINDFALL ($1M in 3 years, keep job, no insurance)")
    config2 = WealthConfig(
        enable_insurance=False,
        life_events=[
            {'years_from_now': 3, 'one_time_payment': 1000000},
        ]
    )
    simulator2 = WealthSimulator(config2)
    results2 = simulator2.run_simulations(1000)
    stats2 = simulator2.analyze_results(results2)

    # ========================================================================
    # SCENARIO 3: STARTUP - $1M windfall, invest in startup
    # ========================================================================
    print("\n\n>>> SCENARIO 3: STARTUP ($1M windfall → invest $500k in startup)")
    config3 = WealthConfig(
        enable_insurance=False,
        life_events=[
            {'years_from_now': 3, 'one_time_payment': 1000000},
            {
                'liquid_trigger': 900000,
                'startup': {
                    'investment': 500000,
                    'monthly_burn_rate': 20000,
                    'revenue_growth_mean': 0.10,
                    'revenue_growth_std': 0.20,
                    'max_months': 48,
                }
            },
        ]
    )
    simulator3 = WealthSimulator(config3)
    results3 = simulator3.run_simulations(1000)
    stats3 = simulator3.analyze_results(results3)

    # ========================================================================
    # SCENARIO 4: INVESTMENTS - Real estate + McDonald's franchise
    # ========================================================================
    print("\n\n>>> SCENARIO 4: INVESTMENTS ($1M windfall → McDonald's franchise + Apartment)")
    config4 = WealthConfig(
        enable_insurance=False,
        life_events=[
            {'years_from_now': 3, 'one_time_payment': 1000000},
            {
                'liquid_trigger': 9000000,
                'investment': {
                    'name': "McDonald's Franchise",
                    'cost': 2500000,  # Will go into debt for this
                    'annual_profit': 150000,  # $12.5k/month profit
                    'growth_rate': 0.03,  # 3% annual growth
                }
            },
            {
                'liquid_trigger': 5000000,
                'investment': {
                    'name': 'Apartment Complex',
                    'cost': 1000000,
                    'annual_profit': 60000,  # $5k/month rent profit
                    'growth_rate': 0.04,  # 4% annual growth
                }
            },
        ]
    )
    simulator4 = WealthSimulator(config4)
    results4 = simulator4.run_simulations(1000)
    stats4 = simulator4.analyze_results(results4)

    # ========================================================================
    # SCENARIO 5: CONSERVATIVE + INSURANCE
    # ========================================================================
    print("\n\n>>> SCENARIO 5: CONSERVATIVE WITH INSURANCE ($1M windfall, keep job, insured)")
    config5 = WealthConfig(
        enable_insurance=True,
        insurance_annual_premium=2000,
        insurance_base_deductible=1000,
        insurance_lifetime_cap=500000,
        life_events=[
            {'years_from_now': 3, 'one_time_payment': 1000000},
        ]
    )
    simulator5 = WealthSimulator(config5)
    results5 = simulator5.run_simulations(1000)
    stats5 = simulator5.analyze_results(results5)

    # ========================================================================
    # SCENARIO 6: AGGRESSIVE + INSURANCE
    # ========================================================================
    print("\n\n>>> SCENARIO 6: AGGRESSIVE STARTUP WITH INSURANCE ($1M windfall → quit job)")
    config6 = WealthConfig(
        enable_insurance=True,
        insurance_annual_premium=2000,
        insurance_base_deductible=1000,
        insurance_lifetime_cap=500000,
        life_events=[
            {'years_from_now': 3, 'one_time_payment': 1000000},
            {
                'liquid_trigger': 900000,
                'annual_salary': 0,
                'monthly_living_expenses': 15000,
            },
        ]
    )
    simulator6 = WealthSimulator(config6)
    results6 = simulator6.run_simulations(1000)
    stats6 = simulator6.analyze_results(results6)

    # ========================================================================
    # SUMMARY COMPARISON
    # ========================================================================
    print("\n\n" + "="*80)
    print("SCENARIO COMPARISON")
    print("="*80)

    scenarios = [
        ("Baseline (no windfall)", stats1),
        ("Windfall + Keep Job", stats2),
        ("Windfall + Startup (high burn)", stats3),
        ("Windfall + Investments (franchise + real estate)", stats4),
        ("Conservative + Insurance", stats5),
        ("Aggressive Startup + Insurance", stats6),
    ]

    print(f"\n{'Scenario':<45} {'Survival %':<12} {'Mean Final NW':<20}")
    print("-" * 80)
    for name, stats in scenarios:
        print(f"{name:<45} {stats['survival_rate']*100:<12.1f} ${stats['mean_final_nw']:<19,.0f}")

    print("\n" + "="*80)
