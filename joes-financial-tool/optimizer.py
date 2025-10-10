"""
Financial optimization engine to generate daily tasks and recommendations.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional, Dict
from models import (
    FinancialConfig,
    CreditCard,
    Bill,
    Income,
    Account,
    PayoffStrategy,
    Frequency,
)
from calendar import monthrange
from simulator import FinancialSimulator, SimulationResult


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
        self.simulator = FinancialSimulator(config, self.today)
        self._optimal_simulation: Optional[SimulationResult] = None

    def get_next_date(
        self, day_of_month: int, from_date: Optional[date] = None
    ) -> date:
        """Get the next occurrence of a specific day of the month."""
        if from_date is None:
            from_date = self.today

        # Try current month
        try:
            next_date = date(
                from_date.year,
                from_date.month,
                min(day_of_month, monthrange(from_date.year, from_date.month)[1]),
            )
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

        return date(
            next_year,
            next_month,
            min(day_of_month, monthrange(next_year, next_month)[1]),
        )

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
        return sum(
            max(0, acc.balance - acc.minimum_balance) for acc in self.config.accounts
        )

    def calculate_emergency_fund(self) -> float:
        """Calculate current emergency fund (savings accounts)."""
        return sum(
            acc.balance for acc in self.config.accounts if acc.type.value == "savings"
        )

    def calculate_credit_card_spending(
        self, card_id: str, days_ahead: int = 30
    ) -> float:
        """Calculate upcoming bills that will be charged to a credit card."""
        total_spending = 0.0
        end_date = self.today + timedelta(days=days_ahead)

        for bill in self.config.bills:
            if bill.paid_by_credit and bill.payment_account == card_id:
                # Get all occurrences of this bill within the time period
                next_due = self.get_next_date(bill.due_day)

                while next_due <= end_date:
                    total_spending += bill.amount

                    if bill.frequency == Frequency.MONTHLY:
                        next_due = self.get_next_date(
                            bill.due_day, next_due + timedelta(days=1)
                        )
                    elif bill.frequency == Frequency.QUARTERLY:
                        # Move forward 3 months
                        next_month = next_due.month + 3
                        next_year = next_due.year
                        while next_month > 12:
                            next_month -= 12
                            next_year += 1
                        next_due = date(
                            next_year,
                            next_month,
                            min(bill.due_day, monthrange(next_year, next_month)[1]),
                        )
                    elif bill.frequency == Frequency.ANNUAL:
                        next_due = next_due.replace(year=next_due.year + 1)
                    else:
                        break

        return total_spending

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
                    next_due = self.get_next_date(
                        bill.due_day, next_due + timedelta(days=1)
                    )
                elif bill.frequency == Frequency.QUARTERLY:
                    next_due = next_due.replace(
                        month=(
                            next_due.month + 3
                            if next_due.month <= 9
                            else next_due.month - 9
                        ),
                        year=(
                            next_due.year if next_due.month <= 9 else next_due.year + 1
                        ),
                    )
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
                next_date = self.get_next_income_date(
                    Income(
                        id=inc.id,
                        source=inc.source,
                        amount=inc.amount,
                        frequency=inc.frequency,
                        next_date=next_date,
                        deposit_account=inc.deposit_account,
                    )
                )

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
            return sorted(
                cards_with_balance,
                key=lambda x: (x.apr * 0.5 + (x.balance / 10000) * 0.5),
                reverse=True,
            )

    def build_cash_flow_timeline(
        self, days_ahead: int = 14
    ) -> Dict[date, DailyBalance]:
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
                    daily.events.append(
                        CashFlowEvent(
                            date=current_date,
                            amount=inc.amount,
                            description=f"Income: {inc.source}",
                            category="income",
                            required=False,
                            account_id=inc.deposit_account,
                        )
                    )

            # Add bill payments (only those paid from checking/savings, not credit)
            for bill_date, bill in self.get_upcoming_bills(days_ahead=days_ahead):
                if bill_date == current_date and not bill.paid_by_credit:
                    # Skip if bill is already paid for this date
                    if bill.is_paid_for_date(current_date):
                        continue

                    # Only deduct from cash flow if paid from checking/savings
                    daily.events.append(
                        CashFlowEvent(
                            date=current_date,
                            amount=-bill.amount,
                            description=f"Bill: {bill.name}{'[AUTO]' if bill.autopay else ''}",
                            category="bill",
                            required=True,
                            account_id=bill.payment_account,
                        )
                    )

            # Add credit card minimum payments
            for cc in self.config.credit_cards:
                if cc.balance > 0:
                    cc_due = self.get_next_date(cc.due_day)
                    if cc_due == current_date:
                        daily.events.append(
                            CashFlowEvent(
                                date=current_date,
                                amount=-cc.minimum_payment,
                                description=f"CC Min Payment: {cc.name}",
                                category="cc_minimum",
                                required=True,
                                account_id=cc.payment_account,
                            )
                        )

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
        current_available = sum(
            acc.balance - acc.minimum_balance for acc in self.config.accounts
        )

        # Safe to spend = current available - buffer for upcoming expenses
        # We need to ensure we don't go below minimum at any point
        safety_buffer = (
            max(0, min_balance_required - min_future_balance) + 200
        )  # Extra $200 buffer for safety
        safe_amount = max(0, current_available - safety_buffer)

        # Don't recommend any extra payments if we don't have enough cushion
        if safe_amount < 50:
            return {}

        # Allocate payments based on strategy
        payments = {}
        remaining = safe_amount

        # Get highest APR among cards with balances
        priority_cards = self.prioritize_credit_cards()
        highest_apr = max((cc.apr for cc in priority_cards), default=0.0)

        # Emergency fund status
        emergency_fund = self.calculate_emergency_fund()
        emergency_target = self.config.settings.emergency_fund_target
        emergency_pct = (
            (emergency_fund / emergency_target) if emergency_target > 0 else 1.0
        )

        # Decision: Prioritize debt over emergency fund if APR is high
        # Logic: If we have high-interest debt (>6% APR), pay that first
        # Only build emergency fund if:
        #   1. Emergency fund is critically low (<50% of target) AND APR < 10%, OR
        #   2. All high-interest debts are paid off
        prioritize_debt = highest_apr > 0.06 and emergency_pct >= 0.5

        if prioritize_debt:
            # Priority 1: Aggressively pay down high-interest debt
            if remaining > 50:
                for cc in priority_cards:
                    if remaining <= 10:
                        break

                    # Don't recommend more than the card's current balance
                    max_extra_payment = max(0, cc.balance - cc.minimum_payment)
                    if max_extra_payment <= 0:
                        continue

                    # Pay up to 80% of remaining to highest priority card (more aggressive)
                    payment = min(remaining * 0.8, max_extra_payment)

                    if payment >= 20:  # Only suggest if $20 or more
                        payments[cc.id] = payment
                        remaining -= payment

            # Priority 2: Build emergency fund with remaining (if any)
            if remaining > 10 and emergency_fund < emergency_target:
                needed = emergency_target - emergency_fund
                emergency_payment = min(remaining, needed)
                if emergency_payment > 10:
                    payments["emergency_fund"] = emergency_payment
                    remaining -= emergency_payment

        else:
            # Priority 1: Build emergency fund if critically low or no high-interest debt
            if emergency_fund < emergency_target:
                needed = emergency_target - emergency_fund
                # If emergency fund is critically low (<50%), allocate more (50%)
                allocation_pct = 0.5 if emergency_pct < 0.5 else 0.3
                emergency_payment = min(remaining * allocation_pct, needed)
                if emergency_payment > 10:
                    payments["emergency_fund"] = emergency_payment
                    remaining -= emergency_payment

            # Priority 2: Extra credit card payments
            if remaining > 50:
                for cc in priority_cards:
                    if remaining <= 10:
                        break

                    max_extra_payment = max(0, cc.balance - cc.minimum_payment)
                    if max_extra_payment <= 0:
                        continue

                    payment = min(remaining * 0.7, max_extra_payment)

                    if payment >= 20:
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
        current_available = sum(
            acc.balance - acc.minimum_balance for acc in self.config.accounts
        )

        # CRITICAL: Check if we're in trouble
        if today_balance.ending_balance < sum(
            acc.minimum_balance for acc in self.config.accounts
        ):
            tasks.append(
                Task(
                    date=target_date,
                    priority=1,
                    category="⚠️  URGENT",
                    description=f"WARNING: Projected to go below minimum balance. Current available: ${current_available:.2f}",
                    action="review",
                )
            )

        # Find the NEXT credit card due date (earliest)
        next_cc_due_date = None
        for cc in self.config.credit_cards:
            if cc.balance > 0:
                cc_due = self.get_next_date(cc.due_day)
                if next_cc_due_date is None or cc_due < next_cc_due_date:
                    next_cc_due_date = cc_due

        # Check if any credit cards are due today
        cards_due_today = {}  # cc.id -> cc object
        cc_min_payments = {}  # cc.id -> minimum payment amount
        for cc in self.config.credit_cards:
            if cc.balance > 0:
                cc_due = self.get_next_date(cc.due_day)
                if cc_due == target_date:
                    cards_due_today[cc.id] = cc
                    cc_min_payments[cc.id] = cc.minimum_payment

        # Only calculate extra payments if today is the NEXT credit card due date
        # This prevents recommending the same money multiple times
        safe_payments = {}
        emergency_fund_payment = 0
        if cards_due_today and target_date == next_cc_due_date:
            safe_payments = self.calculate_safe_payment_amount()
            emergency_fund_payment = safe_payments.get("emergency_fund", 0)

        # Priority 1: Required payments TODAY (combine CC min + extra)
        for event in today_balance.events:
            if event.amount < 0 and event.required:
                # Check if this is a CC minimum payment that we should augment
                is_cc_payment = False
                for cc_id, cc in cards_due_today.items():
                    if f"CC Min Payment: {cc.name}" in event.description:
                        # This is a CC payment - combine min + extra
                        min_payment = cc_min_payments[cc_id]
                        extra_payment = safe_payments.get(cc_id, 0)
                        total_payment = min_payment + extra_payment

                        if extra_payment > 0:
                            daily_savings = (extra_payment * cc.apr) / 365
                            description = f"Pay ${total_payment:,.2f} to {cc.name} (${min_payment:,.2f} min + ${extra_payment:,.2f} extra, saves ${daily_savings:.2f}/day)"
                        else:
                            description = f"Pay ${total_payment:,.2f} to {cc.name} (minimum payment)"

                        tasks.append(
                            Task(
                                date=target_date,
                                priority=1,
                                category="💳 PAY",
                                description=description,
                                amount=total_payment,
                                account_id=event.account_id,
                                action="pay",
                            )
                        )
                        is_cc_payment = True
                        break

                # If not a CC payment, add as regular required payment
                if not is_cc_payment:
                    tasks.append(
                        Task(
                            date=target_date,
                            priority=1,
                            category="💳 PAY",
                            description=event.description.replace("Bill: ", ""),
                            amount=-event.amount,
                            account_id=event.account_id,
                            action="pay",
                        )
                    )

        # Priority 2: Emergency fund (only on CC due dates)
        if emergency_fund_payment > 0:
            tasks.append(
                Task(
                    date=target_date,
                    priority=2,
                    category="🏦 SAVE",
                    description=f"Transfer ${emergency_fund_payment:,.2f} to emergency fund",
                    amount=emergency_fund_payment,
                    action="transfer",
                )
            )

        # Priority 3: Income expected today
        for event in today_balance.events:
            if event.amount > 0:
                source = event.description.replace("Income: ", "")
                tasks.append(
                    Task(
                        date=target_date,
                        priority=3,
                        category="💵 INCOME",
                        description=f"${event.amount:,.2f} from {source}",
                        amount=event.amount,
                        account_id=event.account_id,
                        action="wait",
                    )
                )

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
            tasks.append(
                Task(
                    date=target_date,
                    priority=5,
                    category="📅 UPCOMING",
                    description=f"${total_upcoming:.2f} in required payments over next 7 days ({len(upcoming_required)} items)",
                    action="info",
                )
            )

        return sorted(tasks, key=lambda x: x.priority)

    def get_cash_flow_forecast(self, days: int = 14) -> Dict[date, DailyBalance]:
        """Get detailed cash flow forecast."""
        return self.build_cash_flow_timeline(days_ahead=days)

    def get_optimal_simulation(
        self, days_ahead: int = 30, force_refresh: bool = False
    ) -> SimulationResult:
        """
        Get the optimal financial strategy simulation.

        Runs simulations for different strategies and returns the one with
        the lowest total interest cost while respecting all constraints.

        Parameters
        ----------
        days_ahead : int, optional
            Number of days to simulate (default: 30)
        force_refresh : bool, optional
            Force re-computation even if cached result exists (default: False)

        Returns
        -------
        SimulationResult
            The optimal simulation with lowest interest cost
        """
        if self._optimal_simulation is None or force_refresh:
            self._optimal_simulation = self.simulator.find_optimal_strategy(days_ahead)
        return self._optimal_simulation

    def generate_monthly_action_plan(self) -> dict:
        """Generate action-focused monthly financial plan."""
        # Calculate checking vs savings totals
        checking_total = sum(
            acc.balance for acc in self.config.accounts if acc.type.value == "checking"
        )
        savings_total = sum(
            acc.balance for acc in self.config.accounts if acc.type.value == "savings"
        )
        cash_total = sum(
            acc.balance for acc in self.config.accounts if acc.type.value == "cash"
        )

        # Get monthly income
        monthly_income = []
        for inc_date, inc in self.get_upcoming_income(days_ahead=30):
            monthly_income.append(
                {"date": inc_date, "source": inc.source, "amount": inc.amount}
            )
        total_income = sum(inc["amount"] for inc in monthly_income)

        # Calculate credit card actions with spending
        cc_actions = []
        total_cc_payments = 0
        for cc in self.config.credit_cards:
            cc_due = self.get_next_date(cc.due_day)
            upcoming_spending = self.calculate_credit_card_spending(
                cc.id, days_ahead=30
            )

            # Recommended payment = minimum + any extra we can afford + upcoming spending
            # This prevents new debt from accumulating
            recommended_payment = cc.minimum_payment + upcoming_spending

            # Add safe extra payment if available
            safe_extra = self.calculate_safe_payment_amount().get(cc.id, 0)
            if safe_extra > 0:
                recommended_payment += safe_extra

            if cc.balance > 0 or upcoming_spending > 0:
                cc_actions.append(
                    {
                        "card_name": cc.name,
                        "due_date": cc_due,
                        "current_balance": cc.balance,
                        "upcoming_spending": upcoming_spending,
                        "minimum_payment": cc.minimum_payment,
                        "recommended_payment": min(
                            recommended_payment, cc.balance + upcoming_spending
                        ),
                        "apr": cc.apr,
                    }
                )
                total_cc_payments += min(
                    recommended_payment, cc.balance + upcoming_spending
                )

        # Get bills paid from checking
        checking_bills = []
        total_bill_payments = 0
        for bill_date, bill in self.get_upcoming_bills(days_ahead=30):
            if not bill.paid_by_credit:
                checking_bills.append(
                    {
                        "date": bill_date,
                        "name": bill.name,
                        "amount": bill.amount,
                        "autopay": bill.autopay,
                    }
                )
                total_bill_payments += bill.amount

        # Emergency fund status
        emergency_fund = self.calculate_emergency_fund()
        emergency_target = self.config.settings.emergency_fund_target

        return {
            "current_date": self.today,
            "checking_balance": checking_total,
            "savings_balance": savings_total,
            "cash_balance": cash_total,
            "total_debt": sum(cc.balance for cc in self.config.credit_cards),
            "emergency_fund": emergency_fund,
            "emergency_target": emergency_target,
            "emergency_pct": (
                (emergency_fund / emergency_target * 100) if emergency_target > 0 else 0
            ),
            "monthly_income": monthly_income,
            "total_income": total_income,
            "cc_actions": sorted(cc_actions, key=lambda x: x["due_date"]),
            "checking_bills": sorted(checking_bills, key=lambda x: x["date"]),
            "total_outflows": total_cc_payments + total_bill_payments,
            "net_monthly": total_income - (total_cc_payments + total_bill_payments),
        }
