#!/usr/bin/env python3
"""
ETF library management for investment simulations.

Provides a curated database of ETF presets with historical performance metrics.
"""

import json
from typing import Optional, List, Dict
from dataclasses import dataclass


@dataclass
class ETFPreset:
    """Represents an ETF preset with all simulation parameters."""

    ticker: str
    name: str
    expected_annual_return: float
    annual_volatility: float
    annual_dividend_yield: float
    expense_ratio: float
    category: str
    description: str


class ETFLibrary:
    """Manages ETF presets for simulations."""

    def __init__(self, library_path: str = "etf_presets.json"):
        self.library_path = library_path
        self.etfs: List[ETFPreset] = []
        self.load()

    def load(self):
        """Load ETF presets from JSON file."""
        try:
            with open(self.library_path, "r") as f:
                data = json.load(f)
                self.etfs = [ETFPreset(**etf) for etf in data.get("etfs", [])]
        except FileNotFoundError:
            print(f"⚠️  ETF library not found at {self.library_path}")
            self.etfs = []
        except Exception as e:
            print(f"⚠️  Error loading ETF library: {e}")
            self.etfs = []

    def save(self):
        """Save ETF presets to JSON file."""
        data = {
            "etfs": [
                {
                    "ticker": etf.ticker,
                    "name": etf.name,
                    "expected_annual_return": etf.expected_annual_return,
                    "annual_volatility": etf.annual_volatility,
                    "annual_dividend_yield": etf.annual_dividend_yield,
                    "expense_ratio": etf.expense_ratio,
                    "category": etf.category,
                    "description": etf.description,
                }
                for etf in self.etfs
            ]
        }

        with open(self.library_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_by_ticker(self, ticker: str) -> Optional[ETFPreset]:
        """Get ETF preset by ticker symbol."""
        ticker_upper = ticker.upper()
        return next(
            (etf for etf in self.etfs if etf.ticker.upper() == ticker_upper), None
        )

    def search(self, query: str) -> List[ETFPreset]:
        """Search ETFs by ticker, name, or category."""
        query_lower = query.lower()
        return [
            etf
            for etf in self.etfs
            if query_lower in etf.ticker.lower()
            or query_lower in etf.name.lower()
            or query_lower in etf.category.lower()
        ]

    def list_by_category(self) -> Dict[str, List[ETFPreset]]:
        """Group ETFs by category."""
        categories = {}
        for etf in self.etfs:
            if etf.category not in categories:
                categories[etf.category] = []
            categories[etf.category].append(etf)
        return categories

    def add_etf(self, etf: ETFPreset):
        """Add a new ETF preset to the library."""
        # Check if ticker already exists
        existing = self.get_by_ticker(etf.ticker)
        if existing:
            # Update existing
            self.etfs.remove(existing)
        self.etfs.append(etf)
        self.save()

    def remove_etf(self, ticker: str) -> bool:
        """Remove an ETF preset by ticker."""
        etf = self.get_by_ticker(ticker)
        if etf:
            self.etfs.remove(etf)
            self.save()
            return True
        return False


def view_etf_library(library_path: str = "etf_presets.json"):
    """View all ETFs in the library, organized by category."""
    print("=" * 80)
    print("  ETF LIBRARY")
    print("=" * 80)
    print()

    library = ETFLibrary(library_path)

    if not library.etfs:
        print("No ETFs in library.\n")
        return

    categories = library.list_by_category()

    for category in sorted(categories.keys()):
        print(f"\n{'─' * 80}")
        print(f"📊 {category.upper()}")
        print(f"{'─' * 80}\n")

        for etf in sorted(categories[category], key=lambda e: e.ticker):
            print(f"  {etf.ticker:6s} - {etf.name}")
            print(
                f"         Return: {etf.expected_annual_return*100:5.1f}%  |  Volatility: {etf.annual_volatility*100:5.1f}%  |  Dividend: {etf.annual_dividend_yield*100:5.2f}%  |  Expense: {etf.expense_ratio*100:5.3f}%"
            )
            print(f"         {etf.description}")
            print()

    print(f"\n{'=' * 80}")
    print(f"Total: {len(library.etfs)} ETFs")
    print(f"{'=' * 80}\n")


def add_etf_interactive(library_path: str = "etf_presets.json"):
    """Interactively add a new ETF to the library."""
    print("=" * 80)
    print("  ADD ETF TO LIBRARY")
    print("=" * 80)
    print()

    library = ETFLibrary(library_path)

    # Get ETF details
    print("Enter ETF details:\n")

    ticker = input("Ticker symbol: ").strip().upper()
    if not ticker:
        print("❌ Ticker is required")
        return

    # Check if already exists
    existing = library.get_by_ticker(ticker)
    if existing:
        print(f"\n⚠️  {ticker} already exists in library:")
        print(f"   {existing.name}")
        replace = input("Replace existing entry? (y/n): ").strip().lower()
        if replace != "y":
            print("Cancelled.")
            return

    name = input("Full name: ").strip()
    if not name:
        print("❌ Name is required")
        return

    category = input("Category (e.g., Large Cap Blend, Bond, etc.): ").strip()
    if not category:
        category = "Other"

    try:
        expected_return = float(
            input("Expected annual return (decimal, e.g., 0.10 for 10%): ").strip()
        )
        volatility = float(
            input("Annual volatility (decimal, e.g., 0.15 for 15%): ").strip()
        )
        dividend_yield = float(
            input("Annual dividend yield (decimal, e.g., 0.015 for 1.5%): ").strip()
        )
        expense_ratio = float(
            input("Expense ratio (decimal, e.g., 0.0009 for 0.09%): ").strip()
        )
    except ValueError:
        print("❌ Invalid number format")
        return

    description = input("Description: ").strip()
    if not description:
        description = f"{ticker} ETF"

    # Create and add ETF
    etf = ETFPreset(
        ticker=ticker,
        name=name,
        expected_annual_return=expected_return,
        annual_volatility=volatility,
        annual_dividend_yield=dividend_yield,
        expense_ratio=expense_ratio,
        category=category,
        description=description,
    )

    library.add_etf(etf)
    print(f"\n✅ Added {ticker} to library!")


def search_etf_interactive(library_path: str = "etf_presets.json"):
    """Interactively search for ETFs in the library."""
    print("=" * 80)
    print("  SEARCH ETF LIBRARY")
    print("=" * 80)
    print()

    library = ETFLibrary(library_path)

    if not library.etfs:
        print("No ETFs in library.\n")
        return

    query = input("Search (ticker, name, or category): ").strip()
    if not query:
        print("Cancelled.")
        return

    results = library.search(query)

    if not results:
        print(f"\n❌ No ETFs found matching '{query}'")
        return

    print(f"\n{'─' * 80}")
    print(f"Found {len(results)} result(s):")
    print(f"{'─' * 80}\n")

    for etf in sorted(results, key=lambda e: e.ticker):
        print(f"  {etf.ticker:6s} - {etf.name} ({etf.category})")
        print(
            f"         Return: {etf.expected_annual_return*100:5.1f}%  |  Volatility: {etf.annual_volatility*100:5.1f}%  |  Dividend: {etf.annual_dividend_yield*100:5.2f}%"
        )
        print(f"         {etf.description}")
        print()


if __name__ == "__main__":
    # Test the library
    view_etf_library()
