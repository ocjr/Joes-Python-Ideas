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

    tasks = optimizer.generate_daily_tasks(target_date)

    # Filter to only today's actions (priority 1-4, skip upcoming summary)
    today_tasks = [t for t in tasks if t.priority < 5]

    if not today_tasks:
        print("✓ No required actions today!\n")
    else:
        print("📋 ACTIONS FOR TODAY:\n")
        for task in today_tasks:
            # Description already includes the amount details, don't duplicate
            print(f"{task.category}: {task.description}")

    print()


def print_upcoming_plan(optimizer: FinancialOptimizer, days: int = 5):
    """Print action plan for the next N days."""
    print_header(f"Upcoming {days}-Day Action Plan")

    timeline = optimizer.get_cash_flow_forecast(days=days)

    # Find the NEXT credit card due date to only show extra payments once
    next_cc_due_date = None
    for cc in optimizer.config.credit_cards:
        if cc.balance > 0:
            cc_due = optimizer.get_next_date(cc.due_day)
            if next_cc_due_date is None or cc_due < next_cc_due_date:
                next_cc_due_date = cc_due

    for day_offset in range(days):
        current_date = date.today() + timedelta(days=day_offset)
        if current_date not in timeline:
            continue

        day_data = timeline[current_date]
        day_label = (
            "TODAY"
            if day_offset == 0
            else f"+{day_offset} day{'s' if day_offset > 1 else ''}"
        )

        # Get required events for this day
        required_events = [e for e in day_data.events if e.required and e.amount < 0]
        income_events = [e for e in day_data.events if e.amount > 0]

        # Check if any credit cards are due today
        cards_due_today = {}
        cc_min_payments = {}
        for cc in optimizer.config.credit_cards:
            if cc.balance > 0:
                cc_due = optimizer.get_next_date(cc.due_day)
                if cc_due == current_date:
                    cards_due_today[cc.id] = cc
                    cc_min_payments[cc.id] = cc.minimum_payment

        # Only calculate extra payments if this is the NEXT credit card due date
        safe_payments = {}
        emergency_fund_payment = 0
        if cards_due_today and current_date == next_cc_due_date:
            safe_payments = optimizer.calculate_safe_payment_amount()
            emergency_fund_payment = safe_payments.get("emergency_fund", 0)

        # Show this day if there's anything happening
        if required_events or income_events or cards_due_today:
            print(f"\n📅 {current_date.strftime('%a %b %d')} ({day_label})")

            for event in income_events:
                description = event.description.replace("Income: ", "")
                print(f"   💵 INCOME: +${event.amount:,.2f} from {description}")

            # Show payments (combine CC min + extra)
            for event in required_events:
                # Check if this is a CC payment
                is_cc_payment = False
                for cc_id, cc in cards_due_today.items():
                    if f"CC Min Payment: {cc.name}" in event.description:
                        min_payment = cc_min_payments[cc_id]
                        extra_payment = safe_payments.get(cc_id, 0)
                        total_payment = min_payment + extra_payment

                        if extra_payment > 0:
                            daily_savings = (extra_payment * cc.apr) / 365
                            print(
                                f"   💳 PAY: ${total_payment:,.2f} to {cc.name} (${min_payment:,.2f} min + ${extra_payment:,.2f} extra, saves ${daily_savings:.2f}/day)"
                            )
                        else:
                            print(
                                f"   💳 PAY: ${total_payment:,.2f} to {cc.name} (minimum payment)"
                            )

                        is_cc_payment = True
                        break

                # Not a CC payment, show as regular bill
                if not is_cc_payment:
                    description = (
                        event.description.replace("Bill: ", "")
                        .replace("[AUTO]", "")
                        .strip()
                    )
                    autopay = "[AUTO]" if "[AUTO]" in event.description else ""
                    print(f"   💳 PAY: ${-event.amount:,.2f} - {description} {autopay}")

            # Show emergency fund savings
            if emergency_fund_payment > 0:
                print(f"   🏦 SAVE: ${emergency_fund_payment:,.2f} to Emergency Fund")

    print()


def print_cash_flow_forecast(optimizer: FinancialOptimizer):
    """Print 14-day cash flow forecast with recommended payments."""
    print_header("14-Day Cash Flow Forecast")

    timeline = optimizer.get_cash_flow_forecast(days=14)
    min_required = sum(acc.minimum_balance for acc in optimizer.config.accounts)

    print(f"{'Date':<12} {'Starting':<12} {'Events':<8} {'Ending':<12} {'Status':<10}")
    print("-" * 70)

    # Find the NEXT credit card due date to only show extra payments once
    next_cc_due_date = None
    for cc in optimizer.config.credit_cards:
        if cc.balance > 0:
            cc_due = optimizer.get_next_date(cc.due_day)
            if next_cc_due_date is None or cc_due < next_cc_due_date:
                next_cc_due_date = cc_due

    # Track cumulative extra payments to adjust balances
    cumulative_extra = 0.0

    for day_date in sorted(timeline.keys()):
        day_data = timeline[day_date]
        day_str = day_date.strftime("%a %m/%d")

        # Check if any credit cards are due this day
        cards_due_today = {}
        cc_min_payments = {}
        for cc in optimizer.config.credit_cards:
            if cc.balance > 0:
                cc_due = optimizer.get_next_date(cc.due_day)
                if cc_due == day_date:
                    cards_due_today[cc.id] = cc
                    cc_min_payments[cc.id] = cc.minimum_payment

        # Only calculate extra payments if this is the NEXT credit card due date
        safe_payments = {}
        emergency_fund_payment = 0
        if cards_due_today and day_date == next_cc_due_date:
            safe_payments = optimizer.calculate_safe_payment_amount()
            emergency_fund_payment = safe_payments.get("emergency_fund", 0)

        # Calculate total extra payments for this day
        day_extra_total = 0
        for cc_id in cards_due_today.keys():
            extra_payment = safe_payments.get(cc_id, 0)
            day_extra_total += extra_payment

        if emergency_fund_payment > 0:
            day_extra_total += emergency_fund_payment

        # Adjust starting and ending balances
        adjusted_starting = day_data.starting_balance - cumulative_extra
        adjusted_ending = day_data.ending_balance - cumulative_extra - day_extra_total

        # Update cumulative
        cumulative_extra += day_extra_total

        events_count = len(day_data.events)
        # Add emergency fund as an event if applicable
        if emergency_fund_payment > 0:
            events_count += 1

        events_str = f"{events_count} event{'s' if events_count != 1 else ''}"

        # Status indicator
        if adjusted_ending < min_required:
            status = "⚠️  LOW"
        elif adjusted_ending < min_required + 200:
            status = "⚠️  TIGHT"
        else:
            status = "✓ OK"

        print(
            f"{day_str:<12} ${adjusted_starting:>9,.2f} {events_str:>8} ${adjusted_ending:>9,.2f}  {status}"
        )

        # Show events for this day
        for event in day_data.events:
            # Check if this is a CC payment that should show combined amount
            is_cc_payment = False
            for cc_id, cc in cards_due_today.items():
                if f"CC Min Payment: {cc.name}" in event.description:
                    min_payment = cc_min_payments[cc_id]
                    extra_payment = safe_payments.get(cc_id, 0)
                    total_payment = min_payment + extra_payment

                    if extra_payment > 0:
                        print(
                            f"             └─ $-{total_payment:,.2f} Pay {cc.name} (${min_payment:,.2f} min + ${extra_payment:,.2f} extra)"
                        )
                    else:
                        print(
                            f"             └─ $-{total_payment:,.2f} {event.description}"
                        )

                    is_cc_payment = True
                    break

            if not is_cc_payment:
                symbol = "+" if event.amount > 0 else ""
                description = event.description.replace("Income: ", "").replace(
                    "Bill: ", ""
                )
                print(f"             └─ {symbol}${event.amount:,.2f} {description}")

        # Show emergency fund if applicable
        if emergency_fund_payment > 0:
            print(f"             └─ $-{emergency_fund_payment:,.2f} Emergency Fund")

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
            # View N-Day Action Plan
            try:
                days_input = input(
                    "\nHow many days to show? (1-30, default 5): "
                ).strip()
                if days_input and days_input.isdigit():
                    days = min(max(int(days_input), 1), 30)
                else:
                    days = 5
                print_upcoming_plan(optimizer, days=days)
            except (ValueError, KeyboardInterrupt):
                print_upcoming_plan(optimizer, days=5)
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
