#!/usr/bin/env python3
"""Test that simulator makes preemptive payments when bills would exceed CC limits."""

from config_loader import load_config
from optimizer import FinancialOptimizer
from simulator import FinancialSimulator, OptimizationStrategy
from models import Bill

# Load config
config = load_config("example_config.json")

# Set up scenario: Visa card near limit with a large bill about to be charged
# Visa limit: $5000
# Set balance to $4500, and add a $1000 bill charged to the card
visa_card = next(cc for cc in config.credit_cards if cc.id == "cc_visa")
visa_card.balance = 4500.00  # $500 below limit

print("Initial Setup:")
print(f"  Visa balance: ${visa_card.balance:.2f}")
print(f"  Visa limit: ${visa_card.credit_limit:.2f}")
print(f"  Available credit: ${visa_card.credit_limit - visa_card.balance:.2f}")

# Add a large bill that will be charged to Visa
large_bill = Bill(
    id="large_subscription",
    name="Large Annual Subscription",
    amount=1000.00,  # This would push balance to $5500, exceeding $5000 limit
    due_day=12,  # Oct 12
    frequency="monthly",
    autopay=False,
    payment_account="cc_visa",  # Charged to Visa
    category="subscription",
    paid_by_credit=True,  # This is the key - it's charged to the credit card
)
config.bills.append(large_bill)

print(f"\n  Large bill: ${large_bill.amount:.2f} on day 12 (charged to Visa)")
print(f"  If charged without adjustment: ${visa_card.balance + large_bill.amount:.2f} (over limit by ${visa_card.balance + large_bill.amount - visa_card.credit_limit:.2f})")

optimizer = FinancialOptimizer(config)
simulator = FinancialSimulator(config, optimizer.today)

print("\nRunning simulation...")
print("Expected: Should make preemptive payment to Visa before charging the bill")

result = simulator.run_simulation(OptimizationStrategy.AGGRESSIVE_DEBT, days_ahead=30)

print(f"\n{'='*60}")
if result.failed:
    print(f"❌ Simulation failed")
    print(f"  Days completed: {len(result.days)}")
    if result.warnings:
        print(f"  Violations:")
        for warning in result.warnings[:3]:
            print(f"    - {warning}")
else:
    print(f"✓ Simulation succeeded!")
    print(f"  Completed all {len(result.days)} days")
    print(f"  Total interest: ${result.total_interest_paid:.2f}")

    # Check what happened on day 3 (Oct 12, when the bill is due)
    day_3 = result.days[3]  # Oct 12 is day 3 (Oct 9, 10, 11, 12)

    print(f"\n  Transactions on {day_3.date} (bill due date):")
    has_preemptive = False
    for txn, decision in day_3.transactions:
        if txn.amount < 0:
            print(f"    • {txn.description}: ${abs(txn.amount):.2f}")
            if "preemptive" in txn.description.lower():
                has_preemptive = True
                print(f"      ✓ PREEMPTIVE PAYMENT MADE!")

    if has_preemptive:
        print(f"\n    ✓ Simulator correctly made preemptive payment to avoid exceeding limit")
    else:
        print(f"\n    ℹ️  No preemptive payment detected")

    # Check final Visa balance
    final_visa = day_3.ending_state.credit_card_balances.get("cc_visa", 0)
    print(f"\n  Visa balance after transactions: ${final_visa:.2f}")

    if final_visa <= visa_card.credit_limit:
        print(f"  ✓ Stayed within limit (${final_visa:.2f} <= ${visa_card.credit_limit:.2f})")
    else:
        print(f"  ✗ Exceeded limit! (${final_visa:.2f} > ${visa_card.credit_limit:.2f})")
