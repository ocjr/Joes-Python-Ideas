#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
"""Test the extra payment explanation display."""

from config_loader import load_config
from optimizer import FinancialOptimizer
from cli import print_optimal_simulation

config = load_config("example_config.json")
optimizer = FinancialOptimizer(config)

print("Testing extra payment explanation display with 30 days")
print("Should show detailed reasoning for extra CC payments:")
print("  - Why this card was chosen")
print("  - Why this amount")
print("  - Interest savings")
print()

print_optimal_simulation(optimizer, days=30)
