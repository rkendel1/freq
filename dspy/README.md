# DSPy Read-Only Advisory Layer

## Overview

The DSPy advisory layer is a **read-only observational system** that monitors trading metrics and suggests parameter optimizations without influencing execution.

**Key Principle: OBSERVE → SUGGEST → LOG (NEVER APPLY)**

## Purpose

- **Observe** exploit performance metrics (Sharpe ratio, drawdown, capital efficiency)
- **Suggest** parameter adjustments based on observed patterns
- **Log** suggestions for human review
- **Never apply** suggestions to execution

## Architecture

```
Trade Execution → Attribution → DSPy Observer → Metrics Analysis → Suggestions → Logs
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

- **Low Sharpe Ratio** → Reduce position size
- **High Drawdown** → Tighten stop losses
- **Low Capital Efficiency** → Reduce holding time
- **High Performance** → Increase position size

All suggestions include:
- Parameter name
- Current and suggested values
- Delta (change amount)
- Confidence score
- Rationale

## Usage

### Basic Usage

```python
from dspy.advisor import DSPyAdvisor
from freqtrade.metrics.attribution import attribute_trade

# Initialize the advisor
advisor = DSPyAdvisor(
    min_trades_for_suggestion=20,
    suggestion_confidence_threshold=0.6
)

# Feed trade data to the advisor
for trade in completed_trades:
    trade_attr = attribute_trade(trade)
    advisor.observe_trade(trade_attr)

# Generate suggestions (logged only, never applied)
suggestions = advisor.generate_suggestions()

# Review suggestions
for suggestion in suggestions:
    print(f"{suggestion.parameter_name}: {suggestion.current_value} → {suggestion.suggested_value}")
    print(f"Confidence: {suggestion.confidence:.2%}")
    print(f"Rationale: {suggestion.rationale}")
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
  Suggested=1.1500
  Delta=+0.1500
  Confidence=85.00%
  Rationale=Strong Sharpe ratio (2.5) and capital efficiency (45%) suggest increasing exposure

DSPy generated 1 suggestion(s) - LOGGED ONLY, NOT APPLIED TO EXECUTION
```

## Guarantees

### What DSPy Does

✅ Observes trade metrics  
✅ Calculates performance indicators  
✅ Generates parameter suggestions  
✅ Logs suggestions for review  

### What DSPy Does NOT Do

❌ Modify trading parameters  
❌ Influence trade execution  
❌ Change risk settings  
❌ Interact with the execution engine  
❌ Access live trading systems  

## Integration with Freqtrade

The DSPy advisor integrates with Freqtrade's attribution system but operates completely independently:

```
Freqtrade Execution Engine
    ↓
Trade Attribution (metrics/attribution.py)
    ↓
DSPy Advisor (dspy/advisor.py)
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
PYTHONPATH=/home/runner/work/freq/freq python dspy/example_usage.py
```

This will run 4 example scenarios showing different suggestion types.

## Testing

Run the test suite:

```bash
cd /home/runner/work/freq/freq
PYTHONPATH=/home/runner/work/freq/freq python -m pytest tests/dspy/test_advisor.py -v
```

All tests verify read-only behavior and correct metric calculations.

## Files

- `dspy/advisor.py` - Main advisor implementation
- `dspy/example_usage.py` - Example demonstrations
- `tests/dspy/test_advisor.py` - Test suite

## Design Philosophy

The DSPy advisor is designed with strict separation of concerns:

1. **Observation Only**: Passive monitoring of metrics
2. **No Side Effects**: Cannot modify execution state
3. **Human in the Loop**: Suggestions require human review
4. **Transparency**: All suggestions logged with rationale
5. **Confidence Scoring**: Suggestions include confidence levels

This ensures the advisor can safely observe and suggest without risk of unintended execution impact.

## Future Enhancements

Potential future additions (all maintaining read-only behavior):

- Export suggestions to CSV/JSON for analysis
- Time-series tracking of metric evolution
- Multi-timeframe metric analysis
- Correlation analysis between exploits
- Performance attribution reports

All enhancements will maintain the core principle: **OBSERVE → SUGGEST → LOG (NEVER APPLY)**
