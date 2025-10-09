"""
Data models for financial entities.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Literal
from enum import Enum


class AccountType(Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    CASH = "cash"


class Frequency(Enum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    SEMI_MONTHLY = "semi-monthly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class PayoffStrategy(Enum):
    AVALANCHE = "avalanche"  # Highest interest first
    SNOWBALL = "snowball"    # Lowest balance first
    BALANCED = "balanced"     # Mix of both


@dataclass
class Account:
    """Represents a bank account."""
    id: str
    name: str
    type: AccountType
    balance: float
    minimum_balance: float = 0.0

    def __post_init__(self):
        if isinstance(self.type, str):
            self.type = AccountType(self.type)


@dataclass
class IncomeSplit:
    """Represents how to split income across accounts."""
    account_id: str
    amount: Optional[float] = None  # None means "remainder"

    def __post_init__(self):
        if self.amount is not None and self.amount < 0:
            raise ValueError("Split amount must be positive")


@dataclass
class Income:
    """Represents an income source with optional account splitting."""
    id: str
    source: str
    amount: float
    frequency: Frequency
    next_date: date
    deposit_account: Optional[str] = None  # Deprecated, use splits instead
    splits: Optional[list[IncomeSplit]] = None  # New: split across multiple accounts

    def __post_init__(self):
        if isinstance(self.frequency, str):
            self.frequency = Frequency(self.frequency)
        if isinstance(self.next_date, str):
            self.next_date = datetime.strptime(self.next_date, "%Y-%m-%d").date()

        # Convert splits from dicts if needed
        if self.splits and isinstance(self.splits[0], dict):
            self.splits = [IncomeSplit(**s) for s in self.splits]

    def get_splits(self) -> list[IncomeSplit]:
        """Get income splits, falling back to deposit_account if no splits defined."""
        if self.splits:
            return self.splits
        elif self.deposit_account:
            # Backward compatibility: single deposit account
            return [IncomeSplit(account_id=self.deposit_account, amount=None)]
        else:
            return []


@dataclass
class Bill:
    """Represents a recurring bill."""
    id: str
    name: str
    amount: float
    due_day: int
    frequency: Frequency = Frequency.MONTHLY
    autopay: bool = False
    payment_account: Optional[str] = None  # Account ID or credit card ID
    category: Optional[str] = None
    paid_by_credit: bool = False  # True if payment_account is a credit card
    last_paid: Optional[date] = None  # Last date this bill was paid

    def __post_init__(self):
        if isinstance(self.frequency, str):
            self.frequency = Frequency(self.frequency)
        if not 1 <= self.due_day <= 31:
            raise ValueError(f"due_day must be between 1 and 31, got {self.due_day}")
        if isinstance(self.last_paid, str):
            self.last_paid = datetime.strptime(self.last_paid, "%Y-%m-%d").date()

    def is_paid_for_date(self, check_date: date) -> bool:
        """Check if this bill has been paid for the given date."""
        if not self.last_paid:
            return False

        # For monthly bills, check if we've paid this month
        if self.frequency == Frequency.MONTHLY:
            return (self.last_paid.year == check_date.year and
                    self.last_paid.month == check_date.month)

        # For other frequencies, check if last_paid is on or after the check_date
        return self.last_paid >= check_date


@dataclass
class CreditCard:
    """Represents a credit card account."""
    id: str
    name: str
    balance: float
    credit_limit: float
    apr: float  # Annual Percentage Rate as decimal (e.g., 0.1899)
    due_day: int
    minimum_payment: float
    statement_day: Optional[int] = None
    payment_account: Optional[str] = None

    def __post_init__(self):
        if not 1 <= self.due_day <= 31:
            raise ValueError(f"due_day must be between 1 and 31, got {self.due_day}")
        if self.statement_day and not 1 <= self.statement_day <= 31:
            raise ValueError(f"statement_day must be between 1 and 31, got {self.statement_day}")

    @property
    def utilization(self) -> float:
        """Calculate credit utilization percentage."""
        return (self.balance / self.credit_limit) * 100 if self.credit_limit > 0 else 0

    @property
    def daily_interest(self) -> float:
        """Calculate daily interest charge."""
        return (self.balance * self.apr) / 365


@dataclass
class Settings:
    """Optimization settings."""
    emergency_fund_target: float = 1000.0
    planning_horizon_days: int = 30
    priority: PayoffStrategy = PayoffStrategy.AVALANCHE

    def __post_init__(self):
        if isinstance(self.priority, str):
            self.priority = PayoffStrategy(self.priority)


@dataclass
class FinancialConfig:
    """Complete financial configuration."""
    accounts: list[Account]
    income: list[Income]
    bills: list[Bill]
    credit_cards: list[CreditCard]
    settings: Settings
