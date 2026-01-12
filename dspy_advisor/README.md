# DSPy Advisory Layer with Bounded Control

## Overview

The DSPy advisory layer is a **read-only observational system** with **safety-bounded control** that monitors trading metrics and suggests parameter optimizations without influencing execution.

**Key Principles:**
- **OBSERVE → SUGGEST → LOG (NEVER APPLY)**
- **SAFETY OVERRIDES INTELLIGENCE**

## Purpose

- **Observe** exploit performance metrics (Sharpe ratio, drawdown, capital efficiency)
- **Suggest** parameter adjustments based on observed patterns
- **Enforce bounds** to ensure all suggestions are within safe limits
- **Log** suggestions for human review
- **Never apply** suggestions to execution

## Bounded Control Guardrails

The DSPy advisor enforces strict safety constraints on all suggestions:

### Parameter Bounds

- **Thresholds (±20%)**: stop_loss_percent, max_holding_hours, risk_threshold
  - Maximum allowed change: ±20% of current value
  - Example: If stop_loss is 5%, can only suggest 4% to 6%

- **Allocation Weights (±10%)**: position_size_multiplier, allocation_weight, stake_weight
  - Maximum allowed change: ±10% of current value
  - Example: If position_size is 1.0, can only suggest 0.9 to 1.1

### Forbidden Parameters

DSPy **cannot** adjust these parameters:
- ❌ `place_order` - Cannot place orders
- ❌ `leverage` / `max_leverage` - Cannot change leverage caps
- ❌ `enable_risk_controls` - Cannot disable risk controls
- ❌ `order_placement` - Cannot trigger order execution

Any attempt to adjust forbidden parameters is automatically rejected and logged.

### Safety Enforcement

✅ **All suggestions are bounded**: Even if DSPy calculates that a 50% change would be optimal, guardrails will limit it to the safe bound (10% or 20%)

✅ **Violations are tracked**: All guardrail violations are logged with detailed statistics

✅ **Safety overrides intelligence**: Guardrails always take precedence over DSPy suggestions

## Architecture

```
Trade Execution → Attribution → DSPy Observer → Metrics Analysis → Suggestions
                                                         ↓
                                                  Guardrails (Bounded Control)
                                                         ↓
                                                  Bounded Suggestions → Logs
                                                         ↓
                                                  (NO FEEDBACK TO EXECUTION)
```

## Features

### Observed Metrics

1. **Sharpe Ratio**: Risk-adjusted returns
2. **Drawdown Contribution**: Impact on overall drawdown
3. **Capital Efficiency**: Profit per unit of deployed capital
4. **Win Rate**: Percentage of profitable trades
5. **Average Profit**: Mean profit per trade

### Suggestion Types

The advisor generates suggestions based on observed patterns:

- **Low Sharpe Ratio** → Reduce position size (bounded to ±10%)
- **High Drawdown** → Tighten stop losses (bounded to ±20%)
- **Low Capital Efficiency** → Reduce holding time (bounded to ±20%)
- **High Performance** → Increase position size (bounded to ±10%)

All suggestions include:
- Parameter name
- Current and suggested values
- Delta (change amount)
- Confidence score
- Rationale
- **Guardrail compliance status**

## Usage

### Basic Usage

```python
from dspy.advisor import DSPyAdvisor
from freqtrade.metrics.attribution import attribute_trade

# Initialize the advisor with guardrails enabled (default)
advisor = DSPyAdvisor(
    min_trades_for_suggestion=20,
    suggestion_confidence_threshold=0.6,
    enable_guardrails=True  # Enforce bounded control (default: True)
)

# Feed trade data to the advisor
for trade in completed_trades:
    trade_attr = attribute_trade(trade)
    advisor.observe_trade(trade_attr)

# Generate suggestions (logged only, never applied, all bounded)
suggestions = advisor.generate_suggestions()

# Review suggestions
for suggestion in suggestions:
    print(f"{suggestion.parameter_name}: {suggestion.current_value} → {suggestion.suggested_value}")
    print(f"Confidence: {suggestion.confidence:.2%}")
    print(f"Rationale: {suggestion.rationale}")
```

### Using Guardrails

```python
# Check guardrail statistics
stats = advisor.get_guardrail_stats()
print(f"Total violations: {stats['total_violations']}")
print(f"Violations by type: {stats['violations_by_type']}")

# Manually validate a suggestion
is_valid, violation = advisor.guardrails.validate_suggestion(
    parameter_name="position_size_multiplier",
    current_value=1.0,
    suggested_value=1.15,  # +15% exceeds ±10% bound
)

if not is_valid:
    print(f"Violation: {violation.reason}")

# Apply bounds to a value
bounded_value = advisor.guardrails.apply_bounds(
    parameter_name="position_size_multiplier",
    current_value=1.0,
    suggested_value=1.20,  # Will be clamped to 1.10 (±10% max)
)
```

### Get Metrics

```python
# Get metrics for a specific exploit
metrics = advisor.get_metrics_snapshot("funding_capture")
print(f"Sharpe: {metrics.sharpe_ratio:.2f}")
print(f"Capital Efficiency: {metrics.capital_efficiency:.2%}")

# Get metrics for all exploits
all_metrics = advisor.get_all_metrics()
for exploit_id, metrics in all_metrics.items():
    print(f"{exploit_id}: Sharpe={metrics.sharpe_ratio:.2f}")
```

## Example Output

```
DSPy SUGGESTION (READ-ONLY): 
  Exploit=funding_capture
  Parameter=position_size_multiplier
  Current=1.0000
  Suggested=1.1000
  Delta=+0.1000
  Confidence=85.00%
  Rationale=Strong Sharpe ratio (2.5) and capital efficiency (45%) suggest increasing exposure

✓ BOUNDED: Change of 10.0% is within ±10% allocation bound

DSPy generated 1 suggestion(s) - LOGGED ONLY, NOT APPLIED TO EXECUTION
```

## Guardrail Examples

### Example 1: Bounded Allocation Weight

```
Original suggestion: position_size_multiplier 1.0 → 1.30 (+30%)
Guardrail enforced: position_size_multiplier 1.0 → 1.10 (+10%)
Reason: Allocation weights bounded to ±10%
```

### Example 2: Bounded Threshold

```
Original suggestion: stop_loss_percent 0.05 → 0.10 (+100%)
Guardrail enforced: stop_loss_percent 0.05 → 0.06 (+20%)
Reason: Thresholds bounded to ±20%
```

### Example 3: Forbidden Parameter

```
Attempted: leverage 1.0 → 2.0
Guardrail enforced: REJECTED
Reason: Cannot change leverage caps (forbidden parameter)
```

## Guarantees

### What DSPy Does

✅ Observes trade metrics  
✅ Calculates performance indicators  
✅ Generates parameter suggestions  
✅ **Enforces safety bounds on all suggestions**  
✅ **Tracks guardrail violations**  
✅ Logs suggestions for review  

### What DSPy Does NOT Do

❌ Modify trading parameters  
❌ Influence trade execution  
❌ Change risk settings  
❌ Interact with the execution engine  
❌ Access live trading systems  
❌ **Place orders**  
❌ **Change leverage caps**  
❌ **Disable risk controls**  

### Bounded Control Guarantees

✅ **Thresholds**: All threshold adjustments bounded to ±20%  
✅ **Allocation weights**: All allocation adjustments bounded to ±10%  
✅ **Forbidden parameters**: Cannot be adjusted under any circumstances  
✅ **Safety overrides intelligence**: Guardrails always take precedence  
✅ **Violations logged**: All bound violations are tracked and reported  

## Integration with Freqtrade

The DSPy advisor integrates with Freqtrade's attribution system but operates completely independently:

```
Freqtrade Execution Engine
    ↓
Trade Attribution (metrics/attribution.py)
    ↓
DSPy Advisor (dspy_advisor/advisor.py)
    ↓
Suggestions (logged to stdout/file)
    ↓
(NO FEEDBACK LOOP TO EXECUTION)
```

## Configuration

```python
advisor = DSPyAdvisor(
    # Minimum trades before generating suggestions
    min_trades_for_suggestion=20,
    
    # Minimum confidence threshold for logging suggestions
    suggestion_confidence_threshold=0.6
)
```

## Running Examples

See example demonstrations:

```bash
cd /home/runner/work/freq/freq
PYTHONPATH=/home/runner/work/freq/freq python dspy_advisor/example_usage.py
```

This will run 4 example scenarios showing different suggestion types.

### Bounded Control Example

See bounded control in action:

```bash
cd /home/runner/work/freq/freq
PYTHONPATH=/home/runner/work/freq/freq python dspy_advisor/bounded_control_example.py
```

This demonstrates:
- Guardrail enforcement
- Bound violations
- Forbidden parameter protection

## Testing

Run the test suite:

```bash
cd /home/runner/work/freq/freq

# Test advisor functionality
PYTHONPATH=/home/runner/work/freq/freq python -m pytest tests/dspy_advisor/test_advisor.py -v

# Test guardrails
PYTHONPATH=/home/runner/work/freq/freq python -m pytest tests/dspy_advisor/test_guardrails.py -v

# Test bounded control integration
PYTHONPATH=/home/runner/work/freq/freq python -m pytest tests/dspy_advisor/test_bounded_control.py -v
```

All tests verify:
- Read-only behavior
- Correct metric calculations
- **Guardrail enforcement (±20% thresholds, ±10% allocation weights)**
- **Forbidden parameter protection**
- **Safety bounds compliance**

## Files

- `dspy_advisor/advisor.py` - Main advisor implementation
- `dspy_advisor/guardrails.py` - **Bounded control guardrails**
- `dspy_advisor/example_usage.py` - Example demonstrations
- `dspy_advisor/bounded_control_example.py` - **Bounded control examples**
- `tests/dspy_advisor/test_advisor.py` - Advisor test suite
- `tests/dspy_advisor/test_guardrails.py` - **Guardrails test suite**
- `tests/dspy_advisor/test_bounded_control.py` - **Bounded control integration tests**

## Design Philosophy

The DSPy advisor is designed with strict separation of concerns:

1. **Observation Only**: Passive monitoring of metrics
2. **No Side Effects**: Cannot modify execution state
3. **Bounded Control**: All suggestions are safety-bounded
4. **Safety Overrides Intelligence**: Guardrails take precedence
5. **Human in the Loop**: Suggestions require human review
6. **Transparency**: All suggestions logged with rationale
7. **Confidence Scoring**: Suggestions include confidence levels
8. **Violation Tracking**: All guardrail violations are logged

This ensures the advisor can safely observe and suggest without risk of unintended execution impact.

## Future Enhancements

Potential future additions (all maintaining read-only behavior and bounded control):

- Export suggestions to CSV/JSON for analysis
- Time-series tracking of metric evolution
- Multi-timeframe metric analysis
- Correlation analysis between exploits
- Performance attribution reports
- Adaptive bounds based on market conditions (within safe limits)

All enhancements will maintain the core principles: 
- **OBSERVE → SUGGEST → LOG (NEVER APPLY)**
- **SAFETY OVERRIDES INTELLIGENCE**
