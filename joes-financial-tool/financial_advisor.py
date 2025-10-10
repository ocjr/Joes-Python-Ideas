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


def recommend_primary_cards(
    optimizer: FinancialOptimizer, top_n: int = 5
) -> list[dict[str, Any]]:
    """
    Recommend top N credit cards to use as primary for daily purchases.

    Analyzes credit cards based on available credit, APR, and credit limit to
    determine the best cards for maximizing available credit while minimizing
    interest costs.

    Parameters
    ----------
    optimizer : FinancialOptimizer
        Configured optimizer with current financial state
    top_n : int, optional
        Number of top recommendations to return (default: 5)

    Returns
    -------
    list[dict[str, Any]]
        List of card recommendations, each containing:
        - card_id (str): ID of the card
        - card_name (str): Name of the card
        - score (float): Overall score (lower is better)
        - available_credit (float): Available credit on card
        - utilization (float): Current utilization percentage
        - apr (float): Annual percentage rate
        - reason (str): Brief explanation of strengths

    Notes
    -----
    Recommendation criteria (weighted):
    1. Utilization (50%) - Lower is better for credit score and flexibility
    2. APR (30%) - Lower minimizes interest if balance carried
    3. Credit limit (20%) - Higher provides more flexibility
    """
    cards_with_credit = [
        cc for cc in optimizer.config.credit_cards if cc.available_credit > 0
    ]

    if not cards_with_credit:
        return []

    # Score each card (lower is better)
    scored_cards = []
    max_limit = max(c.credit_limit for c in cards_with_credit)

    for cc in cards_with_credit:
        # Utilization score (0-100, lower is better)
        util_score = cc.utilization

        # APR score (0-100, normalized to percentage)
        apr_score = cc.apr * 100

        # Credit limit score (inverted - higher limit is better)
        limit_score = 100 * (1 - (cc.credit_limit / max_limit))

        # Weighted score: utilization (50%), APR (30%), limit (20%)
        total_score = (util_score * 0.5) + (apr_score * 0.3) + (limit_score * 0.2)

        # Build recommendation reason
        reasons = []
        if cc.utilization < 30:
            reasons.append(f"{cc.utilization:.1f}% util")
        if cc.apr < 0.15:
            reasons.append(f"{cc.apr * 100:.1f}% APR")
        if cc.available_credit > 1000:
            reasons.append(f"${cc.available_credit:,.0f} avail")

        reason = ", ".join(reasons) if reasons else "Has available credit"

        scored_cards.append(
            {
                "card_id": cc.id,
                "card_name": cc.name,
                "score": total_score,
                "available_credit": cc.available_credit,
                "utilization": cc.utilization,
                "apr": cc.apr,
                "credit_limit": cc.credit_limit,
                "reason": reason,
            }
        )

    # Sort by score (lowest first) and return top N
    scored_cards.sort(key=lambda x: x["score"])
    return scored_cards[:top_n]


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

        top_cards = recommend_primary_cards(optimizer, top_n=5)

        if not top_cards:
            print("❌ No cards have available credit\n")
        else:
            print("Top recommended cards for daily purchases:\n")
            print(
                "Rank | Card Name           | Available  | Utilization | APR    | Strengths"
            )
            print("-" * 85)

            for i, card in enumerate(top_cards, 1):
                rank_indicator = "⭐" if i == 1 else f"{i}."
                card_name = card["card_name"][:19].ljust(19)
                avail = f"${card['available_credit']:>8,.0f}"
                util = f"{card['utilization']:>5.1f}%"
                apr = f"{card['apr'] * 100:>5.1f}%"
                reason = card["reason"][:30]

                print(
                    f"{rank_indicator:^4} | {card_name} | {avail} | {util} | {apr} | {reason}"
                )

            print()
            print("💡 Criteria: Utilization (50%), APR (30%), Credit Limit (20%)")
            print()

            # Ask if user wants to set primary card
            set_primary = get_input(
                "Set one as your primary card? (y/n)", default="n", input_type=bool
            )

            if set_primary:
                while True:
                    try:
                        selection = input(
                            f"\nSelect card (1-{len(top_cards)}, 0 to cancel): "
                        ).strip()
                        if not selection.isdigit():
                            print("⚠️  Please enter a number")
                            continue

                        selection_num = int(selection)
                        if selection_num == 0:
                            break
                        if 1 <= selection_num <= len(top_cards):
                            selected_card = top_cards[selection_num - 1]

                            # Update config - mark all as not primary first
                            for cc in optimizer.config.credit_cards:
                                cc.primary_for_purchases = False

                            # Mark selected as primary
                            for cc in optimizer.config.credit_cards:
                                if cc.id == selected_card["card_id"]:
                                    cc.primary_for_purchases = True
                                    break

                            # Save config
                            from config_loader import save_config

                            # Need to get config path - use default
                            save_config(optimizer.config, "financial_config.json")

                            print(
                                f"\n✓ Set {selected_card['card_name']} as primary card for purchases"
                            )
                            print(
                                "   This card will be prioritized in recommendations.\n"
                            )
                            break

                        print(
                            f"⚠️  Please enter a number between 0 and {len(top_cards)}"
                        )
                    except (KeyboardInterrupt, EOFError):
                        print("\n")
                        break

    elif choice == "0":
        print()
    else:
        print("❌ Invalid choice\n")
