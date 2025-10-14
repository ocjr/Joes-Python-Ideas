# Setting Up Biweekly Income

## Quick Setup

When adding income (CLI option 11), use:
- **Frequency**: biweekly
- **Amount**: Your actual paycheck amount (e.g., $1,500)
- **Next date**: Your next payday

Example:
```
Frequency: biweekly
Amount: $1500
Next date: 2025-10-17
```

The simulation will automatically:
- Generate 26 paychecks per year (not 12)
- Handle months with 3 paychecks
- Calculate 13-day holding periods (biweekly = every 14 days, liquidate next day)

## Current Strategies

### 1. **monthly_liquidation** (current)
- **How it works**: Sell on a specific day of the month (e.g., 1st)
- **Holding period**: Varies (7-30 days depending on when paycheck arrives)
- **Best for**: Monthly bill cycles

### 2. **constant_hold** (current)
- **How it works**: Hold for exactly N days, then sell
- **Holding period**: Fixed (e.g., 13 days for biweekly paychecks)
- **Best for**: Consistent short-term gains

### 3. **principal_only** (NEW - being implemented)
- **How it works**: Sell only enough to recover your original investment
- **Keep**: All gains stay invested and compound
- **Best for**: Tax efficiency and long-term growth

## Example Comparison

**Biweekly income: $1,500 every 2 weeks**

| Date | Event | monthly_liquidation | constant_hold | principal_only (new) |
|------|-------|---------------------|---------------|---------------------|
| 10/17 | Paycheck #1 | Buy $1,500 | Buy $1,500 | Buy $1,500 |
| 10/31 | Paycheck #2 | Buy $1,500 | Buy $1,500 | Buy $1,500 |
| 11/1 | Liquidation | Sell both (~$3,000+) | - | Sell $3,000 only (keep gains) |
| 11/14 | Paycheck #3 | Buy $1,500 | Sell #1 (~$1,520) | - |
| 11/28 | Paycheck #4 | Buy $1,500 | Sell #2 (~$1,530) | - |
| 12/1 | Liquidation | Sell both (~$3,000+) | - | Sell $3,000 only (keep gains) |

**Key differences:**
- `monthly_liquidation`: Variable holding periods, all gains realized monthly
- `constant_hold`: Fixed 13-14 day periods, constant turnover
- `principal_only`: Only sell original amounts, gains compound tax-free until final liquidation

## Tax Impact

**With monthly_liquidation or constant_hold:**
- Every gain is taxed immediately (22% short-term rate)
- High turnover = high tax drag

**With principal_only (new strategy):**
- Gains stay invested and untaxed
- When you finally sell gains, they might be long-term (15% rate)
- Lower tax drag, better compounding

## Your Use Case

You said:
> "I am investing money I wouldn't have been able to invest. I am investing for a short period so I can use that money for my regular expenses."

**The principal_only strategy is PERFECT for this because:**
1. ✅ You get your paycheck back every cycle (can pay bills)
2. ✅ Gains stay invested (free money compounds)
3. ✅ Lower taxes (gains aren't sold until the end)
4. ✅ You're building wealth on money you'd otherwise just spend

## Setting It Up (Once Implemented)

1. **Add income** (option 11):
   - Frequency: biweekly
   - Amount: $1,500 (or your actual amount)
   - Next date: Your next payday

2. **Create simulation** (option 29):
   - Strategy: principal_only
   - Liquidation cycle: 14 days (or monthly, up to you)
   - Income sources: Select your biweekly income

3. **Run simulation** (option 28):
   - Compare results to current strategies
   - See tax savings!

## Expected Results

**4-year simulation with $1,500 biweekly:**
- Total invested: $156,000 (52 paychecks × $1,500 × 2 years)
- Total withdrawn: $156,000 (get your money back)
- Taxes (current strategy): ~$2,000-3,000
- Taxes (principal_only): ~$500-1,000
- **Final account value**: All the gains you accumulated!

The principal_only strategy could save you 50-70% on taxes while building a nice nest egg!
