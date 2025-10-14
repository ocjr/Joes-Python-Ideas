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
    INVESTMENT = "investment"


class Frequency(Enum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    SEMI_MONTHLY = "semi-monthly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class PayoffStrategy(Enum):
    AVALANCHE = "avalanche"  # Highest interest first
    SNOWBALL = "snowball"  # Lowest balance first
    BALANCED = "balanced"  # Mix of both


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
class StockTransaction:
    """Represents a buy or sell transaction for a stock."""

    id: str
    date: date  # Transaction date (execution date)
    symbol: str  # Stock ticker (e.g., "AAPL", "TSLA")
    transaction_type: Literal["buy", "sell", "dividend"]
    shares: float  # Number of shares (positive for buy, negative for sell)
    price_per_share: float  # Price per share at transaction time
    total_amount: float  # Total transaction amount (shares * price + commission)
    commission: float = 0.0  # Commission/fees for this transaction
    settlement_date: Optional[date] = None  # Settlement date (when cash/shares transfer)
    notes: Optional[str] = None

    def __post_init__(self):
        if isinstance(self.date, str):
            self.date = datetime.strptime(self.date, "%Y-%m-%d").date()
        if self.settlement_date and isinstance(self.settlement_date, str):
            self.settlement_date = datetime.strptime(self.settlement_date, "%Y-%m-%d").date()

        # Auto-calculate settlement date if not provided (T+1 for US stocks)
        if not self.settlement_date and self.transaction_type in ["buy", "sell"]:
            self.settlement_date = self._calculate_settlement_date(self.date)

    def _calculate_settlement_date(self, trade_date: date) -> date:
        """Calculate settlement date as next business day (T+1)."""
        from datetime import timedelta

        # Add 1 day
        next_day = trade_date + timedelta(days=1)

        # Skip weekends
        while next_day.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
            next_day += timedelta(days=1)

        return next_day


@dataclass
class StockHolding:
    """Represents current holdings of a particular stock."""

    symbol: str
    shares: float
    cost_basis: float  # Total amount paid for these shares
    current_price: float = 0.0  # Current market price per share

    @property
    def market_value(self) -> float:
        """Current market value of holdings."""
        return self.shares * self.current_price

    @property
    def gain_loss(self) -> float:
        """Unrealized gain or loss."""
        return self.market_value - self.cost_basis

    @property
    def gain_loss_pct(self) -> float:
        """Unrealized gain or loss as percentage."""
        return (self.gain_loss / self.cost_basis * 100) if self.cost_basis > 0 else 0.0


@dataclass
class InvestmentAccount:
    """Represents an investment/brokerage account with stock holdings."""

    id: str
    name: str
    cash_balance: float  # Cash available in the account
    minimum_balance: float = 0.0
    default_commission: float = 0.0  # Default commission per transaction
    transactions: list[StockTransaction] = None
    holdings: list[StockHolding] = None

    def __post_init__(self):
        if self.transactions is None:
            self.transactions = []
        if self.holdings is None:
            self.holdings = []

        # Convert transactions from dicts if needed
        if self.transactions and isinstance(self.transactions[0], dict):
            self.transactions = [StockTransaction(**t) for t in self.transactions]

        # Convert holdings from dicts if needed
        if self.holdings and isinstance(self.holdings[0], dict):
            self.holdings = [StockHolding(**h) for h in self.holdings]

    @property
    def total_market_value(self) -> float:
        """Total market value of all holdings."""
        return sum(h.market_value for h in self.holdings)

    @property
    def total_value(self) -> float:
        """Total account value (cash + investments)."""
        return self.cash_balance + self.total_market_value

    @property
    def total_cost_basis(self) -> float:
        """Total amount invested in stocks."""
        return sum(h.cost_basis for h in self.holdings)

    @property
    def total_gain_loss(self) -> float:
        """Total unrealized gain or loss."""
        return self.total_market_value - self.total_cost_basis

    def get_holding(self, symbol: str) -> Optional[StockHolding]:
        """Get holding for a specific stock symbol."""
        return next((h for h in self.holdings if h.symbol.upper() == symbol.upper()), None)

    def update_holdings_from_transactions(self):
        """Recalculate holdings based on transaction history."""
        # Group transactions by symbol
        holdings_dict = {}

        for txn in sorted(self.transactions, key=lambda t: t.date):
            symbol = txn.symbol.upper()

            if symbol not in holdings_dict:
                holdings_dict[symbol] = {"shares": 0.0, "cost_basis": 0.0, "current_price": 0.0}

            if txn.transaction_type == "buy":
                holdings_dict[symbol]["shares"] += txn.shares
                holdings_dict[symbol]["cost_basis"] += txn.total_amount
            elif txn.transaction_type == "sell":
                # Calculate average cost per share before sale
                if holdings_dict[symbol]["shares"] > 0:
                    avg_cost = holdings_dict[symbol]["cost_basis"] / holdings_dict[symbol]["shares"]
                    holdings_dict[symbol]["cost_basis"] -= avg_cost * txn.shares
                holdings_dict[symbol]["shares"] -= txn.shares

            # Preserve current price if we already have it
            existing = self.get_holding(symbol)
            if existing:
                holdings_dict[symbol]["current_price"] = existing.current_price

        # Convert to StockHolding objects, filtering out zero positions
        self.holdings = [
            StockHolding(
                symbol=symbol,
                shares=data["shares"],
                cost_basis=data["cost_basis"],
                current_price=data["current_price"],
            )
            for symbol, data in holdings_dict.items()
            if data["shares"] > 0.01  # Filter out positions smaller than 0.01 shares
        ]


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
    require_checking: bool = (
        False  # True if this bill MUST be paid from checking (no credit allowed)
    )
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
            return (
                self.last_paid.year == check_date.year
                and self.last_paid.month == check_date.month
            )

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
    primary_for_purchases: bool = False  # Use this card for daily purchases

    def __post_init__(self):
        if not 1 <= self.due_day <= 31:
            raise ValueError(f"due_day must be between 1 and 31, got {self.due_day}")
        if self.statement_day and not 1 <= self.statement_day <= 31:
            raise ValueError(
                f"statement_day must be between 1 and 31, got {self.statement_day}"
            )

    @property
    def utilization(self) -> float:
        """Calculate credit utilization percentage."""
        return (self.balance / self.credit_limit) * 100 if self.credit_limit > 0 else 0

    @property
    def available_credit(self) -> float:
        """Calculate available credit remaining."""
        return max(0, self.credit_limit - self.balance)

    @property
    def daily_interest(self) -> float:
        """Calculate daily interest charge."""
        return (self.balance * self.apr) / 365


@dataclass
class ManualPayment:
    """Represents a one-time manual payment to a credit card."""

    id: str
    name: str
    amount: float
    payment_date: date
    credit_card_id: str  # Which card to pay
    payment_account: Optional[str] = None  # Which checking account to pay from

    def __post_init__(self):
        if isinstance(self.payment_date, str):
            self.payment_date = datetime.strptime(self.payment_date, "%Y-%m-%d").date()


@dataclass
class RecurringExpense:
    """Represents recurring spending like groceries, gas, etc."""

    id: str
    name: str
    amount: float  # Average amount per occurrence
    frequency: Frequency = Frequency.WEEKLY
    payment_account: Optional[str] = None  # Account ID or credit card ID
    paid_by_credit: bool = False  # True if payment_account is a credit card
    category: Optional[str] = None
    next_date: Optional[date] = None  # When this expense next occurs

    def __post_init__(self):
        if isinstance(self.frequency, str):
            self.frequency = Frequency(self.frequency)
        if self.next_date and isinstance(self.next_date, str):
            self.next_date = datetime.strptime(self.next_date, "%Y-%m-%d").date()


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
class TransactionEvent:
    """Represents a buy or sell instruction in simulation results."""

    date: date
    transaction_type: Literal["buy", "sell"]
    ticker: str
    amount: float  # Dollar amount to buy or sell
    description: str  # Human-readable description


@dataclass
class InvestmentSimulation:
    """Configuration for investment simulation (e.g., SPY float strategy)."""

    id: str
    name: str
    enabled: bool = True
    current_age: int = 38
    target_ages: list[int] = None  # Ages to report (e.g., [65, 80])

    # Strategy parameters
    strategy_type: Literal["constant_hold", "monthly_liquidation", "principal_only"] = "monthly_liquidation"
    hold_days: int = 14  # For constant_hold strategy
    liquidation_day: int = 1  # For monthly_liquidation and principal_only (day of month to sell)

    # Income sources to include
    income_source_ids: list[str] = None  # List of income IDs to use in simulation

    # Income growth parameters
    income_growth_rate: float = 0.0  # Annual growth rate (e.g., 0.10 for 10%)
    income_growth_frequency: int = 1  # Apply growth every N years (e.g., 2 for biennial)

    # Investment parameters
    ticker: str = "SPY"
    initial_balance: float = 0.0  # Starting account balance
    expected_annual_return: float = 0.10  # 10% historical average
    annual_volatility: float = 0.15  # 15% standard deviation
    annual_dividend_yield: float = 0.015  # 1.5% dividend yield
    expense_ratio: float = 0.0009  # 0.09% SPY expense ratio

    # Tax parameters
    short_term_cap_gains_rate: float = 0.22  # Short-term cap gains (< 1 year)
    long_term_cap_gains_rate: float = 0.15  # Long-term cap gains (>= 1 year)
    dividend_tax_rate: float = 0.15  # Qualified dividend rate

    # Monte Carlo parameters
    num_simulations: int = 1000
    random_seed: Optional[int] = None  # For reproducibility

    # Investment account to use
    investment_account_id: str = None

    def __post_init__(self):
        if self.target_ages is None:
            self.target_ages = [65, 80]
        if self.income_source_ids is None:
            self.income_source_ids = []


@dataclass
class FinancialConfig:
    """Complete financial configuration."""

    accounts: list[Account]
    income: list[Income]
    bills: list[Bill]
    credit_cards: list[CreditCard]
    settings: Settings
    manual_payments: list[ManualPayment] = None
    recurring_expenses: list[RecurringExpense] = None
    investment_accounts: list[InvestmentAccount] = None
    simulations: list[InvestmentSimulation] = None

    def __post_init__(self):
        if self.manual_payments is None:
            self.manual_payments = []
        if self.recurring_expenses is None:
            self.recurring_expenses = []
        if self.investment_accounts is None:
            self.investment_accounts = []
        if self.simulations is None:
            self.simulations = []

        # Convert investment accounts from dicts if needed
        if self.investment_accounts and isinstance(self.investment_accounts[0], dict):
            self.investment_accounts = [InvestmentAccount(**acc) for acc in self.investment_accounts]

        # Convert simulations from dicts if needed
        if self.simulations and isinstance(self.simulations[0], dict):
            self.simulations = [InvestmentSimulation(**sim) for sim in self.simulations]
