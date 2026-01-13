# Knowledge Graph Integration

This module integrates the knowledge graph generator from [rkendel1/graph](https://github.com/rkendel1/graph) to provide post-mortem analysis and institutional memory for trading sessions.

## Overview

The knowledge graph feature creates an evolving, visual "institutional memory" for your trading bot by:

- Analyzing actual vs shadow trades
- Identifying missed opportunities
- Extracting regime-specific patterns
- Generating LLM-based "lessons learned"
- Creating interactive visualizations of trading patterns

## Features

### 1. Post-Mortem Analysis
After each trading session, backtest, or replay run, the knowledge graph generator can:
- Extract insights from trade outcomes
- Identify recurring failure patterns
- Map relationships between market conditions and results
- Create visual graphs of cause-and-effect relationships

### 2. Regret Analysis
Compare actual trades with hypothetical scenarios:
- Actual trades vs shadow trades
- Missed opportunities and their causes
- What-if scenarios from replay analysis

### 3. Visual Memory Graph
Generate interactive HTML visualizations showing:
- Entities (trades, conditions, outcomes) as nodes
- Relationships (caused by, led to, similar to) as edges
- Community detection for pattern clustering
- Color-coded insights for easy navigation

## Installation

The knowledge graph feature requires optional dependencies:

```bash
pip install networkx pyvis python-louvain
```

Or install all optional dependencies:

```bash
pip install -r requirements-full.txt
```

## Configuration

Add the `knowledge_graph` section to your config:

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
    "chunking": {
      "chunk_size": 200,
      "overlap": 20
    },
    "standardization": {
      "enabled": true,
      "use_llm_for_entities": true
    },
    "inference": {
      "enabled": true,
      "use_llm_for_inference": true,
      "apply_transitive": true
    },
    "output": {
      "directory": "exports/knowledge_graphs",
      "format": "html"
    }
  }
}
```

### Configuration Options

#### LLM Settings
- `model`: LLM model name (e.g., "llama3.2", "gpt-4")
- `api_key`: API key for the LLM service
- `base_url`: API endpoint URL (supports Ollama, OpenAI, etc.)
- `max_tokens`: Maximum tokens for LLM responses
- `temperature`: Temperature for generation (0.0-1.0)

#### Chunking Settings
- `chunk_size`: Number of words per text chunk
- `overlap`: Number of overlapping words between chunks

#### Standardization Settings
- `enabled`: Enable entity name standardization
- `use_llm_for_entities`: Use LLM for entity resolution

#### Inference Settings
- `enabled`: Enable relationship inference
- `use_llm_for_inference`: Use LLM for inferring relationships
- `apply_transitive`: Apply transitive inference rules

#### Output Settings
- `directory`: Output directory for knowledge graphs
- `format`: Output format ("html" or "json")

## Usage

### From Python Code

```python
from freqtrade.knowledge_graph import KnowledgeGraphGenerator
from freqtrade.persistence import Trade

# Initialize generator
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

kg = KnowledgeGraphGenerator(config)

# Get trades from database
trades = Trade.get_trades().filter(Trade.is_open == False).all()

# Generate knowledge graph
results = kg.generate_from_trades(
    trades,
    session_metadata={"regime": "high_volatility"},
    output_name="session_2024_01_13"
)

print(f"Graph created: {results['html_path']}")
print(f"Stats: {results['stats']}")
```

### Regret Analysis

```python
# Generate regret analysis comparing actual vs hypothetical
results = kg.generate_regret_analysis(
    actual_trades=actual_trades,
    shadow_trades=shadow_trades,
    missed_opportunities=missed_opportunities,
    output_name="regret_2024_01_13"
)
```

### Integration with Backtesting

**Automatic Integration (Recommended)**

The knowledge graph automatically generates after each backtest when enabled in config:

```json
{
  "knowledge_graph": {
    "enabled": true,
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
}
```

Simply run your backtest normally:

```bash
freqtrade backtesting --strategy MyStrategy --config config.json
```

After the backtest completes, the knowledge graph will be automatically generated and saved to `exports/knowledge_graphs/backtest_YYYYMMDD_HHMMSS_graph.html`.

**Manual Integration**

You can also manually generate knowledge graphs from backtest results:

```python
from freqtrade.optimize.backtesting import Backtesting
from freqtrade.knowledge_graph import KnowledgeGraphGenerator
from freqtrade.persistence import Trade

# After backtest completes
backtesting = Backtesting(config)
results = backtesting.start()

# Manually generate knowledge graph
kg = KnowledgeGraphGenerator(config["knowledge_graph"])
trades = Trade.get_trades().all()
kg_results = kg.generate_from_trades(
    trades,
    session_metadata={"type": "backtest"},
    output_name=f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)
```

## Output

The knowledge graph generator produces:

1. **HTML Visualization** (`*_graph.html`)
   - Interactive graph with zoom, pan, and hover
   - Color-coded communities
   - Node sizes based on importance
   - Edge labels showing relationships

2. **JSON Triples** (`*_triples.json`)
   - Raw SPO (Subject-Predicate-Object) triples
   - Can be used for further analysis or import into other systems

3. **Narrative Text** (`*_narrative.txt`)
   - Human-readable summary of the trading session
   - Input used for LLM-based triple extraction

## Examples

See `config_examples/config_knowledge_graph.example.json` for a complete configuration example.

## Use Cases

### 1. Daily Batch Analysis
Run knowledge graph generation after each trading day:
- Identify patterns in daily trades
- Track evolution of strategy performance
- Build cumulative memory over time

### 2. Backtest Analysis
Generate knowledge graphs from backtest results:
- Compare performance across different market regimes
- Identify regime-specific failure modes
- Visualize strategy evolution

### 3. What-If Analysis
Use replay functionality with shadow trades:
- Compare actual vs hypothetical outcomes
- Identify missed opportunities
- Refine decision criteria

### 4. Strategy Development
Build institutional memory:
- Track recurring failure patterns
- Identify successful patterns by regime
- Create visual documentation of learnings

## Architecture

The knowledge graph module is designed as an **optional add-on** to the core execution engine:

- **Zero impact on execution**: KG generation happens post-trade
- **Modular design**: Can be disabled without affecting core functionality
- **LLM-agnostic**: Works with any OpenAI-compatible API
- **Visualization-optional**: Can generate JSON-only for headless environments

## Limitations

- Requires LLM access (Ollama, OpenAI, etc.)
- HTML visualization requires browser for viewing
- Quality depends on LLM model capabilities
- Not suitable for real-time analysis (designed for batch processing)

## Future Enhancements

Potential improvements:
- Integration with dashboard for live viewing
- Cumulative graph building across sessions
- Pattern matching against historical graphs
- Automated recommendation generation
- Graph-based similarity search for similar market conditions

## Related Issues

- Issue #7: Replay functionality integration
- Issue #5: Memory/state persistence

## Contributing

The knowledge graph module is adapted from [rkendel1/graph](https://github.com/rkendel1/graph). 
Improvements to the core graph generation should be contributed upstream when applicable.
