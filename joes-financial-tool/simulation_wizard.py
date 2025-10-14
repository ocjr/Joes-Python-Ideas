#!/usr/bin/env python3
"""
Wizards for creating and editing simulation configurations.
"""

from models import InvestmentSimulation, FinancialConfig
from config_loader import load_config, save_config
from etf_library import ETFLibrary


def add_simulation_to_config(config_path: str = "financial_config.json"):
    """Interactive wizard to add a new simulation configuration."""
    print("=" * 70)
    print("  ADD NEW SIMULATION")
    print("=" * 70)
    print()

    # Load existing config
    try:
        config = load_config(config_path)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return

    # Get simulation ID
    print("Simulation ID (unique identifier, e.g., 'spy_float_retirement'):")
    sim_id = input("  ID: ").strip()
    if not sim_id:
        print("❌ ID is required")
        return

    # Check for duplicate
    if any(s.id == sim_id for s in config.simulations):
        print(f"❌ Simulation with ID '{sim_id}' already exists")
        return

    # Get simulation name
    print("\nSimulation name (descriptive, e.g., 'SPY Float Strategy to Retirement'):")
    name = input("  Name: ").strip()
    if not name:
        print("❌ Name is required")
        return

    # Current age
    print("\nYour current age:")
    try:
        current_age = int(input(f"  Age (default 38): ").strip() or "38")
    except ValueError:
        print("❌ Invalid age")
        return

    # Target ages
    print("\nTarget ages to simulate (comma-separated, e.g., '65,80'):")
    target_input = input(f"  Ages (default 65,80): ").strip() or "65,80"
    try:
        target_ages = [int(x.strip()) for x in target_input.split(",")]
    except ValueError:
        print("❌ Invalid target ages")
        return

    # Strategy type
    print("\nStrategy type:")
    print("  1. Monthly liquidation (sell on specific day each month)")
    print("  2. Constant hold (hold for fixed number of days)")
    print("  3. Principal-only (sell only principal, let gains compound) 🆕")
    strategy_choice = input("  Choice (1, 2, or 3, default 1): ").strip() or "1"

    if strategy_choice == "2":
        strategy_type = "constant_hold"
        print("\nHold period (days):")
        try:
            hold_days = int(input("  Days (default 14): ").strip() or "14")
        except ValueError:
            print("❌ Invalid hold days")
            return
        liquidation_day = 1  # Not used for constant_hold
    elif strategy_choice == "3":
        strategy_type = "principal_only"
        hold_days = 14  # Not used for principal_only
        print("\nLiquidation day (day of month to sell principal):")
        print(
            "  This is when you'll sell enough shares to recover your paycheck amounts"
        )
        print("  All gains will stay invested and compound!")
        try:
            liquidation_day = int(input("  Day (1-28, default 1): ").strip() or "1")
            if not 1 <= liquidation_day <= 28:
                print("❌ Day must be between 1 and 28")
                return
        except ValueError:
            print("❌ Invalid day")
            return
    else:
        strategy_type = "monthly_liquidation"
        hold_days = 14  # Not used for monthly_liquidation
        print("\nLiquidation day (day of month to sell):")
        try:
            liquidation_day = int(input("  Day (1-28, default 1): ").strip() or "1")
            if not 1 <= liquidation_day <= 28:
                print("❌ Day must be between 1 and 28")
                return
        except ValueError:
            print("❌ Invalid day")
            return

    # Initial balance
    print("\nInitial account balance (starting investment):")
    try:
        initial_balance = float(input("  Balance (default $0): $").strip() or "0")
    except ValueError:
        print("❌ Invalid balance")
        return

    # Income sources
    print("\nSelect income sources to include in simulation:")
    if not config.income:
        print("  (No income sources configured)")
        income_source_ids = []
    else:
        print("  Available income sources:")
        for i, inc in enumerate(config.income, 1):
            print(
                f"    {i}. {inc.source} - ${inc.amount:,.2f} {inc.frequency.value} (ID: {inc.id})"
            )

        print("\n  Enter income source numbers (comma-separated, e.g., '1,2'):")
        print("  Or press Enter to skip (simulation will only use initial balance):")
        income_input = input("  Sources: ").strip()
        if income_input:
            try:
                indices = [int(x.strip()) - 1 for x in income_input.split(",")]
                income_source_ids = [
                    config.income[i].id for i in indices if 0 <= i < len(config.income)
                ]
                if income_source_ids:
                    print(f"  ✓ Selected: {', '.join(income_source_ids)}")
            except (ValueError, IndexError):
                print("❌ Invalid income source selection")
                return
        else:
            income_source_ids = []
            print(
                "  ℹ️  No income sources selected - simulation will only use initial balance"
            )

    # Income growth parameters
    print("\n--- Income Growth Parameters ---")
    print("\nIncome growth rate (decimal, e.g., 0.10 for 10%):")
    try:
        income_growth_rate = float(
            input("  Rate (default 0.0 = no growth): ").strip() or "0.0"
        )
    except ValueError:
        print("❌ Invalid growth rate")
        return

    if income_growth_rate > 0:
        print("\nApply growth every N years (e.g., 2 for biennial growth):")
        try:
            income_growth_frequency = int(
                input("  Years (default 1 = annual): ").strip() or "1"
            )
            if income_growth_frequency < 1:
                print("❌ Frequency must be at least 1 year")
                return
        except ValueError:
            print("❌ Invalid frequency")
            return
    else:
        income_growth_frequency = 1  # Default, not used if growth_rate is 0

    # Investment parameters
    print("\n--- Investment Parameters ---")

    # Load ETF library
    library = ETFLibrary()

    # Ask if they want to use a preset
    print("\nUse ETF preset from library?")
    print("  1. Yes - select from library")
    print("  2. No - enter custom parameters")
    use_preset = input("  Choice (1 or 2, default 1): ").strip() or "1"

    if use_preset == "1" and library.etfs:
        # Show available ETFs by category
        print("\nAvailable ETFs:")
        categories = library.list_by_category()
        all_etfs = []
        idx = 1
        for category in sorted(categories.keys()):
            print(f"\n  {category}:")
            for etf in sorted(categories[category], key=lambda e: e.ticker):
                print(f"    {idx}. {etf.ticker:6s} - {etf.name}")
                print(
                    f"       Return: {etf.expected_annual_return*100:5.1f}%  |  Vol: {etf.annual_volatility*100:5.1f}%  |  Div: {etf.annual_dividend_yield*100:5.2f}%"
                )
                all_etfs.append(etf)
                idx += 1

        # Get selection
        try:
            choice = input(f"\n  Select ETF (1-{len(all_etfs)}): ").strip()
            etf_idx = int(choice) - 1
            if 0 <= etf_idx < len(all_etfs):
                selected_etf = all_etfs[etf_idx]
                ticker = selected_etf.ticker
                expected_return = selected_etf.expected_annual_return
                volatility = selected_etf.annual_volatility
                dividend_yield = selected_etf.annual_dividend_yield
                expense_ratio = selected_etf.expense_ratio

                print(f"\n  ✓ Selected {ticker}: {selected_etf.name}")
                print(f"    {selected_etf.description}")
            else:
                print("❌ Invalid selection, using SPY defaults")
                ticker = "SPY"
                expected_return = 0.10
                volatility = 0.15
                dividend_yield = 0.015
                expense_ratio = 0.0009
        except (ValueError, IndexError):
            print("❌ Invalid input, using SPY defaults")
            ticker = "SPY"
            expected_return = 0.10
            volatility = 0.15
            dividend_yield = 0.015
            expense_ratio = 0.0009
    else:
        # Manual entry
        print("\nTicker symbol:")
        ticker = input("  Ticker (default SPY): ").strip() or "SPY"

        print("\nExpected annual return (decimal):")
        try:
            expected_return = float(
                input("  Return (default 0.10 = 10%): ").strip() or "0.10"
            )
        except ValueError:
            print("❌ Invalid return")
            return

        print("\nAnnual volatility (standard deviation):")
        try:
            volatility = float(
                input("  Volatility (default 0.15 = 15%): ").strip() or "0.15"
            )
        except ValueError:
            print("❌ Invalid volatility")
            return

        print("\nAnnual dividend yield:")
        try:
            dividend_yield = float(
                input("  Yield (default 0.015 = 1.5%): ").strip() or "0.015"
            )
        except ValueError:
            print("❌ Invalid dividend yield")
            return

        print("\nExpense ratio:")
        try:
            expense_ratio = float(
                input("  Ratio (default 0.0009 = 0.09%): ").strip() or "0.0009"
            )
        except ValueError:
            print("❌ Invalid expense ratio")
            return

    # Tax parameters
    print("\n--- Tax Parameters ---")

    print("\nShort-term capital gains rate (< 1 year):")
    try:
        short_term_rate = float(
            input("  Rate (default 0.22 = 22%): ").strip() or "0.22"
        )
    except ValueError:
        print("❌ Invalid rate")
        return

    print("\nLong-term capital gains rate (>= 1 year):")
    try:
        long_term_rate = float(input("  Rate (default 0.15 = 15%): ").strip() or "0.15")
    except ValueError:
        print("❌ Invalid rate")
        return

    print("\nQualified dividend tax rate:")
    try:
        dividend_tax = float(input("  Rate (default 0.15 = 15%): ").strip() or "0.15")
    except ValueError:
        print("❌ Invalid rate")
        return

    # Monte Carlo parameters
    print("\n--- Monte Carlo Parameters ---")

    print("\nNumber of simulation runs:")
    try:
        num_sims = int(input("  Runs (default 1000): ").strip() or "1000")
    except ValueError:
        print("❌ Invalid number")
        return

    print("\nRandom seed (for reproducibility, leave blank for random):")
    seed_input = input("  Seed: ").strip()
    random_seed = int(seed_input) if seed_input else None

    # Create simulation
    simulation = InvestmentSimulation(
        id=sim_id,
        name=name,
        enabled=True,
        current_age=current_age,
        target_ages=target_ages,
        strategy_type=strategy_type,
        hold_days=hold_days,
        liquidation_day=liquidation_day,
        income_source_ids=income_source_ids,
        income_growth_rate=income_growth_rate,
        income_growth_frequency=income_growth_frequency,
        ticker=ticker,
        initial_balance=initial_balance,
        expected_annual_return=expected_return,
        annual_volatility=volatility,
        annual_dividend_yield=dividend_yield,
        expense_ratio=expense_ratio,
        short_term_cap_gains_rate=short_term_rate,
        long_term_cap_gains_rate=long_term_rate,
        dividend_tax_rate=dividend_tax,
        num_simulations=num_sims,
        random_seed=random_seed,
    )

    # Add to config
    config.simulations.append(simulation)

    # Save
    try:
        save_config(config, config_path)
        print(f"\n✅ Simulation '{name}' added successfully!")
    except Exception as e:
        print(f"\n❌ Error saving config: {e}")


def edit_simulation(config_path: str = "financial_config.json"):
    """Interactive wizard to edit an existing simulation."""
    print("=" * 70)
    print("  EDIT SIMULATION")
    print("=" * 70)
    print()

    # Load config
    try:
        config = load_config(config_path)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return

    if not config.simulations:
        print("No simulations configured.")
        return

    # Show simulations
    print("Available simulations:\n")
    for i, sim in enumerate(config.simulations, 1):
        status = "✅" if sim.enabled else "❌"
        print(f"  {i}. {sim.name} ({status})")
        print(f"     ID: {sim.id}")
        print(f"     Strategy: {sim.strategy_type}")
        print()

    # Select simulation
    try:
        choice = input(
            f"Select simulation to edit (1-{len(config.simulations)}, 0 to cancel): "
        ).strip()
        if not choice or choice == "0":
            print("Cancelled.")
            return

        sim_idx = int(choice) - 1
        if sim_idx < 0 or sim_idx >= len(config.simulations):
            print("Invalid selection.")
            return

        sim = config.simulations[sim_idx]
    except (ValueError, KeyboardInterrupt):
        print("\nCancelled.")
        return

    print(f"\nEditing: {sim.name}")
    print("(Press Enter to keep current value)\n")

    # Edit fields
    name = input(f"Name [{sim.name}]: ").strip() or sim.name

    enabled_input = (
        input(f"Enabled (y/n) [{'' if sim.enabled else 'n'}]: ").strip().lower()
    )
    enabled = sim.enabled if not enabled_input else (enabled_input == "y")

    age_input = input(f"Current age [{sim.current_age}]: ").strip()
    current_age = int(age_input) if age_input else sim.current_age

    ages_input = input(f"Target ages [{','.join(map(str, sim.target_ages))}]: ").strip()
    target_ages = (
        [int(x.strip()) for x in ages_input.split(",")]
        if ages_input
        else sim.target_ages
    )

    balance_input = input(f"Initial balance [${sim.initial_balance:,.2f}]: $").strip()
    initial_balance = float(balance_input) if balance_input else sim.initial_balance

    # Strategy parameters
    if sim.strategy_type == "monthly_liquidation":
        liq_input = input(f"Liquidation day [{sim.liquidation_day}]: ").strip()
        liquidation_day = int(liq_input) if liq_input else sim.liquidation_day
    else:
        hold_input = input(f"Hold days [{sim.hold_days}]: ").strip()
        hold_days = int(hold_input) if hold_input else sim.hold_days

    # Investment parameters
    ticker = input(f"Ticker [{sim.ticker}]: ").strip() or sim.ticker

    return_input = input(
        f"Expected annual return [{sim.expected_annual_return}]: "
    ).strip()
    expected_return = (
        float(return_input) if return_input else sim.expected_annual_return
    )

    vol_input = input(f"Annual volatility [{sim.annual_volatility}]: ").strip()
    volatility = float(vol_input) if vol_input else sim.annual_volatility

    div_input = input(f"Dividend yield [{sim.annual_dividend_yield}]: ").strip()
    dividend_yield = float(div_input) if div_input else sim.annual_dividend_yield

    exp_input = input(f"Expense ratio [{sim.expense_ratio}]: ").strip()
    expense_ratio = float(exp_input) if exp_input else sim.expense_ratio

    # Tax rates
    stcg_input = input(
        f"Short-term cap gains rate [{sim.short_term_cap_gains_rate}]: "
    ).strip()
    short_term_rate = float(stcg_input) if stcg_input else sim.short_term_cap_gains_rate

    ltcg_input = input(
        f"Long-term cap gains rate [{sim.long_term_cap_gains_rate}]: "
    ).strip()
    long_term_rate = float(ltcg_input) if ltcg_input else sim.long_term_cap_gains_rate

    divtax_input = input(f"Dividend tax rate [{sim.dividend_tax_rate}]: ").strip()
    dividend_tax = float(divtax_input) if divtax_input else sim.dividend_tax_rate

    # Income growth
    growth_rate_input = input(
        f"Income growth rate [{sim.income_growth_rate}]: "
    ).strip()
    income_growth_rate = (
        float(growth_rate_input) if growth_rate_input else sim.income_growth_rate
    )

    growth_freq_input = input(
        f"Income growth frequency (years) [{sim.income_growth_frequency}]: "
    ).strip()
    income_growth_frequency = (
        int(growth_freq_input) if growth_freq_input else sim.income_growth_frequency
    )

    # Monte Carlo
    sims_input = input(f"Number of simulations [{sim.num_simulations}]: ").strip()
    num_sims = int(sims_input) if sims_input else sim.num_simulations

    # Update simulation
    sim.name = name
    sim.enabled = enabled
    sim.current_age = current_age
    sim.target_ages = target_ages
    sim.initial_balance = initial_balance
    if sim.strategy_type == "monthly_liquidation":
        sim.liquidation_day = liquidation_day
    else:
        sim.hold_days = hold_days
    sim.ticker = ticker
    sim.expected_annual_return = expected_return
    sim.annual_volatility = volatility
    sim.annual_dividend_yield = dividend_yield
    sim.expense_ratio = expense_ratio
    sim.short_term_cap_gains_rate = short_term_rate
    sim.long_term_cap_gains_rate = long_term_rate
    sim.dividend_tax_rate = dividend_tax
    sim.income_growth_rate = income_growth_rate
    sim.income_growth_frequency = income_growth_frequency
    sim.num_simulations = num_sims

    # Save
    try:
        save_config(config, config_path)
        print(f"\n✅ Simulation updated successfully!")
    except Exception as e:
        print(f"\n❌ Error saving config: {e}")
