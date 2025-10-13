# Baseline Simulation CLI

A simple tool to understand how investment timing affects long-term wealth building.

## Overview

This tool simulates a simple investment strategy:
- **Income invested on payday** (weekly, biweekly, or monthly)
- **Expenses withdrawn on the 1st of each month**
- **No life events** - just salary, expenses, and market returns
- **Compare different investment frequencies** to understand timing effects

## Quick Start

### Interactive Mode
```bash
python baseline_sim_cli.py
```

Follow the menu to:
1. Create new configuration
2. Load existing configuration
3. Edit configuration
4. Run simulation
5. Compare investment frequencies (weekly vs biweekly vs monthly)
6. Save configuration
7. Exit

### Using a Config File

Create or edit `example_baseline_config.json`:
```json
{
  "current_age": 38,
  "life_expectancy": 90,
  "annual_salary": 150000,
  "tax_rate": 0.27,
  "monthly_expenses": 9000,
  "investment_frequency": "biweekly",
  "num_simulations": 1000
}
```

Then load it from the CLI menu (option 2).

## Investment Frequencies Explained

### Weekly
- 52 paychecks per year
- Invest $X every week
- Maximum dollar-cost averaging (most frequent buying)
- More opportunities to buy market dips

### Biweekly
- 26 paychecks per year
- Invest $X every 2 weeks
- Common payroll frequency
- Moderate dollar-cost averaging

### Monthly
- 12 paychecks per year
- Invest $X once per month
- Least frequent buying
- Larger lump sums, less averaging

## Output

The tool generates CSV files with unique timestamps:
- `baseline_sim_biweekly_20251012_143022.csv`
- `baseline_sim_weekly_20251012_143045.csv`
- `baseline_sim_monthly_20251012_143108.csv`

Each CSV contains:
- **Configuration summary** (salary, expenses, market parameters)
- **Overall statistics** (success rate, mean/median final balance)
- **Individual simulation results** (all 1000 simulations)

## Understanding the Intervals

The key insight: **investment frequency affects risk and returns**

**More frequent investing (weekly):**
- ✅ Better dollar-cost averaging
- ✅ More opportunities to buy dips
- ⚠️ More transactions (higher fees in real world)
- ⚠️ Less time for each deposit to compound before next withdrawal

**Less frequent investing (monthly):**
- ✅ Larger lump sums can compound longer
- ✅ Fewer transactions
- ⚠️ Less dollar-cost averaging
- ⚠️ More exposed to single bad timing

## Example Workflow

1. **Start with default config:**
   ```
   python baseline_sim_cli.py
   -> Option 1: Create new configuration
   -> Option 4: Run simulation
   ```

2. **Compare frequencies:**
   ```
   -> Option 5: Compare investment frequencies
   ```
   This runs weekly, biweekly, AND monthly - all in one go!

3. **Save your favorite config:**
   ```
   -> Option 6: Save configuration
   -> Enter: my_income_150k.json
   ```

4. **Load it later:**
   ```
   -> Option 2: Load configuration
   -> Enter: my_income_150k.json
   ```

## Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `current_age` | Starting age | 38 |
| `life_expectancy` | Age simulation ends | 90 |
| `annual_salary` | Gross annual income | $150,000 |
| `tax_rate` | Income tax rate | 0.27 (27%) |
| `salary_growth` | Annual raise | 0.01 (1%) |
| `monthly_expenses` | Living costs | $9,000 |
| `expense_growth` | Annual inflation | 0.01 (1%) |
| `investment_frequency` | When to invest | biweekly |
| `spy_mean_return` | Expected market return | 0.10 (10%) |
| `spy_volatility` | Market volatility | 0.18 (18%) |
| `initial_balance` | Starting investment | $0 |
| `initial_cash_buffer` | Emergency fund | $27,000 |
| `num_simulations` | How many runs | 1000 |
| `random_seed` | For reproducibility | null |

## Tips

**For quick experiments:**
- Reduce `num_simulations` to 100 for faster results
- Increase to 10,000 for more statistical confidence

**For comparing frequencies:**
- Use Option 5 to run all three at once
- Look at the comparison table to see which performs best
- Check the CSV files for detailed breakdown

**For understanding your own situation:**
- Adjust `annual_salary` and `monthly_expenses` to match your income
- Set `investment_frequency` to match your actual payroll
- Run simulations to see expected outcomes

## Next Steps

Once you understand baseline intervals, explore:
- `wealth_simulation.py` - Full simulation with life events, windfalls, startups
- `insurance_optimizer.py` - Portfolio insurance strategies
- `startup_simulation.py` - Startup investment modeling
