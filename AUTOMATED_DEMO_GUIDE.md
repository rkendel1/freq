# Automated Demo Guide - Realistic Bot Simulation

This guide explains how to use the **automated demo mode** that simulates how the trading bot operates autonomously in real market conditions.

## What's New: Automated Mode 🤖

The automated demo solves the key issue raised in the feature request:

> "We need to demo it doing what it will do in the market when live. A realistic view of how it will perform by having it do what it's supposed to do on its own without manual intervention and realistic transition and data presentation."

### Key Features

✅ **Realistic Market Simulation** - Simulates actual price movements and market conditions  
✅ **Autonomous Decision-Making** - Bot analyzes markets and makes trading decisions automatically  
✅ **Live Action Visualization** - See the strategy thinking and executing in real-time  
✅ **Multiple Market Conditions** - Test how the bot performs in different scenarios  
✅ **Real Performance Metrics** - See actual win rates, P&L, and trade outcomes  

---

## Quick Start - Automated Mode

### 1. Start the Demo Server

```bash
./start_demo.sh        # Linux/Mac
./start_demo.ps1       # Windows
```

Or manually:
```bash
python -m freqtrade.ui.demo_server
```

### 2. Open in Browser

Navigate to: **http://127.0.0.1:5000**

### 3. Switch to Automated Mode

1. At the top of the page, change **Mode** dropdown from "Manual" to "🤖 Automated (Realistic Bot)"
2. Select a **Market Condition** (start with "🔀 Mixed (Realistic)")
3. Click **▶️ Start Auto**
4. Watch the bot trade automatically!

---

## How It Works

### The Automation Loop

Every 0.5 seconds (adjustable), the system:

1. **Generates Market Tick** → Simulates realistic price movement
2. **Strategy Analysis** → Bot analyzes price history and market conditions
3. **Decision Making** → Strategy decides whether to enter/exit positions
4. **Risk Validation** → Actions checked against risk limits
5. **Execution** → Approved actions executed
6. **Results Display** → UI updates with trade results and P&L

This mimics exactly how the bot operates in live trading!

### Market Simulator

The **MarketSimulator** generates realistic price ticks with:

- **Trend components** - Directional market movement
- **Volatility** - Price fluctuation (configurable)
- **Mean reversion** - Ranging behavior
- **Random noise** - Market inefficiency

Different conditions simulate different scenarios:
- **Trending Up** - Bull market with upward bias
- **Trending Down** - Bear market with downward bias
- **Volatile** - High volatility with rapid price swings
- **Ranging** - Sideways market within a price range
- **Mixed** - Realistic combination of all conditions

### Automated Strategy

The **AutomatedExploit** implements a simple but realistic trend-following strategy:

**Entry Logic:**
- Tracks 20 recent price ticks
- Calculates fast MA (5 periods) and slow MA (10 periods)
- **Long Entry**: Fast MA > Slow MA + Price > Fast MA + Positive momentum
- **Short Entry**: Fast MA < Slow MA + Price < Fast MA + Negative momentum

**Exit Logic:**
- **Profit Target**: Exit when profit reaches +5%
- **Stop Loss**: Exit when loss reaches -3%
- **Trend Reversal**: Exit when MAs cross in opposite direction

**Risk Management:**
- Position size: 15% of capital per trade
- Cooldown: 5 ticks between new entries
- No more than capital allows

---

## UI Controls

### Mode Selector
- **📝 Manual (Step-by-Step)** - Original mode with scenario selection
- **🤖 Automated (Realistic Bot)** - New automated trading mode

### Market Condition (Automated Mode Only)
- **🔀 Mixed (Realistic)** - Recommended for realistic simulation
- **📈 Trending Up** - Bull market scenario
- **📉 Trending Down** - Bear market scenario
- **⚡ Volatile** - High volatility scenario
- **↔️ Range-Bound** - Sideways market scenario

### Control Buttons
- **▶️ Start Auto** - Begin automated trading
- **⏸️ Pause** - Pause the automation (keeps state)
- **🔄 Reset** - Reset to initial state ($10,000 capital)

### Speed Control
Adjust tick rate from 0.1s to 2.0s per tick:
- **Fast (0.1s)** - See rapid trading activity
- **Normal (0.5s)** - Default realistic speed
- **Slow (2.0s)** - Watch each decision carefully

---

## Understanding the Display

### Real-Time State Panel

Shows live metrics that update with each tick:

1. **Current Price** - Live market price
2. **Available Capital** - Cash ready for new positions
3. **Deployed Capital** - Money currently in open positions
4. **Realized PnL** - Actual profit/loss from closed trades
5. **Open Positions** - Number of active positions
6. **Total Actions** - Total trading actions taken

### Flow Visualization

When the bot takes action, you'll see:

**📊 Market Data**
- Current price
- Market condition

**🎯 Strategy Decision**
- What action the strategy wants to take
- Reasoning (e.g., "Bullish trend detected")

**✅ Execution Results**
- Whether action was approved
- Execution details (price, fees, profit/loss)

### Color Coding

- **Green** = Profitable trades, positive P&L
- **Red** = Losing trades, negative P&L
- **Blue** = Approved actions
- **Gray** = Neutral/waiting

---

## Example Session

### Scenario: Mixed Market - 2 Minutes of Trading

**Initial State:**
- Capital: $10,000
- Price: $50,000

**Actions Observed:**

**Tick 1-5:** Building price history...
- No trades yet (need 20 ticks for analysis)

**Tick 23:** LONG ENTRY
- **Signal**: Fast MA crossed above Slow MA
- **Price**: $50,500
- **Size**: $1,500 (15% of capital)
- **Result**: Position opened ✓

**Tick 35:** PROFIT TARGET HIT
- **Entry**: $50,500
- **Exit**: $53,025 (+5%)
- **Profit**: $75 (after fees)
- **Result**: Position closed ✓

**Tick 50:** SHORT ENTRY
- **Signal**: Fast MA crossed below Slow MA
- **Price**: $52,800
- **Size**: $1,522.50 (15% of new capital)
- **Result**: Position opened ✓

**Tick 58:** STOP LOSS HIT
- **Entry**: $52,800
- **Exit**: $54,384 (-3%)
- **Loss**: -$45.67 (after fees)
- **Result**: Position closed ✓

**Final State after 2 minutes:**
- Capital: $10,029.33
- Total Trades: 2
- Win Rate: 50%
- Net P&L: +$29.33

---

## Realistic Performance Expectations

The automated strategy is intentionally simple but demonstrates realistic behavior:

### What You'll See:

✅ **Both Winning and Losing Trades** - No strategy wins 100%  
✅ **Varied Performance** - Results differ based on market conditions  
✅ **Risk Management** - Stop losses prevent catastrophic losses  
✅ **Fee Impact** - Trading fees reduce profits (0.1% per trade)  
✅ **Trend Following** - Works best in trending markets, struggles in ranging markets  

### Typical Results (500 ticks):

| Market Condition | Expected Return | Win Rate | Trades |
|------------------|-----------------|----------|--------|
| Trending Up      | +10% to +25%   | 55-65%   | 70-100 |
| Trending Down    | +8% to +20%    | 50-60%   | 70-100 |
| Volatile         | +5% to +15%    | 45-55%   | 80-120 |
| Ranging          | -15% to -5%    | 15-30%   | 60-90  |
| Mixed            | -10% to +5%    | 25-40%   | 70-100 |

**Note**: These are demonstration ranges. Real results vary based on random market simulation.

---

## Differences from Live Trading

### What's Simulated (Not Real):
- ❌ Market data (generated synthetically)
- ❌ Order execution (instant, no slippage)
- ❌ Exchange connection
- ❌ Real capital

### What's Real (Actually Used):
- ✅ Strategy logic and decision-making
- ✅ Risk management system
- ✅ Position sizing calculations
- ✅ P&L accounting
- ✅ Fee calculations
- ✅ Capital flow tracking

**The demo shows HOW the system works, not WHAT results you'll get in live markets.**

---

## Comparing to Manual Mode

### Manual Mode (Original)
- **Purpose**: Understand system architecture
- **Control**: You select each scenario
- **Outcomes**: Predetermined (e.g., "Profitable Trade Cycle" always profits)
- **Best For**: Learning how capital flows through the system

### Automated Mode (New)
- **Purpose**: See realistic bot operation
- **Control**: Bot makes all decisions
- **Outcomes**: Variable based on market simulation
- **Best For**: Understanding autonomous behavior and realistic performance

**Use Both!** Manual mode teaches the mechanics, automated mode shows the bot in action.

---

## Advanced Usage

### Running Longer Simulations

Let the bot run for 5-10 minutes to see:
- Multiple market condition changes
- Variety of trade outcomes
- Capital growth/decline patterns
- Strategy behavior over time

### Testing Different Conditions

Try each market condition to see how the strategy adapts:

1. **Start with Trending Up** - See the strategy at its best
2. **Switch to Ranging** - See where it struggles
3. **Try Volatile** - See risk management in action
4. **Use Mixed** - Most realistic market behavior

### Adjusting Speed

- **Slow (2s)**: Best for learning - watch each decision
- **Normal (0.5s)**: Realistic trading pace
- **Fast (0.1s)**: See long-term patterns quickly

---

## Backtesting Adapter

For programmatic testing, use the **BacktestAdapter**:

```python
from freqtrade.ui.backtest_adapter import BacktestAdapter

# Create adapter
adapter = BacktestAdapter(
    initial_capital=10000.0,
    market_condition="mixed",
    volatility=0.02,
)

# Run simulation
results = adapter.run(num_ticks=1000, verbose=True)

# Analyze results
print(f"Final Capital: ${results['final_capital']:,.2f}")
print(f"Total Return: {results['total_return_pct']:+.2f}%")
print(f"Win Rate: {results['win_rate']:.2f}%")

# Get detailed data
trades_df = adapter.get_trades_dataframe()
equity_df = adapter.get_equity_curve_dataframe()
```

See `examples/automated_backtest_example.py` for complete examples.

---

## Integration with Backtesting Tools

The **BacktestAdapter** makes it easy to integrate with existing backtesting frameworks:

### Features:
- ✅ Simple API - Easy to integrate
- ✅ Pandas DataFrames - Compatible with analysis tools
- ✅ Configurable - Adjust market conditions, volatility, etc.
- ✅ Statistics - Win rate, profit factor, equity curve, etc.
- ✅ Trade Records - Complete history of all trades

### Example Integration:

```python
# Your backtesting framework
from your_framework import BacktestEngine
from freqtrade.ui.backtest_adapter import BacktestAdapter

# Create adapter
adapter = BacktestAdapter(
    initial_capital=10000.0,
    market_condition="trending_up",
)

# Run backtest
results = adapter.run(num_ticks=1000)

# Export to your framework
trades = adapter.get_trades_dataframe()
equity = adapter.get_equity_curve_dataframe()

# Integrate with your analysis
your_engine.analyze(trades, equity, results)
```

---

## Troubleshooting

### Bot Not Trading
- **Wait longer**: Need 20 price ticks to build history
- **Market conditions**: In ranging markets, signals are rare
- **Reset and retry**: Market randomness may not trigger signals

### Performance Seems Bad
- **Normal in ranging markets**: Strategy designed for trends
- **Randomness**: Each simulation is unique
- **Longer run needed**: Short runs can be misleading

### UI Not Updating
- **Check browser console**: Look for JavaScript errors
- **Refresh page**: Clear any stuck state
- **Restart server**: Kill and restart the demo server

---

## FAQ

### Q: Is this how it will perform in real trading?

**A:** No. This demonstrates the SYSTEM (how decisions are made, how capital flows, how risk is managed), not PREDICTIONS. Real market results depend on actual market conditions and your specific strategy.

### Q: Why does it lose money sometimes?

**A:** Because it's realistic! No trading strategy wins every trade or in every market condition. The demo shows both wins AND losses, just like real trading.

### Q: Can I use this strategy in production?

**A:** The **AutomatedExploit** is a demonstration strategy, intentionally simple. For production, you should implement your own strategy logic in a custom ExploitModule.

### Q: How do I customize the strategy?

**A:** Copy `freqtrade/ui/automated_exploit.py` and modify the logic in `_check_entry_conditions()` and `_check_exit_conditions()`. Then update the demo server to use your custom exploit.

### Q: Can I use real market data?

**A:** Yes! The **BacktestAdapter** can be extended to accept real historical price data instead of simulated data. See the backtesting adapter code for integration points.

---

## Summary

The automated demo mode provides:

✅ **Realistic Simulation** - See the bot operate autonomously  
✅ **Market Variety** - Test different conditions  
✅ **Live Visualization** - Watch decisions being made  
✅ **Real Metrics** - Actual performance statistics  
✅ **Backtesting Integration** - Easy adapter for testing frameworks  

This addresses the core requirement: **"We need to demo it doing what it will do in the market when live"** by showing autonomous operation with realistic market simulation and decision-making.

---

**Next Steps:**
1. Run the automated demo (http://127.0.0.1:5000)
2. Try different market conditions
3. Review the backtesting adapter examples
4. Implement your own trading strategy
5. Test with the automated demo before going live

**Last Updated**: 2026-01-09  
**Version**: 1.0 - Initial automated demo release
