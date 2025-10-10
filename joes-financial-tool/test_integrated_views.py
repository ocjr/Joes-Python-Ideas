#!/usr/bin/env python3
"""Test that all views are integrated with simulation."""

from config_loader import load_config
from optimizer import FinancialOptimizer
from cli import print_tasks, print_upcoming_plan, print_cash_flow_forecast
from datetime import date

config = load_config("example_config.json")
optimizer = FinancialOptimizer(config)

print("="*70)
print("Testing Today's Actions (should use simulation)")
print("="*70)
print_tasks(optimizer)

print("\n" + "="*70)
print("Testing Upcoming 3-Day Plan (should show exactly 3 days)")
print("="*70)
print_upcoming_plan(optimizer, days=3)

print("\n" + "="*70)
print("Testing Upcoming 10-Day Plan (should show exactly 10 days)")
print("="*70)
print_upcoming_plan(optimizer, days=10)

print("\n" + "="*70)
print("Testing 14-Day Forecast (should use simulation)")
print("="*70)
print_cash_flow_forecast(optimizer)
