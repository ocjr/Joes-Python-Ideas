#!/usr/bin/env python3
"""Test that optimal simulation respects the days parameter."""

from config_loader import load_config
from optimizer import FinancialOptimizer
from cli import print_optimal_simulation

config = load_config("example_config.json")
optimizer = FinancialOptimizer(config)

print("="*70)
print("Testing with 3 days (should show 3 days, not 7)")
print("="*70)
print_optimal_simulation(optimizer, days=3)

print("\n" + "="*70)
print("Testing with 15 days (should show 15 days, not 7)")
print("="*70)
print_optimal_simulation(optimizer, days=15)

print("\n" + "="*70)
print("Testing with 30 days (should show 30 days, not 7)")
print("="*70)
print_optimal_simulation(optimizer, days=30)
