"""
Financial optimization engine to generate daily tasks and recommendations.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional, Dict
from models import FinancialConfig, CreditCard, Bill, Income, Account, PayoffStrategy, Frequency
from calendar import monthrange


@dataclass
class CashFlowEvent:
    """Represents a cash flow event (income or expense)."""
    date: date
    amount: float  # Positive for income, negative for expense
    description: str
    category: str
    required: bool = True  # Can't be skipped
    account_id: Optional[str] = None


@dataclass
class DailyBalance:
    """Track balance for a specific day."""
    date: date
    starting_balance: float
    events: List[CashFlowEvent] = field(default_factory=list)
    ending_balance: float = 0.0

    def calculate_ending(self):
        self.ending_balance = self.starting_balance + sum(e.amount for e in self.events)


@dataclass
class Task:
    """Represents a concrete financial action."""
    date: date
    priority: int  # 1 = highest priority (critical)
    category: str
    description: str
    amount: Optional[float] = None
    account_id: Optional[str] = None
    action: Optional[str] = None  # "pay", "transfer", "wait"

    def __str__(self):
        amount_str = f" ${self.amount:.2f}" if self.amount else ""
        return f"{self.description}{amount_str}"


class FinancialOptimizer:
    """Generates optimized financial tasks and recommendations."""

    def __init__(self, config: FinancialConfig):
        self.config = config
        self.today = date.today()

    def get_next_date(self, day_of_month: int, from_date: Optional[date] = None) -> date:
        """Get the next occurrence of a specific day of the month."""
        if from_date is None:
            from_date = self.today

        # Try current month
        try:
            next_date = date(from_date.year, from_date.month, min(day_of_month, monthrange(from_date.year, from_date.month)[1]))
            if next_date >= from_date:
                return next_date
        except ValueError:
            pass

        # Try next month
        next_month = from_date.month + 1
        next_year = from_date.year
        if next_month > 12:
            next_month = 1
            next_year += 1

        return date(next_year, next_month, min(day_of_month, monthrange(next_year, next_month)[1]))

    def get_next_income_date(self, income: Income) -> date:
        """Calculate next income date after the stored next_date."""
        if income.frequency == Frequency.WEEKLY:
            return income.next_date + timedelta(days=7)
        elif income.frequency == Frequency.BIWEEKLY:
            return income.next_date + timedelta(days=14)
        elif income.frequency == Frequency.SEMI_MONTHLY:
            # Approximate: 15 days
            return income.next_date + timedelta(days=15)
        elif income.frequency == Frequency.MONTHLY:
            next_month = income.next_date.month + 1
            next_year = income.next_date.year
            if next_month > 12:
                next_month = 1
                next_year += 1
            return date(next_year, next_month, income.next_date.day)
        return income.next_date

    def calculate_total_available_funds(self) -> float:
        """Calculate total available funds across all accounts."""
        return sum(max(0, acc.balance - acc.minimum_balance) for acc in self.config.accounts)

    def calculate_emergency_fund(self) -> float:
        """Calculate current emergency fund (savings accounts)."""
        return sum(acc.balance for acc in self.config.accounts if acc.type.value == "savings")

    def get_upcoming_bills(self, days_ahead: int = 30) -> List[tuple[date, Bill]]:
        """Get all bills due within the next N days."""
        upcoming = []
        end_date = self.today + timedelta(days=days_ahead)

        for bill in self.config.bills:
            next_due = self.get_next_date(bill.due_day)

            # Add all occurrences within the planning horizon
            while next_due <= end_date:
                upcoming.append((next_due, bill))

                if bill.frequency == Frequency.MONTHLY:
                    next_due = self.get_next_date(bill.due_day, next_due + timedelta(days=1))
                elif bill.frequency == Frequency.QUARTERLY:
                    next_due = next_due.replace(month=next_due.month + 3 if next_due.month <= 9 else next_due.month - 9,
                                               year=next_due.year if next_due.month <= 9 else next_due.year + 1)
                elif bill.frequency == Frequency.ANNUAL:
                    next_due = next_due.replace(year=next_due.year + 1)
                else:
                    break

        return sorted(upcoming, key=lambda x: x[0])

    def get_upcoming_income(self, days_ahead: int = 30) -> List[tuple[date, Income]]:
        """Get all income expected within the next N days."""
        upcoming = []
        end_date = self.today + timedelta(days=days_ahead)

        for inc in self.config.income:
            next_date = inc.next_date

            while next_date <= end_date:
                upcoming.append((next_date, inc))
                next_date = self.get_next_income_date(Income(
                    id=inc.id, source=inc.source, amount=inc.amount,
                    frequency=inc.frequency, next_date=next_date,
                    deposit_account=inc.deposit_account
                ))

        return sorted(upcoming, key=lambda x: x[0])

    def prioritize_credit_cards(self) -> List[CreditCard]:
        """Prioritize credit cards based on strategy."""
        cards_with_balance = [cc for cc in self.config.credit_cards if cc.balance > 0]

        if self.config.settings.priority == PayoffStrategy.AVALANCHE:
            # Highest APR first
            return sorted(cards_with_balance, key=lambda x: x.apr, reverse=True)
        elif self.config.settings.priority == PayoffStrategy.SNOWBALL:
            # Lowest balance first
            return sorted(cards_with_balance, key=lambda x: x.balance)
        else:  # BALANCED
            # Balance between APR and balance
            return sorted(cards_with_balance, key=lambda x: (x.apr * 0.5 + (x.balance / 10000) * 0.5), reverse=True)

    def build_cash_flow_timeline(self, days_ahead: int = 14) -> Dict[date, DailyBalance]:
        """Build a day-by-day cash flow projection."""
        timeline = {}
        current_balance = sum(acc.balance for acc in self.config.accounts)

        # Get minimum balance to maintain across all accounts
        min_balance_required = sum(acc.minimum_balance for acc in self.config.accounts)

        # Build timeline for each day
        for day_offset in range(days_ahead + 1):
            current_date = self.today + timedelta(days=day_offset)
            daily = DailyBalance(date=current_date, starting_balance=current_balance)

            # Add income events
            for inc_date, inc in self.get_upcoming_income(days_ahead=days_ahead):
                if inc_date == current_date:
                    daily.events.append(CashFlowEvent(
                        date=current_date,
                        amount=inc.amount,
                        description=f"Income: {inc.source}",
                        category="income",
                        required=False,
                        account_id=inc.deposit_account
                    ))

            # Add bill payments (including autopay)
            for bill_date, bill in self.get_upcoming_bills(days_ahead=days_ahead):
                if bill_date == current_date:
                    daily.events.append(CashFlowEvent(
                        date=current_date,
                        amount=-bill.amount,
                        description=f"Bill: {bill.name}{'[AUTO]' if bill.autopay else ''}",
                        category="bill",
                        required=True,
                        account_id=bill.payment_account
                    ))

            # Add credit card minimum payments
            for cc in self.config.credit_cards:
                if cc.balance > 0:
                    cc_due = self.get_next_date(cc.due_day)
                    if cc_due == current_date:
                        daily.events.append(CashFlowEvent(
                            date=current_date,
                            amount=-cc.minimum_payment,
                            description=f"CC Min Payment: {cc.name}",
                            category="cc_minimum",
                            required=True,
                            account_id=cc.payment_account
                        ))

            daily.calculate_ending()
            current_balance = daily.ending_balance
            timeline[current_date] = daily

        return timeline

    def calculate_safe_payment_amount(self) -> Dict[str, float]:
        """Calculate safe extra payments based on cash flow projection."""
        timeline = self.build_cash_flow_timeline(days_ahead=14)

        # Find the minimum balance over the next 14 days
        min_future_balance = min(day.ending_balance for day in timeline.values())
        min_balance_required = sum(acc.minimum_balance for acc in self.config.accounts)

        # Current available (today)
        current_available = sum(acc.balance - acc.minimum_balance for acc in self.config.accounts)

        # Safe to spend = current available - buffer for upcoming expenses
        # We need to ensure we don't go below minimum at any point
        safety_buffer = max(0, min_balance_required - min_future_balance) + 100  # Extra $100 buffer
        safe_amount = max(0, current_available - safety_buffer)

        # Allocate payments based on strategy
        payments = {}
        remaining = safe_amount

        # Priority 1: Build emergency fund if below target
        emergency_fund = self.calculate_emergency_fund()
        if emergency_fund < self.config.settings.emergency_fund_target:
            needed = self.config.settings.emergency_fund_target - emergency_fund
            emergency_payment = min(remaining * 0.3, needed)  # 30% max to emergency
            if emergency_payment > 0:
                payments['emergency_fund'] = emergency_payment
                remaining -= emergency_payment

        # Priority 2: Extra credit card payments
        if remaining > 20:  # Only if we have meaningful amount left
            priority_cards = self.prioritize_credit_cards()
            for cc in priority_cards:
                if remaining <= 0:
                    break

                # Calculate how much to pay this card
                # Start with at least $20, or up to 80% of remaining
                payment = min(remaining * 0.8, cc.balance - cc.minimum_payment)

                if payment >= 10:  # Only suggest if meaningful
                    payments[cc.id] = payment
                    remaining -= payment

        return payments

    def generate_daily_tasks(self, target_date: Optional[date] = None) -> List[Task]:
        """Generate concrete tasks with specific payment amounts for today."""
        if target_date is None:
            target_date = self.today

        tasks = []
        timeline = self.build_cash_flow_timeline(days_ahead=14)
        today_balance = timeline[target_date]

        # Calculate current spendable cash
        current_available = sum(acc.balance - acc.minimum_balance for acc in self.config.accounts)

        # CRITICAL: Check if we're in trouble
        if today_balance.ending_balance < sum(acc.minimum_balance for acc in self.config.accounts):
            tasks.append(Task(
                date=target_date,
                priority=1,
                category="⚠️  URGENT",
                description=f"WARNING: Projected to go below minimum balance. Current available: ${current_available:.2f}",
                action="review"
            ))

        # Priority 1: Required payments TODAY
        for event in today_balance.events:
            if event.amount < 0 and event.required:  # Expense that's required
                tasks.append(Task(
                    date=target_date,
                    priority=1,
                    category="💳 REQUIRED",
                    description=event.description,
                    amount=-event.amount,
                    account_id=event.account_id,
                    action="pay"
                ))

        # Priority 2: Income expected today
        for event in today_balance.events:
            if event.amount > 0:
                tasks.append(Task(
                    date=target_date,
                    priority=2,
                    category="💵 INCOME",
                    description=event.description,
                    amount=event.amount,
                    account_id=event.account_id,
                    action="wait"
                ))

        # Priority 3: Calculate and recommend extra payments
        safe_payments = self.calculate_safe_payment_amount()

        if 'emergency_fund' in safe_payments:
            tasks.append(Task(
                date=target_date,
                priority=3,
                category="🏦 SAVE",
                description="Transfer to emergency fund",
                amount=safe_payments['emergency_fund'],
                action="transfer"
            ))

        priority_cards = self.prioritize_credit_cards()
        for cc in priority_cards:
            if cc.id in safe_payments:
                daily_interest_savings = (safe_payments[cc.id] * cc.apr) / 365
                tasks.append(Task(
                    date=target_date,
                    priority=4,
                    category="💳 EXTRA PAYMENT",
                    description=f"Pay extra to {cc.name} (APR {cc.apr*100:.1f}%, saves ${daily_interest_savings:.2f}/day)",
                    amount=safe_payments[cc.id],
                    account_id=cc.payment_account,
                    action="pay"
                ))

        # Priority 5: Show what's coming in next 7 days
        upcoming_required = []
        for days_out in range(1, 8):
            future_date = target_date + timedelta(days=days_out)
            if future_date in timeline:
                for event in timeline[future_date].events:
                    if event.amount < 0 and event.required:
                        upcoming_required.append((future_date, event))

        if upcoming_required:
            total_upcoming = sum(-event.amount for _, event in upcoming_required)
            tasks.append(Task(
                date=target_date,
                priority=5,
                category="📅 UPCOMING",
                description=f"${total_upcoming:.2f} in required payments over next 7 days ({len(upcoming_required)} items)",
                action="info"
            ))

        return sorted(tasks, key=lambda x: x.priority)

    def get_cash_flow_forecast(self, days: int = 14) -> Dict[date, DailyBalance]:
        """Get detailed cash flow forecast."""
        return self.build_cash_flow_timeline(days_ahead=days)

    def generate_weekly_summary(self) -> dict:
        """Generate a 7-day financial summary with cash flow timeline."""
        timeline = self.build_cash_flow_timeline(days_ahead=7)

        summary = {
            'current_date': self.today,
            'total_balance': sum(acc.balance for acc in self.config.accounts),
            'total_debt': sum(cc.balance for cc in self.config.credit_cards),
            'emergency_fund': self.calculate_emergency_fund(),
            'min_balance_required': sum(acc.minimum_balance for acc in self.config.accounts),
            'timeline': timeline,
            'credit_card_status': [
                {
                    'name': cc.name,
                    'balance': cc.balance,
                    'utilization': cc.utilization,
                    'next_due': self.get_next_date(cc.due_day),
                    'minimum_payment': cc.minimum_payment,
                    'daily_interest': cc.daily_interest,
                    'monthly_interest': cc.daily_interest * 30
                }
                for cc in self.config.credit_cards
            ]
        }
        return summary
