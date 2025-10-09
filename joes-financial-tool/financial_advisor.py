#!/usr/bin/env python3
"""
Financial advice and decision support utilities.

This module provides advisory functions to help users make informed financial
decisions about purchases and debt payments based on cash flow analysis.
"""

from datetime import date, timedelta
from typing import Any
from optimizer import FinancialOptimizer
from setup_wizard import print_header, get_input, get_choice


def can_afford_purchase(
    optimizer: FinancialOptimizer, amount: float, days_out: int = 0
) -> dict[str, Any]:
    """
    Check if a purchase is affordable without compromising financial safety.

    Simulates a purchase by analyzing current available funds and 30-day cash flow
    projections to ensure minimum balance requirements are maintained.

    Parameters
    ----------
    optimizer : FinancialOptimizer
        Configured optimizer with current financial state
    amount : float
        Purchase amount in dollars
    days_out : int, optional
        Number of days in the future for the purchase (default: 0 for today)

    Returns
    -------
    dict[str, Any]
        Dictionary with keys:
        - affordable (bool): Whether the purchase is safe
        - reason (str): Explanation of the decision
        - impact (str): Detailed impact analysis

    Examples
    --------
    >>> result = can_afford_purchase(optimizer, 500.00)
    >>> print(result['affordable'])
    True
    >>> print(result['reason'])
    Yes, you can afford this purchase.

    Notes
    -----
    The function applies a $100 safety buffer above minimum balance requirements
    to prevent unexpected overdrafts from small fluctuations.
    """
    # Get cash flow timeline
    timeline = optimizer.build_cash_flow_timeline(days_ahead=30)

    # Current available
    current_available = sum(
        acc.balance - acc.minimum_balance for acc in optimizer.config.accounts
    )
    min_balance_required = sum(acc.minimum_balance for acc in optimizer.config.accounts)

    purchase_date = optimizer.today + timedelta(days=days_out)

    # Check if we even have the money right now
    if amount > current_available:
        return {
            "affordable": False,
            "reason": f"Insufficient funds. You have ${current_available:.2f} available but need ${amount:.2f}.",
            "impact": f"Short by ${amount - current_available:.2f}",
        }

    # Simulate the purchase by reducing balance
    simulated_balance = current_available - amount

    # Check if we'd go below minimum
    if simulated_balance < 0:
        return {
            "affordable": False,
            "reason": "This would put you below minimum balance requirements.",
            "impact": f"Would be ${abs(simulated_balance):.2f} below minimums",
        }

    # Check cash flow for next 30 days after purchase
    min_future_balance = float("inf")
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
            "affordable": False,
            "reason": f'This would create cash flow problems on {critical_date.strftime("%b %d")}.',
            "impact": f"Would leave only ${min_future_balance:.2f} (minimum needed: ${min_balance_required + buffer:.2f})",
        }

    # It's affordable!
    cushion = min_future_balance - min_balance_required
    return {
        "affordable": True,
        "reason": "Yes, you can afford this purchase.",
        "impact": f"After purchase, you'll have ${cushion:.2f} cushion above minimums. Lowest balance will be on {critical_date.strftime('%b %d')}.",
    }


def recommend_lump_sum_payment(
    optimizer: FinancialOptimizer, amount: float
) -> list[dict[str, Any]]:
    """
    Recommend how to allocate a lump sum payment across debts.

    Analyzes the current financial state and debt payoff strategy to provide
    optimal allocation recommendations. Prioritizes emergency fund building
    before debt payments.

    Parameters
    ----------
    optimizer : FinancialOptimizer
        Configured optimizer with current financial state and strategy settings
    amount : float
        Lump sum amount available to allocate

    Returns
    -------
    list[dict[str, Any]]
        List of allocation recommendations, each containing:
        - target (str): Destination for funds (e.g., "Emergency Fund", card name)
        - amount (float): Amount to allocate
        - reason (str): Explanation for the allocation

    Examples
    --------
    >>> recommendations = recommend_lump_sum_payment(optimizer, 1000.00)
    >>> for rec in recommendations:
    ...     print(f"{rec['target']}: ${rec['amount']:.2f}")
    Emergency Fund: $500.00
    High APR Card (Credit Card): $500.00

    Notes
    -----
    Allocation priority:
    1. Emergency fund up to target amount
    2. Credit cards based on selected strategy (Avalanche/Snowball/Balanced)
    3. Additional savings if no debts remain
    """
    recommendations: list[dict[str, Any]] = []
    remaining = amount

    # First check if we should build emergency fund
    emergency_fund = optimizer.calculate_emergency_fund()
    emergency_target = optimizer.config.settings.emergency_fund_target

    if emergency_fund < emergency_target:
        shortage = emergency_target - emergency_fund
        emergency_allocation = min(remaining, shortage)
        recommendations.append(
            {
                "target": "Emergency Fund",
                "amount": emergency_allocation,
                "reason": f"Build emergency fund to target (currently ${emergency_fund:.2f} / ${emergency_target:.2f})",
            }
        )
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
            recommendations.append(
                {
                    "target": f"{cc.name} (Credit Card)",
                    "amount": payment,
                    "reason": f"{strategy_name} strategy - APR: {cc.apr*100:.1f}%, saves ${monthly_savings:.2f}/month in interest",
                }
            )
            remaining -= payment

    # If there's still money left, suggest savings
    if remaining > 0:
        recommendations.append(
            {
                "target": "Additional Savings",
                "amount": remaining,
                "reason": "No high-interest debt remaining. Build additional savings.",
            }
        )

    return recommendations


def recommend_primary_card(optimizer: FinancialOptimizer) -> dict[str, Any]:
    """
    Recommend which credit card to use as primary for daily purchases.

    Analyzes credit cards based on available credit, APR, and rewards to
    determine the best card for maximizing available credit while minimizing
    interest costs.

    Parameters
    ----------
    optimizer : FinancialOptimizer
        Configured optimizer with current financial state

    Returns
    -------
    dict[str, Any]
        Dictionary with keys:
        - recommended_card_id (str): ID of the recommended card
        - card_name (str): Name of the recommended card
        - reason (str): Explanation for the recommendation
        - available_credit (float): Available credit on recommended card
        - utilization (float): Current utilization percentage

    Notes
    -----
    Recommendation criteria (in priority order):
    1. Cards with lowest utilization (maximize available credit)
    2. Cards with lowest APR (minimize interest if balance carried)
    3. Cards with highest credit limit (more flexibility)
    """
    cards_with_credit = [
        cc for cc in optimizer.config.credit_cards if cc.available_credit > 0
    ]

    if not cards_with_credit:
        return {
            "recommended_card_id": None,
            "card_name": None,
            "reason": "No cards have available credit",
            "available_credit": 0,
            "utilization": 100,
        }

    # Score each card (lower is better)
    # Priority: Low utilization > Low APR > High credit limit
    scored_cards = []
    for cc in cards_with_credit:
        # Utilization score (0-100, lower is better)
        util_score = cc.utilization

        # APR score (0-100, normalized to percentage)
        apr_score = cc.apr * 100

        # Credit limit score (inverted - higher limit is better)
        # Normalize to 0-100 scale
        max_limit = max(c.credit_limit for c in cards_with_credit)
        limit_score = 100 * (1 - (cc.credit_limit / max_limit))

        # Weighted score: utilization (50%), APR (30%), limit (20%)
        total_score = (util_score * 0.5) + (apr_score * 0.3) + (limit_score * 0.2)

        scored_cards.append((total_score, cc))

    # Sort by score (lowest first)
    scored_cards.sort(key=lambda x: x[0])
    best_card = scored_cards[0][1]

    # Build recommendation reason
    reasons = []
    if best_card.utilization < 30:
        reasons.append(f"low utilization ({best_card.utilization:.1f}%)")
    if best_card.apr < 0.15:
        reasons.append(f"low APR ({best_card.apr * 100:.1f}%)")
    if best_card.available_credit > 1000:
        reasons.append(f"high available credit (${best_card.available_credit:,.2f})")

    reason = (
        "Best card for purchases: " + ", ".join(reasons)
        if reasons
        else "Has available credit"
    )

    return {
        "recommended_card_id": best_card.id,
        "card_name": best_card.name,
        "reason": reason,
        "available_credit": best_card.available_credit,
        "utilization": best_card.utilization,
    }


def interactive_advice(optimizer: FinancialOptimizer) -> None:
    """
    Interactive financial advice menu.

    Presents a menu of advisory options and handles user interaction for
    purchase affordability checks and lump sum payment recommendations.

    Parameters
    ----------
    optimizer : FinancialOptimizer
        Configured optimizer with current financial state

    Notes
    -----
    Available advice options:
    1. Can I afford a purchase? - Checks if a specific purchase is safe
    2. How should I allocate a lump sum? - Provides debt payoff recommendations
    3. Which card should I use for purchases? - Recommends primary card

    The function handles all user input and displays results in a formatted manner.
    """
    print_header("💡 Financial Advice")

    print("What would you like advice on?\n")
    print("  1. Can I afford a purchase?")
    print("  2. How should I allocate a lump sum payment?")
    print("  3. Which credit card should I use for daily purchases?")
    print("  0. Cancel\n")

    choice = input("Select (0-3): ").strip()

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

    elif choice == "3":
        # Primary card recommendation
        print("\n--- Primary Card Recommendation ---\n")

        result = recommend_primary_card(optimizer)

        if result["recommended_card_id"]:
            print(f"✓ Recommended: {result['card_name']}\n")
            print(f"📊 {result['reason']}")
            print(f"   Available Credit: ${result['available_credit']:,.2f}")
            print(f"   Current Utilization: {result['utilization']:.1f}%\n")
            print("💡 This card will maximize your available credit while")
            print("   minimizing potential interest charges.\n")
        else:
            print(f"❌ {result['reason']}\n")

    elif choice == "0":
        print()
    else:
        print("❌ Invalid choice\n")
