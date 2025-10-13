# Calendar-Based Simulation

## Overview

This simulator models **exact** cash flow with specific dates. Instead of "biweekly" or "monthly", you specify:
- **Income:** "I get paid $4,562.50 on the 1st and 15th"
- **Expenses:** "I withdraw $9,000 on the 5th"

This lets you see how **timing** affects long-term wealth by allowing deposits to compound before withdrawals.

## Quick Start

### Interactive Wizard
```bash
/Users/avi8tors_mac/opt/miniconda3/envs/investing/bin/python calendar_sim.py
```

Select option 1 to run the setup wizard. It will ask you:
1. Age and life expectancy
2. Initial balances
3. Income schedules (amount, days of month, growth rate)
4. Expense schedules (amount, days of month, growth rate)
5. Number of simulations

### Load Existing Scenario
```bash
# Option 2 in the CLI, then enter filename
example_scenarios.json
```

### Quick Test
```bash
# Option 3 runs a pre-configured test scenario
```

## Example Scenarios

We've created 4 scenarios to show the impact of timing:

### 1. Baseline (Income & Expenses on 1st)
- **File:** `example_scenarios.json`
- Income: $4,562.50 on 1st and 15th
- Expenses: $9,000 on 1st
- **Result:** $1,662,765 median market gain

### 2. Optimal Timing (Expenses on 5th)
- **File:** `scenario_optimal_timing.json`
- Income: $4,562.50 on 1st and 15th
- Expenses: $9,000 on **5th** (after both paychecks)
- **Result:** $1,760,669 median market gain (+5.89%)
- **Why better:** 4-19 days for money to compound before withdrawal

### 3. Poor Timing (Expenses on 16th)
- **File:** `scenario_poor_timing.json`
- Income: $4,562.50 on 1st and 15th
- Expenses: $9,000 on **16th** (right after 2nd paycheck)
- **Result:** $1,678,815 median market gain (+0.97%)
- **Why similar:** Still 15-30 days between deposits

### 4. Worst Timing (Split Expenses)
- **File:** `scenario_split_expenses.json`
- Income: $4,562.50 on 1st and 15th
- Expenses: $5,000 on **1st**, $4,000 on **15th** (same days)
- **Result:** $1,483,791 median market gain (-10.76%)
- **Why worst:** Money never sits invested - immediately withdrawn

## Timing Impact Over 52 Years

**Best vs. Worst: $276,878 difference (18.66%)**

```
Best:  Expenses on 5th  → $1,760,669 market gain
Worst: Split expenses   → $1,483,791 market gain
Difference: $276,878 just from timing!
```

## How to Use for Your Situation

### Step 1: Figure out your payday schedule
- **Semi-monthly:** Days 1 and 15 (24 times/year)
- **Biweekly:** Pick a start date, then every 14 days (26 times/year)
- **Monthly:** Day 1 (or whatever day) once per month
- **Weekly:** Days 1, 8, 15, 22 (approximately)

### Step 2: Calculate per-paycheck amount
```
Annual salary after tax ÷ number of paychecks = amount per paycheck
```

Examples:
- $109,500/year ÷ 24 (semi-monthly) = $4,562.50
- $109,500/year ÷ 26 (biweekly) = $4,211.54
- $109,500/year ÷ 12 (monthly) = $9,125.00

### Step 3: Map out your expense dates
When do bills actually hit your account?
- Rent: 1st of month
- Car payment: 5th of month
- Credit cards: 15th of month
- Groceries: Spread throughout

Combine into expense schedules with specific days.

### Step 4: Run the wizard
```bash
python calendar_sim.py
```

Follow prompts to enter your exact schedule.

### Step 5: Optimize timing
Once you see baseline results, experiment with:
- Can you delay any expenses?
- Can you align paychecks before large expenses?
- Should you split expenses across dates or lump them?

## Output

Each simulation generates a CSV with:
- **Configuration summary** (income/expense schedules)
- **Overall statistics** (mean, median, success rate)
- **Individual simulation results** (all 1,000 runs)

Files are timestamped: `calendar_sim_20251012_192930.csv`

## Key Metrics

- **Final Balance:** Total assets at end of simulation
- **Total Income:** All deposits over lifetime (with growth)
- **Total Expenses:** All withdrawals over lifetime (with inflation)
- **Net Contributed:** Income - Expenses (what YOU put in)
- **Market Gain:** Final - Net Contributed (what MARKET gave you)

## Tips for Optimization

**1. Maximize time between income and expenses**
   - Get paid on 1st & 15th, bills on 5th
   - Deposits have 4-19 days to compound

**2. Avoid same-day withdrawals**
   - Deposit and immediate withdrawal = no compounding
   - Split expenses lost 10.76% vs. optimal timing

**3. Consider your cash buffer**
   - Need enough to cover timing gaps
   - Default $27,000 gives flexibility

**4. Pay large bills AFTER multiple paychecks**
   - Let 2-3 deposits accumulate before big withdrawal
   - Maximizes invested balance

## Comparison with Baseline Sim

| Feature | Baseline Sim | Calendar Sim |
|---------|-------------|--------------|
| Timing | Frequency (weekly/biweekly) | Exact dates (1st, 15th, etc.) |
| Granularity | Period-based | Day-by-day |
| Income | Per-period averages | Specific days of month |
| Expenses | Monthly approximation | Specific withdrawal dates |
| Use case | General frequency comparison | Optimize payment timing |

## Advanced Usage

### Multiple Income Sources
```python
income_schedules=[
    IncomeSchedule(amount=4000, days_of_month=[1, 15], description="W-2 job"),
    IncomeSchedule(amount=500, days_of_month=[1], description="Freelance"),
]
```

### Multiple Expense Categories
```python
expense_schedules=[
    ExpenseSchedule(amount=2000, days_of_month=[1], description="Rent"),
    ExpenseSchedule(amount=500, days_of_month=[5], description="Car payment"),
    ExpenseSchedule(amount=3000, days_of_month=[15], description="Credit cards"),
    ExpenseSchedule(amount=3500, days_of_month=[1, 15], description="Food/misc split"),
]
```

### Different Growth Rates
```python
# Salary grows faster than expenses
IncomeSchedule(amount=4562, days_of_month=[1, 15], annual_growth=0.02)  # 2% raises
ExpenseSchedule(amount=9000, days_of_month=[5], annual_growth=0.01)     # 1% inflation
```

## Next Steps

Once you understand baseline timing with this tool:
1. Use `wealth_simulation.py` for life events (windfalls, startups, investments)
2. Use `insurance_optimizer.py` for portfolio insurance strategies
3. Use `startup_simulation.py` for business investment modeling
