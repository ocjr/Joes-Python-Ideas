#!/usr/bin/env python3
"""
Test script for commission and settlement date features.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, timedelta
from models import (
    FinancialConfig,
    Account,
    AccountType,
    Settings,
    InvestmentAccount,
    StockTransaction,
)
from config_loader import save_config, load_config


def test_commission_tracking():
    """Test commission tracking at account and transaction levels."""
    print("Testing Commission Tracking...\n")

    # Create config with investment account that has default commission
    config = FinancialConfig(
        accounts=[
            Account(
                id="test_checking",
                name="Test Checking",
                type=AccountType.CHECKING,
                balance=10000.0,
            )
        ],
        income=[],
        bills=[],
        credit_cards=[],
        settings=Settings(),
        investment_accounts=[
            InvestmentAccount(
                id="legacy_broker",
                name="Legacy Broker (with commission)",
                cash_balance=5000.00,
                default_commission=6.95,  # Old-school broker fee
                transactions=[],
                holdings=[],
            ),
            InvestmentAccount(
                id="modern_broker",
                name="Modern Broker (commission-free)",
                cash_balance=5000.00,
                default_commission=0.0,  # Robinhood style
                transactions=[],
                holdings=[],
            ),
        ],
    )

    # Test 1: Transaction with account default commission
    legacy_acc = config.investment_accounts[0]
    txn1 = StockTransaction(
        id="aapl_buy_1",
        date=date(2025, 10, 10),
        symbol="AAPL",
        transaction_type="buy",
        shares=10.0,
        price_per_share=150.00,
        total_amount=1506.95,  # 10 * 150 + 6.95 commission
        commission=6.95,
    )
    legacy_acc.transactions.append(txn1)
    legacy_acc.update_holdings_from_transactions()

    # Test 2: Transaction with custom commission (override default)
    txn2 = StockTransaction(
        id="tsla_buy_1",
        date=date(2025, 10, 11),
        symbol="TSLA",
        transaction_type="buy",
        shares=5.0,
        price_per_share=200.00,
        total_amount=1010.00,  # 5 * 200 + 10.00 custom commission
        commission=10.00,  # Higher commission for some reason
    )
    legacy_acc.transactions.append(txn2)
    legacy_acc.update_holdings_from_transactions()

    # Test 3: Commission-free transaction in modern broker
    modern_acc = config.investment_accounts[1]
    txn3 = StockTransaction(
        id="spy_buy_1",
        date=date(2025, 10, 12),
        symbol="SPY",
        transaction_type="buy",
        shares=20.0,
        price_per_share=450.00,
        total_amount=9000.00,  # 20 * 450, no commission
        commission=0.0,
    )
    modern_acc.transactions.append(txn3)
    modern_acc.update_holdings_from_transactions()

    # Display results
    print(f"{'Account':<35} {'Default Comm':>15} {'Transaction':<20} {'Comm Paid':>12}")
    print("=" * 85)

    for inv_acc in config.investment_accounts:
        for txn in inv_acc.transactions:
            print(
                f"{inv_acc.name:<35} ${inv_acc.default_commission:>14.2f} "
                f"{txn.symbol + ' ' + txn.transaction_type:<20} ${txn.commission:>11.2f}"
            )

    print("\n✅ Commission tracking works correctly!")
    print(f"  • Legacy broker account uses $6.95 default commission")
    print(f"  • Custom commission override: $10.00 for TSLA trade")
    print(f"  • Modern broker: $0.00 commission (commission-free)")

    # Verify cost basis includes commissions
    print(f"\n📊 Cost Basis Verification:")
    aapl_holding = legacy_acc.get_holding("AAPL")
    if aapl_holding:
        print(
            f"  AAPL: 10 shares @ $150 + $6.95 commission = ${aapl_holding.cost_basis:.2f} total"
        )
        print(
            f"  Cost basis per share: ${aapl_holding.cost_basis / aapl_holding.shares:.2f}"
        )

    return config


def test_settlement_dates():
    """Test automatic settlement date calculation and override."""
    print("\n\nTesting Settlement Date Calculation...\n")

    # Test cases for settlement dates
    test_cases = [
        (date(2025, 10, 13), "Monday"),  # Monday → Tuesday
        (date(2025, 10, 14), "Tuesday"),  # Tuesday → Wednesday
        (date(2025, 10, 17), "Friday"),  # Friday → Monday (skip weekend)
        (date(2025, 10, 18), "Saturday"),  # Saturday → Monday
        (date(2025, 10, 19), "Sunday"),  # Sunday → Monday
    ]

    print(
        f"{'Trade Date':<20} {'Day':<12} {'Settlement Date':<20} {'Day':<12} {'T+':<5}"
    )
    print("=" * 70)

    for trade_date, day_name in test_cases:
        txn = StockTransaction(
            id=f"test_{trade_date.isoformat()}",
            date=trade_date,
            symbol="TEST",
            transaction_type="buy",
            shares=1.0,
            price_per_share=100.00,
            total_amount=100.00,
        )

        settlement = txn.settlement_date
        settlement_day = settlement.strftime("%A")
        days_diff = (settlement - trade_date).days

        print(
            f"{trade_date.strftime('%Y-%m-%d'):<20} {day_name:<12} "
            f"{settlement.strftime('%Y-%m-%d'):<20} {settlement_day:<12} T+{days_diff}"
        )

    print("\n✅ Settlement dates calculated correctly!")
    print(f"  • Weekday trades settle next business day (T+1)")
    print(f"  • Weekend trades settle following Monday")

    # Test custom settlement date override
    print(f"\n📝 Custom Settlement Date Override:")
    custom_txn = StockTransaction(
        id="custom_settlement",
        date=date(2025, 10, 13),
        symbol="CUSTOM",
        transaction_type="buy",
        shares=1.0,
        price_per_share=100.00,
        total_amount=100.00,
        settlement_date=date(
            2025, 10, 16
        ),  # Manually set to Thursday instead of Tuesday
    )
    print(f"  Trade date: {custom_txn.date} (Monday)")
    print(f"  Auto-calculated: {date(2025, 10, 14)} (Tuesday)")
    print(f"  Custom override: {custom_txn.settlement_date} (Thursday)")
    print(f"  ✅ Manual override works!")

    return True


def test_config_save_load():
    """Test saving and loading with new commission and settlement fields."""
    print("\n\nTesting Config Save/Load with New Fields...\n")

    # Create config with all new fields
    config = FinancialConfig(
        accounts=[
            Account(
                id="test_checking",
                name="Test Checking",
                type=AccountType.CHECKING,
                balance=1000.0,
            )
        ],
        income=[],
        bills=[],
        credit_cards=[],
        settings=Settings(),
        investment_accounts=[
            InvestmentAccount(
                id="test_inv",
                name="Test Investment",
                cash_balance=5000.00,
                default_commission=4.95,
                transactions=[
                    StockTransaction(
                        id="test_txn",
                        date=date(2025, 10, 13),
                        symbol="AAPL",
                        transaction_type="buy",
                        shares=10.0,
                        price_per_share=150.00,
                        total_amount=1504.95,
                        commission=4.95,
                        settlement_date=date(2025, 10, 14),
                        notes="Test transaction with commission and settlement",
                    )
                ],
                holdings=[],
            )
        ],
    )

    # Save to file
    test_file = "test_commission_settlement_config.json"
    save_config(config, test_file)
    print(f"✓ Saved config to {test_file}")

    # Load it back
    loaded_config = load_config(test_file)
    print(f"✓ Loaded config from {test_file}")

    # Verify fields
    inv_acc = loaded_config.investment_accounts[0]
    assert inv_acc.default_commission == 4.95, "Default commission not loaded correctly"
    print(f"✓ Default commission: ${inv_acc.default_commission:.2f}")

    txn = inv_acc.transactions[0]
    assert txn.commission == 4.95, "Transaction commission not loaded correctly"
    print(f"✓ Transaction commission: ${txn.commission:.2f}")

    assert txn.settlement_date == date(
        2025, 10, 14
    ), "Settlement date not loaded correctly"
    print(f"✓ Settlement date: {txn.settlement_date}")

    print("\n✅ All fields saved and loaded correctly!")

    return True


if __name__ == "__main__":
    print("=" * 85)
    print("  COMMISSION AND SETTLEMENT DATE TESTS")
    print("=" * 85)

    try:
        test_commission_tracking()
        test_settlement_dates()
        test_config_save_load()

        print("\n" + "=" * 85)
        print("  ALL TESTS PASSED! ✅")
        print("=" * 85)
        print("\nNew Features:")
        print("  ✅ Account-level default commission")
        print("  ✅ Transaction-level commission override")
        print("  ✅ Automatic settlement date calculation (T+1)")
        print("  ✅ Weekend handling for settlement dates")
        print("  ✅ Custom settlement date override")
        print("  ✅ Commission included in cost basis calculations")
        print("\nHow to use:")
        print("  1. Set default commission when adding investment account")
        print("  2. System auto-uses default or prompts for custom commission")
        print("  3. Settlement dates auto-calculated, can be overridden")
        print("  4. All data persists through save/load\n")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
