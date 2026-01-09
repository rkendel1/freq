# Scale Validation

This document describes the scale validation system for verifying system readiness before deployment.

## Overview

The scale validation system performs a simulated 30-day run to verify:
- **System stability** under extended operation
- **Drawdown behavior** and capital protection
- **Capital growth** tracking
- **Exploit isolation** (no cross-contamination)
- **Risk limit** enforcement

## Requirements

As specified in the original issue:
- ✅ 30-day simulated run
- ✅ No parameter changes during execution
- ✅ Verify drawdowns, capital growth, exploit isolation
- ✅ Deliverables: Stability report and list of failure modes

## Usage

### Quick Start

Run validation with default configuration:

```bash
python scripts/scale_validation.py
```

This will:
- Run a 30-day (720 hours) simulated validation
- Use default risk parameters
- Use NullExploitModule (no trading actions)
- Generate a stability report as `scale_validation_report.json`

### Custom Configuration

Create a configuration file (JSON):

```json
{
  "dry_run_wallet": 10000.0,
  "validation_duration_hours": 720,
  "max_position_size": 0.10,
  "max_total_exposure": 0.95,
  "max_open_trades": 3,
  "stoploss": 0.10,
  "max_daily_loss": 0.20,
  "leverage": {"max": 1.0},
  "position_cooldown": 3600,
  "global_cooldown": 0,
  "max_funding_rate": 0.01,
  "funding_rate_change_threshold": 0.005
}
```

Run with custom config:

```bash
python scripts/scale_validation.py --config my_config.json --output my_report.json
```

## Metrics Tracked

### 1. Drawdown Metrics

Tracks capital drawdown behavior:
- **Max Drawdown**: Maximum percentage decline from peak
- **Drawdown Duration**: Longest period in drawdown
- **Drawdown Periods**: All periods of capital decline
- **Recovery Time**: Time to recover from drawdown

Example output:
```
--- DRAWDOWN METRICS ---
Max Drawdown: 12.50%
Max Drawdown Duration: 48 hours
Number of Drawdown Periods: 3
```

### 2. Capital Growth Metrics

Tracks capital performance:
- **Initial Capital**: Starting capital
- **Final Capital**: Ending capital
- **Peak Capital**: Highest capital reached
- **Total PnL**: Total profit/loss
- **Growth Rate**: Percentage growth
- **Hourly Snapshots**: Capital tracked every 24 hours

Example output:
```
--- CAPITAL METRICS ---
Initial Capital: $10,000.00
Final Capital: $10,500.00
Total PnL: $500.00
Growth Rate: 5.00%
Peak Capital: $10,800.00
```

### 3. Exploit Isolation Metrics

Verifies that exploit modules are properly isolated:
- **Exploits Executed**: Number of exploit evaluations
- **Capital Allocation Requests**: Requests for capital
- **Capital Allocation Failures**: Failed allocation attempts
- **Cross-Contamination**: Detected state leakage between exploits

Example output:
```
--- EXPLOIT ISOLATION METRICS ---
Exploits Executed: 1,440
Capital Allocation Requests: 720
Capital Allocation Failures: 0
Cross-Contamination Detected: False
```

## Failure Modes Detected

The validation system detects and categorizes failures:

### 1. Emergency Stops
- **Trigger**: Catastrophic loss (>50%)
- **Severity**: CRITICAL
- **Action**: All trading halted immediately

### 2. Risk Violations
- **Trigger**: Actions that exceed risk limits
- **Severity**: MEDIUM
- **Action**: Action rejected, logged

### 3. Capital Allocation Failures
- **Trigger**: Insufficient capital for requested allocation
- **Severity**: MEDIUM
- **Action**: Allocation rejected, logged

### 4. Exchange Disconnections
- **Trigger**: Exchange connectivity lost
- **Severity**: HIGH
- **Action**: Trading halted until reconnected

### 5. Exploit Evaluation Errors
- **Trigger**: Exception during exploit evaluation
- **Severity**: HIGH
- **Action**: Error logged, evaluation skipped

## Stability Report

The final stability report includes:

### Report Structure

```json
{
  "run_timestamp": "2026-01-09T16:18:08.389789",
  "duration_hours": 720,
  "initial_capital": 10000.0,
  "final_capital": 10000.0,
  "drawdown_metrics": {
    "max_drawdown": 0.0,
    "max_drawdown_duration_hours": 0,
    "current_drawdown": 0.0,
    "peak_capital": 10000.0,
    "drawdown_periods": []
  },
  "capital_growth_metrics": {
    "initial_capital": 10000.0,
    "final_capital": 10000.0,
    "peak_capital": 10000.0,
    "total_pnl": 0.0,
    "growth_rate": 0.0,
    "hourly_snapshots": []
  },
  "exploit_isolation_metrics": {
    "exploits_executed": 0,
    "capital_allocation_requests": 0,
    "capital_allocation_failures": 0,
    "cross_contamination_detected": false
  },
  "failure_modes": [],
  "emergency_stops": 0,
  "risk_violations": 0,
  "validation_passed": true,
  "issues_detected": []
}
```

### Validation Criteria

Validation **PASSES** if:
- No critical failures detected
- No emergency stops triggered
- Max drawdown ≤ 30%
- Final capital ≥ 80% of initial capital

Validation **FAILS** if any of:
- Critical failures detected
- Emergency stops triggered
- Max drawdown > 30%
- Final capital < 80% of initial capital

## Example Output

### Successful Validation

```
================================================================================
SCALE VALIDATION STABILITY REPORT
================================================================================

Run Timestamp: 2026-01-09T16:18:08.389789
Duration: 720 hours (30 days)

--- CAPITAL METRICS ---
Initial Capital: $10,000.00
Final Capital: $10,000.00
Total PnL: $0.00
Growth Rate: 0.00%
Peak Capital: $10,000.00

--- DRAWDOWN METRICS ---
Max Drawdown: 0.00%
Max Drawdown Duration: 0 hours
Number of Drawdown Periods: 0

--- EXPLOIT ISOLATION METRICS ---
Exploits Executed: 0
Capital Allocation Requests: 0
Capital Allocation Failures: 0
Cross-Contamination Detected: False

--- FAILURE MODES OBSERVED ---
Total Failures: 0
Emergency Stops: 0
Risk Violations: 0

✓ No failures detected

--- VALIDATION RESULT ---
✓ VALIDATION PASSED

The system is ready for scale deployment.

================================================================================
```

### Failed Validation

```
--- VALIDATION RESULT ---
✗ VALIDATION FAILED

Issues detected:
  - 2 critical failures detected
  - 1 emergency stops triggered
  - Excessive drawdown: 35.00%

The system requires attention before scale deployment.
```

## Testing

The scale validation system includes comprehensive tests:

```bash
# Run all scale validation tests
python -m pytest tests/test_scale_validation.py -v

# Run specific test
python -m pytest tests/test_scale_validation.py::test_null_exploit_validation -v
```

Test coverage includes:
- ✅ Default configuration creation
- ✅ ScaleValidator initialization
- ✅ Drawdown calculation
- ✅ Capital growth tracking
- ✅ Emergency stop triggers
- ✅ Risk violation detection
- ✅ Capital allocation failures
- ✅ Report generation
- ✅ Deterministic behavior
- ✅ JSON serialization

All 17 tests passing.

## Integration with CI/CD

The scale validation can be integrated into CI/CD pipelines:

```yaml
# .github/workflows/scale-validation.yml
name: Scale Validation

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly
  workflow_dispatch:

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run Scale Validation
        run: python scripts/scale_validation.py --output validation_report.json
      - name: Upload Report
        uses: actions/upload-artifact@v4
        with:
          name: validation-report
          path: validation_report.json
```

## Best Practices

### 1. Run Regularly
- Weekly validation runs
- Before major deployments
- After significant code changes

### 2. Archive Reports
- Keep historical validation reports
- Track trends over time
- Compare validation results

### 3. Set Thresholds
- Adjust validation criteria based on strategy
- More aggressive strategies may have higher drawdown tolerance
- Conservative strategies should have tighter limits

### 4. Monitor Trends
- Track metrics across multiple validations
- Identify deteriorating performance
- Catch regressions early

### 5. Test with Real Exploits
- While NullExploitModule is useful for infrastructure validation
- Real exploit modules should be validated before deployment
- Test with historical data when possible

## Interpreting Results

### Good Indicators
- ✅ Zero failures
- ✅ Low drawdown (<10%)
- ✅ Stable capital growth
- ✅ No capital allocation failures
- ✅ No emergency stops

### Warning Signs
- ⚠️ Multiple risk violations
- ⚠️ Capital allocation failures
- ⚠️ Drawdown 10-20%
- ⚠️ Declining capital trend

### Critical Issues
- 🚨 Emergency stops triggered
- 🚨 Critical failures detected
- 🚨 Drawdown >30%
- 🚨 Capital loss >20%
- 🚨 Cross-contamination detected

## Troubleshooting

### Issue: Validation runs too long

**Solution**: Reduce `validation_duration_hours` for testing:
```json
{
  "validation_duration_hours": 24  // 1 day instead of 30
}
```

### Issue: Too many risk violations

**Cause**: Risk limits too tight or exploit too aggressive

**Solution**: 
- Review exploit module logic
- Adjust risk limits if appropriate
- Check for bugs in action generation

### Issue: Capital allocation failures

**Cause**: Capital fully deployed or insufficient reserves

**Solution**:
- Review `max_total_exposure` setting
- Check if exploit requests are reasonable
- Verify capital accounting logic

### Issue: Validation fails but unsure why

**Solution**: Check the failure modes in the report:
```python
import json
with open('scale_validation_report.json') as f:
    report = json.load(f)
    for failure in report['failure_modes']:
        print(f"{failure['category']}: {failure['description']}")
```

## Advanced Usage

### Custom Exploit Module

To validate with a custom exploit module:

```python
from scale_validation import ScaleValidator
from my_exploits import MyExploitModule

config = {
    "dry_run_wallet": 10000.0,
    "validation_duration_hours": 720,
    # ... other config
}

validator = ScaleValidator(config)
exploit = MyExploitModule(config)
report = validator.run_validation(exploit)
```

### Programmatic Access

Use the validation system programmatically:

```python
from scale_validation import (
    ScaleValidator,
    create_default_config,
    print_stability_report,
    save_report_json,
)

# Create validator
config = create_default_config()
validator = ScaleValidator(config)

# Run validation
report = validator.run_validation()

# Print report
print_stability_report(report)

# Save report
save_report_json(report, Path("my_report.json"))

# Access metrics
print(f"Max Drawdown: {report.drawdown_metrics.max_drawdown:.2%}")
print(f"Growth Rate: {report.capital_growth_metrics.growth_rate:.2%}")
print(f"Failures: {len(report.failure_modes)}")
```

## Future Enhancements

Potential improvements for future versions:

1. **Monte Carlo Simulation**: Run multiple validation runs with different random seeds
2. **Market Condition Scenarios**: Test under different market conditions
3. **Stress Testing**: Apply extreme market conditions
4. **Performance Benchmarking**: Compare against baseline metrics
5. **Real-time Monitoring**: Live validation during production runs
6. **Alert Integration**: Send notifications on validation failures

## Support

For issues or questions about scale validation:

1. Check this documentation
2. Review test cases in `tests/test_scale_validation.py`
3. Check the example output
4. Open an issue on GitHub

## License

Same as the main repository (GPLv3).
