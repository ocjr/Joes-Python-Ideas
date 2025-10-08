"""
Startup Simulation - Realistic Startup Journey Modeling

Simulates a startup journey with:
- Monthly burn rate (operating costs)
- Revenue growth with volatility
- Path to profitability or failure
- Exit scenarios: sell company OR keep operating and take profits

Can be called by wealth_simulation.py to model startup life events.
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, Optional

# ============================================================================
# SCENARIO CONFIGURATIONS
# Edit these to test different startup scenarios
# ============================================================================

STARTUP_SCENARIOS = {
    'bootstrapped': {
        'name': 'Bootstrapped SaaS',
        'description': 'Conservative growth, low burn, keep operating',
        'config': {
            'initial_investment': 500_000,
            'monthly_burn_rate': 15_000,
            'revenue_growth_mean': 0.08,
            'revenue_growth_std': 0.20,
            'force_exit': False,  # Keep operating
            'profit_distribution': 0.50,
        }
    },

    'vc_backed': {
        'name': 'VC-Backed Growth',
        'description': 'Aggressive growth, high burn, sell when profitable',
        'config': {
            'initial_investment': 2_000_000,
            'monthly_burn_rate': 80_000,
            'revenue_growth_mean': 0.12,
            'revenue_growth_std': 0.30,
            'force_exit': True,  # Sell company
            'revenue_multiple_mean': 5.0,
        }
    },

    'lifestyle_business': {
        'name': 'Lifestyle Business',
        'description': 'Small, profitable, keep forever',
        'config': {
            'initial_investment': 100_000,
            'monthly_burn_rate': 5_000,
            'revenue_growth_mean': 0.05,
            'revenue_growth_std': 0.15,
            'force_exit': False,  # Keep operating
            'profit_distribution': 0.80,  # Take 80% as salary
            'min_arr_for_exit': 250_000,  # Lower bar
        }
    },

    'moonshot': {
        'name': 'Moonshot Startup',
        'description': 'High risk, high reward, massive scale or bust',
        'config': {
            'initial_investment': 5_000_000,
            'monthly_burn_rate': 200_000,
            'revenue_growth_mean': 0.15,
            'revenue_growth_std': 0.40,
            'force_exit': True,
            'revenue_multiple_mean': 6.0,
            'revenue_multiple_std': 3.0,
        }
    },
}


# ============================================================================
# BASE CONFIGURATION
# Default values for startup simulation
# ============================================================================

@dataclass
class StartupConfig:
    """Configuration for startup simulation."""

    # Initial investment
    initial_investment: float = 500_000

    # Operating costs
    monthly_burn_rate: float = 20_000
    burn_rate_growth: float = 0.05  # Burn increases as you hire

    # Revenue
    initial_monthly_revenue: float = 0
    revenue_growth_mean: float = 0.08  # 8% monthly growth
    revenue_growth_std: float = 0.25  # High volatility

    # Profitability
    gross_margin: float = 0.70  # 70% gross margin
    target_profit_margin: float = 0.20  # 20% target profit margin

    # Exit conditions
    max_months: int = 48  # 4 years max
    shutdown_if_broke: bool = True
    force_exit: bool = True  # True = sell company, False = keep operating

    # Exit multiples (if selling)
    revenue_multiple_mean: float = 4.0  # Realistic SaaS multiple
    revenue_multiple_std: float = 1.5

    # Founder parameters
    founder_ownership: float = 1.0  # 100% owned initially
    dilution_per_funding_round: float = 0.25  # Give up 25% per round

    # Success thresholds
    min_arr_for_exit: float = 1_000_000  # $1M ARR to be acquirable
    months_profitable_before_exit: int = 12  # Need 12mo profit to sell

    # Keep and operate (if not selling)
    profit_distribution: float = 0.50  # Take 50% of profits as salary


# ============================================================================
# SIMULATION ENGINE
# (Implementation details - usually don't need to edit this)
# ============================================================================

class StartupSimulator:
    """Simulates a startup journey."""

    def __init__(self, config: StartupConfig, random_seed: Optional[int] = None):
        self.config = config
        if random_seed is not None:
            np.random.seed(random_seed)

    def simulate(self) -> Dict:
        """Run single startup simulation."""

        # State
        cash_remaining = self.config.initial_investment
        monthly_revenue = self.config.initial_monthly_revenue
        monthly_burn = self.config.monthly_burn_rate
        ownership = self.config.founder_ownership

        # Tracking
        months_profitable = 0
        total_invested = self.config.initial_investment
        total_revenue = 0
        peak_burn = monthly_burn
        funding_rounds = 0

        for month in range(self.config.max_months):
            # Revenue grows (with volatility)
            if month == 3:  # Start with some initial revenue after 3 months
                monthly_revenue = monthly_burn * 0.10  # Start at 10% of burn
            elif monthly_revenue > 0:
                growth_rate = np.random.normal(
                    self.config.revenue_growth_mean,
                    self.config.revenue_growth_std
                )
                growth_rate = max(-0.30, min(1.00, growth_rate))  # Clamp
                monthly_revenue *= (1 + growth_rate)
                monthly_revenue = max(0, monthly_revenue)

            # Burn grows as company scales
            if monthly_revenue > monthly_burn * 0.5:
                monthly_burn *= (1 + self.config.burn_rate_growth)

            peak_burn = max(peak_burn, monthly_burn)

            # Calculate profit/loss
            gross_revenue = monthly_revenue * self.config.gross_margin
            net_profit = gross_revenue - monthly_burn

            # Update cash
            cash_remaining += net_profit
            total_revenue += monthly_revenue

            # Track profitability streak
            if net_profit > 0:
                months_profitable += 1
            else:
                months_profitable = 0

            # Exit condition 1: Ran out of money
            if cash_remaining <= 0 and self.config.shutdown_if_broke:
                # Try to raise funding if showing traction
                arr = monthly_revenue * 12
                if arr > 100_000 and funding_rounds < 2:
                    funding_needed = monthly_burn * 18
                    cash_remaining += funding_needed
                    total_invested += funding_needed
                    funding_rounds += 1
                    ownership *= (1 - self.config.dilution_per_funding_round)
                    continue
                else:
                    return {
                        'success': False,
                        'exit_value': 0,
                        'exit_type': 'shutdown_broke',
                        'months_duration': month,
                        'final_arr': monthly_revenue * 12,
                        'total_invested': total_invested,
                        'total_revenue': total_revenue,
                        'peak_burn': peak_burn,
                        'funding_rounds': funding_rounds,
                        'final_ownership': ownership,
                        'monthly_profit': 0,
                        'keeps_company': False,
                    }

            # Exit condition 2: Profitable and ready to exit or keep operating
            arr = monthly_revenue * 12
            if (arr >= self.config.min_arr_for_exit and
                months_profitable >= self.config.months_profitable_before_exit):

                # Option 1: Sell the company
                if self.config.force_exit:
                    revenue_multiple = np.random.normal(
                        self.config.revenue_multiple_mean,
                        self.config.revenue_multiple_std
                    )
                    revenue_multiple = max(2.0, revenue_multiple)

                    exit_value = arr * revenue_multiple
                    founder_proceeds = exit_value * ownership

                    return {
                        'success': True,
                        'exit_value': founder_proceeds,
                        'exit_type': 'acquisition',
                        'months_duration': month,
                        'final_arr': arr,
                        'total_invested': total_invested,
                        'total_revenue': total_revenue,
                        'peak_burn': peak_burn,
                        'funding_rounds': funding_rounds,
                        'final_ownership': ownership,
                        'exit_multiple': revenue_multiple,
                        'monthly_profit': 0,
                        'keeps_company': False,
                    }
                else:
                    # Option 2: Keep operating and take profit distributions
                    monthly_profit_to_founder = net_profit * ownership * self.config.profit_distribution

                    return {
                        'success': True,
                        'exit_value': 0,  # Not selling
                        'exit_type': 'kept_operating',
                        'months_duration': month,
                        'final_arr': arr,
                        'total_invested': total_invested,
                        'total_revenue': total_revenue,
                        'peak_burn': peak_burn,
                        'funding_rounds': funding_rounds,
                        'final_ownership': ownership,
                        'monthly_profit': monthly_profit_to_founder,
                        'keeps_company': True,
                    }

        # Reached max months without profitable exit
        arr = monthly_revenue * 12

        # If profitable, can still sell for something
        if months_profitable >= 6:
            revenue_multiple = np.random.normal(2.5, 1.0)
            revenue_multiple = max(1.0, revenue_multiple)
            exit_value = arr * revenue_multiple
            founder_proceeds = exit_value * ownership

            return {
                'success': founder_proceeds > total_invested,
                'exit_value': founder_proceeds,
                'exit_type': 'acqui-hire' if founder_proceeds < total_invested else 'late_exit',
                'months_duration': self.config.max_months,
                'final_arr': arr,
                'total_invested': total_invested,
                'total_revenue': total_revenue,
                'peak_burn': peak_burn,
                'funding_rounds': funding_rounds,
                'final_ownership': ownership,
                'exit_multiple': revenue_multiple,
                'monthly_profit': 0,
                'keeps_company': False,
            }
        else:
            # Gave up, no exit value
            return {
                'success': False,
                'exit_value': cash_remaining * ownership,
                'exit_type': 'gave_up',
                'months_duration': self.config.max_months,
                'final_arr': arr,
                'total_invested': total_invested,
                'total_revenue': total_revenue,
                'peak_burn': peak_burn,
                'funding_rounds': funding_rounds,
                'final_ownership': ownership,
                'monthly_profit': 0,
                'keeps_company': False,
            }


# ============================================================================
# RUN SCENARIOS
# ============================================================================

if __name__ == "__main__":
    NUM_SIMS = 1000

    print("="*80)
    print("STARTUP SIMULATION - SCENARIO COMPARISON")
    print("="*80)
    print(f"\nRunning {NUM_SIMS} simulations per scenario...\n")

    all_results = {}

    for scenario_key, scenario_data in STARTUP_SCENARIOS.items():
        print(f"Running: {scenario_data['name']}...")

        # Build config from base + scenario overrides
        config_dict = scenario_data['config']
        config = StartupConfig(**config_dict)

        # Run simulations
        results = []
        for i in range(NUM_SIMS):
            simulator = StartupSimulator(config, random_seed=i)
            result = simulator.simulate()
            results.append(result)

        all_results[scenario_key] = {
            'name': scenario_data['name'],
            'description': scenario_data['description'],
            'results': results,
        }

    # Print summary
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)

    for scenario_key, data in all_results.items():
        results = data['results']
        successes = [r for r in results if r['success']]
        shutdowns = [r for r in results if 'shutdown' in r['exit_type']]
        acquisitions = [r for r in results if r['exit_type'] == 'acquisition']
        kept_operating = [r for r in results if r['exit_type'] == 'kept_operating']

        print(f"\n{data['name']}")
        print(f"  {data['description']}")
        print(f"  Success Rate: {len(successes)}/{len(results)} ({len(successes)/len(results)*100:.1f}%)")
        print(f"  Shutdowns: {len(shutdowns)} ({len(shutdowns)/len(results)*100:.1f}%)")
        print(f"  Acquisitions: {len(acquisitions)} ({len(acquisitions)/len(results)*100:.1f}%)")
        print(f"  Kept Operating: {len(kept_operating)} ({len(kept_operating)/len(results)*100:.1f}%)")

        if successes:
            # For sold companies, show exit values
            sold = [r for r in successes if r['exit_value'] > 0]
            if sold:
                exit_values = [r['exit_value'] for r in sold]
                print(f"  Exit Values (sold):")
                print(f"    Mean:   ${np.mean(exit_values):>15,.0f}")
                print(f"    Median: ${np.median(exit_values):>15,.0f}")
                print(f"    Min:    ${np.min(exit_values):>15,.0f}")
                print(f"    Max:    ${np.max(exit_values):>15,.0f}")

            # For kept companies, show monthly profit
            kept = [r for r in successes if r.get('keeps_company')]
            if kept:
                monthly_profits = [r['monthly_profit'] for r in kept]
                print(f"  Monthly Profit (kept):")
                print(f"    Mean:   ${np.mean(monthly_profits):>15,.0f}")
                print(f"    Median: ${np.median(monthly_profits):>15,.0f}")
                print(f"    Min:    ${np.min(monthly_profits):>15,.0f}")
                print(f"    Max:    ${np.max(monthly_profits):>15,.0f}")

        # Duration stats
        durations = [r['months_duration'] for r in results]
        print(f"  Duration:")
        print(f"    Mean: {np.mean(durations):.1f} months")
        print(f"    Median: {np.median(durations):.0f} months")

    print("\n" + "="*80)
