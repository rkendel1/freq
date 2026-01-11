# Machine Learning Integration for Pattern Detection

This document describes the optional ML integration for detecting patterns in historical trading metrics.

## Overview

The ML integration uses scikit-learn's RandomForest to predict PnL gain percentage based on historical metrics like deployed capital percentage and number of open positions. This is completely optional and external to the core execution engine.

**Important:** ML predictions are for informational purposes only. They do NOT automatically adjust trading behavior. The predictions are logged for manual review and can optionally inform your custom ExploitModule logic.

## Features

- **Optional Integration**: ML is disabled by default and only loads when explicitly enabled
- **Pattern Detection**: Predicts PnL gain from deployed capital % and open positions
- **Non-Intrusive**: No changes to core execution engine
- **Lightweight**: Adds <100ms per evaluation when enabled
- **Training on Historical Data**: Train models on your own exported metrics

## Setup Instructions

### 1. Install Dependencies

```bash
pip install scikit-learn joblib pandas
```

Or if using requirements.txt:

```bash
pip install -r requirements.txt
```

### 2. Prepare Training Data

The training script expects historical metrics in Parquet format with the following columns:

- `deployed_capital_pct`: Percentage of total capital deployed (0-100)
- `open_positions`: Number of currently open positions
- `pnl_gain_pct`: PnL gain percentage (target variable to predict)

**Option A: Export from QuestDB**

If you're using QuestDB for metrics logging (see [docs/questdb.md](questdb.md)), you can export data:

```sql
-- Export last 30 days of metrics
COPY (
    SELECT 
        deployed_capital_pct,
        open_positions,
        -- Calculate PnL gain percentage
        (realized_pnl + unrealized_pnl) / total_capital * 100 as pnl_gain_pct
    FROM trading_metrics
    WHERE timestamp > dateadd('d', -30, now())
    AND total_capital > 0
) TO 'exports/metrics.parquet' WITH (format = 'PARQUET');
```

**Option B: Generate from Backtest Results**

You can also generate training data from backtest results by adding the required columns to your metrics export.

### 3. Train the Model

Run the training script:

```bash
python ml/train.py
```

This will:
- Load data from `exports/metrics.parquet`
- Train a RandomForest model with 100 estimators
- Evaluate on a 20% test set
- Save the model to `ml/model.pkl`

Expected output:

```
================================================================
ML Model Training Complete!
================================================================
Test Score (R²): 0.7543
Model saved to: ml/model.pkl

To use the model:
1. Set 'ml_enabled': true in your config
2. Restart the execution engine
================================================================
```

The R² score indicates how well the model fits the test data (1.0 = perfect fit, 0.0 = no better than random).

### 4. Enable ML in Config

Add or update your configuration file (e.g., `config.json`):

```json
{
    "ml_enabled": true,
    "ml_model_path": "ml/model.pkl"
}
```

Configuration options:

- `ml_enabled` (boolean): Enable/disable ML predictions (default: `false`)
- `ml_model_path` (string): Path to trained model file (default: `"ml/model.pkl"`)

### 5. Use in Your ExploitModule

**Option A: Inherit from MLCapableExploitModule**

```python
from freqtrade.exploits.exploit_module import (
    MLCapableExploitModule,
    ExecutionState,
    Action,
    ActionType,
)
import logging

logger = logging.getLogger(__name__)


class MyExploit(MLCapableExploitModule):
    """Custom exploit with ML pattern detection."""
    
    def evaluate(self, state: ExecutionState) -> list[Action]:
        # Get ML prediction if available
        if hasattr(self, 'ml_model') and self.ml_model is not None:
            predicted_pnl = self.predict_pnl_gain(state)
            logger.info(f"ML predicted PnL gain: {predicted_pnl:.2f}%")
            
            # Optionally use prediction in your logic
            if predicted_pnl > 5.0 and len(state.open_positions) == 0:
                return [Action(
                    type=ActionType.OPEN_LONG,
                    symbol=state.symbol,
                    size=0.1,
                    reason=f"ml_prediction_positive_{predicted_pnl:.2f}",
                    metadata={"ml_prediction": predicted_pnl}
                )]
        
        return []
    
    def on_execution_result(self, action: Action, result: ExecutionResult) -> None:
        # Handle execution results
        pass
```

**Option B: Use Standard ExploitModule with Manual ML Loading**

```python
import joblib
from freqtrade.exploits.exploit_module import ExploitModule

class MyExploit(ExploitModule):
    def __init__(self, config: dict):
        self.config = config
        self.ml_model = None
        
        if config.get('ml_enabled', False):
            try:
                self.ml_model = joblib.load(config.get('ml_model_path', 'ml/model.pkl'))
            except FileNotFoundError:
                logger.warning("ML model not found")
    
    def evaluate(self, state: ExecutionState) -> list[Action]:
        if self.ml_model:
            # Calculate features
            total = state.available_capital + state.deployed_capital
            deployed_pct = (state.deployed_capital / total * 100) if total > 0 else 0
            features = [[deployed_pct, len(state.open_positions)]]
            
            # Predict
            prediction = self.ml_model.predict(features)[0]
            logger.info(f"ML prediction: {prediction:.2f}%")
        
        return []
```

## Performance

- **Model Loading**: One-time cost at initialization (~50-200ms depending on model size)
- **Prediction**: ~1-5ms per evaluation (negligible overhead)
- **Total Impact**: <100ms per evaluation cycle

## Best Practices

1. **Retrain Regularly**: Retrain the model periodically as you collect more data
2. **Review Predictions**: Monitor ML predictions in logs before relying on them
3. **Combine with Rules**: Use ML predictions as one input among many, not the sole decision factor
4. **Validate Performance**: Track actual vs. predicted PnL to assess model accuracy
5. **Start Conservative**: Begin with ML in observation-only mode before using it for trading decisions

## Customizing the Model

You can customize the training script (`ml/train.py`) to:

- Add more features (e.g., volatility, trade duration, time of day)
- Use different algorithms (e.g., GradientBoosting, XGBoost, neural networks)
- Tune hyperparameters (n_estimators, max_depth, etc.)
- Add feature engineering or preprocessing

Example with more features:

```python
# In ml/train.py
feature_columns = [
    'deployed_capital_pct',
    'open_positions',
    'avg_trade_duration_hours',
    'market_volatility',
    'hour_of_day'
]
X = df[feature_columns]
```

## Troubleshooting

### Model File Not Found

```
WARNING: ML model not found. Train the model first with: python ml/train.py
```

**Solution**: Train the model first by running `python ml/train.py`

### Missing Dependencies

```
ERROR: Missing required package: No module named 'sklearn'
```

**Solution**: Install dependencies with `pip install scikit-learn joblib pandas`

### Missing Data Columns

```
ValueError: Missing required columns: ['pnl_gain_pct']
```

**Solution**: Ensure your training data includes all required columns. You may need to add calculated columns to your metrics export.

### Low Test Score

```
Test Score (R²): 0.1234
```

**Solution**: A low R² score suggests the model doesn't fit well. Try:
- Collecting more training data
- Adding more relevant features
- Using a different algorithm
- Checking data quality (outliers, missing values)

## Limitations

- **Not a Silver Bullet**: ML predictions are probabilistic and can be wrong
- **Requires Historical Data**: Model quality depends on data quantity and quality
- **Market Conditions Change**: Models may become less accurate as market dynamics shift
- **No Decision Making**: ML only provides predictions; trading logic is still your responsibility
- **External to Core**: ML is completely separate from the execution engine

## Integration with QuestDB

ML works seamlessly with QuestDB metrics logging:

1. Enable QuestDB logging in your config
2. Let the system collect metrics over time
3. Export metrics from QuestDB
4. Train the ML model on exported data
5. Enable ML predictions

See [docs/questdb.md](questdb.md) for QuestDB setup and usage.

## Example Workflow

1. **Initial Setup**
   ```bash
   # Install dependencies
   pip install scikit-learn joblib pandas
   
   # Enable QuestDB logging
   # Edit config.json: "questdb_enabled": true
   ```

2. **Collect Data**
   ```bash
   # Run backtests or live trading for a while
   # Let QuestDB collect at least a few hundred data points
   ```

3. **Export and Train**
   ```bash
   # Export from QuestDB (or use backtest results)
   # Place in exports/metrics.parquet
   
   # Train the model
   python ml/train.py
   ```

4. **Enable and Test**
   ```bash
   # Edit config.json: "ml_enabled": true
   
   # Run with ML predictions
   # Check logs for: "ML predicted PnL gain: X.XX%"
   ```

5. **Monitor and Iterate**
   ```bash
   # Review prediction accuracy
   # Retrain as more data becomes available
   # Adjust features or model parameters as needed
   ```

## Further Reading

- [scikit-learn RandomForest Documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html)
- [QuestDB Integration Guide](questdb.md)
- [ExploitModule Interface Documentation](../ARCHITECTURE.md)
