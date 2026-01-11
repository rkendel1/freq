# DSPy LM-Based Insights

## Overview

This guide shows how to use DSPy with a local LLM (via Ollama) to generate manual insights and parameter adjustment suggestions from trading metrics.

**Key Principles:**
- **External Analysis Only**: Runs in a separate script, not in the core engine
- **Manual Review**: Outputs suggestions for human review
- **No Auto-Apply**: Suggestions are NEVER automatically applied
- **Privacy & Low Cost**: Uses local LLM (Ollama) for privacy and zero API costs

## What It Does

The `analysis/dspy_insights.py` script:
1. Loads trading metrics from parquet files or QuestDB
2. Calculates aggregate statistics (deployed capital, PnL, win rate, Sharpe ratio)
3. Uses DSPy with a local LLM to generate contextual suggestions
4. Outputs manual adjustment recommendations (e.g., "Close 20% positions at 55% deployed")

## Setup Instructions

### Step 1: Install Dependencies

```bash
pip install dspy-ai==2.4.0 ollama==0.1.0
```

Or install from requirements.txt (includes DSPy dependencies):

```bash
pip install -r requirements.txt
```

### Step 2: Install and Run Ollama

1. **Install Ollama**: Download from [https://ollama.ai/](https://ollama.ai/)

2. **Download and run llama3.2**:
   ```bash
   ollama run llama3.2
   ```

3. **Verify Ollama is running**:
   ```bash
   ollama list
   ```
   
   You should see `llama3.2` in the list of available models.

4. **Keep Ollama running** in a terminal window while using the analysis script.

### Step 3: Export Metrics

Before running the analysis script, you need metrics data. You can either:

**Option A: Use Sample Data (for testing)**

Run the helper script to create sample metrics:

```bash
python scripts/create_sample_metrics.py
```

This creates `exports/metrics.parquet` with sample data for testing.

**Option B: Export Real Metrics to Parquet** (recommended for actual analysis)

Create a metrics export in your application and save to `exports/metrics.parquet`.

Example columns the script looks for:
- `deployed_capital_pct`: Percentage of capital deployed
- `pnl_gain_pct` or `realized_pnl`: PnL statistics
- `win_rate`: Win rate percentage
- `sharpe_ratio`: Sharpe ratio

**Option C: Use QuestDB** (if already configured)

If you have QuestDB running with trading metrics, the script will automatically try to load from there if no parquet file is found.

See [questdb.md](questdb.md) for QuestDB setup instructions.

## Usage

### Basic Usage

Run the analysis script:

```bash
cd /home/runner/work/freq/freq
python analysis/dspy_insights.py
```

### Expected Output

```
================================================================================
DSPy LM-Based Insights for Trading Metrics
================================================================================

This script generates manual adjustment suggestions using a local LLM.
Suggestions are for MANUAL REVIEW ONLY and have NO IMPACT on execution.

Step 1: Configuring DSPy with Ollama (llama3.2)
--------------------------------------------------------------------------------
✓ DSPy configured with Ollama (llama3.2)

Step 2: Loading metrics
--------------------------------------------------------------------------------
Loading metrics from exports/metrics.parquet...
Loaded 1000 metric records

Step 3: Preparing context from metrics
--------------------------------------------------------------------------------
✓ Context prepared

Step 4: Generating insights
--------------------------------------------------------------------------------

================================================================================
Generating Insights with DSPy ChainOfThought
================================================================================

Context provided to LLM:
Trading Metrics Summary:
- Average Deployed Capital: 55.23%
- Maximum Deployed Capital: 87.50%
- Average PnL Gain: 2.45%
- Maximum PnL Gain: 12.30%
- Minimum PnL Gain: -3.20%
- Win Rate: 62.00%
- Sharpe Ratio: 1.35
- Total Records: 1000

Generating suggestion...

================================================================================
GENERATED SUGGESTION (Manual Review Only)
================================================================================
Based on the metrics, consider closing 20% of positions when deployed capital 
exceeds 70% to maintain a safety buffer. The average PnL gain of 2.45% with a 
Sharpe ratio of 1.35 suggests the current strategy is working well, but the 
maximum deployment of 87.50% indicates occasional over-leverage. Consider 
setting a hard cap at 75% deployed capital to reduce tail risk while 
maintaining the profitable core strategy.
================================================================================

================================================================================
Optional: BootstrapFewShot Optimization Example
================================================================================

To use few-shot optimization, uncomment the following:
# suggestion_optimized = generate_insight_optimized(context)
#
# This approach uses example pairs to improve suggestions.
# See the code for details on how to customize examples.

================================================================================
IMPORTANT: Suggestions above are for MANUAL REVIEW ONLY
They are NOT automatically applied to the trading engine.
Review suggestions and manually adjust configuration if appropriate.
================================================================================
```

## Advanced Usage

### Using BootstrapFewShot Optimization

The script includes an optional `generate_insight_optimized()` function that uses DSPy's BootstrapFewShot optimizer to improve suggestions with few-shot examples.

To use it, edit `analysis/dspy_insights.py` and replace:

```python
# Simple ChainOfThought approach
suggestion = generate_insight_simple(context)
```

With:

```python
# Optimized approach with few-shot examples
suggestion = generate_insight_optimized(context)
```

This approach:
1. Uses example context-suggestion pairs to guide the LLM
2. Optimizes the prompt structure for better results
3. Can be customized with your own examples

### Customizing Examples

Edit the `examples` list in `generate_insight_optimized()`:

```python
examples = [
    dspy.Example(
        context="Your custom context",
        suggestion="Your desired suggestion format"
    ).with_inputs('context'),
    # Add more examples...
]
```

### Using Different LLM Models

To use a different Ollama model, change the model name:

```python
# In analysis/dspy_insights.py, line ~240
ollama = dspy.OllamaLocal(model='llama3.2')  # Change model here
```

Available models (download with `ollama run <model>`):
- `llama3.2` (default, lightweight)
- `llama3` (more powerful)
- `mistral` (alternative)
- `codellama` (code-focused)

See [Ollama Library](https://ollama.ai/library) for all available models.

## Integration with Workflow

### Suggested Workflow

1. **Run trading**: Execute trades using the core engine
2. **Collect metrics**: Metrics are automatically logged to QuestDB or exported to parquet
3. **Run analysis**: `python analysis/dspy_insights.py` (periodically, e.g., daily/weekly)
4. **Review suggestions**: Human reviews the generated insights
5. **Manual adjustments**: If suggestions are reasonable, manually update config
6. **Repeat**: Continue the cycle

### Example Integration

```bash
# 1. Run trading demo
python examples/automated_backtest_example.py

# 2. Export metrics (if not using QuestDB)
# (Add your own export logic here)

# 3. Generate insights
python analysis/dspy_insights.py

# 4. Review output and manually adjust config if needed
# Edit config.json based on suggestions

# 5. Restart trading with new config
python examples/automated_backtest_example.py
```

## Architecture

```
Trading Execution
    ↓
Metrics Export (Parquet/QuestDB)
    ↓
analysis/dspy_insights.py
    ↓
DSPy + Ollama (Local LLM)
    ↓
Suggestions (Logged to stdout)
    ↓
Human Review
    ↓
Manual Config Adjustments (Optional)
    ↓
(NO FEEDBACK LOOP TO EXECUTION)
```

## What DSPy Does

✅ **Does:**
- Analyzes aggregate trading metrics
- Generates contextual parameter suggestions
- Provides reasoning for suggestions
- Runs entirely offline with local LLM
- Outputs to stdout for human review

❌ **Does NOT:**
- Modify trading parameters
- Influence trade execution
- Access the core engine
- Automatically apply suggestions
- Make trading decisions
- Require internet connection (if using local models)

## Guarantees

### Separation from Core Engine

The analysis script is completely isolated from the core trading engine:

1. **Separate Directory**: Lives in `analysis/`, not in core `freqtrade/`
2. **No Imports**: Does not import any execution modules
3. **Read-Only**: Only reads exported metrics, never modifies live data
4. **Manual Execution**: Must be explicitly run by user
5. **No Callbacks**: No registration with execution engine
6. **Logged Output**: Suggestions go to stdout, not to execution state

### Privacy & Cost

- **Local LLM**: Uses Ollama (runs on your machine)
- **No API Calls**: Zero external API dependencies
- **No Data Sharing**: All data stays on your machine
- **Zero Cost**: No API fees or usage charges

## Troubleshooting

### "ERROR: dspy-ai not installed"

```bash
pip install dspy-ai==2.4.0
```

### "ERROR: Failed to configure Ollama"

Make sure Ollama is running:

```bash
# In a separate terminal
ollama run llama3.2
```

Verify it's working:

```bash
ollama list
```

### "Metrics file not found"

Create a metrics export file at `exports/metrics.parquet`, or ensure QuestDB is running with metrics data.

Example metrics dataframe structure:

```python
import pandas as pd

df = pd.DataFrame({
    'deployed_capital_pct': [50.0, 60.0, 55.0],
    'pnl_gain_pct': [2.5, 3.0, 1.8],
    'win_rate': [0.65, 0.70, 0.62],
    'sharpe_ratio': [1.2, 1.5, 1.1],
})

df.to_parquet('exports/metrics.parquet')
```

### "Connection refused" (QuestDB)

If using QuestDB, make sure it's running:

```bash
# Start QuestDB (see questdb.md for setup)
docker run -p 9000:9000 -p 8812:8812 questdb/questdb
```

Or use the parquet export method instead.

## Files

- `analysis/dspy_insights.py` - Main analysis script
- `analysis/__init__.py` - Package initialization
- `docs/dspy.md` - This documentation

## Design Philosophy

The DSPy insights script follows the core principle of separation:

**OBSERVE → ANALYZE → SUGGEST → LOG (NEVER APPLY)**

All insights are:
1. Generated from historical metrics (read-only)
2. Reviewed by humans before any action
3. Manually applied to configuration if appropriate
4. Completely isolated from execution

This ensures the script can safely provide AI-powered insights without risk of unintended execution impact.

## Future Enhancements

Potential future additions (all maintaining external, manual-review workflow):

- Export suggestions to JSON/CSV for tracking
- Visualization of metrics trends
- Multi-timeframe analysis
- Correlation analysis between exploits
- Custom prompt templates
- Integration with other LLM providers (OpenAI, Anthropic, etc.)

All enhancements will preserve the core principle: **EXTERNAL → MANUAL → NO AUTO-APPLY**
