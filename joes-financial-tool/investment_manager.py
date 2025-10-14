#!/usr/bin/env python3
"""
Investment account management functions.
"""

from datetime import date
from typing import Optional
from models import InvestmentAccount, StockTransaction
from config_loader import load_config, save_config


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
                return float(response.replace(",", ""))
            elif input_type == int:
                return int(response)
            elif input_type == bool:
                response_lower = response.lower()
                if response_lower in ["y", "yes"]:
                    return True
                elif response_lower in ["n", "no"]:
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


def add_manual_position(config_path: str = "financial_config.json"):
    """Add a stock position manually without transaction date (for legacy holdings)."""
    try:
        config = load_config(config_path)
    except FileNotFoundError:
        print(f"❌ Config file not found: {config_path}")
        return False
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False

    if not config.investment_accounts:
        print(
            "❌ No investment accounts found. Please add an investment account first.\n"
        )
        return False

    print_header("Add Manual Position")
    print("Add a stock position without transaction history.")
    print("Use this for legacy holdings where you don't have exact purchase dates.\n")

    # Select investment account
    account_labels = [
        f"{acc.name} (Cash: ${acc.cash_balance:,.2f})"
        for acc in config.investment_accounts
    ]
    selected_label = get_choice("Which investment account?", account_labels)
    selected_idx = account_labels.index(selected_label)
    investment_account = config.investment_accounts[selected_idx]

    # Stock symbol
    symbol = get_input("Stock ticker symbol (e.g., AAPL, TSLA)").upper()

    # Check if position already exists
    existing = investment_account.get_holding(symbol)
    if existing and existing.shares > 0:
        print(f"\n⚠️  You already have {existing.shares:.4f} shares of {symbol}")
        print(f"   Current cost basis: ${existing.cost_basis:,.2f}")
        if not get_input(
            "Add to existing position? (y/n)", default="n", input_type=bool
        ):
            return False

    # Position details
    shares = get_input("Number of shares", input_type=float)
    cost_per_share = get_input(
        "Cost basis per share (original purchase price)", input_type=float
    )

    # Calculate total cost basis
    total_cost_basis = shares * cost_per_share
    print(f"\nTotal cost basis: ${total_cost_basis:,.2f}")

    # Optional: current price
    current_price = get_input(
        "Current price per share (optional, for P&L tracking)",
        required=False,
        input_type=float,
    )

    notes = get_input(
        "Notes (optional, e.g., 'Legacy position', 'Inherited shares')",
        required=False,
    )

    # Add or update the holding directly
    if existing:
        # Add to existing position
        existing.shares += shares
        existing.cost_basis += total_cost_basis
        if current_price:
            existing.current_price = current_price
        print(f"\n✓ Added {shares} shares to existing position")
        print(f"✓ New total: {existing.shares:.4f} shares")
        print(f"✓ New total cost basis: ${existing.cost_basis:,.2f}")
    else:
        # Create new holding
        from models import StockHolding

        new_holding = StockHolding(
            symbol=symbol,
            shares=shares,
            cost_basis=total_cost_basis,
            current_price=current_price or 0.0,
        )
        investment_account.holdings.append(new_holding)
        print(f"\n✓ Added position: {shares:.4f} shares of {symbol}")
        print(f"✓ Cost basis: ${total_cost_basis:,.2f}")

    # Optionally create a placeholder transaction for record-keeping
    if get_input(
        "\nCreate placeholder transaction record? (y/n)", default="y", input_type=bool
    ):
        from datetime import date

        placeholder_date = date(1900, 1, 1)  # Placeholder date for manual entries

        txn_id = f"{symbol}_manual_{date.today().isoformat()}"
        transaction = StockTransaction(
            id=txn_id,
            date=placeholder_date,
            symbol=symbol,
            transaction_type="buy",
            shares=shares,
            price_per_share=cost_per_share,
            total_amount=total_cost_basis,
            notes=f"Manual entry - {notes}" if notes else "Manual entry - date unknown",
        )
        investment_account.transactions.append(transaction)

    # Save config
    save_config(config, config_path)

    print(f"\n✓ Configuration updated!\n")

    # Show position summary
    holding = investment_account.get_holding(symbol)
    if holding:
        avg_cost = holding.cost_basis / holding.shares if holding.shares > 0 else 0
        print(f"📊 Position Summary for {symbol}:")
        print(f"   Shares: {holding.shares:.4f}")
        print(f"   Total cost basis: ${holding.cost_basis:,.2f}")
        print(f"   Avg cost basis per share: ${avg_cost:.2f}")
        if holding.current_price > 0:
            print(f"   Current price: ${holding.current_price:.2f}")
            print(f"   Market value: ${holding.market_value:,.2f}")
            print(
                f"   Unrealized gain/loss: ${holding.gain_loss:+,.2f} ({holding.gain_loss_pct:+.2f}%)"
            )
        else:
            print(f"   Current price: Not set (use option 23 to refresh)")
        print()

    return True


def record_stock_transaction(config_path: str = "financial_config.json"):
    """Record a stock buy, sell, or dividend transaction with specific date."""
    try:
        config = load_config(config_path)
    except FileNotFoundError:
        print(f"❌ Config file not found: {config_path}")
        return False
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False

    if not config.investment_accounts:
        print(
            "❌ No investment accounts found. Please add an investment account first.\n"
        )
        return False

    print_header("Record Stock Transaction")
    print("Record a stock buy, sell, or dividend with specific transaction date.\n")

    # Select investment account
    account_labels = [
        f"{acc.name} (Cash: ${acc.cash_balance:,.2f})"
        for acc in config.investment_accounts
    ]
    selected_label = get_choice("Which investment account?", account_labels)
    selected_idx = account_labels.index(selected_label)
    investment_account = config.investment_accounts[selected_idx]

    # Transaction type
    txn_type = get_choice("Transaction type:", ["buy", "sell", "dividend"])

    # Stock symbol
    symbol = get_input("Stock ticker symbol (e.g., AAPL, TSLA)").upper()

    # Transaction date
    print("\nTransaction date:")
    year = get_input("  Year", default=date.today().year, input_type=int)
    month = get_input("  Month (1-12)", default=date.today().month, input_type=int)
    day = get_input("  Day (1-31)", default=date.today().day, input_type=int)

    try:
        txn_date = date(year, month, day)
    except ValueError:
        print("  ⚠️  Invalid date, using today")
        txn_date = date.today()

    if txn_type == "dividend":
        # Dividend payment
        amount = get_input("Dividend amount received", input_type=float)
        shares = 0.0
        price_per_share = 0.0
        total_amount = amount

        # Add to cash balance
        investment_account.cash_balance += amount
    else:
        # Buy or sell
        shares = get_input("Number of shares", input_type=float)
        price_per_share = get_input(
            "Price per share (execution price)", input_type=float
        )

        # Calculate subtotal
        subtotal = shares * price_per_share
        print(f"\nSubtotal: ${subtotal:,.2f}")

        # Commission handling
        default_comm = investment_account.default_commission
        if default_comm > 0:
            print(f"Account default commission: ${default_comm:.2f}")
            use_default = get_input(
                "Use default commission? (y/n)", default="y", input_type=bool
            )
            if use_default:
                commission = default_comm
            else:
                commission = (
                    get_input(
                        "Custom commission for this trade",
                        default=0.0,
                        input_type=float,
                        required=False,
                    )
                    or 0.0
                )
        else:
            commission = (
                get_input(
                    "Commission/fees (if any)",
                    default=0.0,
                    input_type=float,
                    required=False,
                )
                or 0.0
            )

        if commission > 0:
            print(f"Commission: ${commission:.2f}")

        total_amount = subtotal + commission

        if txn_type == "buy":
            print(f"Total cost (including commission): ${total_amount:,.2f}")
            print(f"Cost basis per share: ${total_amount / shares:.2f}")
            # Deduct from cash balance
            if investment_account.cash_balance < total_amount:
                print(
                    f"\n⚠️  Warning: Insufficient cash (${investment_account.cash_balance:,.2f}) for purchase (${total_amount:,.2f})"
                )
                if not get_input("Record anyway? (y/n)", default="n", input_type=bool):
                    return False
            investment_account.cash_balance -= total_amount
        else:  # sell
            print(f"Total proceeds (after commission): ${total_amount:,.2f}")
            # Add to cash balance
            investment_account.cash_balance += total_amount

    notes = get_input(
        "Notes (optional, e.g., 'Quarterly dividend', 'Sold for tax loss')",
        required=False,
    )

    # Create transaction ID
    txn_id = f"{symbol}_{txn_type}_{txn_date.isoformat()}"

    # Settlement date (auto-calculated but allow override)
    print(f"\nTransaction date: {txn_date.strftime('%Y-%m-%d (%A)')}")

    # Create transaction to get auto-calculated settlement date
    temp_transaction = StockTransaction(
        id=txn_id,
        date=txn_date,
        symbol=symbol,
        transaction_type=txn_type,
        shares=shares,
        price_per_share=price_per_share,
        total_amount=total_amount,
        commission=commission if txn_type != "dividend" else 0.0,
        notes=notes,
    )

    auto_settlement = temp_transaction.settlement_date
    if auto_settlement:
        print(
            f"Auto-calculated settlement: {auto_settlement.strftime('%Y-%m-%d (%A)')}"
        )
        custom_settlement = get_input(
            "Use different settlement date? (leave blank for auto)", required=False
        )
        if custom_settlement:
            try:
                year, month, day = custom_settlement.split("-")
                settlement_date = date(int(year), int(month), int(day))
            except:
                print("Invalid date format, using auto-calculated settlement date")
                settlement_date = auto_settlement
        else:
            settlement_date = auto_settlement
    else:
        settlement_date = None

    # Create final transaction
    transaction = StockTransaction(
        id=txn_id,
        date=txn_date,
        symbol=symbol,
        transaction_type=txn_type,
        shares=shares,
        price_per_share=price_per_share,
        total_amount=total_amount,
        commission=commission if txn_type != "dividend" else 0.0,
        settlement_date=settlement_date,
        notes=notes,
    )

    # Add transaction and recalculate holdings
    investment_account.transactions.append(transaction)
    investment_account.update_holdings_from_transactions()

    # Save config
    save_config(config, config_path)

    print(
        f"\n✓ Recorded {txn_type}: {shares} shares of {symbol} @ ${price_per_share:.2f}"
    )
    if commission > 0:
        print(f"  Commission: ${commission:.2f}")
    if settlement_date:
        print(f"  Settlement: {settlement_date.strftime('%Y-%m-%d (%A)')}")
    print(f"✓ New cash balance: ${investment_account.cash_balance:,.2f}")
    print(f"✓ Configuration updated!\n")

    # Show updated holdings for this symbol
    holding = investment_account.get_holding(symbol)
    if holding and holding.shares > 0:
        print(f"📊 Current position in {symbol}:")
        print(f"   Shares: {holding.shares:.4f}")
        print(f"   Cost basis: ${holding.cost_basis:,.2f}")
        print(f"   Avg cost/share: ${holding.cost_basis/holding.shares:.2f}\n")

    return True


def refresh_stock_prices(config_path: str = "financial_config.json"):
    """Update current prices for all stock holdings."""
    try:
        config = load_config(config_path)
    except FileNotFoundError:
        print(f"❌ Config file not found: {config_path}")
        return False
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False

    if not config.investment_accounts:
        print("❌ No investment accounts found.\n")
        return False

    print_header("Refresh Stock Prices")
    print("Update current market prices for your holdings.\n")

    # Check if there are any holdings
    total_holdings = sum(len(acc.holdings) for acc in config.investment_accounts)

    if total_holdings == 0:
        print("📊 No stock holdings found. Record some transactions first!\n")
        return False

    # Go through each investment account
    for inv_acc in config.investment_accounts:
        if not inv_acc.holdings:
            continue

        print(f"\n{'─' * 70}")
        print(f"  {inv_acc.name}")
        print(f"{'─' * 70}\n")

        for holding in inv_acc.holdings:
            current_price = holding.current_price
            current_str = f"${current_price:.2f}" if current_price > 0 else "not set"

            new_price = get_input(
                f"{holding.symbol} - {holding.shares:.4f} shares (current: {current_str})",
                default=current_price if current_price > 0 else None,
                input_type=float,
                required=False,
            )

            if new_price and new_price > 0:
                holding.current_price = new_price
                print(f"   Updated {holding.symbol} to ${new_price:.2f}")

    # Save updated config
    save_config(config, config_path)
    print(f"\n✓ Stock prices updated!\n")

    return True


def view_investment_portfolio(config_path: str = "financial_config.json"):
    """View detailed investment portfolio information."""
    try:
        config = load_config(config_path)
    except FileNotFoundError:
        print(f"❌ Config file not found: {config_path}")
        return False
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False

    if not config.investment_accounts:
        print("❌ No investment accounts found.\n")
        return False

    print_header("Investment Portfolio")

    total_cash = 0.0
    total_market_value = 0.0
    total_cost_basis = 0.0

    for inv_acc in config.investment_accounts:
        print(f"\n{'─' * 70}")
        print(f"  {inv_acc.name}")
        print(f"{'─' * 70}\n")

        print(f"💵 Cash Balance: ${inv_acc.cash_balance:,.2f}\n")

        if inv_acc.holdings:
            print(
                f"{'Symbol':<10} {'Shares':>12} {'Avg Cost':>12} {'Current':>12} {'Value':>14} {'Unrealized G/L':>16}"
            )
            print("─" * 78)

            for holding in inv_acc.holdings:
                avg_cost = (
                    holding.cost_basis / holding.shares if holding.shares > 0 else 0
                )
                gain_loss_str = f"${holding.gain_loss:+,.2f}"
                if holding.current_price > 0:
                    gain_loss_str += f" ({holding.gain_loss_pct:+.2f}%)"
                else:
                    gain_loss_str = "Not set"

                print(
                    f"{holding.symbol:<10} {holding.shares:>12.4f} "
                    f"${avg_cost:>11.2f} ${holding.current_price:>11.2f} "
                    f"${holding.market_value:>13,.2f} {gain_loss_str:>16}"
                )

            print("─" * 78)
            print(
                f"{'TOTAL':<10} {'':<12} {'':<12} {'':<12} "
                f"${inv_acc.total_market_value:>13,.2f} "
                f"${inv_acc.total_gain_loss:>+15,.2f}"
            )

            total_cash += inv_acc.cash_balance
            total_market_value += inv_acc.total_market_value
            total_cost_basis += inv_acc.total_cost_basis
        else:
            print(
                "📊 No stock holdings yet. Record some transactions to get started!\n"
            )

    # Grand total across all accounts
    if len(config.investment_accounts) > 1:
        print(f"\n{'═' * 78}")
        print(f"  ALL INVESTMENT ACCOUNTS - PORTFOLIO SUMMARY")
        print(f"{'═' * 78}\n")
        grand_total = total_cash + total_market_value
        total_gain_loss = total_market_value - total_cost_basis
        print(f"💵 Total Cash: ${total_cash:,.2f}")
        print(f"📊 Total Cost Basis: ${total_cost_basis:,.2f}")
        print(f"📈 Total Market Value: ${total_market_value:,.2f}")
        print(f"💰 Total Account Value: ${grand_total:,.2f}")
        print(f"📊 Total Unrealized Gain/Loss: ${total_gain_loss:+,.2f}")
        if total_cost_basis > 0:
            total_gain_loss_pct = (total_gain_loss / total_cost_basis) * 100
            print(f"📊 Total Return: {total_gain_loss_pct:+.2f}%")

    print()
    return True


if __name__ == "__main__":
    # For testing
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "record":
            record_stock_transaction()
        elif sys.argv[1] == "refresh":
            refresh_stock_prices()
        elif sys.argv[1] == "view":
            view_investment_portfolio()
    else:
        print("Usage: python investment_manager.py [record|refresh|view]")
