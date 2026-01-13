# Knowledge Graph Module

> Post-mortem analysis and institutional memory for trading sessions

This module integrates the knowledge graph generator from [rkendel1/graph](https://github.com/rkendel1/graph) to provide visual, LLM-powered analysis of trading patterns and regrets.

## Quick Start

### Installation

```bash
# Install optional dependencies
pip install networkx pyvis python-louvain

# Or install all optional deps
pip install -r requirements-full.txt
```

### Basic Usage

```python
from freqtrade.knowledge_graph import KnowledgeGraphGenerator
from freqtrade.persistence import Trade

# Configure
config = {
    "enabled": True,
    "llm": {
        "model": "llama3.2",
        "base_url": "http://localhost:11434/v1/chat/completions",
        "api_key": "sk-1234"
    },
    "output": {
        "directory": "exports/knowledge_graphs",
        "format": "html"
    }
}

# Initialize
kg = KnowledgeGraphGenerator(config)

# Get trades
trades = Trade.get_trades().filter(Trade.is_open == False).all()

# Generate knowledge graph
results = kg.generate_from_trades(
    trades,
    session_metadata={"regime": "trending"},
    output_name="session_2024_01_13"
)

print(f"Graph: {results['html_path']}")
print(f"Stats: {results['stats']}")
```

## What It Does

### 1. Session Analysis
Analyzes trading sessions and extracts:
- Winning vs losing patterns
- Regime-specific behaviors
- Common failure modes
- Success factors

### 2. Regret Analysis
Captures "should have" insights:
- ✅ "Should have made more on that trade" (early exits)
- ✅ "Position was too small, could have made 3x more"
- ✅ "Should have cut losses earlier"
- ✅ Trades we didn't take (shadow trades)
- ✅ Missed opportunities and setups
- ✅ Aggregate capture rate metrics

### 3. Visual Knowledge Graph
Creates interactive HTML visualizations showing:
- Entities (trades, conditions, outcomes) as nodes
- Relationships (caused by, led to) as edges
- Community detection for pattern clustering
- Color-coded insights

### 4. Institutional Memory
Builds growing memory of:
- Recurring patterns (good and bad)
- Regime-specific behaviors
- Historical failure modes
- Successful strategies by condition

## Example Output

```
Regret Analysis - What We Learned and Left on the Table

=== Trades We Took - Could We Have Done Better? ===

- REGRET: BTC/USDT - Made 4.00% but could have held longer (exited too conservatively?)
- REGRET: SOL/USDT - Great trade (12.00%) but position was only 1000 - could have made 2-3x more with larger size
- REGRET: ADA/USDT - Lost 6.00%, should have cut earlier (stop loss not tight enough?)

=== Trades We DIDN'T Take (Regret) - 2 Opportunities ===

- REGRET: Didn't take MATIC/USDT long - Could have made 15.00% (Reason skipped: Risk limit reached)

=== Aggregate Regret Summary ===

- Actual Profit: 16.00%
- Left on Table (Shadow): 15.00%
- Capture Rate: 51.6% of total potential

=== Key Regret Patterns to Address ===

- PATTERN: Exiting too early on 3 trades (43% of trades). Consider trailing stops to capture more upside.
- PATTERN: Left 2 potentially winning trades untaken. Risk limits too tight?
```

## Files

```
freqtrade/knowledge_graph/
├── __init__.py              # Module exports
├── config.py                # Configuration management
├── generator.py             # Main KG generator
├── llm.py                   # LLM utilities
├── prompts.py               # Prompt templates
├── trade_analyzer.py        # Trade narrative generator (with regret analysis)
└── visualization.py         # Graph visualization
```

## Configuration

See `config_examples/config_knowledge_graph.example.json` for a complete example.

```json
{
  "knowledge_graph": {
    "enabled": true,
    "llm": {
      "model": "llama3.2",
      "api_key": "sk-1234",
      "base_url": "http://localhost:11434/v1/chat/completions",
      "max_tokens": 8192,
      "temperature": 0.2
    },
    "output": {
      "directory": "exports/knowledge_graphs",
      "format": "html"
    }
  }
}
```

## Documentation

- **[Full Documentation](../../docs/knowledge_graph.md)** - Complete guide
- **[Regret Features](../../docs/knowledge_graph_regret_features.md)** - Detailed regret analysis features
- **[Examples](../../examples/knowledge_graph_example.py)** - Usage examples
- **[Backtest Integration](../../examples/backtest_kg_integration.py)** - Integration guide

## Tests

```bash
# Run tests
python -m pytest tests/knowledge_graph/ -v

# Or run individual test files
python tests/knowledge_graph/test_config.py
python tests/knowledge_graph/test_trade_analyzer.py
python tests/knowledge_graph/test_llm.py
```

## Requirements

**Required:**
- Python 3.11+
- freqtrade core dependencies

**Optional (for full functionality):**
- `networkx>=3.4.2` - Graph creation
- `pyvis>=0.3.2` - HTML visualization
- `python-louvain>=0.16` - Community detection
- LLM API access (Ollama, OpenAI, etc.)

## Use Cases

### 1. Daily Batch Analysis
After each trading day:
```python
# Get today's trades
trades = get_todays_trades()

# Generate KG
kg.generate_from_trades(trades, output_name="daily_2024_01_13")
```

### 2. Backtest Analysis
After backtesting:
```python
# In backtesting.py, after backtest completes
if config.get("knowledge_graph", {}).get("enabled"):
    kg.generate_from_trades(backtest_trades)
```

### 3. Regret Analysis
Compare actual vs hypothetical:
```python
kg.generate_regret_analysis(
    actual_trades=actual,
    shadow_trades=shadow,
    missed_opportunities=missed
)
```

### 4. Pattern Discovery
Build cumulative knowledge over time:
```python
# Generate for each session
# Graphs accumulate insights about:
# - "We always over-size during FOMC → drawdown"
# - "High volatility regime → early exits"
```

## Architecture

The knowledge graph module is designed as an **optional add-on**:
- ✅ Zero impact on execution when disabled
- ✅ Modular design - can be removed without breaking core
- ✅ LLM-agnostic - works with any OpenAI-compatible API
- ✅ Visualization-optional - can generate JSON-only

## Performance

- **LLM calls**: 1-5 calls per session (depending on text length)
- **Processing time**: ~5-30 seconds per session
- **Output size**: ~100KB HTML + ~10KB JSON per session

## Limitations

- Requires LLM access (not suitable for offline use without LLM)
- Quality depends on LLM model capabilities
- Not designed for real-time analysis (batch processing only)
- HTML visualization requires browser for viewing

## Contributing

This module is adapted from [rkendel1/graph](https://github.com/rkendel1/graph).

Improvements to core graph generation should be contributed upstream when applicable.

## License

Same as freqtrade (GPLv3)
