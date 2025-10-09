#!/usr/bin/env python3
"""
Financial advice and decision support utilities.
"""

from datetime import date, timedelta
from optimizer import FinancialOptimizer
from setup_wizard import print_header, get_input, get_choice


def can_afford_purchase(optimizer: FinancialOptimizer, amount: float, days_out: int = 0) -> dict:
    """
    Check if a purchase is affordable without compromising financial safety.

    Returns:
        dict with keys: affordable (bool), reason (str), impact (str)
    """
    # Get cash flow timeline
    timeline = optimizer.build_cash_flow_timeline(days_ahead=30)

    # Current available
    current_available = sum(acc.balance - acc.minimum_balance for acc in optimizer.config.accounts)
    min_balance_required = sum(acc.minimum_balance for acc in optimizer.config.accounts)

    purchase_date = optimizer.today + timedelta(days=days_out)

    # Check if we even have the money right now
    if amount > current_available:
        return {
            'affordable': False,
            'reason': f'Insufficient funds. You have ${current_available:.2f} available but need ${amount:.2f}.',
            'impact': f'Short by ${amount - current_available:.2f}'
        }

    # Simulate the purchase by reducing balance
    simulated_balance = current_available - amount

    # Check if we'd go below minimum
    if simulated_balance < 0:
        return {
            'affordable': False,
            'reason': f'This would put you below minimum balance requirements.',
            'impact': f'Would be ${abs(simulated_balance):.2f} below minimums'
        }

    # Check cash flow for next 30 days after purchase
    min_future_balance = float('inf')
    critical_date = None

    for day_date, day_data in timeline.items():
        if day_date >= purchase_date:
            # Adjust for the purchase
            adjusted_balance = day_data.ending_balance - amount
            if adjusted_balance < min_future_balance:
                min_future_balance = adjusted_balance
                critical_date = day_date

    # Check if we'd go below minimum at any point
    buffer = 100  # $100 safety buffer
    if min_future_balance < min_balance_required + buffer:
        return {
            'affordable': False,
            'reason': f'This would create cash flow problems on {critical_date.strftime("%b %d")}.',
            'impact': f'Would leave only ${min_future_balance:.2f} (minimum needed: ${min_balance_required + buffer:.2f})'
        }

    # It's affordable!
    cushion = min_future_balance - min_balance_required
    return {
        'affordable': True,
        'reason': f'Yes, you can afford this purchase.',
        'impact': f'After purchase, you\'ll have ${cushion:.2f} cushion above minimums. Lowest balance will be on {critical_date.strftime("%b %d")}.'
    }


def recommend_lump_sum_payment(optimizer: FinancialOptimizer, amount: float) -> list:
    """
    Recommend how to allocate a lump sum payment across debts.

    Returns:
        List of dicts with keys: target (str), amount (float), reason (str)
    """
    recommendations = []
    remaining = amount

    # First check if we should build emergency fund
    emergency_fund = optimizer.calculate_emergency_fund()
    emergency_target = optimizer.config.settings.emergency_fund_target

    if emergency_fund < emergency_target:
        shortage = emergency_target - emergency_fund
        emergency_allocation = min(remaining, shortage)
        recommendations.append({
            'target': 'Emergency Fund',
            'amount': emergency_allocation,
            'reason': f'Build emergency fund to target (currently ${emergency_fund:.2f} / ${emergency_target:.2f})'
        })
        remaining -= emergency_allocation

    if remaining <= 0:
        return recommendations

    # Now allocate to credit cards based on strategy
    strategy = optimizer.config.settings.priority
    priority_cards = optimizer.prioritize_credit_cards()

    for cc in priority_cards:
        if remaining <= 0:
            break

        if cc.balance > 0:
            # Don't pay more than the balance
            payment = min(remaining, cc.balance)

            # Calculate interest savings
            annual_savings = payment * cc.apr
            monthly_savings = annual_savings / 12

            strategy_name = strategy.value.title()
            recommendations.append({
                'target': f'{cc.name} (Credit Card)',
                'amount': payment,
                'reason': f'{strategy_name} strategy - APR: {cc.apr*100:.1f}%, saves ${monthly_savings:.2f}/month in interest'
            })
            remaining -= payment

    # If there's still money left, suggest savings
    if remaining > 0:
        recommendations.append({
            'target': 'Additional Savings',
            'amount': remaining,
            'reason': 'No high-interest debt remaining. Build additional savings.'
        })

    return recommendations


def interactive_advice(optimizer: FinancialOptimizer):
    """Interactive financial advice menu."""
    print_header("💡 Financial Advice")

    print("What would you like advice on?\n")
    print("  1. Can I afford a purchase?")
    print("  2. How should I allocate a lump sum payment?")
    print("  0. Cancel\n")

    choice = input("Select (0-2): ").strip()

    if choice == "1":
        # Purchase affordability
        print("\n--- Purchase Affordability Check ---\n")

        try:
            amount_str = input("Purchase amount: $").strip()
            amount = float(amount_str)

            days_str = input("Days from now (0 for today): ").strip()
            days = int(days_str) if days_str else 0

            result = can_afford_purchase(optimizer, amount, days)

            print(f"\n{'✓' if result['affordable'] else '❌'} {result['reason']}")
            print(f"📊 {result['impact']}\n")

        except ValueError:
            print("❌ Invalid input\n")

    elif choice == "2":
        # Lump sum allocation
        print("\n--- Lump Sum Payment Advisor ---\n")

        try:
            amount_str = input("Amount available to pay: $").strip()
            amount = float(amount_str)

            recommendations = recommend_lump_sum_payment(optimizer, amount)

            print(f"\n💰 Recommended allocation for ${amount:,.2f}:\n")

            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec['target']}: ${rec['amount']:,.2f}")
                print(f"   → {rec['reason']}\n")

        except ValueError:
            print("❌ Invalid input\n")

    elif choice == "0":
        print()
    else:
        print("❌ Invalid choice\n")
