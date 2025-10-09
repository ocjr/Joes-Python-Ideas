#!/usr/bin/env python3
"""
Interactive setup wizard to create initial financial configuration.
"""

import sys
from datetime import date, timedelta
from pathlib import Path
from models import (
    FinancialConfig, Account, Income, Bill, CreditCard, Settings,
    AccountType, Frequency, PayoffStrategy, IncomeSplit
)
from config_loader import save_config, load_config


def clear_screen():
    """Clear the terminal screen."""
    print("\n" * 2)


def print_header(title: str):
    """Print a formatted header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def get_input(prompt: str, default=None, input_type=str, required=True):
    """Get user input with validation."""
    while True:
        default_str = f" [{default}]" if default is not None else ""
        response = input(f"{prompt}{default_str}: ").strip()

        if not response and default is not None:
            return default

        if not response and not required:
            return None

        if not response and required:
            print("  ⚠️  This field is required. Please enter a value.")
            continue

        # Type conversion
        try:
            if input_type == float:
                return float(response.replace(',', ''))
            elif input_type == int:
                return int(response)
            elif input_type == bool:
                # Strict y/n validation
                response_lower = response.lower()
                if response_lower in ['y', 'yes']:
                    return True
                elif response_lower in ['n', 'no']:
                    return False
                else:
                    print("  ⚠️  Please enter 'y' or 'n'.")
                    continue
            else:
                return response
        except ValueError:
            print(f"  ⚠️  Invalid input. Expected {input_type.__name__}.")


def get_choice(prompt: str, choices: list, allow_cancel=False):
    """Get user choice from a list."""
    print(f"\n{prompt}")
    for i, choice in enumerate(choices, 1):
        print(f"  {i}. {choice}")
    if allow_cancel:
        print(f"  0. Cancel")

    while True:
        try:
            choice_num = int(input("\nSelect option: "))
            if allow_cancel and choice_num == 0:
                return None
            if 1 <= choice_num <= len(choices):
                return choices[choice_num - 1]
            print(f"  ⚠️  Please enter a number between 1 and {len(choices)}")
        except ValueError:
            print("  ⚠️  Please enter a valid number")


def setup_accounts():
    """Set up bank accounts."""
    print_header("Step 1: Bank Accounts")
    print("Let's set up your bank accounts (checking, savings, cash).\n")

    accounts = []
    account_num = 1

    while True:
        print(f"\n--- Account #{account_num} ---")

        name = get_input("Account name (e.g., 'Main Checking', 'Emergency Fund')")

        account_type = get_choice(
            "Account type:",
            ["checking", "savings", "cash"]
        )

        balance = get_input("Current balance", input_type=float)
        minimum_balance = get_input(
            "Minimum balance to maintain",
            default=0.0,
            input_type=float,
            required=False
        ) or 0.0

        # Create account ID from name
        account_id = name.lower().replace(' ', '_')

        accounts.append(Account(
            id=account_id,
            name=name,
            type=AccountType(account_type),
            balance=balance,
            minimum_balance=minimum_balance
        ))

        print(f"\n✓ Added {name}: ${balance:,.2f}")

        if not get_input("\nAdd another account? (y/n)", default="n", input_type=bool):
            break

        account_num += 1

    return accounts


def setup_income(accounts):
    """Set up income sources with account deposit/split configuration."""
    print_header("Step 2: Income Sources")
    print("Let's set up your income (paychecks, freelance, etc.).\n")

    income_sources = []
    income_num = 1

    while True:
        print(f"\n--- Income Source #{income_num} ---")

        source = get_input("Income source name (e.g., 'Primary Job', 'Freelance')")

        amount = get_input("Amount per payment", input_type=float)

        frequency = get_choice(
            "How often do you get paid?",
            ["weekly", "biweekly", "semi-monthly", "monthly"]
        )

        # Get next payment date
        print("\nWhen is your next payment?")
        year = get_input("  Year", default=date.today().year, input_type=int)
        month = get_input("  Month (1-12)", input_type=int)
        day = get_input("  Day (1-31)", input_type=int)

        try:
            next_date = date(year, month, day)
        except ValueError:
            print("  ⚠️  Invalid date, using today")
            next_date = date.today()

        # Set up account deposits/splits
        splits = []
        print("\nHow should this income be deposited?")

        if not accounts:
            print("⚠️  No accounts available for deposit")
            deposit_account = None
        else:
            account_choices = [f"{acc.name} ({acc.type.value})" for acc in accounts]

            # Ask if they want to split
            split_income = get_input("Split across multiple accounts? (y/n)", default="n", input_type=bool)

            if split_income:
                print("\nSet up splits (last account will receive remainder):")
                total_allocated = 0.0

                for i, acc in enumerate(accounts[:-1]):  # All but last
                    split_amount = get_input(
                        f"  Amount to {acc.name}",
                        input_type=float,
                        required=False
                    )
                    if split_amount and split_amount > 0:
                        splits.append(IncomeSplit(account_id=acc.id, amount=split_amount))
                        total_allocated += split_amount

                # Last account gets remainder
                if accounts:
                    last_acc = accounts[-1]
                    remainder = amount - total_allocated
                    print(f"  Remainder to {last_acc.name}: ${remainder:,.2f}")
                    splits.append(IncomeSplit(account_id=last_acc.id, amount=None))  # None = remainder
            else:
                # Single account
                selected_label = get_choice("Deposit to which account?", account_choices)
                selected_idx = account_choices.index(selected_label)
                selected_account = accounts[selected_idx]
                splits = [IncomeSplit(account_id=selected_account.id, amount=None)]

            deposit_account = None  # Clear deprecated field

        # Create income ID from source
        income_id = source.lower().replace(' ', '_')

        income_sources.append(Income(
            id=income_id,
            source=source,
            amount=amount,
            frequency=Frequency(frequency),
            next_date=next_date,
            deposit_account=deposit_account,
            splits=splits if splits else None
        ))

        print(f"\n✓ Added {source}: ${amount:,.2f} {frequency}")

        if not get_input("\nAdd another income source? (y/n)", default="n", input_type=bool):
            break

        income_num += 1

    return income_sources


def setup_bills(accounts, credit_cards):
    """Set up recurring bills with payment source."""
    print_header("Step 3: Recurring Bills")
    print("Let's set up your recurring bills and expenses.\n")

    bills = []
    bill_num = 1

    while True:
        print(f"\n--- Bill #{bill_num} ---")

        name = get_input("Bill name (e.g., 'Rent', 'Electric', 'Netflix')")

        amount = get_input("Bill amount (average if variable)", input_type=float)

        due_day = get_input("Day of month bill is due (1-31)", input_type=int)

        frequency = get_choice(
            "How often is this bill due?",
            ["monthly", "quarterly", "annual"]
        )

        autopay = get_input("Is this on autopay? (y/n)", default="n", input_type=bool)

        category = get_choice(
            "Bill category:",
            ["housing", "utilities", "insurance", "subscriptions", "transportation", "other"],
            allow_cancel=True
        )

        # Ask which account or credit card pays for this
        print("\nHow do you pay this bill?")
        payment_sources = []

        # Add accounts
        for acc in accounts:
            payment_sources.append((acc.id, f"Account: {acc.name}", False))

        # Add credit cards
        for cc in credit_cards:
            payment_sources.append((cc.id, f"Credit Card: {cc.name}", True))

        if payment_sources:
            source_labels = [label for _, label, _ in payment_sources]
            selected_label = get_choice("Select payment source:", source_labels)
            selected_idx = source_labels.index(selected_label)
            payment_account, _, paid_by_credit = payment_sources[selected_idx]
        else:
            payment_account = None
            paid_by_credit = False

        # Create bill ID from name
        bill_id = name.lower().replace(' ', '_')

        bills.append(Bill(
            id=bill_id,
            name=name,
            amount=amount,
            due_day=due_day,
            frequency=Frequency(frequency),
            autopay=autopay,
            payment_account=payment_account,
            category=category,
            paid_by_credit=paid_by_credit
        ))

        autopay_str = " [AUTOPAY]" if autopay else ""
        payment_str = f" via {payment_account}" if payment_account else ""
        print(f"\n✓ Added {name}: ${amount:,.2f} on day {due_day}{autopay_str}{payment_str}")

        if not get_input("\nAdd another bill? (y/n)", default="n", input_type=bool):
            break

        bill_num += 1

    return bills


def setup_credit_cards():
    """Set up credit cards."""
    print_header("Step 4: Credit Cards")
    print("Let's set up your credit card accounts.\n")

    if not get_input("Do you have any credit cards to track? (y/n)", default="y", input_type=bool):
        return []

    credit_cards = []
    cc_num = 1

    while True:
        print(f"\n--- Credit Card #{cc_num} ---")

        name = get_input("Card name (e.g., 'Visa Card', 'Chase Freedom')")

        balance = get_input("Current balance owed", input_type=float)

        credit_limit = get_input("Credit limit", input_type=float)

        print("\nWhat's the APR (Annual Percentage Rate)?")
        apr_percent = get_input("  APR as percentage (e.g., 18.99 for 18.99%)", input_type=float)
        apr = apr_percent / 100.0

        due_day = get_input("Payment due day of month (1-31)", input_type=int)

        minimum_payment = get_input("Minimum payment amount", input_type=float)

        statement_day = get_input(
            "Statement closing day (optional, 1-31)",
            required=False,
            input_type=int
        )

        # Create card ID from name
        card_id = name.lower().replace(' ', '_')

        credit_cards.append(CreditCard(
            id=card_id,
            name=name,
            balance=balance,
            credit_limit=credit_limit,
            apr=apr,
            due_day=due_day,
            minimum_payment=minimum_payment,
            statement_day=statement_day,
            payment_account=None
        ))

        print(f"\n✓ Added {name}: ${balance:,.2f} / ${credit_limit:,.2f} @ {apr_percent:.2f}% APR")

        if not get_input("\nAdd another credit card? (y/n)", default="n", input_type=bool):
            break

        cc_num += 1

    return credit_cards


def setup_settings():
    """Set up optimization settings."""
    print_header("Step 5: Settings")
    print("Finally, let's configure your optimization preferences.\n")

    emergency_target = get_input(
        "Emergency fund target amount",
        default=1000.0,
        input_type=float
    )

    planning_horizon = get_input(
        "Planning horizon in days",
        default=30,
        input_type=int
    )

    print("\nDebt payoff strategy:")
    print("  - avalanche: Pay highest interest rate first (saves most money)")
    print("  - snowball: Pay lowest balance first (quick wins, motivation)")
    print("  - balanced: Mix of both strategies")

    priority = get_choice(
        "\nChoose your strategy:",
        ["avalanche", "snowball", "balanced"]
    )

    return Settings(
        emergency_fund_target=emergency_target,
        planning_horizon_days=planning_horizon,
        priority=PayoffStrategy(priority)
    )


def run_setup_wizard(output_path: str = "financial_config.json"):
    """Run the complete setup wizard."""
    clear_screen()
    print_header("💰 Financial Optimization Tool - Setup Wizard")
    print("Welcome! Let's set up your financial configuration.\n")
    print("This wizard will guide you through setting up:")
    print("  1. Bank accounts")
    print("  2. Income sources")
    print("  3. Credit cards")
    print("  4. Recurring bills (with payment sources)")
    print("  5. Optimization settings\n")

    if not get_input("Ready to begin? (y/n)", default="y", input_type=bool):
        print("Setup cancelled.")
        return False

    try:
        # Run through all setup steps in correct order
        accounts = setup_accounts()
        income = setup_income(accounts)  # Pass accounts for splits
        credit_cards = setup_credit_cards()
        bills = setup_bills(accounts, credit_cards)  # Pass accounts and cards
        settings = setup_settings()

        # Create config
        config = FinancialConfig(
            accounts=accounts,
            income=income,
            bills=bills,
            credit_cards=credit_cards,
            settings=settings
        )

        # Save to file
        print_header("Saving Configuration")
        save_config(config, output_path)

        print(f"✓ Configuration saved to: {output_path}\n")
        print("Summary:")
        print(f"  • {len(accounts)} account(s)")
        print(f"  • {len(income)} income source(s)")
        print(f"  • {len(bills)} recurring bill(s)")
        print(f"  • {len(credit_cards)} credit card(s)")
        print(f"  • Strategy: {settings.priority.value}")
        print(f"\nYou can now run the main tool to see your action plan!")

        return True

    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        return False
    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        return False


def add_account_to_config(config_path: str = "financial_config.json"):
    """Add a single account to existing config."""
    try:
        config = load_config(config_path)
    except FileNotFoundError:
        print(f"❌ Config file not found: {config_path}")
        return False
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False

    print_header("Add New Account")
    print("Let's add a new account to your configuration.\n")

    name = get_input("Account name (e.g., 'Savings Account', 'Cash Wallet')")

    # Check if account with this name already exists
    account_id = name.lower().replace(' ', '_')
    if any(acc.id == account_id for acc in config.accounts):
        print(f"⚠️  An account with ID '{account_id}' already exists!")
        if not get_input("Continue anyway? (y/n)", default="n", input_type=bool):
            return False

    account_type = get_choice("Account type:", ["checking", "savings", "cash"])
    balance = get_input("Current balance", input_type=float)
    minimum_balance = get_input(
        "Minimum balance to maintain",
        default=0.0,
        input_type=float,
        required=False
    ) or 0.0

    new_account = Account(
        id=account_id,
        name=name,
        type=AccountType(account_type),
        balance=balance,
        minimum_balance=minimum_balance
    )

    config.accounts.append(new_account)
    save_config(config, config_path)

    print(f"\n✓ Added {name}: ${balance:,.2f}")
    print(f"✓ Configuration updated!\n")
    return True


def add_income_to_config(config_path: str = "financial_config.json"):
    """Add a single income source to existing config."""
    try:
        config = load_config(config_path)
    except FileNotFoundError:
        print(f"❌ Config file not found: {config_path}")
        return False
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False

    print_header("Add New Income Source")
    print("Let's add a new income source to your configuration.\n")

    source = get_input("Income source name (e.g., 'Side Hustle', 'Bonus')")
    amount = get_input("Amount per payment", input_type=float)
    frequency = get_choice(
        "How often do you get paid?",
        ["weekly", "biweekly", "semi-monthly", "monthly"]
    )

    print("\nWhen is your next payment?")
    year = get_input("  Year", default=date.today().year, input_type=int)
    month = get_input("  Month (1-12)", input_type=int)
    day = get_input("  Day (1-31)", input_type=int)

    try:
        next_date = date(year, month, day)
    except ValueError:
        print("  ⚠️  Invalid date, using today")
        next_date = date.today()

    income_id = source.lower().replace(' ', '_')

    new_income = Income(
        id=income_id,
        source=source,
        amount=amount,
        frequency=Frequency(frequency),
        next_date=next_date,
        deposit_account=None
    )

    config.income.append(new_income)
    save_config(config, config_path)

    print(f"\n✓ Added {source}: ${amount:,.2f} {frequency}")
    print(f"✓ Configuration updated!\n")
    return True


def add_bill_to_config(config_path: str = "financial_config.json"):
    """Add a single bill to existing config."""
    try:
        config = load_config(config_path)
    except FileNotFoundError:
        print(f"❌ Config file not found: {config_path}")
        return False
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False

    print_header("Add New Bill")
    print("Let's add a new recurring bill to your configuration.\n")

    name = get_input("Bill name (e.g., 'Gym Membership', 'Storage Unit')")
    amount = get_input("Bill amount (average if variable)", input_type=float)
    due_day = get_input("Day of month bill is due (1-31)", input_type=int)
    frequency = get_choice(
        "How often is this bill due?",
        ["monthly", "quarterly", "annual"]
    )
    autopay = get_input("Is this on autopay? (y/n)", default="n", input_type=bool)
    category = get_choice(
        "Bill category:",
        ["housing", "utilities", "insurance", "subscriptions", "transportation", "other"],
        allow_cancel=True
    )

    # Ask which account or credit card pays for this
    print("\nHow do you pay this bill?")
    payment_sources = []

    # Add accounts
    for acc in config.accounts:
        payment_sources.append((acc.id, f"Account: {acc.name}", False))

    # Add credit cards
    for cc in config.credit_cards:
        payment_sources.append((cc.id, f"Credit Card: {cc.name}", True))

    if payment_sources:
        source_labels = [label for _, label, _ in payment_sources]
        selected_label = get_choice("Select payment source:", source_labels)
        selected_idx = source_labels.index(selected_label)
        payment_account, _, paid_by_credit = payment_sources[selected_idx]
    else:
        payment_account = None
        paid_by_credit = False

    bill_id = name.lower().replace(' ', '_')

    new_bill = Bill(
        id=bill_id,
        name=name,
        amount=amount,
        due_day=due_day,
        frequency=Frequency(frequency),
        autopay=autopay,
        payment_account=payment_account,
        category=category,
        paid_by_credit=paid_by_credit
    )

    config.bills.append(new_bill)
    save_config(config, config_path)

    autopay_str = " [AUTOPAY]" if autopay else ""
    print(f"\n✓ Added {name}: ${amount:,.2f} on day {due_day}{autopay_str}")
    print(f"✓ Configuration updated!\n")
    return True


def add_credit_card_to_config(config_path: str = "financial_config.json"):
    """Add a single credit card to existing config."""
    try:
        config = load_config(config_path)
    except FileNotFoundError:
        print(f"❌ Config file not found: {config_path}")
        return False
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False

    print_header("Add New Credit Card")
    print("Let's add a new credit card to your configuration.\n")

    name = get_input("Card name (e.g., 'AmEx Blue', 'Store Card')")
    balance = get_input("Current balance owed", input_type=float)
    credit_limit = get_input("Credit limit", input_type=float)

    print("\nWhat's the APR (Annual Percentage Rate)?")
    apr_percent = get_input("  APR as percentage (e.g., 18.99 for 18.99%)", input_type=float)
    apr = apr_percent / 100.0

    due_day = get_input("Payment due day of month (1-31)", input_type=int)
    minimum_payment = get_input("Minimum payment amount", input_type=float)
    statement_day = get_input(
        "Statement closing day (optional, 1-31)",
        required=False,
        input_type=int
    )

    card_id = name.lower().replace(' ', '_')

    new_card = CreditCard(
        id=card_id,
        name=name,
        balance=balance,
        credit_limit=credit_limit,
        apr=apr,
        due_day=due_day,
        minimum_payment=minimum_payment,
        statement_day=statement_day,
        payment_account=None
    )

    config.credit_cards.append(new_card)
    save_config(config, config_path)

    print(f"\n✓ Added {name}: ${balance:,.2f} / ${credit_limit:,.2f} @ {apr_percent:.2f}% APR")
    print(f"✓ Configuration updated!\n")
    return True


if __name__ == '__main__':
    output_file = sys.argv[1] if len(sys.argv) > 1 else "financial_config.json"
    run_setup_wizard(output_file)
