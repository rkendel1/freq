# Knowledge Graph Regret Analysis - Key Features

## What's Captured in Regret Analysis

The regret analysis feature captures interesting insights and "should have" moments from trading sessions:

### 1. **Trade Execution Regrets**
Things we should have done differently on trades we took:

- **"Should have made more on that trade"**
  - `REGRET: BTC/USDT - Made 4.00% but could have held longer (exited too conservatively?)`
  - Identifies early exits where we left profit on the table

- **"Position was too small"**
  - `REGRET: SOL/USDT - Great trade (12.00%) but position was only 1000 - could have made 2-3x more with larger size`
  - Highlights missed opportunities due to conservative position sizing

- **"Should have cut losses earlier"**
  - `REGRET: ADA/USDT - Lost 6.00%, should have cut earlier (stop loss not tight enough?)`
  - Identifies trades where we held losers too long

### 2. **Trades We Didn't Take**
Opportunities we completely missed:

- **Shadow Trades**
  - `REGRET: Didn't take MATIC/USDT long - Could have made 15.00% (Reason skipped: Risk limit reached)`
  - Shows profitable setups we passed on and why

### 3. **Missed Setups**
Interesting signals we should have caught:

- **Missed Opportunities**
  - `MISSED: Breakout signal fired but we were in cooldown (Could have made ~12.0%)`
  - `MISSED: Entry criteria too strict, missed the move (Could have made ~7.0%)`

### 4. **Aggregate Regret Metrics**
Quantifies total opportunity cost:

```
Actual Profit: 16.00%
Left on Table (Shadow): 15.00%
Missed Completely: 0.00%
Capture Rate: 51.6% of total potential
```

### 5. **Pattern Recognition**
Identifies recurring regret patterns:

- **Early Exit Pattern**
  - `PATTERN: Exiting too early on 3 trades (43% of trades). Consider trailing stops to capture more upside.`

- **Shadow Trade Pattern**
  - `PATTERN: Left 5 potentially winning trades untaken. Risk limits too tight or entry criteria too strict?`

- **Position Sizing Pattern**
  - `PATTERN: 2 big winners had below-average position sizes. Missing conviction signals or risk allocation issues?`

- **Stop Loss Pattern**
  - `PATTERN: 1 trades lost >5%. Stop losses not working or being overridden?`

## Example Output

```
Regret Analysis - What We Learned and Left on the Table

=== Trades We Took - Could We Have Done Better? ===

- REGRET: BTC/USDT - Made 4.00% but could have held longer (exited too conservatively?)
- REGRET: SOL/USDT - Great trade (12.00%) but position was only 1000 - could have made 2-3x more with larger size
- REGRET: ADA/USDT - Lost 6.00%, should have cut earlier (stop loss not tight enough?)

=== Trades We DIDN'T Take (Regret) - 2 Opportunities ===

- REGRET: Didn't take MATIC/USDT long - Could have made 15.00% (Reason skipped: Risk limit reached)
- REGRET: Didn't take UNI/USDT long - Could have made 8.00% (Reason skipped: Signal confidence too low)

=== Interesting Setups We Missed - 2 Cases ===

- MISSED: Breakout signal fired but we were in cooldown (Could have made ~12.0%)
- MISSED: Entry criteria too strict, missed the move (Could have made ~7.0%)

=== Aggregate Regret Summary ===

- Actual Profit: 16.00%
- Left on Table (Shadow): 23.00%
- Missed Completely: 19.00%
- Capture Rate: 27.6% of total potential

=== Key Regret Patterns to Address ===

- PATTERN: Exiting too early on 3 trades (43% of trades). Consider trailing stops to capture more upside.
- PATTERN: Left 2 potentially winning trades untaken. Risk limits too tight or entry criteria too strict?
- PATTERN: 1 trades lost >5%. Stop losses not working or being overridden?
- INSIGHT: Review these patterns when refining strategy parameters
```

## How It Integrates with Knowledge Graph

The regret analysis narrative is then fed into the LLM-based knowledge graph generator which:

1. **Extracts Relationships**
   - "Early exit" → "caused by" → "Conservative stop loss"
   - "High volatility regime" → "led to" → "Frequent stop outs"
   - "Position sizing" → "limited" → "Profit capture"

2. **Builds Visual Graph**
   - Nodes: Trading patterns, market conditions, outcomes
   - Edges: Causal relationships, correlations
   - Communities: Related failure/success modes

3. **Creates Institutional Memory**
   - Growing graph of lessons learned
   - Pattern matching against historical sessions
   - Prevents repeating the same mistakes

## Usage Example

```python
from freqtrade.knowledge_graph import KnowledgeGraphGenerator

kg = KnowledgeGraphGenerator(config)

# Generate regret analysis with all the interesting notes
results = kg.generate_regret_analysis(
    actual_trades=trades,
    shadow_trades=[
        {"pair": "MATIC/USDT", "potential_profit": 0.15, "skip_reason": "Risk limit"},
    ],
    missed_opportunities=[
        {"reason": "Entry too strict, missed breakout", "potential_profit": 0.12},
    ],
    output_name="session_regret"
)

# Output includes:
# - HTML visualization of causal relationships
# - JSON triples for further analysis
# - Narrative with all regret insights
```

## Benefits

1. **Actionable Insights**: Specific suggestions for parameter tuning
2. **Quantified Opportunity Cost**: Know exactly how much was left on the table
3. **Pattern Recognition**: Identify recurring mistakes automatically
4. **Visual Memory**: Interactive graph showing cause-effect relationships
5. **Continuous Improvement**: Build institutional memory over time

## Future Enhancements

- Compare regret patterns across different market regimes
- Track improvement over time (reducing regret rate)
- Automated parameter suggestions based on regret analysis
- Similarity matching: "This looks like that time we..."
