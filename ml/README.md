# ML Integration - Machine Learning for Pattern Detection

This directory contains the optional ML integration for pattern detection in trading metrics.

## Quick Start

### 1. Install Dependencies

```bash
pip install scikit-learn joblib pandas pyarrow
```

### 2. Run the Demo

```bash
python ml/demo.py
```

This will:
- Create sample training data
- Train a RandomForest model
- Show predictions in various scenarios
- Display example output

**Expected Output:**
```
ML Prediction | Symbol: BTC/USDT | Deployed: 5.0% | Positions: 0 | Predicted PnL Gain: 2.80%
ML Prediction | Symbol: ETH/USDT | Deployed: 40.0% | Positions: 2 | Predicted PnL Gain: 6.45%
ML Prediction | Symbol: SOL/USDT | Deployed: 80.0% | Positions: 5 | Predicted PnL Gain: 9.83%
```

### 3. Train on Your Own Data

```bash
# Prepare data in exports/metrics.parquet with columns:
# - deployed_capital_pct
# - open_positions
# - pnl_gain_pct

python ml/train.py
```

### 4. Enable in Config

```json
{
    "ml_enabled": true,
    "ml_model_path": "ml/model.pkl"
}
```

### 5. Use in Your ExploitModule

```python
from freqtrade.exploits.exploit_module import MLCapableExploitModule

class MyExploit(MLCapableExploitModule):
    def evaluate(self, state: ExecutionState) -> list[Action]:
        if self.ml_model is not None:
            predicted_pnl = self.predict_pnl_gain(state)
            logger.info(f"ML prediction: {predicted_pnl:.2f}%")
        
        # Your trading logic here
        return []
```

## Files

- `__init__.py` - Module initialization
- `train.py` - Training script for ML model
- `demo.py` - Interactive demo showing ML in action
- `model.pkl` - Trained model (created after running train.py, gitignored)

## Documentation

See [docs/ml.md](../docs/ml.md) for complete documentation including:
- Detailed setup instructions
- Feature customization
- Troubleshooting
- Best practices
- Integration with QuestDB

## Key Features

- **Optional**: Completely disabled by default
- **Non-Intrusive**: Predictions are logged, not auto-traded
- **Lightweight**: <100ms overhead per evaluation
- **Flexible**: Customize features and model parameters
- **Retrain**: Update model as you collect more data

## Example Output

When ML is enabled, you'll see predictions in your logs:

```
2026-01-11 18:48:03,877 - __main__ - INFO - ML Prediction | Symbol: BTC/USDT | Deployed: 5.0% | Positions: 0 | Predicted PnL Gain: 2.80%
2026-01-11 18:48:03,886 - __main__ - INFO - ML Prediction | Symbol: ETH/USDT | Deployed: 40.0% | Positions: 2 | Predicted PnL Gain: 6.45%
```

The predictions are based on:
- Current deployed capital percentage
- Number of open positions
- Historical patterns learned from your data

## Important Notes

1. **ML is not a silver bullet** - Predictions are probabilistic
2. **Quality depends on data** - More historical data = better predictions
3. **Markets change** - Retrain periodically as conditions evolve
4. **Review predictions** - Monitor accuracy before relying on them
5. **No auto-trading** - Predictions inform your logic, don't replace it

## Support

For issues or questions:
- Check [docs/ml.md](../docs/ml.md) for troubleshooting
- Review the demo output: `python ml/demo.py`
- Verify dependencies are installed correctly
