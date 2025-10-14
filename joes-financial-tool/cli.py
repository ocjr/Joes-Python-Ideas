#!/usr/bin/env python3
"""
Command-line interface for the Financial Optimization Tool.
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import date, timedelta
from config_loader import load_config, save_config
from optimizer import FinancialOptimizer
from setup_wizard import (
    run_setup_wizard,
    add_account_to_config,
    add_income_to_config,
    add_bill_to_config,
    add_credit_card_to_config,
    add_manual_payment_to_config,
    add_recurring_expense_to_config,
    add_investment_account_to_config,
)
from edit_wizard import edit_account, edit_income, edit_bill, edit_credit_card
from bill_tracker import mark_bill_paid
from financial_advisor import interactive_advice
from investment_manager import (
    add_manual_position,
    record_stock_transaction,
    refresh_stock_prices,
    view_investment_portfolio,
)
from simulation_engine import SimulationEngine
from simulation_reports import print_simulation_summary, print_sample_run, print_actionable_instructions
from simulation_wizard import add_simulation_to_config, edit_simulation
from etf_library import view_etf_library, add_etf_interactive, search_etf_interactive
from config_manager import (
    get_dated_config_name,
    select_config_interactive,
    list_config_files,
    get_most_recent_config,
)


def clear_screen():
    """Clear the terminal screen."""
    os.system("clear" if os.name == "posix" else "cls")


def combine_payments_for_display(transactions, credit_cards):
    """
    Combine multiple payments to the same credit card for display purposes.

    Banks typically prefer a single payment per day. This combines payments
    at the display level so users see a single combined payment.
    """
    from simulator import PlannedTransaction, PaymentDecision, PaymentMethod

    payment_categories = ["cc_payment", "manual_cc_payment", "cc_extra_payment"]
    combined = []
    skip_indices = set()

    for i, (txn, decision) in enumerate(transactions):
        if i in skip_indices:
            continue

        # Only combine payment transactions
        if txn.category not in payment_categories:
            combined.append((txn, decision))
            continue

        # Extract card ID from description
        card_id = None
        if "(" in txn.description and ")" in txn.description:
            start = txn.description.rfind("(")
            end = txn.description.rfind(")")
            if start != -1 and end != -1:
                card_id = txn.description[start + 1 : end]

        if not card_id:
            combined.append((txn, decision))
            continue

        # Find all other payments to this card on the same day
        same_card_payments = [(txn, decision)]
        for j, (other_txn, other_decision) in enumerate(transactions):
            if j <= i or j in skip_indices:
                continue

            if other_txn.category in payment_categories:
                # Check if same card
                other_card_id = None
                if "(" in other_txn.description and ")" in other_txn.description:
                    start = other_txn.description.rfind("(")
                    end = other_txn.description.rfind(")")
                    if start != -1 and end != -1:
                        other_card_id = other_txn.description[start + 1 : end]

                if other_card_id == card_id:
                    same_card_payments.append((other_txn, other_decision))
                    skip_indices.add(j)

        # If multiple payments found, combine them
        if len(same_card_payments) > 1:
            total_amount = sum(abs(t.amount) for t, d in same_card_payments)
            # Get card name
            cc = next((c for c in credit_cards if c.id == card_id), None)
            card_name = cc.name if cc else card_id

            # Create combined payment
            combined_txn = PlannedTransaction(
                date=txn.date,
                description=f"Combined Payment: {card_name} ({len(same_card_payments)} payments)",
                amount=-total_amount,
                category="cc_payment",
                required=True,
                preferred_account=txn.preferred_account,
                can_use_credit=False,
            )

            # Use the decision from the first payment
            combined.append((combined_txn, decision))
        else:
            combined.append((txn, decision))

    return combined


def print_header(title: str):
    """Print a formatted header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def print_menu(current_config: str = "financial_config.json"):
    """Print the main menu."""
    clear_screen()
    print_header("💰 Financial Optimization Tool")
    print(f"Current config: {current_config}\n")
    print("Main Menu:\n")
    print("  VIEW:")
    print("    1. 📋 Today's Actions")
    print("    2. 🎯 Optimal Simulation (custom days)")
    print("    3. 📊 Financial Summary")
    print("    4. 📈 14-Day Cash Flow Forecast")
    print("    5. 🏦 Account Details")
    print("    6. 📖 View All Information")
    print()
    print("  ADVICE:")
    print("    7. 💡 Financial Advice")
    print()
    print("  MANAGE:")
    print("    8. ✅ Mark Bill as Paid")
    print("    9. 🔄 Update Account Balances")
    print("   10. ➕ Add New Account")
    print("   11. ➕ Add New Income Source")
    print("   12. ➕ Add New Bill")
    print("   13. ➕ Add New Credit Card")
    print("   14. ➕ Add Manual Payment")
    print("   15. ➕ Add Recurring Expense")
    print("   16. ✏️  Edit Account")
    print("   17. ✏️  Edit Income Source")
    print("   18. ✏️  Edit Bill")
    print("   19. ✏️  Edit Credit Card")
    print()
    print("  INVESTMENTS:")
    print("   20. 📈 View Investment Portfolio")
    print("   21. ➕ Add Investment Account")
    print("   22. 📊 Add Stock Position (no date required)")
    print("   23. 📝 Record Stock Transaction (with date)")
    print("   24. 🔄 Refresh Stock Prices")
    print()
    print("  SIMULATIONS:")
    print("   27. 🎲 View Configured Simulations")
    print("   28. 🚀 Run Simulation")
    print("   29. ➕ Add Simulation Config")
    print("   30. ✏️  Edit Simulation Config")
    print()
    print("  ETF LIBRARY:")
    print("   31. 📚 View ETF Library")
    print("   32. ➕ Add ETF to Library")
    print("   33. 🔍 Search ETF Library")
    print()
    print("  SETUP:")
    print("   25. ⚙️  Run Full Setup Wizard (creates new dated config)")
    print("   26. 📂 Load Previous Config")
    print()
    print("    0. 🚪 Exit")
    print()


def get_menu_choice():
    """Get user's menu choice."""
    while True:
        try:
            choice = input("Select option (0-33): ").strip()
            if choice.isdigit() and 0 <= int(choice) <= 33:
                return int(choice)
            print("⚠️  Please enter a number between 0 and 33")
        except KeyboardInterrupt:
            print("\n")
            return 0
        except EOFError:
            return 0


def pause():
    """Pause and wait for user input."""
    input("\nPress Enter to continue...")


def print_tasks(optimizer: FinancialOptimizer, target_date: date = None):
    """Print concrete daily tasks with specific amounts for today only."""
    if target_date is None:
        target_date = date.today()

    print_header(f"Today's Actions - {target_date.strftime('%A, %B %d, %Y')}")

    # Show current cash position
    available = sum(
        acc.balance - acc.minimum_balance for acc in optimizer.config.accounts
    )
    total = sum(acc.balance for acc in optimizer.config.accounts)
    print(f"💵 Cash Position: ${total:,.2f} total | ${available:,.2f} available\n")

    # Get optimal simulation
    optimal = optimizer.get_optimal_simulation(days_ahead=30)

    if optimal.failed:
        print(
            "⚠️  Simulation shows financial constraints - see full simulation for details\n"
        )
        return

    # Find today's transactions from the simulation
    day_offset = (target_date - optimizer.today).days
    if day_offset < 0 or day_offset >= len(optimal.days):
        print("✓ No actions scheduled for this date\n")
        return

    today_sim = optimal.days[day_offset]

    if not today_sim.transactions:
        print("✓ No required actions today!\n")
    else:
        print("📋 ACTIONS FOR TODAY:\n")
        for txn, decision in today_sim.transactions:
            if txn.amount < 0:  # Expenses/payments
                amount_str = f"${abs(txn.amount):.2f}"
                method_info = ""
                if decision.method.value == "credit_card":
                    method_info = " (using credit card)"
                elif decision.method.value == "split":
                    method_info = f" (${decision.checking_amount:.2f} checking + ${decision.credit_amount:.2f} credit)"

                print(f"  • {txn.description}: {amount_str}{method_info}")

        # Show ending balance
        ending_checking = today_sim.ending_state.get_total_checking()
        print(f"\n  Ending checking balance: ${ending_checking:,.2f}")

    print()


def print_optimal_simulation(optimizer: FinancialOptimizer, days: int = 30):
    """Display the optimal financial strategy simulation."""
    print_header(f"🎯 Optimal {days}-Day Financial Strategy")

    # Get the optimal simulation
    print("⏳ Running simulations to find optimal strategy...")
    optimal = optimizer.get_optimal_simulation(days_ahead=days)

    # Display strategy selected
    print(f"\n✅ Selected Strategy: {optimal.strategy.value.upper().replace('_', ' ')}")

    # Check if simulation failed
    if optimal.failed:
        print(f"\n❌ SIMULATION FAILED - Constraint violations detected")
        print(f"   Completed {len(optimal.days)} days before failure")

        if optimal.warnings:
            print(f"\n   Violations:")
            for warning in optimal.warnings[:5]:  # Show first 5 warnings
                print(f"     - {warning}")
            if len(optimal.warnings) > 5:
                print(f"     ... and {len(optimal.warnings) - 5} more")

        # Show the state when it failed
        if optimal.days:
            last_day = optimal.days[-1]
            print(f"\n   📊 Account Balances at Failure (Day {len(optimal.days)}):")

            # Show checking accounts
            for acc in optimizer.config.accounts:
                if acc.type.value == "checking":
                    balance = last_day.ending_state.account_balances.get(acc.id, 0)
                    status = "✓" if balance >= acc.minimum_balance else "❌"
                    print(
                        f"     {status} {acc.name}: ${balance:.2f} (min ${acc.minimum_balance:.2f})"
                    )

            # Show credit cards
            for cc in optimizer.config.credit_cards:
                balance = last_day.ending_state.credit_card_balances.get(cc.id, 0)
                status = "✓" if balance <= cc.credit_limit else "❌"
                print(
                    f"     {status} {cc.name}: ${balance:.2f} / ${cc.credit_limit:.2f} limit"
                )

            # Show what transactions were attempted on the failure day
            if last_day.transactions:
                print(
                    f"\n   📋 Transactions on Failure Day ({last_day.date.strftime('%a %m/%d')}):"
                )
                for txn, decision in last_day.transactions:
                    if txn.amount != 0:
                        amount_str = f"${abs(txn.amount):.2f}"
                        if txn.amount > 0:
                            print(f"     ✓ {txn.description}: +{amount_str}")
                        else:
                            print(f"     • {txn.description}: -{amount_str}")
                            if decision.reason:
                                print(f"       → {decision.reason}")

        print(f"\n   ⚠️  This strategy would cause accounts to go negative.")
        print(f"   Try a less aggressive approach or increase available cash.\n")
        return

    print(f"💰 Total Interest Cost: ${optimal.total_interest_paid:.2f}")
    print(f"📉 Total Debt Reduction: ${optimal.get_total_debt_reduction():.2f}")
    print(f"\n✅ All constraints satisfied - no accounts go below minimums")

    # Show final state
    print(f"\n📊 Final State (Day {days}):")
    print(f"   Total Checking: ${optimal.final_state.get_total_checking():.2f}")
    print(f"   Total Savings:  ${optimal.final_state.get_total_savings():.2f}")
    print(f"   Total Debt:     ${optimal.final_state.get_total_debt():.2f}")

    # Show key transactions for the requested number of days
    days_to_show = min(days, len(optimal.days))
    print(f"\n📋 Day-by-Day Transactions (next {days_to_show} days):")
    for day in optimal.days[:days_to_show]:
        print(f"\n   {day.date.strftime('%a %m/%d')}:")

        # Show balances at start of day - individual checking accounts
        checking_accounts = [
            acc for acc in optimizer.config.accounts if acc.type.value == "checking"
        ]
        debt_balance = day.starting_state.get_total_debt()

        if len(checking_accounts) > 1:
            # Multiple checking accounts - show each individually
            checking_parts = []
            for acc in checking_accounts:
                balance = day.starting_state.account_balances.get(acc.id, 0)
                checking_parts.append(f"{acc.name} ${balance:,.2f}")
            checking_str = ", ".join(checking_parts)
            print(f"      Starting: {checking_str} | Debt ${debt_balance:,.2f}")
        else:
            # Single checking account - show total
            checking_balance = day.starting_state.get_total_checking()
            print(
                f"      Starting: Checking ${checking_balance:,.2f} | Debt ${debt_balance:,.2f}"
            )

        if not day.transactions or all(txn.amount == 0 for txn, _ in day.transactions):
            print(f"      (no transactions)")
        else:
            # Combine payments to same card on same day for display
            combined_transactions = combine_payments_for_display(
                day.transactions, optimizer.config.credit_cards
            )

            for txn, decision in combined_transactions:
                if txn.amount != 0:
                    amount_str = f"${abs(txn.amount):.2f}"
                    if txn.amount > 0:
                        print(f"      ✓ {txn.description}: +{amount_str}")
                    else:
                        method_str = ""
                        if decision.method.value == "checking":
                            # Find the account name
                            account_name = "Checking"
                            if decision.checking_account_id:
                                acc = next(
                                    (
                                        a
                                        for a in optimizer.config.accounts
                                        if a.id == decision.checking_account_id
                                    ),
                                    None,
                                )
                                if acc:
                                    account_name = acc.name
                            method_str = f" [from {account_name}]"
                        elif decision.method.value == "credit_card":
                            # Find the card name
                            card_name = "Credit"
                            if decision.credit_card_id:
                                cc = next(
                                    (
                                        c
                                        for c in optimizer.config.credit_cards
                                        if c.id == decision.credit_card_id
                                    ),
                                    None,
                                )
                                if cc:
                                    card_name = cc.name
                            method_str = f" [using {card_name}]"
                        elif decision.method.value == "split":
                            # Show both accounts
                            checking_name = "Checking"
                            if decision.checking_account_id:
                                acc = next(
                                    (
                                        a
                                        for a in optimizer.config.accounts
                                        if a.id == decision.checking_account_id
                                    ),
                                    None,
                                )
                                if acc:
                                    checking_name = acc.name
                            card_name = "Credit"
                            if decision.credit_card_id:
                                cc = next(
                                    (
                                        c
                                        for c in optimizer.config.credit_cards
                                        if c.id == decision.credit_card_id
                                    ),
                                    None,
                                )
                                if cc:
                                    card_name = cc.name
                            method_str = f" [Split: ${decision.checking_amount:.0f} from {checking_name} + ${decision.credit_amount:.0f} using {card_name}]"
                        # Check if this is an extra payment with detailed reasoning
                        if (
                            "cc_extra_payment" in txn.category
                            and " - " in txn.description
                        ):
                            # Split description to show reasoning on separate line
                            main_desc, *reason_parts = txn.description.split(" - ")
                            reasoning = " - ".join(reason_parts)
                            print(f"      • {main_desc}: -{amount_str}{method_str}")
                            print(f"          └─ Why: {reasoning}")
                        else:
                            print(
                                f"      • {txn.description}: -{amount_str}{method_str}"
                            )

                        if decision.reason and "⚠️" in decision.reason:
                            print(f"        {decision.reason}")

        # Show balances at end of day - individual checking accounts
        ending_debt = day.ending_state.get_total_debt()

        if len(checking_accounts) > 1:
            # Multiple checking accounts - show each individually
            ending_parts = []
            for acc in checking_accounts:
                balance = day.ending_state.account_balances.get(acc.id, 0)
                ending_parts.append(f"{acc.name} ${balance:,.2f}")
            ending_str = ", ".join(ending_parts)
            print(f"      Ending:   {ending_str} | Debt ${ending_debt:,.2f}")
        else:
            # Single checking account - show total
            ending_checking = day.ending_state.get_total_checking()
            print(
                f"      Ending:   Checking ${ending_checking:,.2f} | Debt ${ending_debt:,.2f}"
            )

    print()


def print_upcoming_plan(optimizer: FinancialOptimizer, days: int = 5):
    """Print action plan for the next N days using simulation results."""
    print_header(f"Upcoming {days}-Day Action Plan")

    # Get optimal simulation
    optimal = optimizer.get_optimal_simulation(days_ahead=max(days, 30))

    if optimal.failed:
        print("⚠️  Simulation failed - see full simulation for details\n")
        # Show what we can from partial results
        days_available = min(days, len(optimal.days))
        if days_available == 0:
            return
        print(f"Showing {days_available} days before failure:\n")

    # Show strategy being used
    print(f"Strategy: {optimal.strategy.value.upper().replace('_', ' ')}\n")

    # Show requested number of days from simulation
    days_to_show = min(days, len(optimal.days))

    print(
        f"{'Date':<12} {'Total Checking':<15} {'Total Debt':<15} {'Key Transactions'}"
    )
    print("-" * 100)

    for day in optimal.days[:days_to_show]:
        # Get balances at end of day
        checking_total = day.ending_state.get_total_checking()
        debt_total = day.ending_state.get_total_debt()

        # Collect key transactions for this day
        key_txns = []
        for txn, decision in day.transactions:
            if txn.amount != 0:
                # Summarize transaction
                if txn.amount > 0:
                    key_txns.append(f"+${txn.amount:.0f} {txn.description}")
                else:
                    amount = abs(txn.amount)
                    # Shorten description for display
                    desc = (
                        txn.description.replace("Income: ", "")
                        .replace("Bill: ", "")
                        .replace("CC Payment: ", "CC: ")
                        .replace("CC Extra Payment: ", "CC+: ")
                        .replace("CC Preemptive Payment:", "CC!:")
                    )
                    if len(desc) > 30:
                        desc = desc[:27] + "..."
                    key_txns.append(f"-${amount:.0f} {desc}")

        # Format for display
        date_str = day.date.strftime("%a %m/%d")
        txns_str = "; ".join(key_txns[:3])  # Show up to 3 transactions
        if len(key_txns) > 3:
            txns_str += f" (+{len(key_txns)-3} more)"

        print(
            f"{date_str:<12} ${checking_total:<14,.2f} ${debt_total:<14,.2f} {txns_str}"
        )

    print()


def print_cash_flow_forecast(optimizer: FinancialOptimizer):
    """Print 14-day cash flow forecast using simulation results."""
    print_header("14-Day Cash Flow Forecast")

    # Get optimal simulation for 14 days
    optimal = optimizer.get_optimal_simulation(days_ahead=14)

    if optimal.failed and len(optimal.days) == 0:
        print("⚠️  Cannot generate forecast - simulation failed immediately\n")
        return

    min_required = sum(acc.minimum_balance for acc in optimizer.config.accounts)

    print(f"{'Date':<12} {'Starting':<12} {'Events':<8} {'Ending':<12} {'Status':<10}")
    print("-" * 70)

    # Show up to 14 days from simulation
    days_to_show = min(14, len(optimal.days))

    for day in optimal.days[:days_to_show]:
        day_str = day.date.strftime("%a %m/%d")
        starting_checking = day.starting_state.get_total_checking()
        ending_checking = day.ending_state.get_total_checking()

        # Count events (transactions with amount != 0)
        events_count = sum(1 for txn, _ in day.transactions if txn.amount != 0)
        events_str = f"{events_count} event{'s' if events_count != 1 else ''}"

        # Status indicator
        if ending_checking < min_required:
            status = "⚠️  LOW"
        elif ending_checking < min_required + 200:
            status = "⚠️  TIGHT"
        else:
            status = "✓ OK"

        print(
            f"{day_str:<12} ${starting_checking:>9,.2f} {events_str:>8} ${ending_checking:>9,.2f}  {status}"
        )

        # Show transaction details - combine payments first
        combined_txns = combine_payments_for_display(
            day.transactions, optimizer.config.credit_cards
        )
        for txn, decision in combined_txns:
            if txn.amount != 0:
                symbol = "+" if txn.amount > 0 else "-"
                # Clean up description
                desc = txn.description.replace("Income: ", "").replace("Bill: ", "")

                # For CC payments, show combined amounts
                if "cc_payment" in txn.category or "cc_extra_payment" in txn.category:
                    # Find matching transactions to combine min + extra
                    desc = desc.replace("CC Payment: ", "").replace(
                        "CC Extra Payment: ", ""
                    )
                    print(f"             └─ {symbol}${abs(txn.amount):,.2f} {desc}")
                else:
                    print(f"             └─ {symbol}${abs(txn.amount):,.2f} {desc}")

    print()


def print_summary(optimizer: FinancialOptimizer):
    """Print concise monthly financial summary."""
    print_header("Monthly Financial Summary")

    plan = optimizer.generate_monthly_action_plan()

    print(f"📅 As of: {plan['current_date'].strftime('%B %d, %Y')}\n")

    # Current total balance
    total_assets = (
        plan["checking_balance"] + plan["savings_balance"] + plan["cash_balance"]
    )
    net_worth = total_assets - plan["total_debt"]

    print("💰 BALANCE TODAY:")
    print(f"   Total Assets: ${total_assets:,.2f}")
    print(f"   Total Debt:   ${plan['total_debt']:,.2f}")
    print(f"   Net Worth:    ${net_worth:,.2f}\n")

    # Emergency fund
    status = "✓" if plan["emergency_pct"] >= 100 else "⚠️ "
    print(
        f"🏦 Emergency Fund: ${plan['emergency_fund']:,.2f} / ${plan['emergency_target']:,.2f} ({status} {plan['emergency_pct']:.0f}%)\n"
    )

    # Monthly outlook
    print("📊 MONTHLY OUTLOOK:")
    print(f"   Expected Income:   +${plan['total_income']:,.2f}")
    print(f"   Expected Outflows: -${plan['total_outflows']:,.2f}")
    net_symbol = "+" if plan["net_monthly"] >= 0 else ""
    print(f"   Net Cash Flow:     {net_symbol}${plan['net_monthly']:,.2f}\n")

    # Projected end of month
    projected_assets = total_assets + plan["net_monthly"]
    # Estimate debt reduction (from extra payments in recommendations)
    debt_reduction = sum(
        action["recommended_payment"] - action["minimum_payment"]
        for action in plan.get("cc_actions", [])
    )
    projected_debt = max(0, plan["total_debt"] - debt_reduction)
    projected_net_worth = projected_assets - projected_debt

    print("📈 PROJECTED END OF MONTH:")
    print(f"   Total Assets: ${projected_assets:,.2f}")
    print(f"   Total Debt:   ${projected_debt:,.2f}")
    print(f"   Net Worth:    ${projected_net_worth:,.2f}")

    # Show change
    change = projected_net_worth - net_worth
    change_symbol = "+" if change >= 0 else ""
    print(f"   Change:       {change_symbol}${change:,.2f}\n")


def print_accounts(optimizer: FinancialOptimizer):
    """Print account details."""
    print_header("Account Details")

    for acc in optimizer.config.accounts:
        available = max(0, acc.balance - acc.minimum_balance)
        print(f"🏦 {acc.name} ({acc.type.value.title()})")
        print(f"   Balance: ${acc.balance:,.2f}")
        if acc.minimum_balance > 0:
            print(f"   Minimum: ${acc.minimum_balance:,.2f}")
            print(f"   Available: ${available:,.2f}")
        print()


def interactive_update(config_path: str):
    """Interactive mode to update balances."""
    print_header("Update Account Balances")

    try:
        config = load_config(config_path)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        sys.exit(1)

    print("Update your current balances. Press Enter to skip an item.\n")

    # Update accounts
    print("💰 ACCOUNTS:")
    for acc in config.accounts:
        current = acc.balance
        response = input(f"  {acc.name} (current: ${current:,.2f}): $")
        if response.strip():
            try:
                acc.balance = float(response.replace(",", ""))
                print(f"    Updated to ${acc.balance:,.2f}")
            except ValueError:
                print(f"    Invalid input, keeping ${current:,.2f}")

    print("\n💳 CREDIT CARDS:")
    for cc in config.credit_cards:
        current = cc.balance
        response = input(f"  {cc.name} balance (current: ${current:,.2f}): $")
        if response.strip():
            try:
                cc.balance = float(response.replace(",", ""))
                print(f"    Updated to ${cc.balance:,.2f}")
            except ValueError:
                print(f"    Invalid input, keeping ${current:,.2f}")

        # Optionally update minimum payment
        current_min = cc.minimum_payment
        response = input(
            f"  {cc.name} minimum payment (current: ${current_min:,.2f}): $"
        )
        if response.strip():
            try:
                cc.minimum_payment = float(response.replace(",", ""))
                print(f"    Updated to ${cc.minimum_payment:,.2f}")
            except ValueError:
                print(f"    Invalid input, keeping ${current_min:,.2f}")

    # Save updated config
    print(f"\n💾 Saving changes to {config_path}...")
    try:
        save_config(config, config_path)
        print("✓ Configuration updated successfully!\n")
    except Exception as e:
        print(f"❌ Error saving config: {e}\n")
        sys.exit(1)


def view_simulations(config_path: str):
    """View configured simulations."""
    print_header("Configured Simulations")

    try:
        config = load_config(config_path)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return

    if not config.simulations:
        print("No simulations configured yet.\n")
        print("To add a simulation, edit your config file and add to the 'simulations' section.")
        return

    for i, sim in enumerate(config.simulations, 1):
        status = "✅ Enabled" if sim.enabled else "❌ Disabled"
        print(f"{i}. {sim.name} ({status})")
        print(f"   ID: {sim.id}")
        print(f"   Initial balance: ${sim.initial_balance:,.2f}")
        print(f"   Current age: {sim.current_age} → Target ages: {', '.join(map(str, sim.target_ages))}")
        print(f"   Strategy: {sim.strategy_type}")
        if sim.strategy_type == "monthly_liquidation":
            print(f"   Liquidation day: {sim.liquidation_day}")
        else:
            print(f"   Hold period: {sim.hold_days} days")

        # Show income sources with validation
        if sim.income_source_ids:
            matched_sources = [inc for inc in config.income if inc.id in sim.income_source_ids]
            unmatched_ids = [sid for sid in sim.income_source_ids if sid not in [inc.id for inc in config.income]]

            print(f"   Income sources: {len(matched_sources)} configured")
            for inc in matched_sources:
                print(f"      ✓ {inc.source} (${inc.amount:,.2f} {inc.frequency.value})")
            if unmatched_ids:
                print(f"      ⚠️  Unmatched IDs: {', '.join(unmatched_ids)}")
        else:
            print(f"   Income sources: None (only initial balance will be invested)")

        print(f"   Simulations per run: {sim.num_simulations}")
        print()


def run_simulation_interactive(config_path: str):
    """Run a simulation interactively."""
    print_header("Run Simulation")

    try:
        config = load_config(config_path)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return

    if not config.simulations:
        print("No simulations configured.\n")
        return

    # Show available simulations
    enabled_sims = [s for s in config.simulations if s.enabled]
    if not enabled_sims:
        print("No enabled simulations found.\n")
        return

    print("Available simulations:\n")
    for i, sim in enumerate(enabled_sims, 1):
        print(f"  {i}. {sim.name}")
        print(f"     Strategy: {sim.strategy_type}")
        print(f"     Target ages: {', '.join(map(str, sim.target_ages))}")
        print()

    # Get user selection
    try:
        choice = input(f"Select simulation (1-{len(enabled_sims)}, 0 to cancel): ").strip()
        if not choice or choice == "0":
            print("Cancelled.")
            return

        sim_idx = int(choice) - 1
        if sim_idx < 0 or sim_idx >= len(enabled_sims):
            print("Invalid selection.")
            return

        selected_sim = enabled_sims[sim_idx]
    except (ValueError, KeyboardInterrupt):
        print("\nCancelled.")
        return

    # Get target age
    print(f"\nAvailable target ages: {', '.join(map(str, selected_sim.target_ages))}")
    try:
        age_input = input("Select target age (or press Enter for first): ").strip()
        if not age_input:
            target_age = selected_sim.target_ages[0]
        else:
            target_age = int(age_input)
            if target_age not in selected_sim.target_ages:
                print(f"⚠️  Age {target_age} not in configured targets, using anyway...")
    except (ValueError, KeyboardInterrupt):
        print("\nCancelled.")
        return

    # Allow temporary override of simulation count
    years = target_age - selected_sim.current_age

    # Estimate time based on which engine will be used
    try:
        import simulation_engine
        rust_available = simulation_engine.RUST_AVAILABLE
    except:
        rust_available = False

    if rust_available and selected_sim.num_simulations > 10:
        # Rust: ~100,000 runs/sec
        estimated_time = (selected_sim.num_simulations * years) / 100000 * 60  # in seconds, then to minutes
        engine_note = " (Rust)"
    else:
        # Python: ~200 runs/sec
        estimated_time = (selected_sim.num_simulations * years) / 200 / 60  # in minutes
        engine_note = " (Python)"

    print(f"\nConfigured simulations: {selected_sim.num_simulations}{engine_note} (estimated ~{estimated_time:.1f} minutes)")
    override = input(f"Override count for this run? (press Enter to use {selected_sim.num_simulations}): ").strip()
    if override:
        try:
            num_runs = int(override)
            if num_runs > 0:
                selected_sim = InvestmentSimulation(
                    id=selected_sim.id,
                    name=selected_sim.name,
                    enabled=selected_sim.enabled,
                    current_age=selected_sim.current_age,
                    target_ages=selected_sim.target_ages,
                    strategy_type=selected_sim.strategy_type,
                    hold_days=selected_sim.hold_days,
                    liquidation_day=selected_sim.liquidation_day,
                    income_source_ids=selected_sim.income_source_ids,
                    ticker=selected_sim.ticker,
                    initial_balance=selected_sim.initial_balance,
                    expected_annual_return=selected_sim.expected_annual_return,
                    annual_volatility=selected_sim.annual_volatility,
                    annual_dividend_yield=selected_sim.annual_dividend_yield,
                    expense_ratio=selected_sim.expense_ratio,
                    short_term_cap_gains_rate=selected_sim.short_term_cap_gains_rate,
                    long_term_cap_gains_rate=selected_sim.long_term_cap_gains_rate,
                    dividend_tax_rate=selected_sim.dividend_tax_rate,
                    num_simulations=num_runs,
                    random_seed=selected_sim.random_seed,
                )
                print(f"  Using {num_runs} simulations for this run")
        except ValueError:
            pass

    # Validate income sources before running
    print(f"\n🔍 Validating simulation configuration...")

    if selected_sim.income_source_ids:
        matched_sources = [inc for inc in config.income if inc.id in selected_sim.income_source_ids]
        unmatched_ids = [sid for sid in selected_sim.income_source_ids if sid not in [inc.id for inc in config.income]]

        if unmatched_ids:
            print(f"\n❌ ERROR: Income source IDs not found in config!")
            print(f"   Missing IDs: {', '.join(unmatched_ids)}")
            print(f"\n   Available income IDs in config:")
            for inc in config.income:
                print(f"     - {inc.id} ({inc.source})")
            print(f"\n   Please edit the simulation config (option 30) to fix the income_source_ids.")
            return

        if not matched_sources:
            print(f"\n⚠️  WARNING: No income sources configured for this simulation!")
            print(f"   The simulation will only use the initial balance of ${selected_sim.initial_balance:,.2f}")
            proceed = input(f"   Continue anyway? (y/n): ").strip().lower()
            if proceed != 'y':
                print("Cancelled.")
                return
        else:
            print(f"✓ Found {len(matched_sources)} income source(s):")
            for inc in matched_sources:
                print(f"    - {inc.source}: ${inc.amount:,.2f} {inc.frequency.value}")
    else:
        print(f"⚠️  No income sources configured - only initial balance will be invested")
        proceed = input(f"   Continue with just ${selected_sim.initial_balance:,.2f} initial balance? (y/n): ").strip().lower()
        if proceed != 'y':
            print("Cancelled.")
            return

    if selected_sim.initial_balance == 0 and not selected_sim.income_source_ids:
        print(f"\n❌ ERROR: Both initial balance and income sources are zero!")
        print(f"   There is nothing to invest. Please edit the simulation config.")
        return

    # Run simulation
    print(f"\n🚀 Starting simulation: {selected_sim.name}")
    print(f"   Target age: {target_age}")
    print(f"   Number of runs: {selected_sim.num_simulations}")
    print(f"   Press Ctrl+C to interrupt at any time")
    print()

    try:
        engine = SimulationEngine(config, selected_sim)
        results = engine.run_monte_carlo(target_age=target_age)

        # Display results
        print_simulation_summary(results)

        # Ask if they want to see actionable instructions
        show_instructions = input("\nShow actionable buy/sell instructions? (y/n): ").strip().lower()
        if show_instructions == "y":
            print_actionable_instructions(results, max_instructions=50, config=config)

        # Ask if they want to see sample run
        show_sample = input("\nShow detailed sample run? (y/n): ").strip().lower()
        if show_sample == "y":
            print_sample_run(results.runs[0], max_events=20)

        # Ask if they want to export to CSV
        export = input("\nExport results to CSV? (y/n): ").strip().lower()
        if export == "y":
            from simulation_reports import export_results_to_csv
            filename = f"simulation_{selected_sim.id}_age{target_age}_{date.today().isoformat()}.csv"
            export_results_to_csv(results, filename)

    except KeyboardInterrupt:
        print(f"\n\n⚠️  Simulation interrupted by user!")
        print(f"   Partial results may be incomplete.")
    except Exception as e:
        print(f"\n❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()


def run_interactive_mode(config_path: str = "financial_config.json"):
    """Run the interactive menu-driven interface."""

    # Use the provided config path or default
    current_config = config_path

    while True:
        print_menu(current_config)
        choice = get_menu_choice()

        if choice == 0:
            # Exit
            clear_screen()
            print("\n👋 Thanks for using Financial Optimization Tool!\n")
            break

        elif choice == 20:
            # View Investment Portfolio
            clear_screen()
            view_investment_portfolio(current_config)
            pause()
            continue

        elif choice == 21:
            # Add Investment Account
            clear_screen()
            add_investment_account_to_config(current_config)
            pause()
            continue

        elif choice == 22:
            # Add Manual Position
            clear_screen()
            add_manual_position(current_config)
            pause()
            continue

        elif choice == 23:
            # Record Stock Transaction
            clear_screen()
            record_stock_transaction(current_config)
            pause()
            continue

        elif choice == 24:
            # Refresh Stock Prices
            clear_screen()
            refresh_stock_prices(current_config)
            pause()
            continue

        elif choice == 27:
            # View Configured Simulations
            clear_screen()
            view_simulations(current_config)
            pause()
            continue

        elif choice == 28:
            # Run Simulation
            clear_screen()
            run_simulation_interactive(current_config)
            pause()
            continue

        elif choice == 29:
            # Add Simulation Config
            clear_screen()
            add_simulation_to_config(current_config)
            pause()
            continue

        elif choice == 30:
            # Edit Simulation Config
            clear_screen()
            edit_simulation(current_config)
            pause()
            continue

        elif choice == 31:
            # View ETF Library
            clear_screen()
            view_etf_library()
            pause()
            continue

        elif choice == 32:
            # Add ETF to Library
            clear_screen()
            add_etf_interactive()
            pause()
            continue

        elif choice == 33:
            # Search ETF Library
            clear_screen()
            search_etf_interactive()
            pause()
            continue

        elif choice == 25:
            # Run full setup wizard - creates new dated config
            clear_screen()
            dated_config = get_dated_config_name()
            print(f"Creating new configuration: {dated_config}\n")
            if run_setup_wizard(dated_config):
                current_config = dated_config
                print(f"\n✓ Now using: {current_config}")
                pause()
            continue

        elif choice == 26:
            # Load previous config
            clear_screen()
            print_header("Load Previous Configuration")
            selected = select_config_interactive()
            if selected:
                current_config = selected
                print(f"✓ Switched to: {current_config}")
            pause()
            continue

        # For options 8 and 10-15, we can add/mark without loading full config
        if choice in [8, 10, 11, 12, 13, 14, 15]:
            clear_screen()
            if choice == 8:
                mark_bill_paid(current_config)
            elif choice == 10:
                add_account_to_config(current_config)
            elif choice == 11:
                add_income_to_config(current_config)
            elif choice == 12:
                add_bill_to_config(current_config)
            elif choice == 13:
                add_credit_card_to_config(current_config)
            elif choice == 14:
                add_manual_payment_to_config(current_config)
            elif choice == 15:
                add_recurring_expense_to_config(current_config)
            pause()
            continue

        # For options 16-19, edit existing items (need valid config)
        if choice in [16, 17, 18, 19]:
            clear_screen()
            if choice == 16:
                edit_account(current_config)
            elif choice == 17:
                edit_income(current_config)
            elif choice == 18:
                edit_bill(current_config)
            elif choice == 19:
                edit_credit_card(current_config)
            pause()
            continue

        # For all other options, we need a valid config
        try:
            config = load_config(current_config)
            optimizer = FinancialOptimizer(config)
        except FileNotFoundError:
            clear_screen()
            print(f"\n❌ Config file not found: {current_config}\n")
            print(
                "Please run the Full Setup Wizard (option 20) to create your configuration,"
            )
            print("or Load Previous Config (option 21) to use an existing one.")
            pause()
            continue
        except Exception as e:
            clear_screen()
            print(f"\n❌ Error loading config: {e}\n")
            pause()
            continue

        clear_screen()

        if choice == 1:
            # View Today's Actions
            print_tasks(optimizer)
            pause()

        elif choice == 2:
            # View N-Day Action Plan (Optimal Simulation)
            try:
                days_input = input(
                    "\nHow many days to show? (1-30, default 30): "
                ).strip()
                if days_input and days_input.isdigit():
                    days = min(max(int(days_input), 1), 30)
                else:
                    days = 30
                print_optimal_simulation(optimizer, days=days)
            except (ValueError, KeyboardInterrupt):
                print_optimal_simulation(optimizer, days=30)
            pause()

        elif choice == 3:
            # View Financial Summary
            print_summary(optimizer)
            pause()

        elif choice == 4:
            # View 14-Day Cash Flow Forecast
            print_cash_flow_forecast(optimizer)
            pause()

        elif choice == 5:
            # View Account Details
            print_accounts(optimizer)
            pause()

        elif choice == 6:
            # View All Information
            print_tasks(optimizer)
            print_upcoming_plan(optimizer, days=5)
            print_summary(optimizer)
            print_cash_flow_forecast(optimizer)
            print_accounts(optimizer)
            pause()

        elif choice == 7:
            # Financial Advice
            interactive_advice(optimizer)
            pause()

        elif choice == 9:
            # Update Account Balances
            interactive_update(current_config)
            pause()


def run_argument_mode(args):
    """Run with command-line arguments (non-interactive mode)."""

    # Handle interactive update mode
    if args.update:
        interactive_update(args.config)
        # After update, show tasks by default
        args.tasks = True

    # Load configuration
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        print(f"❌ Error: Config file not found: {args.config}")
        print(
            f"\nCreate a config file named '{args.config}' or specify a different path."
        )
        print(f"See 'example_config.json' for a template.")
        print(f"\nRun without arguments for interactive setup wizard.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        sys.exit(1)

    # Create optimizer
    optimizer = FinancialOptimizer(config)

    # Parse target date if provided
    target_date = None
    if args.date:
        try:
            target_date = date.fromisoformat(args.date)
        except ValueError:
            print(f"❌ Error: Invalid date format. Use YYYY-MM-DD")
            sys.exit(1)

    # If no flags specified, show tasks by default
    if not (args.tasks or args.summary or args.accounts or args.forecast or args.all):
        args.tasks = True

    # Show requested information
    if args.all or args.tasks:
        print_tasks(optimizer, target_date)

    if args.all or args.summary:
        print_summary(optimizer)

    if args.all or args.forecast:
        print_cash_flow_forecast(optimizer)

    if args.all or args.accounts:
        print_accounts(optimizer)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Financial Optimization Tool - Manage your finances and get daily tasks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Interactive Mode (default):
  Run without arguments to enter interactive menu mode

Argument Mode (shortcuts):
  Use flags for quick access to specific views

Examples:
  %(prog)s                    # Interactive menu
  %(prog)s -t                 # Show today's tasks (quick)
  %(prog)s --all              # Show everything (quick)
  %(prog)s -u                 # Update balances
        """,
    )
    parser.add_argument(
        "config",
        type=str,
        nargs="?",
        default="financial_config.json",
        help="Path to financial configuration JSON file (default: financial_config.json)",
    )
    parser.add_argument(
        "-t", "--tasks", action="store_true", help="Show today's tasks (argument mode)"
    )
    parser.add_argument(
        "-s",
        "--summary",
        action="store_true",
        help="Show weekly summary (argument mode)",
    )
    parser.add_argument(
        "-a",
        "--accounts",
        action="store_true",
        help="Show account details (argument mode)",
    )
    parser.add_argument(
        "-f",
        "--forecast",
        action="store_true",
        help="Show 14-day cash flow forecast (argument mode)",
    )
    parser.add_argument(
        "-u",
        "--update",
        action="store_true",
        help="Update account balances interactively (argument mode)",
    )
    parser.add_argument(
        "-d",
        "--date",
        type=str,
        help="Target date for tasks in YYYY-MM-DD format (argument mode)",
    )
    parser.add_argument(
        "--all", action="store_true", help="Show all information (argument mode)"
    )
    parser.add_argument(
        "-i", "--interactive", action="store_true", help="Force interactive menu mode"
    )

    args = parser.parse_args()

    # If no config specified, use the most recent one
    if args.config == "financial_config.json":
        most_recent = get_most_recent_config()
        if most_recent and Path(most_recent).exists():
            args.config = most_recent

    # Determine mode: interactive vs argument
    has_arguments = any(
        [
            args.tasks,
            args.summary,
            args.accounts,
            args.forecast,
            args.update,
            args.date,
            args.all,
        ]
    )

    if args.interactive or not has_arguments:
        # Interactive menu mode
        run_interactive_mode(args.config)
    else:
        # Argument mode
        run_argument_mode(args)


if __name__ == "__main__":
    main()
