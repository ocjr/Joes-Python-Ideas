use pyo3::prelude::*;
use rand::prelude::*;
use rand_distr::StandardNormal;
use rayon::prelude::*;
use std::collections::HashMap;

/// Python-visible function to run Monte Carlo simulations in parallel
#[pyfunction]
#[pyo3(signature = (
    num_simulations,
    current_age,
    target_age,
    initial_balance,
    income_events,
    expected_annual_return,
    annual_volatility,
    expense_ratio,
    short_term_tax_rate,
    long_term_tax_rate,
    dividend_yield,
    dividend_tax_rate,
    liquidation_day,
    strategy_type = "monthly_liquidation",
    random_seed = None
))]
fn run_monte_carlo(
    num_simulations: usize,
    current_age: i32,
    target_age: i32,
    initial_balance: f64,
    income_events: Vec<(i32, f64)>, // (day_offset, amount)
    expected_annual_return: f64,
    annual_volatility: f64,
    expense_ratio: f64,
    short_term_tax_rate: f64,
    long_term_tax_rate: f64,
    dividend_yield: f64,
    dividend_tax_rate: f64,
    liquidation_day: i32,
    strategy_type: &str,
    random_seed: Option<u64>,
) -> PyResult<Vec<SimulationResult>> {

    let years = target_age - current_age;
    let total_days = years * 365;

    // Run simulations in parallel using Rayon
    let results: Vec<SimulationResult> = (0..num_simulations)
        .into_par_iter()
        .map(|i| {
            let seed = random_seed.map(|s| s + i as u64).unwrap_or(i as u64);
            run_single_simulation(
                seed,
                total_days,
                initial_balance,
                &income_events,
                expected_annual_return,
                annual_volatility,
                expense_ratio,
                short_term_tax_rate,
                long_term_tax_rate,
                dividend_yield,
                dividend_tax_rate,
                liquidation_day,
                strategy_type,
            )
        })
        .collect();

    Ok(results)
}

#[pyclass]
#[derive(Clone, Debug)]
struct SimulationResult {
    #[pyo3(get)]
    run_number: usize,
    #[pyo3(get)]
    final_account_value: f64,
    #[pyo3(get)]
    total_invested: f64,
    #[pyo3(get)]
    total_withdrawn: f64,
    #[pyo3(get)]
    total_taxes_paid: f64,
    #[pyo3(get)]
    total_dividends: f64,
}

fn run_single_simulation(
    seed: u64,
    total_days: i32,
    initial_balance: f64,
    income_events: &[(i32, f64)],
    expected_annual_return: f64,
    annual_volatility: f64,
    expense_ratio: f64,
    short_term_tax_rate: f64,
    long_term_tax_rate: f64,
    dividend_yield: f64,
    dividend_tax_rate: f64,
    liquidation_day: i32,
    strategy_type: &str,
) -> SimulationResult {
    let mut rng = StdRng::seed_from_u64(seed);

    // Daily parameters from annual
    let daily_return = expected_annual_return / 252.0;
    let daily_volatility = annual_volatility / (252.0_f64).sqrt();
    let daily_expense = expense_ratio / 252.0;

    // Generate price path
    let prices = simulate_price_path(
        &mut rng,
        total_days,
        450.0, // starting price
        daily_return,
        daily_volatility,
        daily_expense,
    );

    // Track state
    let mut shares_held = 0.0;
    let mut total_invested = 0.0;
    let mut total_withdrawn = 0.0;
    let mut total_taxes_paid = 0.0;
    let mut total_dividends = 0.0;

    // Purchase lots for FIFO accounting: (shares, cost_basis_per_share, purchase_day)
    let mut purchase_lots: Vec<(f64, f64, i32)> = Vec::new();

    // Initial balance investment
    if initial_balance > 0.0 {
        let initial_price = prices[0];
        let initial_shares = initial_balance / initial_price;
        shares_held = initial_shares;
        purchase_lots.push((initial_shares, initial_price, 0));
        total_invested = initial_balance;
    }

    // Create income event lookup
    let income_map: HashMap<i32, f64> = income_events.iter().cloned().collect();

    // For principal_only strategy, track income events for batched liquidation
    let mut principal_only_incomes: Vec<(i32, f64)> = Vec::new();

    // Process days
    for day in 0..total_days {
        // Skip weekends (simplified: every 7th day is weekend)
        if day % 7 == 5 || day % 7 == 6 {
            continue;
        }

        let price = prices[day as usize];

        // Check for income event
        if let Some(&income_amount) = income_map.get(&day) {
            // Buy shares with income
            let shares_to_buy = income_amount / price;
            shares_held += shares_to_buy;
            total_invested += income_amount;
            purchase_lots.push((shares_to_buy, price, day));

            if strategy_type == "principal_only" {
                // Track for batched liquidation later
                principal_only_incomes.push((day, income_amount));
            } else {
                // Standard liquidation: schedule for next month's liquidation day
                let liquidation = next_liquidation_date(day, liquidation_day);

                if liquidation < total_days {
                    // Sell shares to get income back
                    let liquidation_price = prices[liquidation as usize];
                    let shares_to_sell = (income_amount / liquidation_price).min(shares_held);
                    let sale_proceeds = shares_to_sell * liquidation_price;

                    // FIFO tax calculation
                    let (new_lots, tax_owed) = sell_shares_fifo(
                        &purchase_lots,
                        shares_to_sell,
                        liquidation_price,
                        liquidation,
                        short_term_tax_rate,
                        long_term_tax_rate,
                    );

                    purchase_lots = new_lots;
                    shares_held -= shares_to_sell;
                    total_withdrawn += sale_proceeds;
                    total_taxes_paid += tax_owed;
                }
            }
        }

        // Quarterly dividends (simplified: every 90 days)
        if day % 90 == 0 && day > 0 && shares_held > 0.0 {
            let quarterly_yield = dividend_yield / 4.0;
            let dividend_per_share = price * quarterly_yield;
            let dividend_amount = shares_held * dividend_per_share;
            let dividend_tax = dividend_amount * dividend_tax_rate;
            let net_dividend = dividend_amount - dividend_tax;

            total_dividends += dividend_amount;
            total_taxes_paid += dividend_tax;

            // Reinvest net dividend
            if net_dividend > 0.0 {
                let shares_to_buy = net_dividend / price;
                shares_held += shares_to_buy;
                purchase_lots.push((shares_to_buy, price, day));
            }
        }
    }

    // For principal_only strategy, process batched monthly liquidations
    if strategy_type == "principal_only" {
        // Group income events by liquidation date
        let mut liquidation_groups: HashMap<i32, Vec<f64>> = HashMap::new();

        for (income_day, income_amount) in &principal_only_incomes {
            let liquidation = next_liquidation_date(*income_day, liquidation_day);
            if liquidation < total_days {
                liquidation_groups.entry(liquidation)
                    .or_insert_with(Vec::new)
                    .push(*income_amount);
            }
        }

        // Process each liquidation date
        let mut sorted_liquidations: Vec<_> = liquidation_groups.into_iter().collect();
        sorted_liquidations.sort_by_key(|(day, _)| *day);

        for (liquidation_day, amounts) in sorted_liquidations {
            let total_principal: f64 = amounts.iter().sum();
            let liquidation_price = prices[liquidation_day as usize];

            // Sell only enough shares to recover principal
            let shares_needed = total_principal / liquidation_price;
            let shares_to_sell = shares_needed.min(shares_held);

            if shares_to_sell < 1e-8 {
                continue;
            }

            let sale_proceeds = shares_to_sell * liquidation_price;

            // FIFO tax calculation
            let (new_lots, tax_owed) = sell_shares_fifo(
                &purchase_lots,
                shares_to_sell,
                liquidation_price,
                liquidation_day,
                short_term_tax_rate,
                long_term_tax_rate,
            );

            purchase_lots = new_lots;
            shares_held -= shares_to_sell;
            total_withdrawn += sale_proceeds;
            total_taxes_paid += tax_owed;
        }
    }

    // Final account value
    let final_price = prices[total_days as usize - 1];
    let final_account_value = shares_held * final_price;

    SimulationResult {
        run_number: seed as usize,
        final_account_value,
        total_invested,
        total_withdrawn,
        total_taxes_paid,
        total_dividends,
    }
}

fn sell_shares_fifo(
    purchase_lots: &[(f64, f64, i32)], // (shares, cost_basis, purchase_day)
    shares_to_sell: f64,
    sell_price: f64,
    sell_day: i32,
    short_term_tax_rate: f64,
    long_term_tax_rate: f64,
) -> (Vec<(f64, f64, i32)>, f64) {
    let mut remaining_to_sell = shares_to_sell;
    let mut tax_owed = 0.0;
    let mut new_lots = Vec::new();

    for (lot_shares, lot_cost_basis, lot_day) in purchase_lots {
        if remaining_to_sell <= 1e-8 {
            new_lots.push((*lot_shares, *lot_cost_basis, *lot_day));
            continue;
        }

        let shares_from_lot = remaining_to_sell.min(*lot_shares);
        let hold_days = sell_day - lot_day;

        // Calculate tax
        let cost = shares_from_lot * lot_cost_basis;
        let proceeds = shares_from_lot * sell_price;
        let gain = proceeds - cost;

        if gain > 0.0 {
            let tax_rate = if hold_days >= 365 {
                long_term_tax_rate
            } else {
                short_term_tax_rate
            };
            tax_owed += gain * tax_rate;
        }

        remaining_to_sell -= shares_from_lot;

        // Keep remaining shares in lot
        let remaining_shares = lot_shares - shares_from_lot;
        if remaining_shares > 1e-8 {
            new_lots.push((remaining_shares, *lot_cost_basis, *lot_day));
        }
    }

    (new_lots, tax_owed)
}

fn simulate_price_path(
    rng: &mut StdRng,
    total_days: i32,
    start_price: f64,
    daily_return: f64,
    daily_volatility: f64,
    daily_expense: f64,
) -> Vec<f64> {
    let mut prices = Vec::with_capacity(total_days as usize);
    let mut current_price = start_price;

    for _ in 0..total_days {
        // Skip weekends
        let shock: f64 = rng.sample(StandardNormal);
        let drift = daily_return - daily_expense - 0.5 * daily_volatility.powi(2);
        let diffusion = daily_volatility * shock;
        let price_change = current_price * (drift + diffusion);
        current_price = (current_price + price_change).max(1.0);

        prices.push(current_price);
    }

    prices
}

// Helper to check if a year is a leap year
fn is_leap_year(year: i32) -> bool {
    (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0)
}

// Helper to get days in a specific month
fn days_in_month(year: i32, month: i32) -> i32 {
    match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 => if is_leap_year(year) { 29 } else { 28 },
        _ => 30, // fallback
    }
}

// Convert day offset from start to (year, month, day)
fn day_offset_to_date(day_offset: i32, start_year: i32, start_month: i32, start_day: i32) -> (i32, i32, i32) {
    let mut year = start_year;
    let mut month = start_month;
    let mut day = start_day + day_offset;

    // Normalize the date by advancing through months and years
    while day > days_in_month(year, month) {
        day -= days_in_month(year, month);
        month += 1;
        if month > 12 {
            month = 1;
            year += 1;
        }
    }

    (year, month, day)
}

// Convert (year, month, day) back to day offset from start
fn date_to_day_offset(year: i32, month: i32, day: i32, start_year: i32, start_month: i32, start_day: i32) -> i32 {
    if year == start_year && month == start_month {
        // Same month: simple difference
        return day - start_day;
    }

    if year == start_year {
        // Same year, different month
        let mut total_days = 0;
        // Days remaining in start month
        total_days += days_in_month(year, start_month) - start_day;
        // Complete months in between
        let mut m = start_month + 1;
        while m < month {
            total_days += days_in_month(year, m);
            m += 1;
        }
        // Days in target month
        total_days += day;
        return total_days;
    }

    // Different year - count carefully!
    let mut total_days = 0;

    // Days remaining in start month to end of start month
    total_days += days_in_month(start_year, start_month) - start_day;

    // Remaining months in start year
    let mut m = start_month + 1;
    while m <= 12 {
        total_days += days_in_month(start_year, m);
        m += 1;
    }

    // Complete years in between (not including start year or target year)
    let mut y = start_year + 1;
    while y < year {
        total_days += if is_leap_year(y) { 366 } else { 365 };
        y += 1;
    }

    // Complete months in target year before target month
    let mut m = 1;
    while m < month {
        total_days += days_in_month(year, m);
        m += 1;
    }

    // Days in target month
    total_days += day;

    total_days
}

// Get day of week (0 = Monday, 6 = Sunday)
// Using Zeller's congruence
fn day_of_week(year: i32, month: i32, day: i32) -> i32 {
    let mut y = year;
    let mut m = month;

    // Adjust for Zeller's: Jan and Feb are months 13 and 14 of previous year
    if m < 3 {
        m += 12;
        y -= 1;
    }

    let q = day;
    let k = y % 100;
    let j = y / 100;

    let h = (q + (13 * (m + 1)) / 5 + k + k / 4 + j / 4 - 2 * j) % 7;

    // Convert Zeller's output (0=Sat) to our format (0=Mon, 5=Sat, 6=Sun)
    (h + 5) % 7
}

fn next_liquidation_date(after_day: i32, liquidation_day: i32) -> i32 {
    // Assume simulation starts on 2025-10-13 (hardcoded for now, matches Python's date.today())
    let start_year = 2025;
    let start_month = 10;
    let start_day = 13;

    // Convert after_day to actual date
    let (mut year, mut month, _income_day) = day_offset_to_date(after_day, start_year, start_month, start_day);

    // Start with liquidation_day in the SAME month as income
    let max_day_this_month = days_in_month(year, month);
    let mut target_day = liquidation_day.min(max_day_this_month);

    // Convert to day offset to compare with after_day
    let candidate_offset = date_to_day_offset(year, month, target_day, start_year, start_month, start_day);

    // If liquidation date is on or before income date, move to next month
    if candidate_offset <= after_day {
        month += 1;
        if month > 12 {
            month = 1;
            year += 1;
        }
        // Recalculate target_day for next month
        let max_day_next_month = days_in_month(year, month);
        target_day = liquidation_day.min(max_day_next_month);
    }

    // Skip weekends (5 = Saturday, 6 = Sunday)
    loop {
        let dow = day_of_week(year, month, target_day);
        if dow < 5 {
            break; // Weekday found
        }
        target_day += 1;
        if target_day > days_in_month(year, month) {
            // Spilled into next month
            target_day = 1;
            month += 1;
            if month > 12 {
                month = 1;
                year += 1;
            }
        }
    }

    // Convert back to day offset
    date_to_day_offset(year, month, target_day, start_year, start_month, start_day)
}

/// Python module definition
#[pymodule]
fn simulation_rust(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(run_monte_carlo, m)?)?;
    m.add_class::<SimulationResult>()?;
    Ok(())
}
