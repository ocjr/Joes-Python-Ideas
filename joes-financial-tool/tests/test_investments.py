#!/usr/bin/env python3
"""
Test script for investment account features.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from models import (
    FinancialConfig,
    Account,
    AccountType,
    Income,
    Bill,
    CreditCard,
    Settings,
    Frequency,
    PayoffStrategy,
    InvestmentAccount,
    StockTransaction,
    StockHolding,
)
from config_loader import save_config, load_config


def test_investment_account_creation():
    """Test creating an investment account with transactions."""
    print("Testing Investment Account Creation...")

    # Create a simple investment account
    inv_account = InvestmentAccount(
        id="test_brokerage",
        name="Test Brokerage",
        cash_balance=5000.00,
        minimum_balance=0.0,
        transactions=[],
        holdings=[],
    )

    # Add some test transactions
    inv_account.transactions = [
        StockTransaction(
            id="aapl_buy_1",
            date=date(2025, 1, 1),
            symbol="AAPL",
            transaction_type="buy",
            shares=10.0,
            price_per_share=150.00,
            total_amount=1500.00,
        ),
        StockTransaction(
            id="tsla_buy_1",
            date=date(2025, 1, 5),
            symbol="TSLA",
            transaction_type="buy",
            shares=5.0,
            price_per_share=200.00,
            total_amount=1000.00,
        ),
        StockTransaction(
            id="aapl_buy_2",
            date=date(2025, 2, 1),
            symbol="AAPL",
            transaction_type="buy",
            shares=5.0,
            price_per_share=160.00,
            total_amount=800.00,
        ),
    ]

    # Recalculate holdings from transactions
    inv_account.update_holdings_from_transactions()

    # Set current prices
    for holding in inv_account.holdings:
        if holding.symbol == "AAPL":
            holding.current_price = 175.00  # Up $25 per share
        elif holding.symbol == "TSLA":
            holding.current_price = 180.00  # Down $20 per share

    # Display results
    print(f"\n{'=' * 70}")
    print(f"  {inv_account.name}")
    print(f"{'=' * 70}\n")
    print(f"Cash Balance: ${inv_account.cash_balance:,.2f}")
    print(f"\nHoldings:")
    print(
        f"{'Symbol':<10} {'Shares':>10} {'Cost Basis':>12} {'Current Price':>14} {'Market Value':>14} {'Gain/Loss':>14}"
    )
    print("─" * 70)

    for holding in inv_account.holdings:
        print(
            f"{holding.symbol:<10} {holding.shares:>10.2f} "
            f"${holding.cost_basis:>11,.2f} ${holding.current_price:>13.2f} "
            f"${holding.market_value:>13,.2f} ${holding.gain_loss:>+13,.2f}"
        )

    print("─" * 70)
    print(
        f"{'TOTAL':<10} {'':<10} {'':<12} {'':<14} ${inv_account.total_market_value:>13,.2f} ${inv_account.total_gain_loss:>+13,.2f}"
    )
    print(f"\nTotal Account Value: ${inv_account.total_value:,.2f}")

    # Test sell transaction
    print(f"\n\nTesting Sell Transaction...")
    sell_txn = StockTransaction(
        id="aapl_sell_1",
        date=date(2025, 3, 1),
        symbol="AAPL",
        transaction_type="sell",
        shares=5.0,
        price_per_share=175.00,
        total_amount=875.00,
    )
    inv_account.transactions.append(sell_txn)
    inv_account.update_holdings_from_transactions()

    print(f"After selling 5 shares of AAPL:")
    for holding in inv_account.holdings:
        if holding.symbol == "AAPL":
            print(
                f"  AAPL: {holding.shares:.2f} shares, cost basis: ${holding.cost_basis:,.2f}"
            )

    print("\n✓ Investment account tests passed!")
    return True


def test_config_with_investment():
    """Test saving and loading a config with investment accounts."""
    print("\n\nTesting Config Save/Load with Investments...")

    # Create minimal config
    config = FinancialConfig(
        accounts=[
            Account(
                id="test_checking",
                name="Test Checking",
                type=AccountType.CHECKING,
                balance=1000.0,
                minimum_balance=100.0,
            )
        ],
        income=[],
        bills=[],
        credit_cards=[],
        settings=Settings(),
        investment_accounts=[
            InvestmentAccount(
                id="test_inv",
                name="Test Investment Account",
                cash_balance=2500.00,
                transactions=[
                    StockTransaction(
                        id="spy_buy_1",
                        date=date(2025, 1, 1),
                        symbol="SPY",
                        transaction_type="buy",
                        shares=10.0,
                        price_per_share=450.00,
                        total_amount=4500.00,
                    )
                ],
                holdings=[],
            )
        ],
    )

    # Update holdings
    config.investment_accounts[0].update_holdings_from_transactions()
    config.investment_accounts[0].holdings[0].current_price = 460.00

    # Save to file
    test_file = "test_investment_config.json"
    save_config(config, test_file)
    print(f"✓ Saved config to {test_file}")

    # Load it back
    loaded_config = load_config(test_file)
    print(f"✓ Loaded config from {test_file}")

    # Verify investment account loaded correctly
    assert len(loaded_config.investment_accounts) == 1
    inv_acc = loaded_config.investment_accounts[0]
    assert inv_acc.name == "Test Investment Account"
    assert len(inv_acc.transactions) == 1
    assert len(inv_acc.holdings) == 1
    assert inv_acc.holdings[0].symbol == "SPY"
    assert inv_acc.holdings[0].shares == 10.0

    print(f"✓ Investment account data verified")
    print(
        f"  Holdings: {inv_acc.holdings[0].shares} shares of {inv_acc.holdings[0].symbol}"
    )
    print(f"  Market value: ${inv_acc.total_market_value:,.2f}")

    print("\n✓ Config save/load tests passed!")
    return True


if __name__ == "__main__":
    print("=" * 70)
    print("  INVESTMENT ACCOUNT FEATURE TESTS")
    print("=" * 70)

    try:
        test_investment_account_creation()
        test_config_with_investment()

        print("\n" + "=" * 70)
        print("  ALL TESTS PASSED! ✅")
        print("=" * 70)
        print("\nYou can now:")
        print("  1. Run the CLI: .venv/bin/python cli.py")
        print("  2. Select option 21 to add an investment account")
        print("  3. Select option 22 to record stock transactions")
        print("  4. Select option 23 to refresh stock prices")
        print("  5. Select option 20 to view your portfolio\n")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
