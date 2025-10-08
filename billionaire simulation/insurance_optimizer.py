"""
Insurance Optimization - Find Profitable Insurance Parameters

This file varies insurance parameters to find configurations that are:
1. Profitable for the insurance company (loss ratio < 70%)
2. Actually useful for customers (reduces bankruptcy risk)
3. Priced reasonably (premiums not excessive)

We'll test combinations of:
- Annual premium ($500 - $5000)
- Monthly deductible ($500 - $5000)
- Lifetime payout cap ($100k - $1M)
- Cash buffer requirements (0 - 12 months)
"""

import numpy as np
import pandas as pd
from wealth_simulation import WealthSimulator, WealthConfig

# Base scenario: No life events, just see if insurance helps with market volatility
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
    'cash_return_rate': 0.02,
    'target_buffer_months': 3,
    'spy_mean_return': 0.10,
    'spy_volatility': 0.18,
    'debt_interest_rate': 0.05,
    'debt_bankruptcy_threshold': 100000,
    'insurance_stop_net_worth': 5000000,
    'insurance_settlement_age': 70,
    'life_events': [],
    'random_seed': 42,
}

# Insurance parameter grid to test
PREMIUM_OPTIONS = [500, 1000, 2000, 3000, 5000]
DEDUCTIBLE_OPTIONS = [500, 1000, 2000, 5000]
LIFETIME_CAP_OPTIONS = [100000, 250000, 500000, 1000000]
BUFFER_MONTHS_OPTIONS = [0, 1, 3, 6, 12]

NUM_SIMULATIONS = 500


def test_insurance_config(premium, deductible, lifetime_cap, buffer_months, num_sims=100):
    """Test a specific insurance configuration."""
    config_dict = BASE_CONFIG.copy()
    config_dict['enable_insurance'] = True
    config_dict['insurance_annual_premium'] = premium
    config_dict['insurance_base_deductible'] = deductible
    config_dict['insurance_lifetime_cap'] = lifetime_cap
    config_dict['initial_cash_buffer'] = config_dict['monthly_living_expenses'] * buffer_months

    config = WealthConfig(**config_dict)
    simulator = WealthSimulator(config)
    results = simulator.run_simulations(num_sims)

    # Extract metrics
    survived = sum(1 for r in results if r['success'])
    bankruptcies = sum(1 for r in results if r['bankruptcy'])

    premiums = [r['insurance_premiums'] for r in results]
    payouts = [r['insurance_payouts'] for r in results]
    claims_list = [r['insurance_claims'] for r in results]
    settlements = [r['insurance_settlement'] for r in results]

    # Insurance company profit
    insurance_profits = [(p + s - payout) for p, payout, s in zip(premiums, payouts, settlements)]

    # Customer benefit (positive = good for customer)
    customer_benefits = [(payout - p - s) for payout, p, s in zip(payouts, premiums, settlements)]

    # Loss ratio
    total_premiums = sum(premiums) + sum(settlements)
    total_payouts = sum(payouts)
    loss_ratio = (total_payouts / total_premiums * 100) if total_premiums > 0 else 0

    return {
        'premium': premium,
        'deductible': deductible,
        'lifetime_cap': lifetime_cap,
        'buffer_months': buffer_months,

        # Customer outcomes
        'survival_rate': survived / num_sims * 100,
        'bankruptcy_rate': bankruptcies / num_sims * 100,

        # Insurance metrics
        'mean_premiums': np.mean(premiums),
        'mean_payouts': np.mean(payouts),
        'mean_claims': np.mean(claims_list),
        'policies_with_claims_pct': sum(1 for c in claims_list if c > 0) / len(claims_list) * 100,

        # Profitability
        'mean_insurance_profit': np.mean(insurance_profits),
        'median_insurance_profit': np.median(insurance_profits),
        'profitable_policies_pct': sum(1 for p in insurance_profits if p > 0) / len(insurance_profits) * 100,
        'loss_ratio': loss_ratio,

        # Customer value
        'mean_customer_benefit': np.mean(customer_benefits),
        'customers_with_benefit_pct': sum(1 for b in customer_benefits if b > 0) / len(customer_benefits) * 100,
    }


def run_baseline_no_insurance(num_sims=500):
    """Run baseline with no insurance to compare."""
    print("\n" + "="*80)
    print("BASELINE: NO INSURANCE")
    print("="*80)

    config_dict = BASE_CONFIG.copy()
    config_dict['enable_insurance'] = False
    config_dict['initial_cash_buffer'] = config_dict['monthly_living_expenses'] * 3  # 3 months

    config = WealthConfig(**config_dict)
    simulator = WealthSimulator(config)
    results = simulator.run_simulations(num_sims)

    survived = sum(1 for r in results if r['success'])
    bankruptcies = sum(1 for r in results if r['bankruptcy'])

    print(f"\nResults:")
    print(f"  Survival Rate: {survived/num_sims*100:.1f}%")
    print(f"  Bankruptcy Rate: {bankruptcies/num_sims*100:.1f}%")
    print("\n" + "="*80)

    return survived / num_sims * 100


def main():
    """Run insurance optimization."""
    print("="*80)
    print("INSURANCE PARAMETER OPTIMIZATION")
    print("="*80)
    print(f"\nTesting configurations:")
    print(f"  Premiums: {PREMIUM_OPTIONS}")
    print(f"  Deductibles: {DEDUCTIBLE_OPTIONS}")
    print(f"  Lifetime Caps: {[f'${c:,}' for c in LIFETIME_CAP_OPTIONS]}")
    print(f"  Buffer Sizes: {BUFFER_MONTHS_OPTIONS} months")
    print(f"  Simulations per config: {NUM_SIMULATIONS}")

    total_configs = len(PREMIUM_OPTIONS) * len(DEDUCTIBLE_OPTIONS) * len(LIFETIME_CAP_OPTIONS) * len(BUFFER_MONTHS_OPTIONS)
    print(f"\nTotal configurations to test: {total_configs}")
    print("="*80)

    # Run baseline
    baseline_survival = run_baseline_no_insurance(NUM_SIMULATIONS)

    # Test all combinations
    results = []
    completed = 0

    for premium in PREMIUM_OPTIONS:
        for deductible in DEDUCTIBLE_OPTIONS:
            for lifetime_cap in LIFETIME_CAP_OPTIONS:
                for buffer_months in BUFFER_MONTHS_OPTIONS:
                    completed += 1
                    print(f"\n[{completed}/{total_configs}] Testing: Premium=${premium}, Deductible=${deductible}, Cap=${lifetime_cap:,}, Buffer={buffer_months}mo")

                    result = test_insurance_config(premium, deductible, lifetime_cap, buffer_months, NUM_SIMULATIONS)
                    results.append(result)

                    print(f"  → Survival: {result['survival_rate']:.1f}%, Loss Ratio: {result['loss_ratio']:.1f}%, Claims: {result['mean_claims']:.1f}")

    # Analysis
    print("\n\n" + "="*80)
    print("OPTIMIZATION RESULTS")
    print("="*80)

    df = pd.DataFrame(results)

    # Find profitable configurations
    print("\n--- PROFITABLE CONFIGURATIONS (Loss Ratio < 70%) ---")
    profitable = df[df['loss_ratio'] < 70].sort_values('mean_insurance_profit', ascending=False)

    if len(profitable) > 0:
        print(f"\nTop 10 Most Profitable:")
        print(f"\n{'Premium':<10} {'Deduct':<10} {'Cap':<12} {'Buffer':<8} {'Loss%':<8} {'Profit':<12} {'Survival%':<12}")
        print("-" * 90)

        for idx, row in profitable.head(10).iterrows():
            print(f"${row['premium']:<9,.0f} ${row['deductible']:<9,.0f} ${row['lifetime_cap']:<11,.0f} "
                  f"{row['buffer_months']:<8.0f} {row['loss_ratio']:<8.1f} "
                  f"${row['mean_insurance_profit']:<11,.0f} {row['survival_rate']:<12.1f}%")
    else:
        print("\n  No profitable configurations found!")
        print(f"\n  Best case (lowest loss ratio):")
        best = df.loc[df['loss_ratio'].idxmin()]
        print(f"    Premium: ${best['premium']:,.0f}")
        print(f"    Deductible: ${best['deductible']:,.0f}")
        print(f"    Lifetime Cap: ${best['lifetime_cap']:,.0f}")
        print(f"    Buffer: {best['buffer_months']} months")
        print(f"    Loss Ratio: {best['loss_ratio']:.1f}%")
        print(f"    Mean Profit: ${best['mean_insurance_profit']:,.0f}")

    # Find configurations that improve survival vs baseline
    print("\n\n--- CONFIGURATIONS THAT IMPROVE CUSTOMER SURVIVAL ---")
    print(f"\nBaseline (no insurance): {baseline_survival:.1f}%")

    improved = df[df['survival_rate'] > baseline_survival].sort_values('survival_rate', ascending=False)

    if len(improved) > 0:
        print(f"\nTop 10 Survival Improvers:")
        print(f"\n{'Premium':<10} {'Deduct':<10} {'Cap':<12} {'Buffer':<8} {'Survival%':<12} {'vs Baseline':<12} {'Loss%':<8}")
        print("-" * 90)

        for idx, row in improved.head(10).iterrows():
            improvement = row['survival_rate'] - baseline_survival
            print(f"${row['premium']:<9,.0f} ${row['deductible']:<9,.0f} ${row['lifetime_cap']:<11,.0f} "
                  f"{row['buffer_months']:<8.0f} {row['survival_rate']:<12.1f}% "
                  f"+{improvement:<11.1f}% {row['loss_ratio']:<8.1f}%")
    else:
        print("\n  No configurations improve survival over baseline!")

    # Sweet spot: profitable AND improves survival
    print("\n\n--- SWEET SPOT: PROFITABLE + IMPROVES SURVIVAL ---")
    sweet_spot = df[(df['loss_ratio'] < 70) & (df['survival_rate'] > baseline_survival)].sort_values('loss_ratio')

    if len(sweet_spot) > 0:
        print(f"\nConfigurations that are profitable AND improve customer outcomes:")
        print(f"\n{'Premium':<10} {'Deduct':<10} {'Cap':<12} {'Buffer':<8} {'Survival%':<12} {'Loss%':<8} {'Profit':<12}")
        print("-" * 90)

        for idx, row in sweet_spot.head(10).iterrows():
            print(f"${row['premium']:<9,.0f} ${row['deductible']:<9,.0f} ${row['lifetime_cap']:<11,.0f} "
                  f"{row['buffer_months']:<8.0f} {row['survival_rate']:<12.1f}% "
                  f"{row['loss_ratio']:<8.1f}% ${row['mean_insurance_profit']:<11,.0f}")
    else:
        print("\n  No sweet spot found - insurance either unprofitable OR doesn't help customers")

        # Check if ANY are close
        close = df[(df['loss_ratio'] < 100) & (df['survival_rate'] > baseline_survival * 0.95)]
        if len(close) > 0:
            print(f"\n  Close configurations (loss ratio < 100%, survival within 5% of baseline):")
            best_close = close.sort_values('loss_ratio').head(3)
            for idx, row in best_close.iterrows():
                print(f"\n    Premium: ${row['premium']:,.0f}, Deductible: ${row['deductible']:,.0f}, "
                      f"Cap: ${row['lifetime_cap']:,}, Buffer: {row['buffer_months']} months")
                print(f"    Survival: {row['survival_rate']:.1f}%, Loss Ratio: {row['loss_ratio']:.1f}%, "
                      f"Profit: ${row['mean_insurance_profit']:,.0f}")

    # Save results
    df.to_csv('insurance_optimization_results.csv', index=False)
    print(f"\n\nDetailed results saved to: insurance_optimization_results.csv")
    print("="*80)


if __name__ == "__main__":
    main()
