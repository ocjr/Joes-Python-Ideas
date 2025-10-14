# Test Suite

This directory contains all test files for Joe's Financial Tool.

## Running Tests

All tests can be run directly with Python from the project root directory:

```bash
# Run a specific test
python3 tests/test_events.py

# Run instruction generation test
python3 tests/test_instructions_generation.py

# Run Python simulation test (works without Rust)
python3 tests/test_events.py
```

## Test Categories

### Simulation Tests
- `test_events.py` - Demonstrates detailed event tracking (Python implementation)
- `test_instructions_generation.py` - Tests actionable instruction generation
- `test_python_vs_rust.py` - Compares Python and Rust simulation accuracy/performance
- `test_rust_performance.py` - Benchmarks Rust acceleration
- `test_simulation.py` - Basic simulation engine tests
- `test_principal_only_strategy.py` - Tests principal-only liquidation strategy

### Financial Logic Tests
- `test_bills_on_credit.py` - Bill autopay with credit cards
- `test_cc_payments.py` - Credit card payment calculations
- `test_cc_limit_adjustment.py` - Credit limit handling
- `test_combined_payments.py` - Multiple payments on same day
- `test_commission_settlement.py` - Commission income handling
- `test_income_growth.py` - Income growth simulations

### Display Tests
- `test_detailed_display.py` - Output formatting
- `test_extra_payment_display.py` - Extra payment displays
- `test_multi_checking_display.py` - Multiple checking accounts
- `test_integrated_views.py` - Consistency across views

### Edge Cases
- `test_constraint_failure.py` - Handles impossible constraints
- `test_failure_output.py` - Error message formatting
- `test_over_limit.py` - Credit card over-limit scenarios
- `test_validation.py` - Configuration validation

## Test Configuration Files

Some tests use dedicated config files:
- `test_commission_settlement_config.json`
- `test_investment_config.json`
- `test_manual_position_config.json`

## Notes

- All tests automatically add the parent directory to `sys.path` for imports
- Rust tests require the Rust module to be built (`cargo build --release` in `simulation_rust/`)
- Python-only tests will work without Rust acceleration
- Tests output detailed results to stdout for verification
