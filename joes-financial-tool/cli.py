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
)
from edit_wizard import edit_account, edit_income, edit_bill, edit_credit_card
from bill_tracker import mark_bill_paid
from financial_advisor import interactive_advice
from config_manager import (
    get_dated_config_name,
    select_config_interactive,
    list_config_files,
    get_most_recent_config,
)


def clear_screen():
    """Clear the terminal screen."""
    os.system("clear" if os.name == "posix" else "cls")


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
    print("    2. 📅 Action Plan (custom days)")
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
    print("   14. ✏️  Edit Account")
    print("   15. ✏️  Edit Income Source")
    print("   16. ✏️  Edit Bill")
    print("   17. ✏️  Edit Credit Card")
    print()
    print("  SETUP:")
    print("   18. ⚙️  Run Full Setup Wizard (creates new dated config)")
    print("   19. 📂 Load Previous Config")
    print()
    print("    0. 🚪 Exit")
    print()


def get_menu_choice():
    """Get user's menu choice."""
    while True:
        try:
            choice = input("Select option (0-19): ").strip()
            if choice.isdigit() and 0 <= int(choice) <= 19:
                return int(choice)
            print("⚠️  Please enter a number between 0 and 19")
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

    # Show key transactions
    print(f"\n📋 Key Transactions (next 7 days):")
    for day in optimal.days[:7]:
        if day.transactions:
            print(f"\n   {day.date.strftime('%a %m/%d')}:")
            for txn, decision in day.transactions:
                if txn.amount != 0:
                    amount_str = f"${abs(txn.amount):.2f}"
                    if txn.amount > 0:
                        print(f"      ✓ {txn.description}: +{amount_str}")
                    else:
                        method_str = ""
                        if decision.method.value == "checking":
                            method_str = " [Checking]"
                        elif decision.method.value == "credit_card":
                            method_str = f" [Credit]"
                        elif decision.method.value == "split":
                            method_str = f" [Split: ${decision.checking_amount:.0f} checking + ${decision.credit_amount:.0f} credit]"
                        print(f"      • {txn.description}: -{amount_str}{method_str}")
                        if decision.reason and "⚠️" in decision.reason:
                            print(f"        {decision.reason}")

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

        # Show transaction details
        for txn, decision in day.transactions:
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

        elif choice == 18:
            # Run full setup wizard - creates new dated config
            clear_screen()
            dated_config = get_dated_config_name()
            print(f"Creating new configuration: {dated_config}\n")
            if run_setup_wizard(dated_config):
                current_config = dated_config
                print(f"\n✓ Now using: {current_config}")
                pause()
            continue

        elif choice == 19:
            # Load previous config
            clear_screen()
            print_header("Load Previous Configuration")
            selected = select_config_interactive()
            if selected:
                current_config = selected
                print(f"✓ Switched to: {current_config}")
            pause()
            continue

        # For options 8 and 10-13, we can add/mark bills without loading full config
        if choice in [8, 10, 11, 12, 13]:
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
            pause()
            continue

        # For options 14-17, edit existing items (need valid config)
        if choice in [14, 15, 16, 17]:
            clear_screen()
            if choice == 14:
                edit_account(current_config)
            elif choice == 15:
                edit_income(current_config)
            elif choice == 16:
                edit_bill(current_config)
            elif choice == 17:
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
                "Please run the Full Setup Wizard (option 18) to create your configuration,"
            )
            print("or Load Previous Config (option 19) to use an existing one.")
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
