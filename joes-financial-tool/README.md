# Financial Optimization Tool

A Python-based financial management tool that helps you optimize your finances by tracking accounts, bills, credit cards, and income, then generating **concrete daily action plans** with specific payment amounts.

## Features

- 🏦 **Multiple Account Management**: Track checking, savings, and cash accounts
- 💵 **Income Tracking**: Monitor paydays with various frequencies (weekly, biweekly, monthly, etc.)
- 💰 **Bill Management**: Track recurring bills with due dates and autopay status
- 💳 **Credit Card Optimization**: Manage multiple credit cards with balance, APR, and payment tracking
- 📋 **Concrete Action Plans**: Get specific payment amounts, not abstract advice
- 📅 **14-Day Cash Flow Forecast**: Day-by-day projection to avoid overdrafts
- 🎯 **Debt Payoff Strategies**: Choose between avalanche (highest interest), snowball (lowest balance), or balanced approaches
- 🔄 **Interactive Setup Wizard**: Easy guided configuration for first-time users
- 💻 **Menu-Driven Interface**: Active CLI with options to select (no memorizing arguments!)

## Quick Start

### First Time Setup

1. Navigate to the tool directory:
```bash
cd joes-financial-tool
```

2. Run the interactive setup wizard:
```bash
python cli.py
```

On first run, you'll be prompted to create your configuration. The wizard will guide you through:
- Setting up bank accounts
- Adding income sources
- Configuring recurring bills
- Adding credit cards
- Choosing your debt payoff strategy

### Daily Usage

Simply run the tool to see the interactive menu:
```bash
python cli.py
```

You'll see:
```
======================================================================
  💰 Financial Optimization Tool
======================================================================

Main Menu:

  1. 📋 View Today's Action Plan
  2. 📊 View Financial Summary
  3. 📅 View 14-Day Cash Flow Forecast
  4. 🏦 View Account Details
  5. 🔄 Update Account Balances
  6. ⚙️  Run Setup Wizard (create new config)
  7. 📖 View All Information
  0. 🚪 Exit

Select option (0-7):
```

## Installation

No external dependencies required! Uses only Python standard library.

Optional: Make the CLI executable:
```bash
chmod +x cli.py
```

## Configuration (Manual - Optional)

If you prefer to manually create/edit your config instead of using the wizard:

Create a `financial_config.json` file based on the provided `example_config.json`:

```bash
cp example_config.json financial_config.json
```

Edit `financial_config.json` with your actual financial information:

### Accounts
```json
{
  "id": "checking_main",
  "name": "Main Checking",
  "type": "checking",
  "balance": 2500.00,
  "minimum_balance": 500.00
}
```

### Income
```json
{
  "id": "paycheck_main",
  "source": "Primary Job",
  "amount": 2400.00,
  "frequency": "biweekly",
  "next_date": "2025-10-10",
  "deposit_account": "checking_main"
}
```

### Bills
```json
{
  "id": "rent",
  "name": "Rent",
  "amount": 1200.00,
  "due_day": 1,
  "frequency": "monthly",
  "autopay": false,
  "payment_account": "checking_main",
  "category": "housing"
}
```

### Credit Cards
```json
{
  "id": "cc_visa",
  "name": "Visa Card",
  "balance": 1850.00,
  "credit_limit": 5000.00,
  "apr": 0.1899,
  "due_day": 22,
  "minimum_payment": 55.00,
  "statement_day": 15,
  "payment_account": "checking_main"
}
```

### Settings
```json
{
  "emergency_fund_target": 1000.00,
  "planning_horizon_days": 30,
  "priority": "avalanche"
}
```

**Priority Options:**
- `avalanche`: Pay off highest APR credit cards first (saves most on interest)
- `snowball`: Pay off lowest balance first (quick wins for motivation)
- `balanced`: Mix of both strategies

## Usage

### Interactive Mode (Recommended)

Just run the tool and select from the menu:
```bash
python cli.py
```

**Menu Options:**

*VIEW:*
1. **Today's Action Plan** - See exactly what to pay today with specific amounts
2. **Financial Summary** - Overview of balances, debt, and emergency fund status
3. **14-Day Cash Flow Forecast** - Day-by-day projection to avoid overdrafts
4. **Account Details** - See all your accounts and available balances
5. **View All Information** - See everything at once

*MANAGE:*
6. **Update Account Balances** - Interactive update of current balances
7. **Add New Account** - Add a bank account to your existing config
8. **Add New Income Source** - Add an income source to your existing config
9. **Add New Bill** - Add a recurring bill to your existing config
10. **Add New Credit Card** - Add a credit card to your existing config

*SETUP:*
11. **Run Full Setup Wizard** - Create new dated config (e.g., `financial_config_2025-10-08.json`)
12. **Load Previous Config** - Switch between saved configurations or recover from corruption

### Quick Access Mode (Arguments)

For power users who want shortcuts:

```bash
# Quick view of today's tasks
python cli.py -t

# Quick view of everything
python cli.py --all

# Update balances then see tasks
python cli.py -u

# View forecast
python cli.py -f

# Use custom config file
python cli.py my_finances.json -t
```

## Command Line Options

```
usage: cli.py [-h] [-t] [-s] [-a] [-f] [-u] [-d DATE] [--all] [-i] [config]

Interactive Mode (default):
  Run without arguments to enter interactive menu mode

Argument Mode (shortcuts):
  Use flags for quick access to specific views

positional arguments:
  config                Path to config file (default: financial_config.json)

options:
  -h, --help            Show this help message
  -t, --tasks           Show today's tasks (argument mode)
  -s, --summary         Show financial summary (argument mode)
  -a, --accounts        Show account details (argument mode)
  -f, --forecast        Show 14-day cash flow forecast (argument mode)
  -u, --update          Update account balances interactively
  -d DATE, --date DATE  Target date for tasks (YYYY-MM-DD format)
  --all                 Show all information (argument mode)
  -i, --interactive     Force interactive menu mode
```

## Configuration Versioning

The tool automatically manages configuration versions:

- **Dated Configs**: When you run the Full Setup Wizard (option 11), it creates a new config file with today's date (e.g., `financial_config_2025-10-08.json`)
- **Config History**: All previous configs are preserved, allowing you to:
  - Switch between different financial scenarios
  - Recover from accidental corruption
  - Review historical configurations
- **Config Selection**: Use option 12 to see a list of all available configs and switch between them
- **Current Config**: The menu shows which config you're currently using

**Example workflow:**
```
Oct 1: Run wizard → creates financial_config_2025-10-01.json
Oct 8: Run wizard again → creates financial_config_2025-10-08.json
      Both configs preserved, use option 12 to switch between them
```

## How It Works

The tool builds a 14-day cash flow projection considering:
- Current account balances and minimum balance requirements
- All upcoming income (paychecks, etc.)
- All required payments (bills, credit card minimums)
- Safety buffer to prevent overdrafts

Then it calculates **exactly how much you can safely pay** toward:
1. Building emergency fund (if below target)
2. Extra credit card payments (prioritized by your strategy)

## Action Plan Categories

**Concrete actions with specific dollar amounts:**

1. **💳 REQUIRED** - Must pay today (bills due, credit card minimums)
2. **💵 INCOME** - Money coming in today
3. **🏦 SAVE** - Safe amount to transfer to emergency fund
4. **💳 EXTRA PAYMENT** - Safe extra debt payments (shows daily interest saved)
5. **📅 UPCOMING** - Preview of required payments in next 7 days

## Example Output

```
======================================================================
  Action Plan for Wednesday, October 08, 2025
======================================================================

💵 Cash Position: $3,450.00 total | $2,950.00 available

💳 REQUIRED: CC Min Payment: MasterCard $25.00
🏦 SAVE: Transfer to emergency fund $200.00
💳 EXTRA PAYMENT: Pay extra to MasterCard (APR 23.0%, saves $0.39/day) $625.00
💳 EXTRA PAYMENT: Pay extra to Visa Card (APR 19.0%, saves $0.84/day) $1,620.00
📅 UPCOMING: $170.00 in required payments over next 7 days (3 items)

======================================================================
  Financial Summary
======================================================================

📅 As of: October 08, 2025

💰 Account Balances:
   Total Balance: $3,450.00
   Emergency Fund: $800.00
   Target Fund: $1,000.00
   Status: ! 80% of target

...
```

## File Structure

```
joes-financial-tool/
├── __init__.py                  # Package initialization
├── models.py                    # Data models (Account, Bill, CreditCard, etc.)
├── config_loader.py             # JSON config loading/saving
├── config_manager.py            # Config versioning and selection utilities
├── optimizer.py                 # Financial optimization engine with cash flow projection
├── setup_wizard.py              # Interactive setup wizard for first-time users
├── cli.py                       # Interactive menu-driven CLI
├── config_schema.json           # JSON schema definition
├── example_config.json          # Example configuration with sample data
├── financial_config.json        # Your personal config (git-ignored)
├── financial_config_*.json      # Dated config backups (git-ignored)
├── .gitignore                   # Protects sensitive financial data
└── README.md                    # This file
```

## Future Enhancements

Potential additions (contributions welcome!):
- [ ] Web UI dashboard
- [ ] Rust performance optimizations for large datasets
- [ ] Budget tracking and variance analysis
- [ ] Investment account tracking
- [ ] Spending pattern analysis
- [ ] Export to CSV/PDF reports
- [ ] Mobile notifications for due dates
- [ ] Multi-currency support
- [ ] Goal tracking (vacation fund, down payment, etc.)

## Security Note

**IMPORTANT**: Your `financial_config.json` contains sensitive financial information.
- Do NOT commit it to version control
- Consider encrypting it at rest
- Use appropriate file permissions (chmod 600)

## License

Personal use project - feel free to modify and extend!
