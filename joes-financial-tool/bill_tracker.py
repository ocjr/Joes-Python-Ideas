#!/usr/bin/env python3
"""
Bill payment tracking utilities.

This module provides functionality to mark bills as paid and track payment history,
which prevents duplicate payment recommendations in financial forecasts.
"""

from datetime import date
from config_loader import load_config, save_config
from setup_wizard import print_header, get_input


def mark_bill_paid(config_path: str = "financial_config.json") -> bool:
    """
    Mark a bill as paid for the current period.

    Displays a list of non-autopay bills and allows the user to mark one as paid
    with a specified payment date. The payment status is used to exclude the bill
    from upcoming cash flow forecasts.

    Parameters
    ----------
    config_path : str, optional
        Path to the configuration file (default: "financial_config.json")

    Returns
    -------
    bool
        True if a bill was successfully marked as paid, False otherwise

    Raises
    ------
    FileNotFoundError
        If the configuration file does not exist
    ValueError
        If the configuration file contains invalid data

    Examples
    --------
    >>> mark_bill_paid()
    Select bill to mark as paid:
      1. Netflix - $15.99 (due day 10) [⚠️  UNPAID]
      2. Electric - $120.00 (due day 15) [⚠️  UNPAID]
      0. Cancel
    Select bill (0-2): 1
    ✓ Marked Netflix as paid on 2025-10-09
    True

    Notes
    -----
    - Only non-autopay bills are shown for selection
    - Monthly bills are considered paid for the entire month once marked
    - Other frequency bills use simple date comparison
    """
    try:
        config = load_config(config_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ Error loading config: {e}")
        return False

    print_header("Mark Bill as Paid")

    # Filter to non-autopay bills only
    non_autopay_bills = [b for b in config.bills if not b.autopay]

    if not non_autopay_bills:
        print("\n❌ No non-autopay bills found in configuration.\n")
        return False

    print("\nSelect bill to mark as paid:\n")
    for i, bill in enumerate(non_autopay_bills, 1):
        paid_status = "✓ PAID" if bill.is_paid_for_date(date.today()) else "⚠️  UNPAID"
        print(
            f"  {i}. {bill.name} - ${bill.amount:.2f} (due day {bill.due_day}) [{paid_status}]"
        )
    print("  0. Cancel")

    while True:
        try:
            choice = input(f"\nSelect bill (0-{len(non_autopay_bills)}): ").strip()
            if not choice.isdigit():
                print("⚠️  Please enter a number")
                continue

            choice_num = int(choice)
            if choice_num == 0:
                return False
            if 1 <= choice_num <= len(non_autopay_bills):
                selected = non_autopay_bills[choice_num - 1]
                break

            print(f"⚠️  Please enter a number between 0 and {len(non_autopay_bills)}")
        except KeyboardInterrupt:
            print("\n")
            return False

    # Ask for payment date
    print(f"\nMarking {selected.name} as paid")
    use_today = get_input("Use today's date? (y/n)", default="y", input_type=bool)

    if use_today:
        payment_date = date.today()
    else:
        print("\nEnter payment date:")
        year = get_input("  Year", default=date.today().year, input_type=int)
        month = get_input("  Month (1-12)", input_type=int)
        day = get_input("  Day (1-31)", input_type=int)

        try:
            payment_date = date(year, month, day)
        except ValueError:
            print("  ⚠️  Invalid date, using today")
            payment_date = date.today()

    # Update bill's last_paid
    selected.last_paid = payment_date

    try:
        save_config(config, config_path)
    except (IOError, PermissionError) as e:
        print(f"❌ Error saving config: {e}")
        return False

    print(f"\n✓ Marked {selected.name} as paid on {payment_date.isoformat()}\n")
    return True
