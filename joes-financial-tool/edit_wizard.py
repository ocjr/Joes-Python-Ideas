#!/usr/bin/env python3
"""
Edit wizard for modifying existing financial configuration items.
"""

from config_loader import load_config, save_config
from setup_wizard import print_header, get_input, get_choice


def list_and_select_item(items: list, item_type: str, display_func):
    """Generic function to list items and let user select one."""
    if not items:
        print(f"\n❌ No {item_type}s found in configuration.\n")
        return None

    print(f"\nSelect {item_type} to edit:\n")
    for i, item in enumerate(items, 1):
        print(f"  {i}. {display_func(item)}")
    print(f"  0. Cancel")

    while True:
        try:
            choice = input(f"\nSelect {item_type} (0-{len(items)}): ").strip()
            if not choice.isdigit():
                print("⚠️  Please enter a number")
                continue

            choice_num = int(choice)
            if choice_num == 0:
                return None
            if 1 <= choice_num <= len(items):
                return items[choice_num - 1]

            print(f"⚠️  Please enter a number between 0 and {len(items)}")
        except KeyboardInterrupt:
            print("\n")
            return None


def edit_bill(config_path: str = "financial_config.json"):
    """Edit an existing bill."""
    try:
        config = load_config(config_path)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False

    print_header("Edit Bill")

    # Select bill to edit
    selected = list_and_select_item(
        config.bills,
        "bill",
        lambda b: f"{b.name} - ${b.amount:.2f} (due day {b.due_day})",
    )

    if not selected:
        return False

    print(f"\nEditing: {selected.name}\n")
    print("Press Enter to keep current value, or enter new value:\n")

    # Edit fields
    name = (
        get_input(f"Bill name", default=selected.name, required=False) or selected.name
    )
    amount = get_input(
        f"Amount", default=selected.amount, input_type=float, required=False
    )
    if amount is None:
        amount = selected.amount

    due_day = get_input(
        f"Due day (1-31)", default=selected.due_day, input_type=int, required=False
    )
    if due_day is None:
        due_day = selected.due_day

    # Payment source
    change_source = get_input(
        "Change payment source? (y/n)", default="n", input_type=bool
    )
    if change_source:
        payment_sources = []
        for acc in config.accounts:
            payment_sources.append((acc.id, f"Account: {acc.name}", False))
        for cc in config.credit_cards:
            payment_sources.append((cc.id, f"Credit Card: {cc.name}", True))

        if payment_sources:
            source_labels = [label for _, label, _ in payment_sources]
            selected_label = get_choice("Select payment source:", source_labels)
            selected_idx = source_labels.index(selected_label)
            selected.payment_account, _, selected.paid_by_credit = payment_sources[
                selected_idx
            ]

    # Update bill
    selected.name = name
    selected.amount = amount
    selected.due_day = due_day

    save_config(config, config_path)
    print(f"\n✓ Updated {name}\n")
    return True


def edit_account(config_path: str = "financial_config.json"):
    """Edit an existing account."""
    try:
        config = load_config(config_path)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False

    print_header("Edit Account")

    selected = list_and_select_item(
        config.accounts,
        "account",
        lambda a: f"{a.name} ({a.type.value}) - ${a.balance:,.2f}",
    )

    if not selected:
        return False

    print(f"\nEditing: {selected.name}\n")
    print("Press Enter to keep current value:\n")

    name = (
        get_input(f"Account name", default=selected.name, required=False)
        or selected.name
    )
    balance = get_input(
        f"Balance", default=selected.balance, input_type=float, required=False
    )
    if balance is None:
        balance = selected.balance

    min_balance = get_input(
        f"Minimum balance",
        default=selected.minimum_balance,
        input_type=float,
        required=False,
    )
    if min_balance is None:
        min_balance = selected.minimum_balance

    selected.name = name
    selected.balance = balance
    selected.minimum_balance = min_balance

    save_config(config, config_path)
    print(f"\n✓ Updated {name}\n")
    return True


def edit_credit_card(config_path: str = "financial_config.json"):
    """Edit an existing credit card."""
    try:
        config = load_config(config_path)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False

    print_header("Edit Credit Card")

    selected = list_and_select_item(
        config.credit_cards,
        "credit card",
        lambda cc: f"{cc.name} - ${cc.balance:,.2f} / ${cc.credit_limit:,.2f}",
    )

    if not selected:
        return False

    print(f"\nEditing: {selected.name}\n")
    print("Press Enter to keep current value:\n")

    name = (
        get_input(f"Card name", default=selected.name, required=False) or selected.name
    )
    balance = get_input(
        f"Balance", default=selected.balance, input_type=float, required=False
    )
    if balance is None:
        balance = selected.balance

    credit_limit = get_input(
        f"Credit limit", default=selected.credit_limit, input_type=float, required=False
    )
    if credit_limit is None:
        credit_limit = selected.credit_limit

    min_payment = get_input(
        f"Minimum payment",
        default=selected.minimum_payment,
        input_type=float,
        required=False,
    )
    if min_payment is None:
        min_payment = selected.minimum_payment

    selected.name = name
    selected.balance = balance
    selected.credit_limit = credit_limit
    selected.minimum_payment = min_payment

    save_config(config, config_path)
    print(f"\n✓ Updated {name}\n")
    return True


def edit_income(config_path: str = "financial_config.json"):
    """Edit an existing income source."""
    try:
        config = load_config(config_path)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False

    print_header("Edit Income Source")

    selected = list_and_select_item(
        config.income,
        "income source",
        lambda inc: f"{inc.source} - ${inc.amount:,.2f} {inc.frequency.value}",
    )

    if not selected:
        return False

    print(f"\nEditing: {selected.source}\n")
    print("Press Enter to keep current value:\n")

    source = (
        get_input(f"Source name", default=selected.source, required=False)
        or selected.source
    )
    amount = get_input(
        f"Amount", default=selected.amount, input_type=float, required=False
    )
    if amount is None:
        amount = selected.amount

    # Account splits
    change_splits = get_input(
        "Change account deposits/splits? (y/n)", default="n", input_type=bool
    )
    if change_splits:
        from models import IncomeSplit

        splits = []
        print("\nHow should this income be deposited?")

        if not config.accounts:
            print("⚠️  No accounts available for deposit")
        else:
            account_choices = [
                f"{acc.name} ({acc.type.value})" for acc in config.accounts
            ]

            # Ask if they want to split
            split_income = get_input(
                "Split across multiple accounts? (y/n)", default="n", input_type=bool
            )

            if split_income:
                print("\nSet up splits (last account will receive remainder):")
                total_allocated = 0.0

                for i, acc in enumerate(config.accounts[:-1]):  # All but last
                    split_amount = get_input(
                        f"  Amount to {acc.name}", input_type=float, required=False
                    )
                    if split_amount and split_amount > 0:
                        splits.append(
                            IncomeSplit(account_id=acc.id, amount=split_amount)
                        )
                        total_allocated += split_amount

                # Last account gets remainder
                if config.accounts:
                    last_acc = config.accounts[-1]
                    remainder = amount - total_allocated
                    print(f"  Remainder to {last_acc.name}: ${remainder:,.2f}")
                    splits.append(
                        IncomeSplit(account_id=last_acc.id, amount=None)
                    )  # None = remainder
            else:
                # Single account
                selected_label = get_choice(
                    "Deposit to which account?", account_choices
                )
                selected_idx = account_choices.index(selected_label)
                selected_account = config.accounts[selected_idx]
                splits = [IncomeSplit(account_id=selected_account.id, amount=None)]

            selected.splits = splits if splits else None
            selected.deposit_account = None  # Clear deprecated field

    selected.source = source
    selected.amount = amount

    save_config(config, config_path)
    print(f"\n✓ Updated {source}\n")
    return True
