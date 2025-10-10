#!/usr/bin/env python3
"""
Simulation-based financial optimizer.

This module provides a simulation engine that evaluates different financial strategies
by projecting 30 days forward and calculating the total interest cost for each strategy.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional
from enum import Enum
from copy import deepcopy
from models import FinancialConfig, CreditCard, Account, Bill, Income


class PaymentMethod(Enum):
    """Payment method for a transaction."""

    CHECKING = "checking"
    CREDIT_CARD = "credit_card"
    SPLIT = "split"


class OptimizationStrategy(Enum):
    """Strategy for optimizing payments."""

    AGGRESSIVE_DEBT = "aggressive_debt"  # Maximize debt payoff
    BALANCED = "balanced"  # Balance between debt and emergency fund
    EMERGENCY_FIRST = "emergency_first"  # Build emergency fund first


@dataclass
class FinancialState:
    """Snapshot of financial state at a point in time."""

    date: date
    account_balances: dict[str, float]  # account_id -> balance
    credit_card_balances: dict[str, float]  # card_id -> balance
    total_interest_paid: float = 0.0

    def get_total_checking(self) -> float:
        """Get total checking account balance."""
        return sum(
            bal
            for acc_id, bal in self.account_balances.items()
            if acc_id.startswith("checking") or "check" in acc_id.lower()
        )

    def get_total_savings(self) -> float:
        """Get total savings account balance."""
        return sum(
            bal
            for acc_id, bal in self.account_balances.items()
            if acc_id.startswith("savings") or "save" in acc_id.lower()
        )

    def get_total_debt(self) -> float:
        """Get total credit card debt."""
        return sum(self.credit_card_balances.values())


@dataclass
class PlannedTransaction:
    """A planned transaction (income or expense)."""

    date: date
    description: str
    amount: float  # Positive for income, negative for expense
    category: str
    required: bool = True
    preferred_account: Optional[str] = None
    can_use_credit: bool = False


@dataclass
class PaymentDecision:
    """Decision about how to pay for a transaction."""

    method: PaymentMethod
    checking_amount: float = 0.0
    credit_card_id: Optional[str] = None
    credit_amount: float = 0.0
    reason: str = ""


@dataclass
class DaySimulation:
    """Results of simulating a single day."""

    date: date
    starting_state: FinancialState
    transactions: list[tuple[PlannedTransaction, PaymentDecision]]
    ending_state: FinancialState
    interest_accrued: float = 0.0


@dataclass
class SimulationResult:
    """Results of a 30-day simulation."""

    strategy: OptimizationStrategy
    days: list[DaySimulation]
    total_interest_paid: float
    final_state: FinancialState
    warnings: list[str] = field(default_factory=list)
    failed: bool = False  # True if simulation violated constraints

    def get_total_debt_reduction(self) -> float:
        """Calculate total debt paid off during simulation."""
        if not self.days:
            return 0.0
        initial_debt = self.days[0].starting_state.get_total_debt()
        final_debt = self.final_state.get_total_debt()
        return initial_debt - final_debt


class FinancialSimulator:
    """Simulation engine for financial optimization."""

    def __init__(self, config: FinancialConfig, today: Optional[date] = None):
        self.config = config
        self.today = today or date.today()

    def create_initial_state(self) -> FinancialState:
        """Create initial financial state from config."""
        account_balances = {acc.id: acc.balance for acc in self.config.accounts}
        credit_card_balances = {cc.id: cc.balance for cc in self.config.credit_cards}

        return FinancialState(
            date=self.today,
            account_balances=account_balances,
            credit_card_balances=credit_card_balances,
            total_interest_paid=0.0,
        )

    def get_planned_transactions(
        self, days_ahead: int = 30, strategy: Optional[OptimizationStrategy] = None
    ) -> list[PlannedTransaction]:
        """Generate list of all planned transactions for the next N days.

        Parameters
        ----------
        days_ahead : int
            Number of days to plan ahead
        strategy : OptimizationStrategy, optional
            Strategy to use for extra payments. If provided, will add extra CC payments.
        """
        transactions = []
        end_date = self.today + timedelta(days=days_ahead)

        # Add income
        for inc in self.config.income:
            current_date = inc.next_date
            while current_date <= end_date:
                transactions.append(
                    PlannedTransaction(
                        date=current_date,
                        description=f"Income: {inc.source}",
                        amount=inc.amount,
                        category="income",
                        required=False,
                        preferred_account=(
                            inc.deposit_account or inc.get_splits()[0].account_id
                            if inc.get_splits()
                            else None
                        ),
                    )
                )

                # Calculate next occurrence
                if inc.frequency.value == "weekly":
                    current_date += timedelta(days=7)
                elif inc.frequency.value == "biweekly":
                    current_date += timedelta(days=14)
                elif inc.frequency.value == "monthly":
                    # Move to next month
                    month = current_date.month + 1
                    year = current_date.year
                    if month > 12:
                        month = 1
                        year += 1
                    try:
                        current_date = current_date.replace(month=month, year=year)
                    except ValueError:
                        # Handle day overflow (e.g., Jan 31 -> Feb 31)
                        import calendar

                        last_day = calendar.monthrange(year, month)[1]
                        current_date = date(year, month, last_day)
                else:
                    break

        # Add bills
        for bill in self.config.bills:
            # Get next due date
            from optimizer import FinancialOptimizer

            temp_optimizer = FinancialOptimizer(self.config)
            next_due = temp_optimizer.get_next_date(bill.due_day)

            while next_due <= end_date:
                # Skip bills paid by credit - they'll be handled as CC charges
                if bill.paid_by_credit:
                    # Bill is charged to credit card - create a CC charge transaction
                    # Note: The simulator will check if the card is over limit and handle accordingly
                    transactions.append(
                        PlannedTransaction(
                            date=next_due,
                            description=f"Bill: {bill.name} (charged to CC)",
                            amount=-bill.amount,
                            category="bill_on_credit",
                            required=True,
                            preferred_account=bill.payment_account,  # This is the CC ID
                            can_use_credit=False,  # Already on credit
                        )
                    )
                else:
                    # Bill paid from checking/savings
                    transactions.append(
                        PlannedTransaction(
                            date=next_due,
                            description=f"Bill: {bill.name}",
                            amount=-bill.amount,
                            category="bill",
                            required=True,
                            preferred_account=bill.payment_account,
                            can_use_credit=True,  # Can optionally use credit if cash is low
                        )
                    )

                # Calculate next occurrence
                if bill.frequency.value == "monthly":
                    next_due = temp_optimizer.get_next_date(
                        bill.due_day, next_due + timedelta(days=1)
                    )
                elif bill.frequency.value == "quarterly":
                    next_due = next_due + timedelta(days=90)
                elif bill.frequency.value == "annual":
                    next_due = next_due.replace(year=next_due.year + 1)
                else:
                    break

        # Add credit card minimum payments
        for cc in self.config.credit_cards:
            if cc.balance > 0:
                from optimizer import FinancialOptimizer

                temp_optimizer = FinancialOptimizer(self.config)
                next_due = temp_optimizer.get_next_date(cc.due_day)

                if next_due <= end_date:
                    transactions.append(
                        PlannedTransaction(
                            date=next_due,
                            description=f"CC Payment: {cc.name} ({cc.id})",  # Include ID for tracking
                            amount=-cc.minimum_payment,
                            category="cc_payment",  # Change to cc_payment so we can identify it
                            required=True,
                            preferred_account=cc.payment_account,
                            can_use_credit=False,  # Can't pay CC with another CC in this simple model
                        )
                    )

        return sorted(transactions, key=lambda x: x.date)

    def decide_payment_method(
        self,
        transaction: PlannedTransaction,
        state: FinancialState,
        future_transactions: list[PlannedTransaction],
        strategy: OptimizationStrategy,
    ) -> PaymentDecision:
        """
        Decide how to pay for a transaction (checking, credit, or split).

        Considers:
        - Available checking balance and minimum requirements
        - Available credit on cards
        - Future transactions to ensure we don't run out of money
        - Optimization strategy (minimize interest)
        """
        if transaction.amount > 0:
            # This is income - no payment decision needed (handled separately)
            return PaymentDecision(
                method=PaymentMethod.CHECKING,
                checking_amount=0,
                reason="Income deposit",
            )

        # Bill on credit - already charged to CC, no payment decision needed
        if transaction.category == "bill_on_credit":
            return PaymentDecision(
                method=PaymentMethod.CREDIT_CARD,
                credit_card_id=transaction.preferred_account,
                credit_amount=abs(transaction.amount),
                reason="Bill charged to credit card",
            )

        expense_amount = abs(transaction.amount)

        # Get checking account info
        checking_accounts = [
            acc for acc in self.config.accounts if acc.type.value == "checking"
        ]
        total_checking = sum(
            state.account_balances.get(acc.id, 0) for acc in checking_accounts
        )
        min_balance_required = sum(acc.minimum_balance for acc in checking_accounts)
        available_checking = total_checking - min_balance_required

        # Look ahead to calculate how much checking we'll need for upcoming required transactions
        # Be very conservative here to prevent any violations
        buffer_needed = 0.0
        for future_txn in future_transactions[
            :20
        ]:  # Look at next 20 transactions for better safety
            if future_txn.required and future_txn.amount < 0:
                buffer_needed += abs(future_txn.amount)

        # Adjust available checking for future needs (keep 75% buffer for extra safety)
        # This ensures we have enough for most upcoming expenses
        safe_checking = max(0, available_checking - (buffer_needed * 0.75))

        # Can we afford this from checking?
        can_afford_checking = safe_checking >= expense_amount

        if can_afford_checking and not transaction.can_use_credit:
            # Must use checking (e.g., CC payments)
            return PaymentDecision(
                method=PaymentMethod.CHECKING,
                checking_amount=expense_amount,
                reason="Required checking payment",
            )

        # Should we use credit card to preserve cash?
        # Strategy: Use credit for discretionary items if we have low cash or high APR cards
        if (
            transaction.can_use_credit
            and strategy == OptimizationStrategy.AGGRESSIVE_DEBT
        ):
            # In aggressive debt mode, avoid using credit cards - pay cash when possible
            if can_afford_checking:
                return PaymentDecision(
                    method=PaymentMethod.CHECKING,
                    checking_amount=expense_amount,
                    reason="Avoid credit to minimize debt",
                )

        # If we can't afford from checking, try credit card
        if not can_afford_checking and transaction.can_use_credit:
            # Find card with available credit (not over limit or has room)
            for cc in self.config.credit_cards:
                current_balance = state.credit_card_balances.get(cc.id, 0)

                # Skip cards that are already over limit
                if current_balance >= cc.credit_limit:
                    continue

                available_credit = cc.credit_limit - current_balance

                if available_credit >= expense_amount:
                    return PaymentDecision(
                        method=PaymentMethod.CREDIT_CARD,
                        credit_card_id=cc.id,
                        credit_amount=expense_amount,
                        reason=f"Use credit - insufficient checking (need ${expense_amount:.2f}, have ${safe_checking:.2f})",
                    )

        # Need to split between checking and credit
        if transaction.can_use_credit and safe_checking > 0:
            # Only use what we actually need from checking (up to expense amount)
            checking_part = min(safe_checking, expense_amount)
            credit_part = max(0, expense_amount - checking_part)

            # If no credit part needed, just pay from checking
            if credit_part == 0:
                return PaymentDecision(
                    method=PaymentMethod.CHECKING,
                    checking_amount=checking_part,
                    reason=f"Pay from checking (${checking_part:.2f})",
                )

            # Find card with available credit for the remainder (skip over-limit cards)
            for cc in self.config.credit_cards:
                current_balance = state.credit_card_balances.get(cc.id, 0)

                # Skip cards already over limit
                if current_balance >= cc.credit_limit:
                    continue

                available_credit = cc.credit_limit - current_balance

                if available_credit >= credit_part:
                    return PaymentDecision(
                        method=PaymentMethod.SPLIT,
                        checking_amount=checking_part,
                        credit_card_id=cc.id,
                        credit_amount=credit_part,
                        reason=f"Split payment: ${checking_part:.2f} checking + ${credit_part:.2f} credit",
                    )

        # Default: use checking even if it violates constraints (will generate warning)
        return PaymentDecision(
            method=PaymentMethod.CHECKING,
            checking_amount=expense_amount,
            reason="⚠️ WARNING: May violate minimum balance",
        )

    def calculate_daily_interest(self, state: FinancialState) -> float:
        """Calculate interest accrued for one day on all credit cards."""
        total_interest = 0.0
        for cc in self.config.credit_cards:
            balance = state.credit_card_balances.get(cc.id, 0)
            if balance > 0:
                daily_rate = cc.apr / 365
                interest = balance * daily_rate
                total_interest += interest
        return total_interest

    def check_constraints(
        self, state: FinancialState, previous_state: Optional[FinancialState] = None
    ) -> tuple[bool, list[str]]:
        """
        Check if a financial state violates any constraints.

        Parameters
        ----------
        state : FinancialState
            Current financial state to check
        previous_state : FinancialState, optional
            Previous day's state (to check if we made things worse)

        Returns
        -------
        tuple[bool, list[str]]
            (is_valid, list of violation messages)
        """
        violations = []

        # Check account minimum balances - always enforce
        for acc in self.config.accounts:
            balance = state.account_balances.get(acc.id, 0)
            if balance < acc.minimum_balance:
                violations.append(
                    f"{state.date}: {acc.name} below minimum (${balance:.2f} < ${acc.minimum_balance:.2f})"
                )

        # Check credit card limits - but allow cards already over limit to stay/decrease
        for cc in self.config.credit_cards:
            current_balance = state.credit_card_balances.get(cc.id, 0)

            if current_balance > cc.credit_limit:
                # Card is over limit - check if we made it worse
                if previous_state:
                    previous_balance = previous_state.credit_card_balances.get(cc.id, 0)
                    if current_balance > previous_balance:
                        # We INCREASED the balance while over limit - that's a violation
                        violations.append(
                            f"{state.date}: {cc.name} increased while over limit "
                            f"(${previous_balance:.2f} → ${current_balance:.2f}, limit ${cc.credit_limit:.2f})"
                        )
                else:
                    # No previous state (first day) - only fail if we're significantly over
                    # Allow some wiggle room for initial state (interest, fees, etc)
                    if current_balance > cc.credit_limit * 1.01:  # 1% tolerance
                        violations.append(
                            f"{state.date}: {cc.name} over limit (${current_balance:.2f} > ${cc.credit_limit:.2f})"
                        )

        return (len(violations) == 0, violations)

    def calculate_extra_cc_payments(
        self,
        current_state: FinancialState,
        current_date: date,
        future_transactions: list[PlannedTransaction],
        strategy: OptimizationStrategy,
    ) -> list[PlannedTransaction]:
        """
        Calculate extra CC payments that can be safely made without compromising future obligations.

        Looks ahead at all required future transactions and ensures we maintain adequate cash reserves.

        Parameters
        ----------
        current_state : FinancialState
            Current financial state after all regular transactions for the day
        current_date : date
            Current date in the simulation
        future_transactions : list[PlannedTransaction]
            All upcoming transactions to consider
        strategy : OptimizationStrategy
            Strategy to use for prioritizing payments

        Returns
        -------
        list[PlannedTransaction]
            Extra payment transactions to add for today
        """
        extra_payments = []

        # Get current checking balance
        checking_accounts = [
            acc for acc in self.config.accounts if acc.type.value == "checking"
        ]
        total_checking = sum(
            current_state.account_balances.get(acc.id, 0) for acc in checking_accounts
        )
        min_balance_required = sum(acc.minimum_balance for acc in checking_accounts)
        available_checking = total_checking - min_balance_required

        # Calculate total required payments coming up (look 30 days ahead)
        # Be VERY conservative - we need to ensure we NEVER go negative
        future_required_amount = 0.0
        future_income_amount = 0.0
        cutoff_date = current_date + timedelta(days=30)

        for txn in future_transactions:
            if txn.date > cutoff_date:
                break
            if txn.required and txn.amount < 0:
                future_required_amount += abs(txn.amount)
            elif txn.amount > 0:
                future_income_amount += txn.amount

        # Calculate safe amount VERY conservatively
        # We want: current + future_income - future_required - buffer > min_balance
        # So safe = current - min_required + future_income - future_required - buffer
        # Simplify: safe = available + future_net - buffer

        # Use a large buffer to ensure we never violate constraints
        # Include minimum balance in the buffer calculation
        safety_buffer = max(
            1000, min_balance_required * 1.5
        )  # At least $1000 or 150% of min balance

        net_future_cash = future_income_amount - future_required_amount

        # Safe amount = what we have available now + net future cash - safety buffer
        # This ensures we maintain minimum balances plus extra cushion
        safe_amount = max(0, available_checking + net_future_cash - safety_buffer)

        # Don't make extra payments if we don't have significant cushion
        if safe_amount < 100:
            return []

        # Prioritize cards based on strategy
        cards_with_balance = [
            cc
            for cc in self.config.credit_cards
            if current_state.credit_card_balances.get(cc.id, 0) > 0
        ]

        if strategy == OptimizationStrategy.AGGRESSIVE_DEBT:
            # Highest APR first
            cards_with_balance.sort(key=lambda x: x.apr, reverse=True)
            allocation_pct = 0.8  # Use 80% of safe amount for debt
        elif strategy == OptimizationStrategy.BALANCED:
            # Balance between APR and balance
            cards_with_balance.sort(
                key=lambda x: (x.apr * 0.6 + (x.balance / 10000) * 0.4), reverse=True
            )
            allocation_pct = 0.5  # Use 50% of safe amount for debt
        else:  # EMERGENCY_FIRST
            # Only pay debt with leftover
            cards_with_balance.sort(key=lambda x: x.balance)
            allocation_pct = 0.2  # Use 20% of safe amount for debt

        remaining = safe_amount * allocation_pct

        # Allocate to cards
        for cc in cards_with_balance:
            if remaining <= 20:  # Don't bother with tiny payments
                break

            current_balance = current_state.credit_card_balances.get(cc.id, 0)
            if current_balance <= 0:
                continue

            # Calculate payment amount - don't pay more than the balance
            payment_amount = min(remaining, current_balance)

            if payment_amount >= 20:  # Minimum $20 extra payment
                # Create extra payment transaction
                extra_payments.append(
                    PlannedTransaction(
                        date=current_date,
                        description=f"CC Extra Payment: {cc.name} ({cc.id})",
                        amount=-payment_amount,
                        category="cc_extra_payment",
                        required=False,
                        preferred_account=cc.payment_account,
                        can_use_credit=False,
                    )
                )
                remaining -= payment_amount

        return extra_payments

    def simulate_day(
        self,
        current_state: FinancialState,
        day_transactions: list[PlannedTransaction],
        all_future_transactions: list[PlannedTransaction],
        strategy: OptimizationStrategy,
    ) -> DaySimulation:
        """Simulate a single day with all its transactions."""
        starting_state = deepcopy(current_state)
        working_state = deepcopy(current_state)
        processed = []

        for txn in day_transactions:
            # Skip CC payments if card has $0 balance (already paid off)
            if (
                txn.category == "cc_payment"
                and "(" in txn.description
                and ")" in txn.description
            ):
                cc_id = txn.description.split("(")[1].split(")")[0]
                if cc_id in working_state.credit_card_balances:
                    if working_state.credit_card_balances[cc_id] <= 0:
                        # Card already paid off, skip this payment
                        continue

            # Decide how to pay
            decision = self.decide_payment_method(
                txn, working_state, all_future_transactions, strategy
            )

            # Apply the transaction to working state
            if txn.amount > 0:
                # Income - deposit to preferred account or first checking
                if (
                    txn.preferred_account
                    and txn.preferred_account in working_state.account_balances
                ):
                    working_state.account_balances[txn.preferred_account] += txn.amount
                else:
                    checking_accounts = [
                        acc
                        for acc in self.config.accounts
                        if acc.type.value == "checking"
                    ]
                    if checking_accounts:
                        working_state.account_balances[
                            checking_accounts[0].id
                        ] += txn.amount
            else:
                # Expense - apply according to decision
                # Special case: CC payments reduce debt instead of increasing it
                is_cc_payment = (
                    txn.category == "cc_payment" or txn.category == "cc_extra_payment"
                )

                # Special case: Bills on credit just add to CC balance
                if txn.category == "bill_on_credit":
                    # Check if the card is already at/over limit - if so, pay from checking instead
                    if (
                        txn.preferred_account
                        and txn.preferred_account in working_state.credit_card_balances
                    ):
                        current_cc_balance = working_state.credit_card_balances[
                            txn.preferred_account
                        ]
                        cc = next(
                            (
                                c
                                for c in self.config.credit_cards
                                if c.id == txn.preferred_account
                            ),
                            None,
                        )

                        if cc and current_cc_balance >= cc.credit_limit:
                            # Card is at or over limit - pay from checking instead to avoid making it worse
                            checking_accounts = [
                                acc
                                for acc in self.config.accounts
                                if acc.type.value == "checking"
                            ]
                            if checking_accounts:
                                acc_id = checking_accounts[0].id
                                working_state.account_balances[acc_id] -= abs(
                                    txn.amount
                                )
                        else:
                            # Card has room - charge to it normally
                            working_state.credit_card_balances[
                                txn.preferred_account
                            ] += abs(txn.amount)
                    # No more processing needed for bill_on_credit
                elif decision.method == PaymentMethod.CHECKING:
                    # Pay from checking account (subtract expense_amount)
                    checking_accounts = [
                        acc
                        for acc in self.config.accounts
                        if acc.type.value == "checking"
                    ]
                    if checking_accounts:
                        acc_id = checking_accounts[0].id
                        working_state.account_balances[
                            acc_id
                        ] -= decision.checking_amount

                    # If this is a CC payment, also reduce the CC balance
                    if (
                        is_cc_payment
                        and "(" in txn.description
                        and ")" in txn.description
                    ):
                        # Extract CC ID from description like "CC Payment: Visa Card (cc_1)"
                        cc_id = txn.description.split("(")[1].split(")")[0]
                        if cc_id in working_state.credit_card_balances:
                            working_state.credit_card_balances[
                                cc_id
                            ] -= decision.checking_amount

                elif decision.method == PaymentMethod.CREDIT_CARD:
                    # Charge to credit card (increases debt)
                    if decision.credit_card_id:
                        working_state.credit_card_balances[
                            decision.credit_card_id
                        ] += decision.credit_amount

                elif decision.method == PaymentMethod.SPLIT:
                    # Split between checking and credit
                    checking_accounts = [
                        acc
                        for acc in self.config.accounts
                        if acc.type.value == "checking"
                    ]
                    if checking_accounts:
                        acc_id = checking_accounts[0].id
                        working_state.account_balances[
                            acc_id
                        ] -= decision.checking_amount
                    if decision.credit_card_id:
                        working_state.credit_card_balances[
                            decision.credit_card_id
                        ] += decision.credit_amount

            processed.append((txn, decision))

        # After processing all regular transactions, check if we should make extra CC payments
        # Only do this on days when we made a CC minimum payment (CC due dates)
        has_cc_payment = any(txn.category == "cc_payment" for txn in day_transactions)

        if has_cc_payment:
            extra_payments = self.calculate_extra_cc_payments(
                working_state, current_state.date, all_future_transactions, strategy
            )

            # Process extra payments
            for extra_txn in extra_payments:
                decision = self.decide_payment_method(
                    extra_txn, working_state, all_future_transactions, strategy
                )

                # Apply extra payment
                if decision.method == PaymentMethod.CHECKING:
                    checking_accounts = [
                        acc
                        for acc in self.config.accounts
                        if acc.type.value == "checking"
                    ]
                    if checking_accounts:
                        acc_id = checking_accounts[0].id
                        working_state.account_balances[
                            acc_id
                        ] -= decision.checking_amount

                    # Reduce CC balance
                    if "(" in extra_txn.description and ")" in extra_txn.description:
                        cc_id = extra_txn.description.split("(")[1].split(")")[0]
                        if cc_id in working_state.credit_card_balances:
                            working_state.credit_card_balances[
                                cc_id
                            ] -= decision.checking_amount

                processed.append((extra_txn, decision))

        # Calculate interest for the day
        interest = self.calculate_daily_interest(working_state)
        working_state.total_interest_paid += interest

        # Note: Constraint checking is done at the simulation level, not here
        # This allows us to try the entire day and see if it works

        return DaySimulation(
            date=current_state.date,
            starting_state=starting_state,
            transactions=processed,
            ending_state=working_state,
            interest_accrued=interest,
        )

    def run_simulation(
        self, strategy: OptimizationStrategy, days_ahead: int = 30
    ) -> SimulationResult:
        """Run a complete simulation with the given strategy."""
        current_state = self.create_initial_state()
        all_transactions = self.get_planned_transactions(days_ahead)

        day_results = []
        warnings = []
        failed = False
        previous_day_state = None

        for day_offset in range(days_ahead + 1):
            current_date = self.today + timedelta(days=day_offset)

            # Get transactions for this day
            day_txns = [t for t in all_transactions if t.date == current_date]

            # Get all future transactions
            future_txns = [t for t in all_transactions if t.date > current_date]

            # Simulate the day
            day_sim = self.simulate_day(current_state, day_txns, future_txns, strategy)
            day_results.append(day_sim)

            # Check for constraint violations, comparing to previous day
            # Skip checking on the very first day - we accept the starting state as-is
            if day_offset > 0:
                is_valid, violations = self.check_constraints(
                    day_sim.ending_state, previous_day_state
                )
                if not is_valid:
                    # HARD FAIL - this simulation is invalid
                    warnings.extend(violations)
                    failed = True
                    # Stop the simulation - no point continuing with invalid state
                    break

            # Update state for next day
            previous_day_state = day_sim.ending_state  # Track previous state
            current_state = day_sim.ending_state
            current_state.date = current_date + timedelta(days=1)

        return SimulationResult(
            strategy=strategy,
            days=day_results,
            total_interest_paid=current_state.total_interest_paid,
            final_state=current_state,
            warnings=warnings,
            failed=failed,
        )

    def find_optimal_strategy(self, days_ahead: int = 30) -> SimulationResult:
        """Run simulations for all strategies and return the one with lowest interest cost.

        Only considers valid simulations (no constraint violations). If all simulations
        fail, returns the one that made it furthest before failing.
        """
        results = []

        for strategy in OptimizationStrategy:
            result = self.run_simulation(strategy, days_ahead)
            results.append(result)

        # Filter out failed simulations
        valid_results = [r for r in results if not r.failed]

        if not valid_results:
            # All simulations failed - return the one that made it furthest
            # (most days completed before failure)
            return max(results, key=lambda r: len(r.days))

        # Among valid results, pick the one with lowest interest
        optimal = min(valid_results, key=lambda r: r.total_interest_paid)

        return optimal
