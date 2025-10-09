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
    run_setup_wizard, add_account_to_config, add_income_to_config,
    add_bill_to_config, add_credit_card_to_config
)
from config_manager import (
    get_dated_config_name, select_config_interactive, list_config_files
)


def clear_screen():
    """Clear the terminal screen."""
    os.system('clear' if os.name == 'posix' else 'cls')


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
    print("    1. 📋 Today's Action Plan")
    print("    2. 📊 Financial Summary")
    print("    3. 📅 14-Day Cash Flow Forecast")
    print("    4. 🏦 Account Details")
    print("    5. 📖 View All Information")
    print()
    print("  MANAGE:")
    print("    6. 🔄 Update Account Balances")
    print("    7. ➕ Add New Account")
    print("    8. ➕ Add New Income Source")
    print("    9. ➕ Add New Bill")
    print("   10. ➕ Add New Credit Card")
    print()
    print("  SETUP:")
    print("   11. ⚙️  Run Full Setup Wizard (creates new dated config)")
    print("   12. 📂 Load Previous Config")
    print()
    print("    0. 🚪 Exit")
    print()


def get_menu_choice():
    """Get user's menu choice."""
    while True:
        try:
            choice = input("Select option (0-12): ").strip()
            if choice.isdigit() and 0 <= int(choice) <= 12:
                return int(choice)
            print("⚠️  Please enter a number between 0 and 12")
        except KeyboardInterrupt:
            print("\n")
            return 0
        except EOFError:
            return 0


def pause():
    """Pause and wait for user input."""
    input("\nPress Enter to continue...")


def print_tasks(optimizer: FinancialOptimizer, target_date: date = None):
    """Print concrete daily tasks with specific amounts."""
    if target_date is None:
        target_date = date.today()

    print_header(f"Action Plan for {target_date.strftime('%A, %B %d, %Y')}")

    # Show current cash position
    available = sum(acc.balance - acc.minimum_balance for acc in optimizer.config.accounts)
    total = sum(acc.balance for acc in optimizer.config.accounts)
    print(f"💵 Cash Position: ${total:,.2f} total | ${available:,.2f} available\n")

    tasks = optimizer.generate_daily_tasks(target_date)

    if not tasks:
        print("✓ No required actions today!\n")
        return

    for task in tasks:
        print(f"{task.category}: {task}")

    print()


def print_cash_flow_forecast(optimizer: FinancialOptimizer):
    """Print 14-day cash flow forecast."""
    print_header("14-Day Cash Flow Forecast")

    timeline = optimizer.get_cash_flow_forecast(days=14)
    min_required = sum(acc.minimum_balance for acc in optimizer.config.accounts)

    print(f"{'Date':<12} {'Starting':<12} {'Events':<8} {'Ending':<12} {'Status':<10}")
    print("-" * 70)

    for day_date in sorted(timeline.keys()):
        day_data = timeline[day_date]
        day_str = day_date.strftime("%a %m/%d")

        events_count = len(day_data.events)
        events_str = f"{events_count} event{'s' if events_count != 1 else ''}"

        # Status indicator
        if day_data.ending_balance < min_required:
            status = "⚠️  LOW"
        elif day_data.ending_balance < min_required + 200:
            status = "⚠️  TIGHT"
        else:
            status = "✓ OK"

        print(f"{day_str:<12} ${day_data.starting_balance:>9,.2f} {events_str:>8} ${day_data.ending_balance:>9,.2f}  {status}")

        # Show events for this day
        for event in day_data.events:
            symbol = "+" if event.amount > 0 else ""
            print(f"             └─ {symbol}${event.amount:,.2f} {event.description}")

    print()


def print_summary(optimizer: FinancialOptimizer):
    """Print action-focused monthly summary."""
    print_header("Monthly Action Plan")

    plan = optimizer.generate_monthly_action_plan()

    print(f"📅 As of: {plan['current_date'].strftime('%B %d, %Y')}\n")

    # Summary balances
    print("💰 CURRENT POSITION:")
    print(f"   Checking: ${plan['checking_balance']:,.2f}")
    print(f"   Savings:  ${plan['savings_balance']:,.2f}")
    if plan['cash_balance'] > 0:
        print(f"   Cash:     ${plan['cash_balance']:,.2f}")
    print(f"   Debt:     ${plan['total_debt']:,.2f}")

    # Emergency fund
    status = "✓" if plan['emergency_pct'] >= 100 else "⚠️ "
    print(f"\n🏦 Emergency Fund: ${plan['emergency_fund']:,.2f} / ${plan['emergency_target']:,.2f} ({status} {plan['emergency_pct']:.0f}%)\n")

    # Monthly cash flow
    print("📊 MONTHLY OUTLOOK:")
    print(f"   Expected Income:   +${plan['total_income']:,.2f}")
    print(f"   Expected Outflows: -${plan['total_outflows']:,.2f}")
    net_symbol = "+" if plan['net_monthly'] >= 0 else ""
    print(f"   Net Cash Flow:     {net_symbol}${plan['net_monthly']:,.2f}\n")

    # Credit card actions
    if plan['cc_actions']:
        print("💳 CREDIT CARD ACTIONS (Next 30 Days):\n")
        for action in plan['cc_actions']:
            days_until = (action['due_date'] - plan['current_date']).days
            day_str = "TODAY" if days_until == 0 else f"in {days_until} days" if days_until > 0 else f"{-days_until} days overdue"

            print(f"   📅 {action['due_date'].strftime('%b %d')} ({day_str})")
            print(f"      Pay ${action['recommended_payment']:,.2f} to {action['card_name']}")

            # Show breakdown
            parts = []
            if action['current_balance'] > 0:
                parts.append(f"${action['current_balance']:,.2f} balance")
            if action['upcoming_spending'] > 0:
                parts.append(f"${action['upcoming_spending']:,.2f} upcoming bills")
            extra = action['recommended_payment'] - action['minimum_payment'] - action['upcoming_spending']
            if extra > 0:
                parts.append(f"${extra:,.2f} extra")

            if parts:
                print(f"         ({' + '.join(parts)})")
            print(f"         Minimum required: ${action['minimum_payment']:,.2f} | APR: {action['apr']*100:.1f}%")
            print()

    # Bills from checking
    if plan['checking_bills']:
        print("💰 BILLS FROM CHECKING (Next 30 Days):\n")
        for bill in plan['checking_bills']:
            days_until = (bill['date'] - plan['current_date']).days
            day_str = "TODAY" if days_until == 0 else f"in {days_until} days" if days_until > 0 else f"{-days_until} days overdue"
            autopay_str = " [AUTOPAY]" if bill['autopay'] else ""

            print(f"   📅 {bill['date'].strftime('%b %d')} ({day_str})")
            print(f"      Pay ${bill['amount']:,.2f} - {bill['name']}{autopay_str}")
        print()

    # Income expected
    if plan['monthly_income']:
        print("💵 EXPECTED INCOME (Next 30 Days):\n")
        for income in plan['monthly_income']:
            days_until = (income['date'] - plan['current_date']).days
            day_str = "TODAY" if days_until == 0 else f"in {days_until} days"

            print(f"   📅 {income['date'].strftime('%b %d')} ({day_str})")
            print(f"      ${income['amount']:,.2f} from {income['source']}")
        print()


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
                acc.balance = float(response.replace(',', ''))
                print(f"    Updated to ${acc.balance:,.2f}")
            except ValueError:
                print(f"    Invalid input, keeping ${current:,.2f}")

    print("\n💳 CREDIT CARDS:")
    for cc in config.credit_cards:
        current = cc.balance
        response = input(f"  {cc.name} balance (current: ${current:,.2f}): $")
        if response.strip():
            try:
                cc.balance = float(response.replace(',', ''))
                print(f"    Updated to ${cc.balance:,.2f}")
            except ValueError:
                print(f"    Invalid input, keeping ${current:,.2f}")

        # Optionally update minimum payment
        current_min = cc.minimum_payment
        response = input(f"  {cc.name} minimum payment (current: ${current_min:,.2f}): $")
        if response.strip():
            try:
                cc.minimum_payment = float(response.replace(',', ''))
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


def run_interactive_mode(config_path: str = 'financial_config.json'):
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

        elif choice == 11:
            # Run full setup wizard - creates new dated config
            clear_screen()
            dated_config = get_dated_config_name()
            print(f"Creating new configuration: {dated_config}\n")
            if run_setup_wizard(dated_config):
                current_config = dated_config
                print(f"\n✓ Now using: {current_config}")
                pause()
            continue

        elif choice == 12:
            # Load previous config
            clear_screen()
            print_header("Load Previous Configuration")
            selected = select_config_interactive()
            if selected:
                current_config = selected
                print(f"✓ Switched to: {current_config}")
            pause()
            continue

        # For options 7-10, we can add to config even if it doesn't exist yet
        if choice in [7, 8, 9, 10]:
            clear_screen()
            if choice == 7:
                add_account_to_config(current_config)
            elif choice == 8:
                add_income_to_config(current_config)
            elif choice == 9:
                add_bill_to_config(current_config)
            elif choice == 10:
                add_credit_card_to_config(current_config)
            pause()
            continue

        # For all other options, we need a valid config
        try:
            config = load_config(current_config)
            optimizer = FinancialOptimizer(config)
        except FileNotFoundError:
            clear_screen()
            print(f"\n❌ Config file not found: {current_config}\n")
            print("Please run the Full Setup Wizard (option 11) to create your configuration,")
            print("or Load Previous Config (option 12) to use an existing one.")
            pause()
            continue
        except Exception as e:
            clear_screen()
            print(f"\n❌ Error loading config: {e}\n")
            pause()
            continue

        clear_screen()

        if choice == 1:
            # View Today's Action Plan
            print_tasks(optimizer)
            pause()

        elif choice == 2:
            # View Financial Summary
            print_summary(optimizer)
            pause()

        elif choice == 3:
            # View 14-Day Cash Flow Forecast
            print_cash_flow_forecast(optimizer)
            pause()

        elif choice == 4:
            # View Account Details
            print_accounts(optimizer)
            pause()

        elif choice == 5:
            # View All Information
            print_tasks(optimizer)
            print_summary(optimizer)
            print_cash_flow_forecast(optimizer)
            print_accounts(optimizer)
            pause()

        elif choice == 6:
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
        print(f"\nCreate a config file named '{args.config}' or specify a different path.")
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
        """
    )
    parser.add_argument(
        'config',
        type=str,
        nargs='?',
        default='financial_config.json',
        help='Path to financial configuration JSON file (default: financial_config.json)'
    )
    parser.add_argument(
        '-t', '--tasks',
        action='store_true',
        help='Show today\'s tasks (argument mode)'
    )
    parser.add_argument(
        '-s', '--summary',
        action='store_true',
        help='Show weekly summary (argument mode)'
    )
    parser.add_argument(
        '-a', '--accounts',
        action='store_true',
        help='Show account details (argument mode)'
    )
    parser.add_argument(
        '-f', '--forecast',
        action='store_true',
        help='Show 14-day cash flow forecast (argument mode)'
    )
    parser.add_argument(
        '-u', '--update',
        action='store_true',
        help='Update account balances interactively (argument mode)'
    )
    parser.add_argument(
        '-d', '--date',
        type=str,
        help='Target date for tasks in YYYY-MM-DD format (argument mode)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Show all information (argument mode)'
    )
    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='Force interactive menu mode'
    )

    args = parser.parse_args()

    # Determine mode: interactive vs argument
    has_arguments = any([
        args.tasks, args.summary, args.accounts, args.forecast,
        args.update, args.date, args.all
    ])

    if args.interactive or not has_arguments:
        # Interactive menu mode
        run_interactive_mode(args.config)
    else:
        # Argument mode
        run_argument_mode(args)


if __name__ == '__main__':
    main()
