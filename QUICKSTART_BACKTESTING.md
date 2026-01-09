# Quick Start: FundingCapture Backtesting

This guide shows how to quickly run the FundingCapture backtesting validation.

## Prerequisites

```bash
# Install required packages
pip install numpy pandas pyarrow
```

## Run Backtesting

```bash
# Navigate to repository root
cd /home/runner/work/freq/freq

# Run the backtesting script
python scripts/backtest_funding_capture.py
```

## Expected Output

You should see output similar to:

```
================================================================================
FUNDING CAPTURE BACKTEST SUMMARY
================================================================================

Scenario: flat_market
  Market Type: flat
  Data Points: 1440
  Price Change: 1.96%
  Volatility: 0.0965%
  Avg Funding Rate: 0.0029%
  Positive Funding Periods: 702
  Negative Funding Periods: 645
  Determinism: ✓ PASS

[... additional scenarios ...]

================================================================================
DETERMINISM VALIDATION
================================================================================

✓ All scenarios produce deterministic results
```

## Verify Results

Results are saved to:
```
user_data/backtest_results/funding_capture_results_TIMESTAMP.json
```

View results:
```bash
cat user_data/backtest_results/funding_capture_results_*.json | jq .
```

## Key Files

- **Strategy**: `freqtrade/exploits/funding_capture.py`
- **Backtest Script**: `scripts/backtest_funding_capture.py`
- **Tests**: `tests/exploits/test_funding_capture.py`
- **Documentation**: `BACKTESTING_FUNDING_CAPTURE.md`
- **Results Summary**: `BACKTEST_RESULTS.md`

## What Gets Tested

1. **Flat Market**: Sideways price action with low volatility
2. **Trending Market**: Strong upward trend with medium volatility  
3. **Volatile Market**: Large price swings with high volatility

Each scenario validates:
- Deterministic data generation
- Consistent funding rate calculation
- Reproducible results across runs

## Success Criteria

✅ All scenarios show `Determinism: ✓ PASS`
✅ Results file created successfully
✅ No errors during execution

## Next Steps

See `BACKTESTING_FUNDING_CAPTURE.md` for:
- Detailed strategy explanation
- Configuration options
- Integration with real data
- Production deployment

See `BACKTEST_RESULTS.md` for:
- Complete results analysis
- Market scenario comparisons
- Recommendations
