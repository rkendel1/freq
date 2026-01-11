# Analysis Scripts

This directory contains external analysis scripts for trading metrics.

## Purpose

Scripts in this directory run SEPARATELY from the core trading engine and are used for:
- Analyzing historical metrics
- Generating insights and suggestions
- Manual parameter optimization research

## Key Principles

- **External Only**: No integration with core execution engine
- **Read-Only**: Only reads exported metrics, never modifies live data
- **Manual Review**: All outputs are for human review
- **Zero Execution Impact**: No automatic application of suggestions

## Available Scripts

### `dspy_insights.py` - LM-Based Insights

Uses DSPy with a local LLM (Ollama) to generate manual adjustment suggestions from trading metrics.

**Usage:**
```bash
python analysis/dspy_insights.py
```

**See documentation:** [docs/dspy.md](../docs/dspy.md)

## Adding New Analysis Scripts

When adding new analysis scripts:

1. Keep them in this directory (`analysis/`)
2. Ensure they are read-only (no execution state modification)
3. Output suggestions for manual review only
4. Document clearly that they have zero execution impact
5. Add documentation in `docs/`

## Integration

Analysis scripts integrate with the workflow as follows:

```
Trading Execution → Metrics Export → Analysis Scripts → Human Review → Manual Config Changes
                                            ↑
                                    (NO AUTOMATIC FEEDBACK LOOP)
```

All suggestions from analysis scripts must be:
- Reviewed by humans
- Manually applied to configuration if appropriate
- Never automatically applied to execution
