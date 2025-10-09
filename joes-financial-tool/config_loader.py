"""
Configuration loader for financial data.
"""

import json
from pathlib import Path
from typing import Union
from models import (
    FinancialConfig, Account, Income, Bill, CreditCard, Settings,
    AccountType, Frequency, PayoffStrategy
)


def load_config(config_path: Union[str, Path]) -> FinancialConfig:
    """Load financial configuration from JSON file."""
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r') as f:
        data = json.load(f)

    # Parse accounts
    accounts = [Account(**acc) for acc in data.get('accounts', [])]

    # Parse income sources
    income = [Income(**inc) for inc in data.get('income', [])]

    # Parse bills
    bills = [Bill(**bill) for bill in data.get('bills', [])]

    # Parse credit cards
    credit_cards = [CreditCard(**cc) for cc in data.get('credit_cards', [])]

    # Parse settings
    settings_data = data.get('settings', {})
    settings = Settings(**settings_data)

    return FinancialConfig(
        accounts=accounts,
        income=income,
        bills=bills,
        credit_cards=credit_cards,
        settings=settings
    )


def save_config(config: FinancialConfig, config_path: Union[str, Path]) -> None:
    """Save financial configuration to JSON file."""
    config_path = Path(config_path)

    data = {
        'accounts': [
            {
                'id': acc.id,
                'name': acc.name,
                'type': acc.type.value,
                'balance': acc.balance,
                'minimum_balance': acc.minimum_balance
            }
            for acc in config.accounts
        ],
        'income': [
            {
                'id': inc.id,
                'source': inc.source,
                'amount': inc.amount,
                'frequency': inc.frequency.value,
                'next_date': inc.next_date.isoformat(),
                'deposit_account': inc.deposit_account,
                'splits': [
                    {
                        'account_id': split.account_id,
                        'amount': split.amount
                    }
                    for split in (inc.splits or [])
                ] if inc.splits else None
            }
            for inc in config.income
        ],
        'bills': [
            {
                'id': bill.id,
                'name': bill.name,
                'amount': bill.amount,
                'due_day': bill.due_day,
                'frequency': bill.frequency.value,
                'autopay': bill.autopay,
                'payment_account': bill.payment_account,
                'category': bill.category,
                'paid_by_credit': bill.paid_by_credit
            }
            for bill in config.bills
        ],
        'credit_cards': [
            {
                'id': cc.id,
                'name': cc.name,
                'balance': cc.balance,
                'credit_limit': cc.credit_limit,
                'apr': cc.apr,
                'due_day': cc.due_day,
                'minimum_payment': cc.minimum_payment,
                'statement_day': cc.statement_day,
                'payment_account': cc.payment_account
            }
            for cc in config.credit_cards
        ],
        'settings': {
            'emergency_fund_target': config.settings.emergency_fund_target,
            'planning_horizon_days': config.settings.planning_horizon_days,
            'priority': config.settings.priority.value
        }
    }

    with open(config_path, 'w') as f:
        json.dump(data, f, indent=2)
