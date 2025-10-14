# Rust Acceleration for Monte Carlo Simulations

## Performance Analysis

**Current Performance (Pure Python):**
- ~2.3 simulations/second for 27-year projections
- 1000 runs to age 65: ~7 minutes
- 1000 runs to age 80: ~10+ minutes

**Expected Performance (Rust):**
- ~100-500 simulations/second (10-50x faster)
- 1000 runs to age 65: **~10-60 seconds**
- 1000 runs to age 80: **~15-90 seconds**
- With parallelization: **~2-10 seconds**

## Implementation Plan

### Option 1: PyO3 (Recommended)
Use PyO3 to create a Rust library callable from Python.

**Benefits:**
- Seamless integration with existing Python code
- No rewrite of CLI or data models needed
- Just the hot path (simulation loop) in Rust

**Structure:**
```
joes-financial-tool/
├── simulation_engine.py      (Python wrapper)
├── simulation_engine_rust/    (Rust implementation)
│   ├── Cargo.toml
│   ├── src/
│   │   ├── lib.rs            (PyO3 bindings)
│   │   ├── monte_carlo.rs    (Core simulation)
│   │   ├── price_path.rs     (GBM price generation)
│   │   └── events.rs         (Event processing)
```

**Key Rust Features to Use:**
1. **Rayon** - Parallel iterator for running simulations concurrently
2. **rand** - Fast random number generation
3. **chrono** - Date/time handling
4. **PyO3** - Python bindings

### Option 2: Standalone Rust Binary
Create a separate Rust binary that Python shells out to.

**Benefits:**
- Even faster (no Python/Rust boundary crossing)
- Can be distributed as standalone tool
- JSON input/output for data exchange

**Drawbacks:**
- More complex integration
- Data serialization overhead

## Quick Setup (Option 1 - PyO3)

### 1. Install Rust
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

### 2. Create Rust Library
```bash
cd joes-financial-tool
cargo new --lib simulation_engine_rust
cd simulation_engine_rust
```

### 3. Add Dependencies (Cargo.toml)
```toml
[package]
name = "simulation_engine_rust"
version = "0.1.0"
edition = "2021"

[lib]
name = "simulation_engine_rust"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.20", features = ["extension-module"] }
rand = "0.8"
rand_distr = "0.4"
rayon = "1.8"
chrono = "0.4"
```

### 4. Core Rust Implementation (src/lib.rs)
```rust
use pyo3::prelude::*;
use rand::prelude::*;
use rand_distr::StandardNormal;
use rayon::prelude::*;

#[pyfunction]
fn run_monte_carlo_fast(
    num_simulations: usize,
    years_to_simulate: i32,
    initial_balance: f64,
    monthly_income: f64,
    expected_return: f64,
    volatility: f64,
    expense_ratio: f64,
    short_term_tax: f64,
    long_term_tax: f64,
) -> PyResult<Vec<f64>> {

    // Run simulations in parallel using Rayon
    let results: Vec<f64> = (0..num_simulations)
        .into_par_iter()
        .map(|seed| {
            run_single_simulation(
                seed as u64,
                years_to_simulate,
                initial_balance,
                monthly_income,
                expected_return,
                volatility,
                expense_ratio,
                short_term_tax,
                long_term_tax,
            )
        })
        .collect();

    Ok(results)
}

fn run_single_simulation(
    seed: u64,
    years: i32,
    initial_balance: f64,
    monthly_income: f64,
    expected_return: f64,
    volatility: f64,
    expense_ratio: f64,
    short_term_tax: f64,
    long_term_tax: f64,
) -> f64 {
    let mut rng = StdRng::seed_from_u64(seed);
    let days = years * 365;

    // Daily parameters
    let daily_return = expected_return / 252.0;
    let daily_volatility = volatility / 252.0_f64.sqrt();
    let daily_expense = expense_ratio / 252.0;

    // Generate price path using geometric Brownian motion
    let mut price = 450.0;
    let mut account_value = initial_balance;

    for day in 0..days {
        // Weekend check (simplified)
        if day % 7 == 5 || day % 7 == 6 {
            continue;
        }

        // Price evolution
        let shock: f64 = rng.sample(StandardNormal);
        let drift = daily_return - daily_expense - 0.5 * daily_volatility.powi(2);
        let diffusion = daily_volatility * shock;
        price = (price * (1.0 + drift + diffusion)).max(1.0);

        // Monthly income investment (simplified)
        if day % 30 == 0 && day > 0 {
            account_value += monthly_income;
        }

        // Update account value
        let shares = account_value / price;
        account_value = shares * price;
    }

    account_value
}

#[pymodule]
fn simulation_engine_rust(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(run_monte_carlo_fast, m)?)?;
    Ok(())
}
```

### 5. Build
```bash
cd simulation_engine_rust
pip install maturin
maturin develop --release
```

### 6. Use from Python
```python
# In simulation_engine.py
try:
    from simulation_engine_rust import run_monte_carlo_fast
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False

def run_monte_carlo(self, target_age: int) -> MonteCarloResults:
    if RUST_AVAILABLE:
        # Use Rust implementation
        results = run_monte_carlo_fast(...)
    else:
        # Fallback to Python
        results = self._run_monte_carlo_python(target_age)
```

## Expected Results

**Before (Python):**
```
Running 1000 simulations...
  [1000/1000] 2.3 runs/sec
  ✓ Completed in 434.8s (7.2 minutes)
```

**After (Rust, Single-threaded):**
```
Running 1000 simulations...
  [1000/1000] 50+ runs/sec
  ✓ Completed in 20s
```

**After (Rust, Parallel):**
```
Running 1000 simulations...
  [1000/1000] 200+ runs/sec
  ✓ Completed in 5s
```

## Recommendation

Given your preferences ("Any significant performance improvement justifies Rust"), I recommend implementing Option 1 (PyO3). This gives us:

1. **10-50x speedup** for numerical computations
2. **Parallel execution** across CPU cores
3. **Zero changes** to CLI or user-facing code
4. **Fallback** to Python if Rust not available

The investment in Rust here is well worth it - turning 7 minutes into 5-20 seconds makes a huge difference in usability, especially when iterating on simulation parameters.

Want me to implement this?
