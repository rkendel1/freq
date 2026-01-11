# QuestDB Integration for Trading Metrics

This guide explains how to set up and use QuestDB for logging and querying trading metrics from the execution engine.

## Overview

QuestDB is a high-performance time-series database that can be used to:
- Log key trading metrics (deployed capital %, realized PnL, open positions, etc.)
- Store backtest results for comparison across different market conditions
- Query historical performance data efficiently
- Build custom dashboards and analytics

**Key Features:**
- **Optional and non-intrusive** - only logs if enabled in config
- **No changes to core engine** - uses the `on_execution_result` hook in ExploitModules
- **Minimal latency impact** - ~50ms per log operation when enabled
- **Separate from persistence layer** - SQLAlchemy remains for trades/orders

## Setup Instructions

### 1. Install QuestDB Client

Add the QuestDB Python client to your environment:

```bash
pip install questdb
```

Or if using the full development environment, it's already included in `requirements.txt`.

### 2. Run QuestDB Server

The easiest way to run QuestDB is via Docker:

```bash
# Start QuestDB server
docker run -d \
  --name questdb \
  -p 9000:9000 \
  -p 8812:8812 \
  -p 9009:9009 \
  questdb/questdb

# Verify it's running
docker ps | grep questdb
```

**Ports:**
- `9000` - Web console (open http://localhost:9000 in your browser)
- `8812` - PostgreSQL wire protocol
- `9009` - InfluxDB line protocol (used by the Python client)

### 3. Enable QuestDB in Config

Add the following to your `config.json`:

```json
{
  "questdb_enabled": true,
  "questdb_host": "localhost",
  "questdb_port": 9009,
  "strategy_name": "my_strategy"
}
```

**Configuration Options:**
- `questdb_enabled` (bool, required): Enable/disable QuestDB logging
- `questdb_host` (str, optional): QuestDB host, default `"localhost"`
- `questdb_port` (int, optional): QuestDB ILP port, default `9009`
- `strategy_name` (str, optional): Name to tag metrics with, default `"unknown"`

## Usage

### Logging from ExploitModules

The `log_to_questdb` helper function can be called from your custom ExploitModule's `on_execution_result` method:

```python
from freqtrade.exploits.exploit_module import (
    ExploitModule,
    ExecutionState,
    ExecutionResult,
    Action,
    log_to_questdb,
)

class MyExploit(ExploitModule):
    def __init__(self, config: dict):
        self.config = config
        self._last_state = None
    
    def evaluate(self, state: ExecutionState) -> list[Action]:
        self._last_state = state
        # Your trading logic here
        return []
    
    def on_execution_result(self, action: Action, result: ExecutionResult) -> None:
        # Your custom result handling
        # ...
        
        # Optional: Log to QuestDB if enabled
        if self._last_state:
            log_to_questdb(self.config, self._last_state, action, result)
```

**Metrics Logged to `trading_metrics` table:**
- `symbol` - Trading pair (e.g., "BTC/USDT")
- `strategy` - Strategy name from config
- `deployed_capital_pct` - Percentage of capital currently deployed
- `available_capital` - Available capital for new positions
- `deployed_capital` - Capital currently in positions
- `total_capital` - Total capital (available + deployed)
- `realized_pnl` - Realized profit/loss
- `unrealized_pnl` - Unrealized profit/loss from open positions
- `open_positions` - Number of open positions
- `current_price` - Current market price
- `timestamp` - Event timestamp

### Logging Backtest Results

Use the `run_quick_backtest` function with a config to automatically log results:

```python
from freqtrade.ui.backtest_adapter import run_quick_backtest

config = {
    "questdb_enabled": True,
    "strategy_name": "my_strategy"
}

results = run_quick_backtest(
    market_condition="trending_up",
    num_ticks=1000,
    initial_capital=10000.0,
    verbose=True,
    config=config,  # Pass config to enable QuestDB logging
)
```

**Metrics Logged to `backtest_results` table:**
- `market_condition` - Market condition tested (e.g., "trending_up", "mixed")
- `strategy` - Strategy name from config
- `initial_capital` - Starting capital
- `final_capital` - Ending capital
- `total_return` - Absolute return
- `total_return_pct` - Return percentage
- `total_trades` - Total number of trades
- `winning_trades` - Number of winning trades
- `losing_trades` - Number of losing trades
- `win_rate` - Win rate percentage
- `avg_win` - Average winning trade amount
- `avg_loss` - Average losing trade amount
- `profit_factor` - Profit factor (avg_win / avg_loss)
- `price_change_pct` - Market price change percentage
- `total_ticks` - Number of ticks simulated
- `timestamp` - Backtest completion timestamp

## Querying Data

### Using the Web Console

Open http://localhost:9000 in your browser to access the QuestDB web console.

**Example Queries:**

```sql
-- View recent trading metrics
SELECT * FROM trading_metrics 
ORDER BY timestamp DESC 
LIMIT 10;

-- Calculate average deployed capital by strategy
SELECT 
    strategy,
    AVG(deployed_capital_pct) as avg_deployed_pct,
    COUNT(*) as metrics_count
FROM trading_metrics
GROUP BY strategy;

-- View backtest results sorted by performance
SELECT * FROM backtest_results
ORDER BY total_return_pct DESC;

-- Compare strategies across different market conditions
SELECT 
    strategy,
    market_condition,
    AVG(total_return_pct) as avg_return,
    AVG(win_rate) as avg_win_rate
FROM backtest_results
GROUP BY strategy, market_condition;

-- Time-series analysis of capital deployment
SELECT 
    timestamp,
    deployed_capital_pct,
    realized_pnl,
    unrealized_pnl
FROM trading_metrics
WHERE symbol = 'BTC/USDT'
    AND timestamp > dateadd('h', -24, now())
ORDER BY timestamp;
```

### Using Python

```python
import psycopg2

# Connect using PostgreSQL wire protocol
conn = psycopg2.connect(
    host='localhost',
    port=8812,
    database='qdb',
    user='admin',
    password='quest'
)

cursor = conn.cursor()
cursor.execute("SELECT * FROM trading_metrics ORDER BY timestamp DESC LIMIT 10")
rows = cursor.fetchall()

for row in rows:
    print(row)

cursor.close()
conn.close()
```

## Performance Considerations

- **Latency**: Each log operation adds ~50ms when enabled
- **Batching**: For high-frequency strategies, consider batching metrics
- **Async**: The current implementation is synchronous; for production consider async logging
- **Disk Space**: QuestDB is efficient but monitor disk usage for long-running systems

## Troubleshooting

### QuestDB not receiving data

1. **Check if QuestDB is running:**
   ```bash
   docker ps | grep questdb
   curl http://localhost:9000/
   ```

2. **Verify port 9009 is accessible:**
   ```bash
   nc -zv localhost 9009
   ```

3. **Check logs:**
   ```bash
   docker logs questdb
   ```

### Import errors

If you see "questdb package not installed":
```bash
pip install questdb==4.1.0
```

### Connection errors

Ensure `questdb_host` and `questdb_port` in config match your QuestDB server settings.

## Advanced Usage

### Custom Tables

You can create your own tables and log custom metrics:

```python
from questdb.ingress import Sender, TimestampNanos
import time

config = {"questdb_host": "localhost", "questdb_port": 9009}

with Sender.from_conf(f'tcp::{config["questdb_host"]}:{config["questdb_port"]}') as sender:
    sender.row(
        'custom_metrics',
        symbols={'strategy': 'my_strategy'},
        columns={'value': 123.45},
        at=TimestampNanos(int(time.time() * 1_000_000_000)),
    )
    sender.flush()
```

### Grafana Integration

QuestDB can be used as a data source for Grafana dashboards. See the [QuestDB documentation](https://questdb.io/docs/third-party-tools/grafana/) for setup instructions.

## References

- [QuestDB Documentation](https://questdb.io/docs/)
- [QuestDB Python Client](https://py-questdb-client.readthedocs.io/)
- [QuestDB Docker Setup](https://questdb.io/docs/get-started/docker/)
