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
class Income:
    """Represents an income source."""
    id: str
    source: str
    amount: float
    frequency: Frequency
    next_date: date
    deposit_account: Optional[str] = None

    def __post_init__(self):
        if isinstance(self.frequency, str):
            self.frequency = Frequency(self.frequency)
        if isinstance(self.next_date, str):
            self.next_date = datetime.strptime(self.next_date, "%Y-%m-%d").date()


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

    def __post_init__(self):
        if isinstance(self.frequency, str):
            self.frequency = Frequency(self.frequency)
        if not 1 <= self.due_day <= 31:
            raise ValueError(f"due_day must be between 1 and 31, got {self.due_day}")


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
