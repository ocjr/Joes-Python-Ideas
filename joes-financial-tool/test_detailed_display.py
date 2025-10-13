#!/usr/bin/env python3
"""Test the detailed display with specific accounts and balances."""

from config_loader import load_config
from optimizer import FinancialOptimizer
from cli import print_optimal_simulation

config = load_config("example_config.json")
optimizer = FinancialOptimizer(config)

print("Testing detailed display with 7 days")
print("Should show:")
print("  - Specific account names (Main Checking, Visa Card, etc.)")
print("  - Starting and ending balances for each day")
print("  - Car Insurance marked as require_checking (should always pay from checking)")
print()

print_optimal_simulation(optimizer, days=7)
