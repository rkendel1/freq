# MYCELIUM - Metrics Dashboard

A separate Streamlit application for visualizing and mapping trading metrics over time. This dashboard provides interactive charts for PnL trends, deployed capital heatmaps, and statistical analysis.

## Features

- 📈 **Time Series Visualization**: Track PnL and deployed capital over time
- 🔥 **Heatmaps**: Analyze metric correlations and time-based patterns
- 📊 **Statistical Analysis**: View distributions and summary statistics
- 📋 **Raw Data Explorer**: Filter, view, and export raw metrics
- 🔄 **Dual Data Source**: Query from QuestDB (live) or Parquet files (exported)

## Installation

### 1. Install Dependencies

```bash
# From the repository root
pip install streamlit plotly pandas psycopg2-binary pyarrow

# Or install from dashboard requirements
pip install -r dashboard/requirements.txt
```

### 2. Set Up Data Source

#### Option A: QuestDB (Recommended for Live Data)

1. **Start QuestDB server:**
   ```bash
   docker run -d \
     --name questdb \
     -p 9000:9000 \
     -p 8812:8812 \
     -p 9009:9009 \
     questdb/questdb
   ```

2. **Enable QuestDB logging in your engine config:**
   ```json
   {
     "questdb_enabled": true,
     "questdb_host": "localhost",
     "questdb_port": 9009,
     "strategy_name": "my_strategy"
   }
   ```

3. **Run the trading engine** - metrics will be automatically logged to QuestDB

4. **Verify data in QuestDB web console:**
   - Open http://localhost:9000
   - Run: `SELECT * FROM trading_metrics ORDER BY timestamp DESC LIMIT 10;`

#### Option B: Parquet Files (Fallback/Export Mode)

If QuestDB is not available or you want to work with exported data:

1. **Export metrics from your running engine** (or use the dashboard's export button)

2. **Manually create sample data:**
   ```python
   import pandas as pd
   from datetime import datetime, timedelta
   
   # Create sample data
   df = pd.DataFrame({
       'timestamp': [datetime.now() - timedelta(hours=i) for i in range(100)],
       'symbol': ['BTC/USDT'] * 100,
       'strategy': ['example_strategy'] * 100,
       'deployed_capital_pct': [50 + i*0.5 for i in range(100)],
       'realized_pnl': [100 + i*10 for i in range(100)],
       'unrealized_pnl': [50 + i*2 for i in range(100)],
       'total_capital': [10000] * 100,
       'available_capital': [5000] * 100,
       'deployed_capital': [5000] * 100,
       'open_positions': [1] * 100,
       'current_price': [50000 + i*100 for i in range(100)]
   })
   
   # Save to Parquet
   df.to_parquet('exports/metrics.parquet')
   ```

## Usage

### Running the Dashboard

From the repository root:

```bash
streamlit run dashboard/app.py
```

The dashboard will open automatically in your browser at http://localhost:8501

### Configuration

Use the sidebar to configure:

- **Data Source**: Switch between QuestDB (live) or Parquet (exported)
- **QuestDB Host**: Hostname for QuestDB server (default: localhost)
- **QuestDB Port**: PostgreSQL wire protocol port (default: 8812)

### Dashboard Tabs

1. **📈 Time Series**
   - View PnL and deployed capital trends over time
   - Filter by strategy
   - Interactive zoom and hover
   - Multi-metric comparison

2. **🔥 Heatmaps**
   - Correlation matrix of all metrics
   - Deployed capital % by time of day
   - Color-coded intensity maps

3. **📊 Statistics**
   - Strategy-wise performance summary
   - Overall statistical analysis
   - Distribution histograms
   - Box plots for outlier detection

4. **📋 Raw Data**
   - View and filter raw metrics
   - Download as CSV
   - Adjustable row count

### Exporting Data

1. Load data from QuestDB
2. Click "📦 Export to Parquet" button
3. Data saved to `exports/metrics.parquet`
4. Switch to "Parquet Export" mode to view offline

## Architecture

### Data Flow

```
Trading Engine
    ↓
QuestDB (optional) ──→ Dashboard (live queries)
    ↓
Parquet Export ──────→ Dashboard (offline mode)
```

### Key Design Principles

- **Completely separate from core engine**: No modifications to execution logic
- **No engine overhead**: Dashboard runs as standalone process
- **Flexible data sources**: QuestDB for live, Parquet for exports
- **No impact on demo UI**: Runs independently on different port

### File Structure

```
dashboard/
├── app.py              # Main Streamlit application
├── README.md           # This file
├── requirements.txt    # Dashboard-specific dependencies
└── __init__.py         # Python package marker

exports/
└── metrics.parquet     # Exported metrics (created on demand)
```

## Troubleshooting

### QuestDB Connection Failed

**Error**: `Failed to connect to QuestDB`

**Solutions**:
1. Verify QuestDB is running: `docker ps | grep questdb`
2. Check port accessibility: `curl http://localhost:9000/`
3. Ensure correct host/port in sidebar
4. Switch to Parquet mode as fallback

### No Data Available

**Error**: `No data available`

**Solutions**:
1. **QuestDB mode**: Ensure engine is running with `questdb_enabled: true`
2. **Parquet mode**: Export data first or create sample data
3. Check that `trading_metrics` table exists in QuestDB: http://localhost:9000

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'streamlit'`

**Solution**:
```bash
pip install -r dashboard/requirements.txt
```

### Permission Errors

**Error**: `Permission denied: 'exports/metrics.parquet'`

**Solution**:
```bash
mkdir -p exports
chmod 755 exports
```

## Performance Considerations

- **Data Caching**: Dashboard caches data for 60 seconds (configurable via `@st.cache_data(ttl=60)`)
- **Query Limits**: QuestDB queries limited to 10,000 most recent records
- **Refresh Rate**: Use browser refresh to reload data
- **Large Datasets**: Use Parquet mode for datasets > 100K records

## Examples

### Quick Start with Sample Data

```bash
# 1. Create sample data
python -c "
import pandas as pd
from datetime import datetime, timedelta
import random

df = pd.DataFrame({
    'timestamp': [datetime.now() - timedelta(minutes=i*5) for i in range(1000)],
    'symbol': ['BTC/USDT'] * 1000,
    'strategy': ['momentum'] * 500 + ['mean_reversion'] * 500,
    'deployed_capital_pct': [random.uniform(30, 70) for _ in range(1000)],
    'realized_pnl': [random.uniform(-100, 500) for _ in range(1000)],
    'unrealized_pnl': [random.uniform(-50, 100) for _ in range(1000)],
    'total_capital': [10000 + i*10 for i in range(1000)],
    'available_capital': [5000] * 1000,
    'deployed_capital': [5000] * 1000,
    'open_positions': [random.randint(0, 3) for _ in range(1000)],
    'current_price': [50000 + random.uniform(-1000, 1000) for _ in range(1000)]
})
df.to_parquet('exports/metrics.parquet')
print('Sample data created!')
"

# 2. Run dashboard
streamlit run dashboard/app.py
```

### Compare Multiple Strategies

Run backtests with different strategies, all logging to QuestDB:

```python
from freqtrade.ui.backtest_adapter import run_quick_backtest

strategies = ['momentum', 'mean_reversion', 'breakout']

for strategy in strategies:
    config = {
        "questdb_enabled": True,
        "strategy_name": strategy
    }
    
    results = run_quick_backtest(
        market_condition="mixed",
        num_ticks=1000,
        config=config
    )
```

Then use the dashboard to compare performance across strategies.

## Advanced Usage

### Custom Metrics

To log custom metrics to QuestDB:

```python
from questdb.ingress import Sender, TimestampNanos
import time

with Sender.from_conf('tcp::addr=localhost:9009;') as sender:
    sender.row(
        'trading_metrics',
        symbols={
            'symbol': 'BTC/USDT',
            'strategy': 'custom_strategy'
        },
        columns={
            'deployed_capital_pct': 45.5,
            'realized_pnl': 1250.0,
            'custom_metric': 123.45
        },
        at=TimestampNanos(int(time.time() * 1_000_000_000))
    )
    sender.flush()
```

### Scheduled Exports

Create a cron job to export metrics regularly:

```bash
# Export metrics daily at midnight
0 0 * * * cd /path/to/freq && python -c "
import pandas as pd
import psycopg2

conn = psycopg2.connect(host='localhost', port=8812, database='qdb', user='admin', password='quest')
df = pd.read_sql('SELECT * FROM trading_metrics', conn)
df.to_parquet('exports/metrics_backup.parquet')
conn.close()
"
```

## Integration with Existing Tools

- **Grafana**: Use QuestDB as data source for Grafana dashboards
- **Jupyter**: Load Parquet exports in notebooks for custom analysis
- **Excel**: Export CSV from dashboard and import into spreadsheets

## References

- [Streamlit Documentation](https://docs.streamlit.io/)
- [Plotly Documentation](https://plotly.com/python/)
- [QuestDB Documentation](https://questdb.io/docs/)
- [QuestDB Integration Guide](../docs/questdb.md)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review QuestDB logs: `docker logs questdb`
3. Verify data exists: http://localhost:9000
4. Open an issue on GitHub
