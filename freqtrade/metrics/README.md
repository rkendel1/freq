# Metrics Module

The metrics module provides tools for analyzing trade performance and attributing profits/losses to various factors.

## Attribution Module

The attribution module (`freqtrade.metrics.attribution`) provides **raw attribution** for trades, allowing you to track the sources and components of profit/loss for each trade.

### Features

- **Exploit Attribution**: Track which exploit/strategy generated each trade
- **Capital Source Tracking**: Identify the source of capital used (initial, reinvested, borrowed)
- **Fee Analysis**: Capture both entry and exit fees with absolute costs
- **Funding Fees**: Track funding fees earned or paid (for futures/margin trades)
- **Holding Duration**: Calculate exact holding time in seconds and hours
- **PnL Metrics**: Access realized profit and profit ratios for closed trades

### Quick Start

```python
from freqtrade.persistence import Trade
from freqtrade.metrics.attribution import attribute_trade

# Get a trade from the database
trade = Trade.get_trades().filter(Trade.is_open == False).first()

# Attribute the trade
attribution = attribute_trade(trade, capital_source="initial")

# Access attribution data
print(f"Exploit: {attribution.exploit_id}")
print(f"Total Fees: ${attribution.total_fees}")
print(f"Funding Fees: ${attribution.funding_fees}")
print(f"Duration: {attribution.holding_duration_hours}h")
print(f"Profit: ${attribution.realized_profit}")
```

### Attribution Fields

The `TradeAttribution` dataclass includes:

**Identification:**
- `trade_id`: Unique identifier for the trade
- `exploit_id`: ID of the exploit that generated this trade
- `capital_source`: Source of capital used
- `pair`: Trading pair
- `is_short`: Whether this is a short position

**Entry Metrics:**
- `entry_price`: Price at which position was opened
- `entry_amount`: Amount of asset purchased/sold
- `entry_stake`: Total stake amount
- `entry_date`: Timestamp when position was opened

**Exit Metrics:**
- `exit_price`: Price at which position was closed (None if open)
- `exit_date`: Timestamp when position was closed (None if open)

**Cost Breakdown:**
- `fee_open`: Fee paid on entry (as percentage)
- `fee_close`: Fee paid on exit (as percentage)
- `fee_open_cost`: Absolute cost of entry fee
- `fee_close_cost`: Absolute cost of exit fee
- `total_fees`: Total fees paid
- `funding_fees`: Funding fees earned/paid (negative = paid)

**Duration:**
- `holding_duration_seconds`: Holding time in seconds
- `holding_duration_hours`: Holding time in hours

**PnL:**
- `realized_profit`: Absolute profit (None if open)
- `profit_ratio`: Profit ratio (None if open)

**Metadata:**
- `is_open`: Whether the trade is still open
- `exit_reason`: Reason for exit (None if open)

### Examples

See `examples/attribution_example.py` for comprehensive examples including:

1. Attributing closed trades
2. Attributing open trades
3. Batch attribution for analysis
4. Exporting attribution as dictionary

### Design Philosophy

This module provides **RAW attribution only** - no analytics, aggregation, or visualization. The goal is to create a clean foundation for building higher-level analytics tools.

The attribution data can be:
- Stored in a database for historical analysis
- Exported to JSON/CSV for external analysis
- Aggregated to analyze performance by exploit, capital source, etc.
- Used as input for machine learning models

### Testing

Run tests with:

```bash
python -m pytest tests/metrics/test_attribution.py -v
```

Or validate manually:

```bash
python examples/attribution_example.py
```

### Future Extensions

This raw attribution module is designed to be extended with:
- Aggregation functions (e.g., total profit by exploit)
- Time-series analysis (e.g., profit over time)
- Comparative analytics (e.g., exploit performance comparison)
- Risk-adjusted metrics (e.g., Sharpe ratio by exploit)

These extensions should be built on top of the raw attribution data, not mixed into this module.
