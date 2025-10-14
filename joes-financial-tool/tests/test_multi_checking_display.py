#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
"""Test that multiple checking accounts are displayed separately."""

from config_loader import load_config
from optimizer import FinancialOptimizer
from cli import print_optimal_simulation
from models import Account, AccountType

# Load config
config = load_config("example_config.json")

# Add a secondary checking account
secondary_checking = Account(
    id="checking_secondary",
    name="Summit Checking",
    type=AccountType.CHECKING,
    balance=1500.00,
    minimum_balance=200.00,
)
config.accounts.append(secondary_checking)

# Adjust main checking
config.accounts[0].name = "Chase Checking"

print("Testing multi-checking account display")
print(f"Accounts: {config.accounts[0].name} and {secondary_checking.name}")
print()

optimizer = FinancialOptimizer(config)

# Run a short simulation to see the display
print_optimal_simulation(optimizer, days=5)
