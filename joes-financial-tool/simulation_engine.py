#!/usr/bin/env python3
"""
Monte Carlo simulation engine for investment strategies.

Simulates the "float strategy" where income is invested briefly before withdrawal.
"""

import random
from datetime import date, timedelta
from dataclasses import dataclass, field
from typing import Optional
import math

from models import FinancialConfig, InvestmentSimulation, Income, Frequency

# Try to import Rust acceleration module
try:
    import simulation_rust
    RUST_AVAILABLE = True
    print("✓ Rust acceleration available")
except ImportError:
    RUST_AVAILABLE = False
    print("ℹ️  Using Python implementation (Rust not available)")


@dataclass
class SimulationEvent:
    """Single event in the simulation (buy, sell, dividend)."""

    date: date
    event_type: str  # 'buy', 'sell', 'dividend'
    shares: float
    price_per_share: float
    amount: float  # Dollar amount (positive = inflow, negative = outflow)
    tax_owed: float = 0.0
    notes: str = ""


@dataclass
class SingleRunResult:
    """Results from one Monte Carlo simulation run."""

    run_number: int
    final_age: int
    final_account_value: float
    total_invested: float  # Total dollars put in
    total_withdrawn: float  # Total dollars taken out
    total_taxes_paid: float
    total_dividends: float
    events: list[SimulationEvent] = field(default_factory=list)

    @property
    def net_gain(self) -> float:
        """Net gain/loss from the strategy."""
        return self.final_account_value + self.total_withdrawn - self.total_invested - self.total_taxes_paid


@dataclass
class MonteCarloResults:
    """Aggregated results from multiple simulation runs."""

    simulation_config: InvestmentSimulation
    runs: list[SingleRunResult]
    target_age: int

    @property
    def num_runs(self) -> int:
        return len(self.runs)

    def get_percentile(self, percentile: float, metric: str = "final_account_value") -> float:
        """Get percentile value for a specific metric."""
        values = sorted([getattr(run, metric) for run in self.runs])
        index = int(len(values) * (percentile / 100.0))
        return values[min(index, len(values) - 1)]

    def get_statistics(self) -> dict:
        """Get summary statistics across all runs."""
        final_values = [run.final_account_value for run in self.runs]
        net_gains = [run.net_gain for run in self.runs]

        return {
            "target_age": self.target_age,
            "num_runs": self.num_runs,
            "final_value": {
                "min": min(final_values),
                "p10": self.get_percentile(10, "final_account_value"),
                "p25": self.get_percentile(25, "final_account_value"),
                "median": self.get_percentile(50, "final_account_value"),
                "p75": self.get_percentile(75, "final_account_value"),
                "p90": self.get_percentile(90, "final_account_value"),
                "max": max(final_values),
                "mean": sum(final_values) / len(final_values),
            },
            "net_gain": {
                "min": min(net_gains),
                "p10": self.get_percentile(10, "net_gain"),
                "median": self.get_percentile(50, "net_gain"),
                "p90": self.get_percentile(90, "net_gain"),
                "max": max(net_gains),
                "mean": sum(net_gains) / len(net_gains),
            },
            "total_invested": {
                "mean": sum(run.total_invested for run in self.runs) / len(self.runs),
            },
            "total_withdrawn": {
                "mean": sum(run.total_withdrawn for run in self.runs) / len(self.runs),
            },
            "total_taxes": {
                "mean": sum(run.total_taxes_paid for run in self.runs) / len(self.runs),
            },
        }


class SimulationEngine:
    """Monte Carlo simulation engine for float investment strategy."""

    def __init__(self, config: FinancialConfig, simulation: InvestmentSimulation):
        self.config = config
        self.simulation = simulation
        self.start_date = date.today()

    def get_next_income_date(self, income: Income, after_date: date) -> Optional[date]:
        """Calculate next income date after given date."""
        current = income.next_date

        # Find first occurrence after after_date
        while current <= after_date:
            if income.frequency == Frequency.WEEKLY:
                current += timedelta(days=7)
            elif income.frequency == Frequency.BIWEEKLY:
                current += timedelta(days=14)
            elif income.frequency == Frequency.SEMI_MONTHLY:
                # Approximate as 15 days
                current += timedelta(days=15)
            elif income.frequency == Frequency.MONTHLY:
                # Move to next month, same day
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    try:
                        current = current.replace(month=current.month + 1)
                    except ValueError:
                        # Day doesn't exist in next month
                        import calendar
                        next_month = current.month + 1
                        year = current.year
                        if next_month > 12:
                            next_month = 1
                            year += 1
                        last_day = calendar.monthrange(year, next_month)[1]
                        current = date(year, next_month, min(current.day, last_day))
            else:
                return None

        return current

    def get_liquidation_date(self, after_date: date) -> date:
        """Get next liquidation date based on strategy."""
        if self.simulation.strategy_type == "constant_hold":
            # Simple: hold for fixed number of days
            return after_date + timedelta(days=self.simulation.hold_days)
        else:
            # monthly_liquidation: sell on specific day of month
            liquidation_day = self.simulation.liquidation_day

            # Start with next month
            if after_date.month == 12:
                target_month = 1
                target_year = after_date.year + 1
            else:
                target_month = after_date.month + 1
                target_year = after_date.year

            # Handle day overflow (e.g., day 31 in month with 30 days)
            import calendar
            last_day = calendar.monthrange(target_year, target_month)[1]
            target_day = min(liquidation_day, last_day)

            liquidation = date(target_year, target_month, target_day)

            # Skip weekends
            while liquidation.weekday() >= 5:
                liquidation += timedelta(days=1)

            return liquidation

    def simulate_price_path(self, start_date: date, end_date: date, start_price: float = 450.0) -> dict[date, float]:
        """
        Simulate SPY price path using geometric Brownian motion.

        Returns dict mapping date -> price
        """
        prices = {}
        current_price = start_price
        current_date = start_date

        # Daily parameters from annual
        daily_return = self.simulation.expected_annual_return / 252  # 252 trading days
        daily_volatility = self.simulation.annual_volatility / math.sqrt(252)
        daily_expense = self.simulation.expense_ratio / 252

        while current_date <= end_date:
            # Skip weekends
            if current_date.weekday() < 5:
                # Geometric Brownian motion
                random_shock = random.gauss(0, 1)
                drift = (daily_return - daily_expense - 0.5 * daily_volatility ** 2)
                diffusion = daily_volatility * random_shock
                price_change = current_price * (drift + diffusion)
                current_price = max(1.0, current_price + price_change)  # Floor at $1

            prices[current_date] = current_price
            current_date += timedelta(days=1)

        return prices

    def calculate_tax(self, cost_basis: float, sale_proceeds: float, hold_days: int) -> float:
        """Calculate capital gains tax."""
        gain = sale_proceeds - cost_basis

        if gain <= 0:
            return 0.0  # No tax on losses

        # Determine tax rate based on holding period
        if hold_days >= 365:
            tax_rate = self.simulation.long_term_cap_gains_rate
        else:
            tax_rate = self.simulation.short_term_cap_gains_rate

        return gain * tax_rate

    def generate_dividend_dates(self, start_date: date, end_date: date) -> list[date]:
        """
        Generate quarterly dividend payment dates for SPY.
        SPY typically pays dividends in late March, June, September, December.
        """
        dividend_dates = []
        # Use the 3rd Friday of the last month of each quarter (approximate SPY schedule)
        months = [3, 6, 9, 12]  # March, June, September, December

        current_year = start_date.year
        end_year = end_date.year

        for year in range(current_year, end_year + 1):
            for month in months:
                # Find 3rd Friday of the month
                # Start with the 15th (earliest the 3rd Friday can be)
                candidate = date(year, month, 15)
                # Find the first Friday on or after the 15th
                days_until_friday = (4 - candidate.weekday()) % 7
                dividend_date = candidate + timedelta(days=days_until_friday)

                # Check if in range
                if start_date <= dividend_date <= end_date:
                    dividend_dates.append(dividend_date)

        return sorted(dividend_dates)

    def run_single_simulation(self, run_number: int, target_age: int) -> SingleRunResult:
        """Run single Monte Carlo simulation to target age."""
        # Set random seed for reproducibility if specified
        if self.simulation.random_seed is not None:
            random.seed(self.simulation.random_seed + run_number)

        years_to_simulate = target_age - self.simulation.current_age
        end_date = self.start_date + timedelta(days=years_to_simulate * 365)

        # Generate price path
        prices = self.simulate_price_path(self.start_date, end_date)

        # Get income sources to use
        income_sources = [
            inc for inc in self.config.income
            if inc.id in self.simulation.income_source_ids
        ]

        # Validate income sources (only in first run to avoid spam)
        if run_number == 0:
            if not income_sources and self.simulation.income_source_ids:
                print(f"\n⚠️  WARNING: No income sources matched!")
                print(f"   Simulation expects IDs: {self.simulation.income_source_ids}")
                print(f"   Available income IDs: {[inc.id for inc in self.config.income]}")
                print(f"   Only the initial balance of ${self.simulation.initial_balance:,.2f} will be invested.\n")
            elif not income_sources and self.simulation.initial_balance == 0:
                raise ValueError("No income sources and no initial balance configured - nothing to invest!")

        # Track state
        events = []
        shares_held = 0.0
        purchase_lots = []  # List of (lot_id, shares, cost_basis_per_share, purchase_date)
        total_invested = 0.0
        total_withdrawn = 0.0
        total_taxes_paid = 0.0
        total_dividends = 0.0

        # Handle initial balance - convert to shares at starting price
        if self.simulation.initial_balance > 0:
            start_price = prices[self.start_date]
            initial_shares = self.simulation.initial_balance / start_price
            shares_held = initial_shares
            purchase_lots.append(("initial", initial_shares, start_price, self.start_date))
            total_invested = self.simulation.initial_balance

            events.append(SimulationEvent(
                date=self.start_date,
                event_type='buy',
                shares=initial_shares,
                price_per_share=start_price,
                amount=-self.simulation.initial_balance,
                notes=f"Initial investment"
            ))

        # Generate all income events with growth applied
        income_events = []
        for income_source in income_sources:
            current_date = self.start_date
            while current_date <= end_date:
                next_income = self.get_next_income_date(income_source, current_date)
                if next_income is None or next_income > end_date:
                    break

                # Apply income growth based on years elapsed
                years_elapsed = (next_income - self.start_date).days / 365.0
                growth_periods = int(years_elapsed / self.simulation.income_growth_frequency) if self.simulation.income_growth_frequency > 0 else 0
                income_multiplier = (1 + self.simulation.income_growth_rate) ** growth_periods
                adjusted_amount = income_source.amount * income_multiplier

                income_events.append((next_income, adjusted_amount, income_source.id))
                current_date = next_income

        # Sort income events by date
        income_events.sort(key=lambda x: x[0])

        # Generate dividend payment dates
        dividend_dates = self.generate_dividend_dates(self.start_date, end_date)

        # Process events in chronological order (income deposits and dividends)
        all_events = [(d, 'income', amt, iid) for d, amt, iid in income_events]
        all_events += [(d, 'dividend', None, None) for d in dividend_dates]
        all_events.sort(key=lambda x: x[0])

        for event_date, event_type, event_amount, event_id in all_events:
            # Skip weekends
            if event_date.weekday() >= 5:
                continue

            if event_type == 'dividend':
                # Calculate dividend payment based on shares held
                if shares_held > 0:
                    # Quarterly dividend = annual yield / 4
                    quarterly_yield = self.simulation.annual_dividend_yield / 4.0
                    current_price = prices.get(event_date, prices[min(prices.keys(), key=lambda d: abs((d - event_date).days))])
                    dividend_per_share = current_price * quarterly_yield
                    dividend_amount = shares_held * dividend_per_share

                    # Apply dividend tax
                    dividend_tax = dividend_amount * self.simulation.dividend_tax_rate
                    net_dividend = dividend_amount - dividend_tax

                    total_dividends += dividend_amount
                    total_taxes_paid += dividend_tax

                    # Reinvest net dividend
                    if net_dividend > 0:
                        shares_to_buy = net_dividend / current_price
                        lot_id = f"{event_date.isoformat()}_dividend"
                        purchase_lots.append((lot_id, shares_to_buy, current_price, event_date))
                        shares_held += shares_to_buy

                        events.append(SimulationEvent(
                            date=event_date,
                            event_type='dividend',
                            shares=shares_to_buy,
                            price_per_share=current_price,
                            amount=dividend_amount,
                            tax_owed=dividend_tax,
                            notes=f"Dividend ${dividend_amount:.2f}, reinvested ${net_dividend:.2f}"
                        ))

                continue

            # Process income event (existing logic)
            income_date = event_date
            income_amount = event_amount
            income_id = event_id

            # BUY: Invest the income
            buy_price = prices.get(income_date, prices[min(prices.keys(), key=lambda d: abs((d - income_date).days))])
            shares_to_buy = income_amount / buy_price

            # Record purchase lot
            lot_id = f"{income_date.isoformat()}_{income_id}"
            purchase_lots.append((lot_id, shares_to_buy, buy_price, income_date))

            shares_held += shares_to_buy
            total_invested += income_amount

            events.append(SimulationEvent(
                date=income_date,
                event_type='buy',
                shares=shares_to_buy,
                price_per_share=buy_price,
                amount=-income_amount,
                notes=f"Invested {income_id} paycheck"
            ))

            # SELL: Liquidate on next liquidation date (or skip for principal_only)
            # For principal_only strategy, we batch liquidations monthly rather than per-income
            if self.simulation.strategy_type != "principal_only":
                # Standard liquidation per income event
                liquidation_date = self.get_liquidation_date(income_date)
                if liquidation_date > end_date:
                    continue

                # Skip weekends
                while liquidation_date.weekday() >= 5:
                    liquidation_date += timedelta(days=1)

                sell_price = prices.get(liquidation_date, prices[min(prices.keys(), key=lambda d: abs((d - liquidation_date).days))])

                # Calculate how many shares to sell to get income_amount back
                shares_to_sell = min(shares_held, income_amount / sell_price)
                sale_proceeds = shares_to_sell * sell_price

                # Calculate tax (FIFO basis) - sell from oldest lots first
                tax_owed = 0.0
                shares_remaining_to_sell = shares_to_sell
                lots_to_update = []

                for i, (lot_id, lot_shares, lot_cost_basis, lot_purchase_date) in enumerate(purchase_lots):
                    if shares_remaining_to_sell <= 1e-8:  # Use small epsilon for float comparison
                        break

                    # Determine how many shares from this lot to sell
                    shares_from_this_lot = min(shares_remaining_to_sell, lot_shares)

                    # Calculate proceeds and cost for this portion
                    lot_sale_proceeds = shares_from_this_lot * sell_price
                    lot_cost = shares_from_this_lot * lot_cost_basis

                    # Calculate holding period and tax
                    hold_days = (liquidation_date - lot_purchase_date).days
                    tax_owed += self.calculate_tax(lot_cost, lot_sale_proceeds, hold_days)

                    # Update lot
                    remaining_shares = lot_shares - shares_from_this_lot
                    if remaining_shares > 1e-8:
                        # Partial sale - keep remaining shares
                        lots_to_update.append((i, lot_id, remaining_shares, lot_cost_basis, lot_purchase_date))
                    else:
                        # Full sale - mark for removal
                        lots_to_update.append((i, None, 0, 0, None))

                    shares_remaining_to_sell -= shares_from_this_lot

                # Apply updates to purchase_lots (in reverse to avoid index issues)
                new_lots = []
                for i, (lot_id, lot_shares, lot_cost_basis, lot_purchase_date) in enumerate(purchase_lots):
                    # Check if this lot was updated
                    updated = False
                    for update_idx, update_lot_id, update_shares, update_cost, update_date in lots_to_update:
                        if i == update_idx:
                            if update_lot_id is not None:  # Keep remaining shares
                                new_lots.append((update_lot_id, update_shares, update_cost, update_date))
                            updated = True
                            break
                    if not updated:
                        new_lots.append((lot_id, lot_shares, lot_cost_basis, lot_purchase_date))

                purchase_lots = new_lots
                shares_held -= shares_to_sell
                total_withdrawn += sale_proceeds
                total_taxes_paid += tax_owed

                events.append(SimulationEvent(
                    date=liquidation_date,
                    event_type='sell',
                    shares=shares_to_sell,
                    price_per_share=sell_price,
                    amount=sale_proceeds,
                    tax_owed=tax_owed,
                    notes=f"Liquidated for expenses (held {(liquidation_date - income_date).days} days)"
                ))

        # For principal_only strategy, process batched monthly liquidations
        if self.simulation.strategy_type == "principal_only":
            # Group income events by liquidation month and calculate principal to recover
            liquidation_groups = {}  # {liquidation_date: [(income_date, income_amount), ...]}

            for income_date, income_amount, income_id in income_events:
                # Calculate NEXT liquidation date after the income date
                # Start with the liquidation day in the income month
                liquidation_date = date(income_date.year, income_date.month, self.simulation.liquidation_day)

                # Adjust if liquidation_day doesn't exist in this month
                import calendar
                last_day = calendar.monthrange(liquidation_date.year, liquidation_date.month)[1]
                if self.simulation.liquidation_day > last_day:
                    liquidation_date = liquidation_date.replace(day=last_day)

                # If the liquidation date is on or before the income date, move to next month
                if liquidation_date <= income_date:
                    if liquidation_date.month == 12:
                        liquidation_date = date(liquidation_date.year + 1, 1, self.simulation.liquidation_day)
                    else:
                        next_month = liquidation_date.month + 1
                        last_day_next = calendar.monthrange(liquidation_date.year, next_month)[1]
                        liquidation_date = date(
                            liquidation_date.year,
                            next_month,
                            min(self.simulation.liquidation_day, last_day_next)
                        )

                # Skip weekends
                while liquidation_date.weekday() >= 5:
                    liquidation_date += timedelta(days=1)

                # Only process if liquidation date is within simulation period
                if self.start_date <= liquidation_date <= end_date:
                    if liquidation_date not in liquidation_groups:
                        liquidation_groups[liquidation_date] = []
                    liquidation_groups[liquidation_date].append((income_date, income_amount, income_id))

            # Process each liquidation date
            for liquidation_date in sorted(liquidation_groups.keys()):
                income_list = liquidation_groups[liquidation_date]
                total_principal_to_recover = sum(amt for _, amt, _ in income_list)

                # Get price at liquidation date
                sell_price = prices.get(liquidation_date, prices[min(prices.keys(), key=lambda d: abs((d - liquidation_date).days))])

                # Calculate how many shares we need to sell to recover principal
                # This is the key difference: we only sell enough to get the principal back
                shares_needed_for_principal = total_principal_to_recover / sell_price
                shares_to_sell = min(shares_held, shares_needed_for_principal)

                if shares_to_sell < 1e-8:  # Skip if nothing to sell
                    continue

                sale_proceeds = shares_to_sell * sell_price

                # Calculate tax (FIFO basis) - sell from oldest lots first
                tax_owed = 0.0
                shares_remaining_to_sell = shares_to_sell
                lots_to_update = []

                for i, (lot_id, lot_shares, lot_cost_basis, lot_purchase_date) in enumerate(purchase_lots):
                    if shares_remaining_to_sell <= 1e-8:
                        break

                    # Determine how many shares from this lot to sell
                    shares_from_this_lot = min(shares_remaining_to_sell, lot_shares)

                    # Calculate proceeds and cost for this portion
                    lot_sale_proceeds = shares_from_this_lot * sell_price
                    lot_cost = shares_from_this_lot * lot_cost_basis

                    # Calculate holding period and tax
                    hold_days = (liquidation_date - lot_purchase_date).days
                    tax_owed += self.calculate_tax(lot_cost, lot_sale_proceeds, hold_days)

                    # Update lot
                    remaining_shares = lot_shares - shares_from_this_lot
                    if remaining_shares > 1e-8:
                        # Partial sale - keep remaining shares
                        lots_to_update.append((i, lot_id, remaining_shares, lot_cost_basis, lot_purchase_date))
                    else:
                        # Full sale - mark for removal
                        lots_to_update.append((i, None, 0, 0, None))

                    shares_remaining_to_sell -= shares_from_this_lot

                # Apply updates to purchase_lots
                new_lots = []
                for i, (lot_id, lot_shares, lot_cost_basis, lot_purchase_date) in enumerate(purchase_lots):
                    updated = False
                    for update_idx, update_lot_id, update_shares, update_cost, update_date in lots_to_update:
                        if i == update_idx:
                            if update_lot_id is not None:  # Keep remaining shares
                                new_lots.append((update_lot_id, update_shares, update_cost, update_date))
                            updated = True
                            break
                    if not updated:
                        new_lots.append((lot_id, lot_shares, lot_cost_basis, lot_purchase_date))

                purchase_lots = new_lots
                shares_held -= shares_to_sell
                total_withdrawn += sale_proceeds
                total_taxes_paid += tax_owed

                # Create descriptive note showing what was liquidated
                income_descriptions = [f"${amt:.0f} from {dt.strftime('%m/%d')}" for dt, amt, _ in income_list[:3]]
                if len(income_list) > 3:
                    income_descriptions.append(f"+ {len(income_list) - 3} more")
                income_desc = ", ".join(income_descriptions)

                events.append(SimulationEvent(
                    date=liquidation_date,
                    event_type='sell',
                    shares=shares_to_sell,
                    price_per_share=sell_price,
                    amount=sale_proceeds,
                    tax_owed=tax_owed,
                    notes=f"Principal-only liquidation: ${total_principal_to_recover:.0f} from {len(income_list)} paycheck(s) ({income_desc})"
                ))

        # Calculate final account value
        final_price = prices[end_date]
        final_account_value = shares_held * final_price

        # Sort events by date for cleaner reporting
        events.sort(key=lambda e: e.date)

        return SingleRunResult(
            run_number=run_number,
            final_age=target_age,
            final_account_value=final_account_value,
            total_invested=total_invested,
            total_withdrawn=total_withdrawn,
            total_taxes_paid=total_taxes_paid,
            total_dividends=total_dividends,
            events=events,
        )

    def run_monte_carlo_rust(self, target_age: int) -> MonteCarloResults:
        """Run Monte Carlo simulation using Rust acceleration."""
        import time

        # Get income sources
        income_sources = [
            inc for inc in self.config.income
            if inc.id in self.simulation.income_source_ids
        ]

        # Build income events as (day_offset, amount) tuples with growth applied
        income_events = []
        years = target_age - self.simulation.current_age
        end_date = self.start_date + timedelta(days=years * 365)

        for income_source in income_sources:
            current_date = self.start_date
            while current_date <= end_date:
                next_income = self.get_next_income_date(income_source, current_date)
                if next_income is None or next_income > end_date:
                    break

                # Apply income growth based on years elapsed
                years_elapsed = (next_income - self.start_date).days / 365.0
                growth_periods = int(years_elapsed / self.simulation.income_growth_frequency) if self.simulation.income_growth_frequency > 0 else 0
                income_multiplier = (1 + self.simulation.income_growth_rate) ** growth_periods
                adjusted_amount = income_source.amount * income_multiplier

                day_offset = (next_income - self.start_date).days
                income_events.append((day_offset, adjusted_amount))
                current_date = next_income

        print(f"Running {self.simulation.num_simulations} simulations using Rust...")
        print(f"  Simulating {years} years (age {self.simulation.current_age} → {target_age})")

        start_time = time.time()

        try:
            # Call Rust function
            rust_results = simulation_rust.run_monte_carlo(
                num_simulations=self.simulation.num_simulations,
                current_age=self.simulation.current_age,
                target_age=target_age,
                initial_balance=self.simulation.initial_balance,
                income_events=income_events,
                expected_annual_return=self.simulation.expected_annual_return,
                annual_volatility=self.simulation.annual_volatility,
                expense_ratio=self.simulation.expense_ratio,
                short_term_tax_rate=self.simulation.short_term_cap_gains_rate,
                long_term_tax_rate=self.simulation.long_term_cap_gains_rate,
                dividend_yield=self.simulation.annual_dividend_yield,
                dividend_tax_rate=self.simulation.dividend_tax_rate,
                liquidation_day=self.simulation.liquidation_day,
                strategy_type=self.simulation.strategy_type,
                random_seed=self.simulation.random_seed,
            )

            # Convert Rust results to Python SingleRunResult objects
            runs = []
            for rust_result in rust_results:
                run = SingleRunResult(
                    run_number=rust_result.run_number,
                    final_age=target_age,
                    final_account_value=rust_result.final_account_value,
                    total_invested=rust_result.total_invested,
                    total_withdrawn=rust_result.total_withdrawn,
                    total_taxes_paid=rust_result.total_taxes_paid,
                    total_dividends=rust_result.total_dividends,
                    events=[],  # Events not tracked in Rust version for performance
                )
                runs.append(run)

            elapsed = time.time() - start_time
            rate = len(runs) / elapsed
            print(f"  ✓ Completed all {len(runs)} runs in {elapsed:.1f}s ({rate:.1f} runs/sec)!")

        except KeyboardInterrupt:
            print(f"\n  ⚠️  Simulation interrupted!")
            raise

        return MonteCarloResults(
            simulation_config=self.simulation,
            runs=runs,
            target_age=target_age,
        )

    def run_monte_carlo(self, target_age: int, force_python: bool = False) -> MonteCarloResults:
        """
        Run Monte Carlo simulation with multiple iterations.

        Args:
            target_age: Target age to simulate to
            force_python: If True, always use Python (for detailed events).
                         If False, auto-select based on num_simulations:
                         - Small runs (<=10): Python with full event tracking
                         - Large runs (>10): Rust for speed (no events)
        """

        # Decide which engine to use
        use_rust = False
        if RUST_AVAILABLE and not force_python:
            # For small runs, use Python to get detailed events
            # For large runs, use Rust for performance
            if self.simulation.num_simulations > 10:
                use_rust = True
            else:
                print(f"ℹ️  Using Python for detailed event tracking (num_simulations={self.simulation.num_simulations})")

        if use_rust:
            return self.run_monte_carlo_rust(target_age)

        # Python implementation
        import time

        years = target_age - self.simulation.current_age
        print(f"Running {self.simulation.num_simulations} simulations (Python)...")
        print(f"  Simulating {years} years (age {self.simulation.current_age} → {target_age})")
        print(f"  This may take a few moments...")

        start_time = time.time()
        runs = []

        # More frequent updates for better feedback
        update_interval = max(1, self.simulation.num_simulations // 20)  # 20 updates max

        try:
            for i in range(self.simulation.num_simulations):
                if (i + 1) % update_interval == 0 or i == 0:
                    elapsed = time.time() - start_time
                    rate = (i + 1) / elapsed if elapsed > 0 else 0
                    remaining = (self.simulation.num_simulations - i - 1) / rate if rate > 0 else 0
                    print(f"  [{i + 1:4d}/{self.simulation.num_simulations}] {rate:.1f} runs/sec, ~{remaining:.0f}s remaining")

                run_result = self.run_single_simulation(i, target_age)
                runs.append(run_result)

            elapsed = time.time() - start_time
            print(f"  ✓ Completed all {self.simulation.num_simulations} runs in {elapsed:.1f}s!")

        except KeyboardInterrupt:
            print(f"\n  ⚠️  Interrupted after {len(runs)} runs")
            if len(runs) < 10:
                raise  # Re-raise if we don't have enough data for meaningful results
            print(f"  Continuing with {len(runs)} completed runs...")

        return MonteCarloResults(
            simulation_config=self.simulation,
            runs=runs,
            target_age=target_age,
        )
