"""
Billionaire Path Optimization - Find Realistic Path to $100M+

This file varies startup and investment parameters to find configurations that:
1. Realistically reach billionaire status ($100M+)
2. Model typical entrepreneurial outcomes (most fail, few succeed massively)
3. Show the probability distribution of outcomes

We'll test:
- Windfall timing and amounts
- Startup success parameters (burn rate, growth rate, profitability)
- Follow-on investment opportunities
- Risk/return tradeoffs
"""

import numpy as np
import pandas as pd
from wealth_simulation import WealthSimulator, WealthConfig

# Base configuration with conservative startup
BASE_CONFIG = {
    'current_age': 38,
    'retirement_age': 68,
    'life_expectancy': 90,
    'starting_salary': 150000,
    'tax_rate': 0.27,
    'base_salary_growth': 0.01,
    'job_change_years': 4,
    'job_change_raise_min': 0.10,
    'job_change_raise_max': 0.20,
    'monthly_living_expenses': 9000,
    'expense_growth': 0.01,
    'initial_cash_buffer': 27000,
    'cash_return_rate': 0.02,
    'target_buffer_months': 3,
    'spy_mean_return': 0.10,
    'spy_volatility': 0.18,
    'enable_insurance': False,
    'debt_interest_rate': 0.05,
    'debt_bankruptcy_threshold': 100000,
    'random_seed': None,  # Important: use different seeds for each sim
}

# Scenarios to test
WINDFALL_AMOUNTS = [500_000, 1_000_000, 2_000_000, 5_000_000]
WINDFALL_TIMING = [3, 5, 10]  # Years from now

# Startup parameters to vary
STARTUP_INVESTMENT_PCT = [0.5, 0.75, 1.0]  # % of liquid assets to invest


def create_aggressive_scenario(windfall_amount, windfall_years):
    """Create life events for aggressive wealth building."""
    return [
        {
            'years_from_now': windfall_years,
            'one_time_payment': windfall_amount,
        },
        {
            'liquid_trigger': windfall_amount * 0.9,  # Start startup after windfall
            'annual_salary': 0,  # Quit job for startup
            'monthly_living_expenses': 15000,  # Increased expenses during startup
        }
    ]


def create_conservative_scenario(windfall_amount, windfall_years):
    """Create life events for conservative wealth building."""
    return [
        {
            'years_from_now': windfall_years,
            'one_time_payment': windfall_amount,
        },
        # Keep job, just invest the windfall
    ]


def create_staged_investment_scenario(windfall_amount, windfall_years):
    """Create life events with staged investments as wealth grows."""
    return [
        {
            'years_from_now': windfall_years,
            'one_time_payment': windfall_amount,
        },
        {
            'liquid_trigger': 10_000_000,
            'monthly_living_expenses': 20000,  # Lifestyle inflation
        },
        {
            'liquid_trigger': 50_000_000,
            'monthly_living_expenses': 50000,  # More lifestyle inflation
        },
    ]


def test_scenario(scenario_name, windfall_amount, windfall_years, life_events, num_sims=1000):
    """Test a specific scenario."""
    config_dict = BASE_CONFIG.copy()
    config_dict['life_events'] = life_events

    config = WealthConfig(**config_dict)
    results = []

    # Run with different random seeds
    for i in range(num_sims):
        config_dict['random_seed'] = i
        config = WealthConfig(**config_dict)
        simulator = WealthSimulator(config)
        result = simulator.run_single_simulation()
        results.append(result)

    # Analyze outcomes
    survived = sum(1 for r in results if r['success'])
    bankruptcies = sum(1 for r in results if r['bankruptcy'])

    final_nw = [r['final_net_worth'] for r in results if r['success']]

    # Wealth tiers
    millionaires = sum(1 for nw in final_nw if nw >= 1_000_000)
    multi_millionaires = sum(1 for nw in final_nw if nw >= 10_000_000)
    ultra_wealthy = sum(1 for nw in final_nw if nw >= 100_000_000)
    billionaires = sum(1 for nw in final_nw if nw >= 1_000_000_000)

    return {
        'scenario': scenario_name,
        'windfall_amount': windfall_amount,
        'windfall_years': windfall_years,

        # Outcomes
        'survival_rate': survived / num_sims * 100,
        'bankruptcy_rate': bankruptcies / num_sims * 100,

        # Wealth distribution
        'mean_final_nw': np.mean(final_nw) if final_nw else 0,
        'median_final_nw': np.median(final_nw) if final_nw else 0,
        'p10_final_nw': np.percentile(final_nw, 10) if final_nw else 0,
        'p90_final_nw': np.percentile(final_nw, 90) if final_nw else 0,
        'max_final_nw': np.max(final_nw) if final_nw else 0,

        # Wealth tiers
        'millionaire_pct': millionaires / num_sims * 100 if final_nw else 0,
        'multi_millionaire_pct': multi_millionaires / num_sims * 100 if final_nw else 0,
        'ultra_wealthy_pct': ultra_wealthy / num_sims * 100 if final_nw else 0,
        'billionaire_pct': billionaires / num_sims * 100 if final_nw else 0,
    }


def main():
    """Run billionaire path optimization."""
    print("="*80)
    print("BILLIONAIRE PATH OPTIMIZATION")
    print("="*80)
    print(f"\nTesting scenarios:")
    print(f"  Windfall amounts: {[f'${w:,}' for w in WINDFALL_AMOUNTS]}")
    print(f"  Windfall timing: {WINDFALL_TIMING} years")
    print(f"  Simulations per scenario: 1000")
    print("="*80)

    results = []

    # Test baseline (no windfall)
    print("\n\nBASELINE: No windfall, just salary + market growth")
    baseline = test_scenario("Baseline", 0, 0, [], 1000)
    results.append(baseline)
    print(f"  Survival: {baseline['survival_rate']:.1f}%")
    print(f"  Mean Final NW: ${baseline['mean_final_nw']:,.0f}")
    print(f"  Millionaires: {baseline['millionaire_pct']:.1f}%")
    print(f"  Multi-Millionaires ($10M+): {baseline['multi_millionaire_pct']:.1f}%")

    # Test conservative scenarios
    print("\n\n" + "="*80)
    print("CONSERVATIVE: Windfall + keep job + invest in market")
    print("="*80)

    for windfall in WINDFALL_AMOUNTS:
        for years in WINDFALL_TIMING:
            print(f"\n  Testing: ${windfall:,} in {years} years...")
            life_events = create_conservative_scenario(windfall, years)
            result = test_scenario(f"Conservative ${windfall/1e6:.1f}M @ {years}yr",
                                   windfall, years, life_events, 1000)
            results.append(result)
            print(f"    Survival: {result['survival_rate']:.1f}%, "
                  f"Mean NW: ${result['mean_final_nw']:,.0f}, "
                  f"$100M+: {result['ultra_wealthy_pct']:.1f}%")

    # Test aggressive scenarios
    print("\n\n" + "="*80)
    print("AGGRESSIVE: Windfall + quit job + all-in on startup")
    print("="*80)

    for windfall in WINDFALL_AMOUNTS:
        for years in WINDFALL_TIMING:
            print(f"\n  Testing: ${windfall:,} in {years} years...")
            life_events = create_aggressive_scenario(windfall, years)
            result = test_scenario(f"Aggressive ${windfall/1e6:.1f}M @ {years}yr",
                                   windfall, years, life_events, 1000)
            results.append(result)
            print(f"    Survival: {result['survival_rate']:.1f}%, "
                  f"Mean NW: ${result['mean_final_nw']:,.0f}, "
                  f"$100M+: {result['ultra_wealthy_pct']:.1f}%")

    # Test staged investment scenarios
    print("\n\n" + "="*80)
    print("STAGED: Windfall + lifestyle inflation as wealth grows")
    print("="*80)

    for windfall in WINDFALL_AMOUNTS:
        for years in WINDFALL_TIMING:
            print(f"\n  Testing: ${windfall:,} in {years} years...")
            life_events = create_staged_investment_scenario(windfall, years)
            result = test_scenario(f"Staged ${windfall/1e6:.1f}M @ {years}yr",
                                   windfall, years, life_events, 1000)
            results.append(result)
            print(f"    Survival: {result['survival_rate']:.1f}%, "
                  f"Mean NW: ${result['mean_final_nw']:,.0f}, "
                  f"$100M+: {result['ultra_wealthy_pct']:.1f}%")

    # Analysis
    print("\n\n" + "="*80)
    print("OPTIMIZATION RESULTS")
    print("="*80)

    df = pd.DataFrame(results)

    # Best chance of reaching $100M+
    print("\n--- BEST PATHS TO $100M+ ---")
    ultra = df.sort_values('ultra_wealthy_pct', ascending=False).head(10)
    print(f"\n{'Scenario':<40} {'Windfall':<15} {'Ultra Wealthy %':<15} {'Mean NW':<15}")
    print("-" * 90)
    for idx, row in ultra.iterrows():
        print(f"{row['scenario']:<40} ${row['windfall_amount']:<14,.0f} "
              f"{row['ultra_wealthy_pct']:<15.1f}% ${row['mean_final_nw']:<14,.0f}")

    # Best risk-adjusted (high survival + high wealth)
    print("\n\n--- BEST RISK-ADJUSTED (Survival > 90% + Highest Mean NW) ---")
    safe_and_wealthy = df[df['survival_rate'] > 90].sort_values('mean_final_nw', ascending=False).head(10)
    print(f"\n{'Scenario':<40} {'Survival %':<12} {'Mean NW':<15} {'$10M+ %':<12}")
    print("-" * 90)
    for idx, row in safe_and_wealthy.iterrows():
        print(f"{row['scenario']:<40} {row['survival_rate']:<12.1f}% "
              f"${row['mean_final_nw']:<14,.0f} {row['multi_millionaire_pct']:<12.1f}%")

    # Wealth distribution across scenarios
    print("\n\n--- WEALTH DISTRIBUTION COMPARISON ---")
    print(f"\n{'Scenario':<40} {'Median':<15} {'90th %ile':<15} {'Max':<15}")
    print("-" * 90)
    for idx, row in df.sort_values('median_final_nw', ascending=False).head(10).iterrows():
        print(f"{row['scenario']:<40} ${row['median_final_nw']:<14,.0f} "
              f"${row['p90_final_nw']:<14,.0f} ${row['max_final_nw']:<14,.0f}")

    # Probability of each wealth tier
    print("\n\n--- PROBABILITY OF REACHING EACH WEALTH TIER ---")
    print(f"\n{'Scenario':<40} {'$1M+':<10} {'$10M+':<10} {'$100M+':<10} {'$1B+':<10}")
    print("-" * 90)
    for idx, row in df.sort_values('ultra_wealthy_pct', ascending=False).head(10).iterrows():
        print(f"{row['scenario']:<40} {row['millionaire_pct']:<10.1f}% "
              f"{row['multi_millionaire_pct']:<10.1f}% "
              f"{row['ultra_wealthy_pct']:<10.1f}% "
              f"{row['billionaire_pct']:<10.1f}%")

    # Recommendations
    print("\n\n--- RECOMMENDATIONS ---")

    best_overall = df[df['survival_rate'] > 95].sort_values('mean_final_nw', ascending=False).iloc[0]
    print(f"\nBest Overall Path (High Survival + Maximum Wealth):")
    print(f"  Scenario: {best_overall['scenario']}")
    print(f"  Windfall: ${best_overall['windfall_amount']:,.0f} in {best_overall['windfall_years']} years")
    print(f"  Survival Rate: {best_overall['survival_rate']:.1f}%")
    print(f"  Mean Final NW: ${best_overall['mean_final_nw']:,.0f}")
    print(f"  Median Final NW: ${best_overall['median_final_nw']:,.0f}")
    print(f"  Chance of $10M+: {best_overall['multi_millionaire_pct']:.1f}%")
    print(f"  Chance of $100M+: {best_overall['ultra_wealthy_pct']:.1f}%")

    if df['ultra_wealthy_pct'].max() > 0:
        best_billionaire = df.sort_values('ultra_wealthy_pct', ascending=False).iloc[0]
        print(f"\nBest Path to $100M+ (Highest Probability):")
        print(f"  Scenario: {best_billionaire['scenario']}")
        print(f"  Windfall: ${best_billionaire['windfall_amount']:,.0f} in {best_billionaire['windfall_years']} years")
        print(f"  Chance of $100M+: {best_billionaire['ultra_wealthy_pct']:.1f}%")
        print(f"  Survival Rate: {best_billionaire['survival_rate']:.1f}%")
        print(f"  Mean Final NW: ${best_billionaire['mean_final_nw']:,.0f}")

    # Save results
    df.to_csv('billionaire_optimization_results.csv', index=False)
    print(f"\n\nDetailed results saved to: billionaire_optimization_results.csv")
    print("="*80)


if __name__ == "__main__":
    main()
