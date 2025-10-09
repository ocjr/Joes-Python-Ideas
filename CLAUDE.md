# Project Context for Claude Code

<!-- 
INSTRUCTIONS FOR CLAUDE:
Keep this file updated as the project evolves. When architectural decisions are made,
new patterns emerge, or project-specific context is added, update the relevant sections below.
This is a living document that should grow with the project.
-->

Top level instructions: Keep this documents Project Specific Information up to date, and commit changes after conversation. 

## Project-Specific Information

### Project Name & Purpose
**Joe's Financial Tool** - A comprehensive financial optimization and planning tool designed for users in financial distress who need concrete, actionable guidance. Provides specific dollar amounts for payments, bills, and savings rather than abstract advice. Safety-first approach to prevent overdrafts and cash flow problems.

### Current Focus
The project is feature-complete for initial release. Current state includes:
- Interactive menu-driven CLI with 19 options
- Today's actions showing only what's due today
- Configurable N-day action plans
- Financial advice system (purchase affordability, lump sum allocation)
- Bill payment tracking with paid status
- Income splitting across multiple accounts
- All three views (Today's Actions, Action Plan, Cash Flow) now consistent

### Architecture Overview
Modular Python CLI application with no external dependencies (stdlib only):
- **Data Layer:** JSON configuration with dataclass models and validation
- **Business Logic:** Optimizer calculates cash flow, safety buffers, payment recommendations
- **Presentation Layer:** CLI with interactive menus and formatted reports
- **Wizards:** Setup and edit wizards for user-friendly configuration management
- **Versioning:** Date-stamped configs with git integration for recovery

### Domain Knowledge
**Personal Finance Management:**
- Cash flow forecasting with 14-day lookahead
- Minimum balance requirements to prevent overdrafts
- Credit card payment strategies: Avalanche (highest APR first), Snowball (lowest balance first), Balanced
- Emergency fund building (target-based, recommended 30% of available funds)
- Income frequency handling: weekly, biweekly, semi-monthly, monthly, quarterly, annual
- Bill tracking with autopay vs manual payment distinction
- Payment timing: only recommend extra payments on NEXT due date to avoid double-counting funds

**Key Financial Concepts:**
- Safety buffer: minimum required balance + $200 cushion
- Available funds: total balance - minimum balance requirements
- Safe payment amount: available - safety_buffer (only if >= $50)
- Daily interest savings: (extra_payment * APR) / 365

### Key Integration Points
None - completely standalone tool with no external API dependencies. Uses:
- Local JSON files for configuration storage
- Git for version control (optional, wizard creates commits)
- Python stdlib only (no pip dependencies)

### Known Issues & Technical Debt
None currently identified. All major issues resolved:
- ✅ Payment recommendations now only for NEXT due date (prevents double-counting)
- ✅ All three views show consistent transactions
- ✅ Cash flow balances cascade properly with extra payments
- ✅ Combined payment display (min + extra on same line)
- ✅ Bill paid tracking excludes paid bills from forecasts
- ✅ Income splitting with remainder allocation

### Performance Requirements
Not performance-critical - runs instantly for typical use cases:
- Supports reasonable number of accounts (< 50), bills (< 100), credit cards (< 20)
- Cash flow calculations for 30-day periods complete in milliseconds
- No real-time or concurrent user requirements

### Security & Compliance
**Data Privacy:**
- All financial data stored locally in JSON files
- No cloud services, no data transmission
- User controls all data through git repository

**Sensitive Data Handling:**
- Financial amounts, account balances, bill information stored in plaintext JSON
- User responsible for file system permissions
- Git repository should be private
- No passwords, credentials, or authentication tokens stored

---

## Language & Technology Preferences

### Python (Primary Language)
Python is the main language for business logic and general application development due to its readability and maintainability.

**Formatting & Style:**
- Use Black formatting with default settings
- Full type hints are required on all functions and methods
- `Any` type is acceptable when specific types would be overly complex
- Annotate functions to accept the broadest, most abstract types possible (e.g., `Iterable` over `list`)
- Return concrete types from functions
- Classes should have more than just `__init__` - if it's only initialization, use a dataclass instead

**Libraries:**
- Minimize external dependencies when possible
- Preferred libraries: `requests` for HTTP, `pandas` for data manipulation
- `polars` is interesting but less familiar - consider for performance-critical data work
- Testing: `pytest` (no specific flavor preference)

**Async/Await:**
- Use when the situation dictates it
- Most appropriate for Kafka and streaming systems
- Don't force async where synchronous code is clearer

**Error Handling:**
- Keep exception handling clear and concise
- Tracebacks should be minimal (under 20 lines)
- Highlight the specific code that failed with clear explanation
- Implement robust error logging
- Catch specific exceptions rather than broad catches

**Logging:**
- Log extensively - observability is key (second only to IaC)
- Ideal target: PostgreSQL table for queryability and analysis
- Logs should be structured and analyzable

**Documentation:**
- Docstrings required for any function/method that might be called in testing or troubleshooting
- Avoid Google docstring style
- NumPy or Sphinx style preferred
- Document what the code does and why it matters

### Rust (Performance-Critical Code)
Use Rust for lower-level work that benefits from compiled performance.

**When to Use Rust:**
- Any significant performance improvement justifies Rust
- Performance-critical data processing
- System-level operations
- Would use Rust for everything if it were as easy to read as Python

### React/TypeScript (Web Interfaces)
React is the standard for web interfaces.

**Stack:**
- TypeScript (not JavaScript)
- Functional components with Props interfaces
- State management: Redux or Zustand
- Code should be responsive

## Development Environment

### Python Environment Management
- Use `uv` for environment management
- Each project must have its own `pyproject.toml`
- Generate and commit lock files for reproducibility
- Multi-platform support required: Windows, macOS, Linux
- Everything must be portable across platforms

### Directory Structure
- Organize based on GitHub repository best practices
- Structure should facilitate data workflows
- Tests organized intuitively within project constraints
- Flexibility based on project needs, but always consider scalability

## Infrastructure as Code (IaC)

**Philosophy:** Everything in code or machine-readable format unless extreme circumstances prevent it.

**Tools:**
- Pulumi for cloud infrastructure (e.g., AWS EC2 instances)
- Docker definitions for local development when Pulumi is used
- Local development should mirror production architecture using Docker containers
- S3 for production storage, but Docker should enable local equivalents

**Configuration:**
- Prefer TOML over JSON
- Either is better than hardcoding
- All configuration should be version-controlled

## Data Infrastructure

**Stack:**
- PostgreSQL for data storage
- dbt for data transformation
- Spark for data ingestion
- Scale to these tools as data needs grow

## Secrets Management

**Production:**
- AWS Secrets Manager for all production secrets
- Never commit secrets to repositories

**Development/Testing:**
- Local environment variables acceptable for testing and building
- Document required secrets in README

## CI/CD & Version Control

**Version Control:**
- All code stored in GitHub
- Use branching strategy and Pull Requests for all work (good habit for scaling)
- Currently solo development, but build for team scalability

**CI/CD:**
- GitHub Actions for production pipelines
- Local build scripts acceptable for initial builds and testing
- Automate testing and deployment where possible

## Code Review Standards

**Current State:** Solo development

**Future-Proofing:**
- Branch for all features/fixes
- Create PRs even if self-reviewing
- Build habits that will scale to team development
- Document decisions and rationale in PR descriptions

## Key Principles

1. **Readability First:** Code should be easy to understand and maintain
2. **Observability:** After IaC, logging and monitoring are paramount
3. **Portability:** Everything works on Windows, macOS, and Linux
4. **Infrastructure as Code:** If it can be defined in code, it should be
5. **Minimize Dependencies:** Only add libraries when they provide clear value
6. **Type Safety:** Use type hints to catch errors early
7. **Scalability:** Build for future growth, even in solo projects

---

## Project Evolution Log

### 2025-10-03 - Initial Project Setup
- Created Joe's Financial Tool as modular Python CLI application
- Established core architecture: data layer (JSON + dataclasses), business logic (optimizer), presentation layer (CLI)
- Implemented setup wizard for initial configuration (accounts, bills, credit cards, income)
- Built cash flow forecasting with 14-day lookahead
- Added credit card payment strategies: Avalanche, Snowball, Balanced
- Designed date-stamped configuration versioning with git integration
- Decision: No external dependencies (stdlib only) for maximum portability

### 2025-10-04 - Income Splitting and Edit Capabilities
- Added `IncomeSplit` dataclass to support income distribution across multiple accounts
- Implemented remainder allocation (e.g., "$500 to Account A, rest to Account B")
- Created `edit_wizard.py` with functions to edit bills, accounts, credit cards, and income
- Updated `setup_wizard.py` to support income splitting during initial setup
- Enhanced `config_loader.py` to persist splits in JSON format
- Why: Users needed flexibility to route income to multiple accounts and modify existing configurations

### 2025-10-05 - Summary Improvements and Smart Defaults
- Refactored summary output to be concise (removed verbose action lists)
- Added "Balance Today" section showing total assets, debt, and net worth
- Added "Projected End of Month" section with expected balances and changes
- Implemented `get_most_recent_config()` to automatically load latest dated configuration
- Modified CLI to default to most recent config file
- Why: Users wanted quick overview without scrolling, and automatic latest config selection

### 2025-10-06 - Action Plan Refinements and Bill Tracking
- Modified "Today's Actions" to show only items due TODAY (not future dates)
- Added 5-day action preview to "Action Plan"
- Implemented bill payment tracking with `last_paid` field on Bill model
- Created `bill_tracker.py` with `mark_bill_paid()` function for manual payment tracking
- Updated optimizer to skip paid bills in cash flow calculations using `is_paid_for_date()`
- Made extra payment logic more conservative (increased safety buffer from $100 to $200, minimum $50 threshold)
- Why: Users needed to know what to do today vs. later, and track manual payments to avoid double-counting

### 2025-10-07 - Payment Date Logic Fix
- Fixed critical bug: payments were showing in "Today's Actions" every day instead of only on due dates
- Modified `generate_daily_tasks()` to only calculate extra payments when target_date matches due date
- Updated autopay bill logic to show only on actual due dates
- Result: Oct 9 correctly shows "No actions", Oct 10 shows only income deposit
- Why: Users were confused by seeing payments listed on wrong dates

### 2025-10-08 - Financial Advice and Configurable Planning
- Created `financial_advisor.py` with two advisory functions:
  - `can_afford_purchase()`: Checks if spending $X is safe based on 30-day cash flow projection
  - `recommend_lump_sum_payment()`: Suggests debt allocation prioritizing emergency fund then high-interest debt
- Added interactive advice menu (option 7) with user-friendly prompts
- Made action plan configurable: user can specify 1-30 days (default 5)
- Expanded CLI to 19 total menu options
- Why: Users needed decision support for purchases and windfalls

### 2025-10-08 - Payment Consolidation and View Consistency
- Combined minimum + extra payments on same line with breakdown and daily savings
- Format: "Pay $XXX to Card (min + extra, saves $X.XX/day)"
- Refactored all three views to use consistent transaction logic:
  - Today's Actions (option 1)
  - Action Plan (option 2)
  - Cash Flow Forecast (option 3)
- Enhanced `print_cash_flow_forecast()` to include extra payments with cumulative balance tracking
- Why: Users reported inconsistent data across views and wanted cleaner payment display

### 2025-10-09 - Extra Payment Double-Counting Fix
- Fixed critical bug: system calculated extra payments for EVERY due date using same balance
- Example bug: Oct 8 ($850 extra) + Oct 22 ($1,547.50 extra) = $2,397.50 total (impossible with ~$900 available)
- Solution: Added logic to find NEXT credit card due date (earliest), only recommend extras when current_date == next_cc_due_date
- Updated all three views to use consistent next-due-date logic
- Result: Oct 8 shows $850 extra, Oct 22 shows only $55 minimum payment
- Why: Prevented recommending impossible payment amounts by ensuring funds only counted once

### 2025-10-09 - Documentation and Project Context
- Updated CLAUDE.md with comprehensive project-specific information
- Documented architecture, domain knowledge, key concepts, and resolved issues
- Added security/privacy notes (local-only data, no cloud services)
- Created project evolution log to maintain historical context
- Why: Enable future development with full context of decisions and patterns