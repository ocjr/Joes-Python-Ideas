#!/usr/bin/env python3
"""
Configuration loader for financial data.

This module handles loading and saving financial configurations from/to JSON files.
It provides serialization and deserialization of all financial data models.
"""

import json
from pathlib import Path
from typing import Union
from models import (
    FinancialConfig,
    Account,
    Income,
    Bill,
    CreditCard,
    Settings,
    ManualPayment,
    RecurringExpense,
    InvestmentAccount,
    StockTransaction,
    StockHolding,
    InvestmentSimulation,
)


def load_config(config_path: Union[str, Path]) -> FinancialConfig:
    """
    Load financial configuration from JSON file.

    Parses a JSON configuration file and constructs a complete FinancialConfig
    object with all accounts, income sources, bills, credit cards, and settings.

    Parameters
    ----------
    config_path : Union[str, Path]
        Path to the JSON configuration file

    Returns
    -------
    FinancialConfig
        Complete financial configuration object with all entities loaded

    Raises
    ------
    FileNotFoundError
        If the configuration file does not exist
    json.JSONDecodeError
        If the file contains invalid JSON
    KeyError
        If required fields are missing from the configuration
    ValueError
        If configuration values are invalid (e.g., invalid enums, dates)

    Examples
    --------
    >>> config = load_config("financial_config.json")
    >>> print(f"Loaded {len(config.accounts)} accounts")
    Loaded 3 accounts

    Notes
    -----
    The function automatically converts string representations of enums and dates
    to their proper types through the model __post_init__ methods.
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid JSON in config file: {e.msg}", e.doc, e.pos
        )

    try:
        # Parse accounts
        accounts = [Account(**acc) for acc in data.get("accounts", [])]

        # Parse income sources
        income = [Income(**inc) for inc in data.get("income", [])]

        # Parse bills
        bills = [Bill(**bill) for bill in data.get("bills", [])]

        # Parse credit cards
        credit_cards = [CreditCard(**cc) for cc in data.get("credit_cards", [])]

        # Parse manual payments
        manual_payments = [
            ManualPayment(**mp) for mp in data.get("manual_payments", [])
        ]

        # Parse recurring expenses
        recurring_expenses = [
            RecurringExpense(**exp) for exp in data.get("recurring_expenses", [])
        ]

        # Parse investment accounts
        investment_accounts = [
            InvestmentAccount(**inv_acc) for inv_acc in data.get("investment_accounts", [])
        ]

        # Parse simulations
        simulations = [
            InvestmentSimulation(**sim) for sim in data.get("simulations", [])
        ]

        # Parse settings
        settings_data = data.get("settings", {})
        settings = Settings(**settings_data)

        return FinancialConfig(
            accounts=accounts,
            income=income,
            bills=bills,
            credit_cards=credit_cards,
            settings=settings,
            manual_payments=manual_payments,
            recurring_expenses=recurring_expenses,
            investment_accounts=investment_accounts,
            simulations=simulations,
        )
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError(f"Error parsing configuration: {e}") from e


def save_config(config: FinancialConfig, config_path: Union[str, Path]) -> None:
    """
    Save financial configuration to JSON file.

    Serializes a FinancialConfig object to JSON format and writes it to a file.
    All enum values and dates are converted to their string representations.

    Parameters
    ----------
    config : FinancialConfig
        Complete financial configuration to save
    config_path : Union[str, Path]
        Destination path for the JSON configuration file

    Raises
    ------
    IOError
        If the file cannot be written
    PermissionError
        If there are insufficient permissions to write the file

    Examples
    --------
    >>> config = FinancialConfig(accounts=[], income=[], bills=[], credit_cards=[], settings=Settings())
    >>> save_config(config, "financial_config.json")

    Notes
    -----
    The file is written with 2-space indentation for readability. Existing files
    are overwritten without backup. Use create_backup() from config_manager before
    calling this function if you need to preserve the previous version.
    """
    config_path = Path(config_path)

    data = {
        "accounts": [
            {
                "id": acc.id,
                "name": acc.name,
                "type": acc.type.value,
                "balance": acc.balance,
                "minimum_balance": acc.minimum_balance,
            }
            for acc in config.accounts
        ],
        "income": [
            {
                "id": inc.id,
                "source": inc.source,
                "amount": inc.amount,
                "frequency": inc.frequency.value,
                "next_date": inc.next_date.isoformat(),
                "deposit_account": inc.deposit_account,
                "splits": (
                    [
                        {"account_id": split.account_id, "amount": split.amount}
                        for split in inc.splits
                    ]
                    if inc.splits
                    else None
                ),
            }
            for inc in config.income
        ],
        "bills": [
            {
                "id": bill.id,
                "name": bill.name,
                "amount": bill.amount,
                "due_day": bill.due_day,
                "frequency": bill.frequency.value,
                "autopay": bill.autopay,
                "payment_account": bill.payment_account,
                "category": bill.category,
                "paid_by_credit": bill.paid_by_credit,
                "require_checking": bill.require_checking,
                "last_paid": bill.last_paid.isoformat() if bill.last_paid else None,
            }
            for bill in config.bills
        ],
        "credit_cards": [
            {
                "id": cc.id,
                "name": cc.name,
                "balance": cc.balance,
                "credit_limit": cc.credit_limit,
                "apr": cc.apr,
                "due_day": cc.due_day,
                "minimum_payment": cc.minimum_payment,
                "statement_day": cc.statement_day,
                "payment_account": cc.payment_account,
                "primary_for_purchases": cc.primary_for_purchases,
            }
            for cc in config.credit_cards
        ],
        "manual_payments": [
            {
                "id": mp.id,
                "name": mp.name,
                "amount": mp.amount,
                "payment_date": mp.payment_date.isoformat(),
                "credit_card_id": mp.credit_card_id,
                "payment_account": mp.payment_account,
            }
            for mp in config.manual_payments
        ],
        "recurring_expenses": [
            {
                "id": exp.id,
                "name": exp.name,
                "amount": exp.amount,
                "frequency": exp.frequency.value,
                "payment_account": exp.payment_account,
                "paid_by_credit": exp.paid_by_credit,
                "category": exp.category,
                "next_date": exp.next_date.isoformat() if exp.next_date else None,
            }
            for exp in config.recurring_expenses
        ],
        "investment_accounts": [
            {
                "id": inv_acc.id,
                "name": inv_acc.name,
                "cash_balance": inv_acc.cash_balance,
                "minimum_balance": inv_acc.minimum_balance,
                "default_commission": inv_acc.default_commission,
                "transactions": [
                    {
                        "id": txn.id,
                        "date": txn.date.isoformat(),
                        "symbol": txn.symbol,
                        "transaction_type": txn.transaction_type,
                        "shares": txn.shares,
                        "price_per_share": txn.price_per_share,
                        "total_amount": txn.total_amount,
                        "commission": txn.commission,
                        "settlement_date": txn.settlement_date.isoformat() if txn.settlement_date else None,
                        "notes": txn.notes,
                    }
                    for txn in inv_acc.transactions
                ],
                "holdings": [
                    {
                        "symbol": holding.symbol,
                        "shares": holding.shares,
                        "cost_basis": holding.cost_basis,
                        "current_price": holding.current_price,
                    }
                    for holding in inv_acc.holdings
                ],
            }
            for inv_acc in config.investment_accounts
        ],
        "simulations": [
            {
                "id": sim.id,
                "name": sim.name,
                "enabled": sim.enabled,
                "current_age": sim.current_age,
                "target_ages": sim.target_ages,
                "strategy_type": sim.strategy_type,
                "hold_days": sim.hold_days,
                "liquidation_day": sim.liquidation_day,
                "income_source_ids": sim.income_source_ids,
                "ticker": sim.ticker,
                "initial_balance": sim.initial_balance,
                "expected_annual_return": sim.expected_annual_return,
                "annual_volatility": sim.annual_volatility,
                "annual_dividend_yield": sim.annual_dividend_yield,
                "expense_ratio": sim.expense_ratio,
                "short_term_cap_gains_rate": sim.short_term_cap_gains_rate,
                "long_term_cap_gains_rate": sim.long_term_cap_gains_rate,
                "dividend_tax_rate": sim.dividend_tax_rate,
                "num_simulations": sim.num_simulations,
                "random_seed": sim.random_seed,
                "investment_account_id": sim.investment_account_id,
            }
            for sim in config.simulations
        ],
        "settings": {
            "emergency_fund_target": config.settings.emergency_fund_target,
            "planning_horizon_days": config.settings.planning_horizon_days,
            "priority": config.settings.priority.value,
        },
    }

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except (IOError, PermissionError) as e:
        raise IOError(f"Failed to save configuration to {config_path}: {e}") from e
