# Minimal Trading Execution Engine

**This is infrastructure, not a trading bot.**

This repository has been stripped down from Freqtrade into a minimal, deterministic execution engine.
It provides the core infrastructure for order execution, position tracking, and PnL attribution,
but contains **no trading logic** or signal generation.

## ⚠️ What This Is NOT

- ❌ A trading bot
- ❌ A strategy framework
- ❌ An indicator library (TA-Lib removed)
- ❌ A machine learning system (FreqAI removed)
- ❌ A retail trading platform (UI/API removed)
- ❌ A hyperparameter optimizer (Hyperopt removed)

## ✅ What This IS

- ✅ Order execution engine
- ✅ Position tracking system
- ✅ PnL attribution
- ✅ Exchange abstraction layer (ccxt-based)
- ✅ Backtesting/simulation framework (price replay)
- ✅ Risk management primitives
- ✅ Capital and state isolation

## 🚀 Quick Start - Try It Online

**🌐 Live Demo on Render:** [https://freq-0x5y.onrender.com/](https://freq-0x5y.onrender.com/)

No installation needed - try the full demo UI instantly in your browser!

---

## 🚀 Quick Start - Run Locally

**Pushbutton startup - get the platform running in seconds:**

```bash
# Linux/Mac
./start.sh

# Windows
./start.ps1
```

This single command will:
- ✅ Check dependencies and install if needed
- ✅ Start the demo UI server
- ✅ Open the platform at http://localhost:5000

📖 **[Complete Local Development Guide](LOCAL_DEVELOPMENT.md)** - Full setup instructions, troubleshooting, and development workflow

---

## 🎯 Demo UI - See It In Action

**Interactive demo with TWO modes:**

**Option 1: Use the live demo (no setup needed)**
- 🌐 **Live Demo:** [https://freq-0x5y.onrender.com/](https://freq-0x5y.onrender.com/)

**Option 2: Run locally**
```bash
# Quick start - just run this script
./start_demo.sh         # Linux/Mac
./start_demo.ps1        # Windows

# Then open your browser to:
# http://localhost:5000
```

![Demo UI Screenshot](https://github.com/user-attachments/assets/d01df924-4108-478d-a0fd-9cc0a5108209)

### 📝 Manual Mode - Understanding the System

Shows the complete money-making cycle step-by-step:
- **Open Position** → Deploy capital into a trade
- **Market Movement** → Price moves in your favor  
- **Close Position** → Realize profit and get capital back **with gains**

**💡 Try the "Profitable Trade Cycle" scenario:**
1. Opens a 15% position (deploys $1,500)
2. Closes with 8% profit (returns $1,500 + $120 profit)
3. Your capital grows from $10,000 → $10,120

### 🤖 Automated Mode - Realistic Bot Operation **NEW!**

**See the bot operate autonomously with realistic market simulation:**
- ✅ **Continuous operation** - Bot runs automatically without manual intervention
- ✅ **Realistic market data** - Simulated price ticks mimicking real markets
- ✅ **Live decision-making** - Watch the strategy analyze and execute in real-time
- ✅ **Multiple market conditions** - Test in trending, volatile, ranging markets
- ✅ **Real performance metrics** - See actual wins, losses, and P&L

Switch to **Automated Mode** in the UI and click "Start Auto" to see the platform do what it will do in live markets!

📖 **[Automated Demo Guide](AUTOMATED_DEMO_GUIDE.md)** | 📖 **[Full Demo UI Documentation](freqtrade/ui/README.md)** | 📝 **[Quick Start Guide](DEMO_UI_QUICKSTART.md)**

### 🧪 Backtesting Adapter

**Easy integration with backtesting tools:**

```python
from freqtrade.ui.backtest_adapter import run_quick_backtest

# Run realistic automated simulation
results = run_quick_backtest(
    market_condition="mixed",
    num_ticks=1000,
    initial_capital=10000.0
)

print(f"Final Capital: ${results['final_capital']:,.2f}")
print(f"Total Return: {results['total_return_pct']:+.2f}%")
print(f"Win Rate: {results['win_rate']:.2f}%")
```

See `examples/automated_backtest_example.py` for complete examples.



---

## Architecture

This system follows a strict **Intent → Execution** separation:

```
External System → ExploitModule → Action → Risk Check → Execution → Result
```

### Key Principle

**The engine NEVER decides when to trade — only HOW.**

All trading decisions (WHEN to trade) come from external ExploitModules.
The engine only executes explicit Actions and enforces risk limits.

### Core Components

#### `/freqtrade/core/` - Execution Infrastructure
- `risk.py` - Risk management with hard bounds
- `state.py` - Capital and state isolation

#### `/freqtrade/exploits/` - Signal Providers (Empty by Design)
- `exploit_module.py` - Base interface
- `example_exploit.py` - Stub implementation

External systems (DSPy, MYCELIUM, etc.) implement `ExploitModule` to provide trading intent.

#### `/freqtrade/exchange/` - Exchange Connectors
- Exchange abstraction (ccxt-based)
- Order placement and tracking
- Balance management

#### `/freqtrade/persistence/` - State Persistence
- Trade and Order models
- Database migrations
- Key-value store

#### `/freqtrade/optimize/` - Backtesting Only
- Deterministic price replay
- Result reporting

## What Was Removed

Over **40,000 lines of code** deleted, including:

- ❌ **FreqAI** - All ML/AI features
- ❌ **RPC/API/Telegram** - All communication systems
- ❌ **Plotting** - All visualization
- ❌ **Hyperopt** - All optimization
- ❌ **Strategy Templates** - All example strategies
- ❌ **TA-Lib** - All technical indicators
- ❌ **Analysis Tools** - Lookahead/recursive analysis
- ❌ **Web UI** - All UI components
- ❌ **Documentation** - 140+ markdown files

See [FILES_DELETED.md](FILES_DELETED.md) for complete list.

## Dependencies

Minimal dependencies only:

**Core:**
- `ccxt` - Exchange connectivity
- `SQLAlchemy` - Persistence
- `pandas`/`numpy` - Data handling
- `requests`/`aiohttp` - Networking

**Removed:**
- TA-Lib, ft-pandas-ta, technical (indicators)
- python-telegram-bot (notifications)
- FastAPI, uvicorn, websockets (API/WebSocket)
- scipy, scikit-learn, optuna (ML/optimization)
- LightGBM, XGBoost, torch (ML models)
- plotly (plotting)

## Quick Start

### 1. Implement an ExploitModule

```python
from freqtrade.exploits.exploit_module import (
    ExploitModule,
    ExecutionState,
    Action,
    ActionType,
)

class MyExploit(ExploitModule):
    def evaluate(self, state: ExecutionState) -> list[Action]:
        # Your logic here - connect to DSPy, MYCELIUM, etc.
        if should_open_long(state):
            return [Action(
                type=ActionType.OPEN_LONG,
                symbol=state.symbol,
                size=0.1,  # 10% of capital
                reason="my_signal",
            )]
        return []
    
    def on_execution_result(self, action: Action, result: ExecutionResult) -> None:
        # Handle result - feed back to your system
        pass
```

### 2. Configure

```json
{
  "exploit_module": "my_module.MyExploit",
  "max_open_trades": 3,
  "max_position_size": 0.1,
  "max_total_exposure": 0.95,
  "exchange": {
    "name": "binance",
    "key": "...",
    "secret": "..."
  }
}
```

### 3. Run

```bash
freqtrade trade --config config.json
```

The engine will:
1. Call your `evaluate()` method with current state
2. Check Actions against risk limits
3. Execute approved Actions
4. Return results to your `on_execution_result()`

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [DEPENDENCIES.md](DEPENDENCIES.md) - Dependency graph
- [FILES_DELETED.md](FILES_DELETED.md) - What was removed
- [REMAINING_WORK.md](REMAINING_WORK.md) - What still needs work

## Testing

The system can run with **zero exploits** loaded (NullExploitModule).
It should do nothing - this proves execution is decoupled from decision-making.

```python
# Engine with no exploits = no trades
engine = ExecutionEngine(NullExploitModule())
engine.run()  # Does nothing
```

## Example: Position Lifecycle

```python
# 1. ExploitModule proposes action
action = Action(
    type=ActionType.OPEN_LONG,
    symbol="BTC/USDT",
    size=0.1,
    reason="external_signal"
)

# 2. Engine checks risk
allowed, reason = risk_manager.check_action(action, state)

# 3. If allowed, execute
if allowed:
    result = engine.execute(action)
    
# 4. Result returned to exploit
exploit.on_execution_result(action, result)
```

## Integration Points

### DSPy Integration (External)
```
DSPy → ExploitModule.evaluate() → Actions → Engine → Results → DSPy
```

### MYCELIUM Exploits (External)
Each micro-exploit implements ExploitModule independently.
Capital is explicitly managed, no hidden coupling.

## Risk Management

Risk limits are enforced **before execution**:

```python
RiskLimits(
    max_position_size=0.10,      # Max 10% per position
    max_total_exposure=0.95,     # Max 95% deployed
    max_open_positions=3,         # Max 3 simultaneous
    max_daily_loss=0.20,         # Max 20% daily loss
    position_cooldown=0,         # Cooldown in seconds
)
```

All risk is config-driven, not code-driven.

## State Isolation

All capital is explicitly tracked:

```python
CapitalState(
    total_capital=10000.0,
    available_capital=9000.0,    # Available for new positions
    deployed_capital=1000.0,     # Currently in positions
    reserved_capital=0.0,        # Reserved for fees/margin
    pnl_realized=0.0,
    pnl_unrealized=0.0,
)
```

No global mutable state - everything is explicit.

## Original Freqtrade

This was derived from [Freqtrade](https://github.com/freqtrade/freqtrade).

**Original purpose:** Retail crypto trading bot with strategies, indicators, optimization.

**New purpose:** Infrastructure for building custom execution systems.

## License

GPLv3 (inherited from Freqtrade)

## Disclaimer

This software is for educational purposes only. Do not risk money you cannot afford to lose.
USE THE SOFTWARE AT YOUR OWN RISK. THE AUTHORS ASSUME NO RESPONSIBILITY FOR YOUR TRADING RESULTS.

Please make sure to read the [exchange specific notes](docs/exchanges.md), as well as the [trading with leverage](docs/leverage.md) documentation before diving in.

### Community tested

Exchanges confirmed working by the community:

- [X] [Bitvavo](https://bitvavo.com/)
- [X] [Kucoin](https://www.kucoin.com/)

## Documentation

We invite you to read the bot documentation to ensure you understand how the bot is working.

Please find the complete documentation on the [freqtrade website](https://www.freqtrade.io).

## Features

- [x] **Based on Python 3.11+**: For botting on any operating system - Windows, macOS and Linux.
- [x] **Persistence**: Persistence is achieved through sqlite.
- [x] **Dry-run**: Run the bot without paying money.
- [x] **Backtesting**: Run a simulation of your buy/sell strategy.
- [x] **Strategy Optimization by machine learning**: Use machine learning to optimize your buy/sell strategy parameters with real exchange data.
- [X] **Adaptive prediction modeling**: Build a smart strategy with FreqAI that self-trains to the market via adaptive machine learning methods. [Learn more](https://www.freqtrade.io/en/stable/freqai/)
- [x] **Whitelist crypto-currencies**: Select which crypto-currency you want to trade or use dynamic whitelists.
- [x] **Blacklist crypto-currencies**: Select which crypto-currency you want to avoid.
- [x] **Builtin WebUI**: Builtin web UI to manage your bot.
- [x] **Manageable via Telegram**: Manage the bot with Telegram.
- [x] **Display profit/loss in fiat**: Display your profit/loss in fiat currency.
- [x] **Performance status report**: Provide a performance status of your current trades.

## Quick start

Please refer to the [Docker Quickstart documentation](https://www.freqtrade.io/en/stable/docker_quickstart/) on how to get started quickly.

For further (native) installation methods, please refer to the [Installation documentation page](https://www.freqtrade.io/en/stable/installation/).

## Basic Usage

### Bot commands

```
usage: freqtrade [-h] [-V]
                 {trade,create-userdir,new-config,show-config,new-strategy,download-data,convert-data,convert-trade-data,trades-to-ohlcv,list-data,backtesting,backtesting-show,backtesting-analysis,edge,hyperopt,hyperopt-list,hyperopt-show,list-exchanges,list-markets,list-pairs,list-strategies,list-hyperoptloss,list-freqaimodels,list-timeframes,show-trades,test-pairlist,convert-db,install-ui,plot-dataframe,plot-profit,webserver,strategy-updater,lookahead-analysis,recursive-analysis}
                 ...

Free, open source crypto trading bot

positional arguments:
  {trade,create-userdir,new-config,show-config,new-strategy,download-data,convert-data,convert-trade-data,trades-to-ohlcv,list-data,backtesting,backtesting-show,backtesting-analysis,edge,hyperopt,hyperopt-list,hyperopt-show,list-exchanges,list-markets,list-pairs,list-strategies,list-hyperoptloss,list-freqaimodels,list-timeframes,show-trades,test-pairlist,convert-db,install-ui,plot-dataframe,plot-profit,webserver,strategy-updater,lookahead-analysis,recursive-analysis}
    trade               Trade module.
    create-userdir      Create user-data directory.
    new-config          Create new config
    show-config         Show resolved config
    new-strategy        Create new strategy
    download-data       Download backtesting data.
    convert-data        Convert candle (OHLCV) data from one format to
                        another.
    convert-trade-data  Convert trade data from one format to another.
    trades-to-ohlcv     Convert trade data to OHLCV data.
    list-data           List downloaded data.
    backtesting         Backtesting module.
    backtesting-show    Show past Backtest results
    backtesting-analysis
                        Backtest Analysis module.
    hyperopt            Hyperopt module.
    hyperopt-list       List Hyperopt results
    hyperopt-show       Show details of Hyperopt results
    list-exchanges      Print available exchanges.
    list-markets        Print markets on exchange.
    list-pairs          Print pairs on exchange.
    list-strategies     Print available strategies.
    list-hyperoptloss   Print available hyperopt loss functions.
    list-freqaimodels   Print available freqAI models.
    list-timeframes     Print available timeframes for the exchange.
    show-trades         Show trades.
    test-pairlist       Test your pairlist configuration.
    convert-db          Migrate database to different system
    install-ui          Install FreqUI
    plot-dataframe      Plot candles with indicators.
    plot-profit         Generate plot showing profits.
    webserver           Webserver module.
    strategy-updater    updates outdated strategy files to the current version
    lookahead-analysis  Check for potential look ahead bias.
    recursive-analysis  Check for potential recursive formula issue.

options:
  -h, --help            show this help message and exit
  -V, --version         show program's version number and exit
```

### Telegram RPC commands

Telegram is not mandatory. However, this is a great way to control your bot. More details and the full command list on the [documentation](https://www.freqtrade.io/en/latest/telegram-usage/)

- `/start`: Starts the trader.
- `/stop`: Stops the trader.
- `/stopentry`: Stop entering new trades.
- `/status <trade_id>|[table]`: Lists all or specific open trades.
- `/profit [<n>]`: Lists cumulative profit from all finished trades, over the last n days.
- `/profit_long [<n>]`: Lists cumulative profit from all finished long trades, over the last n days.
- `/profit_short [<n>]`: Lists cumulative profit from all finished short trades, over the last n days.
- `/forceexit <trade_id>|all`: Instantly exits the given trade (Ignoring `minimum_roi`).
- `/fx <trade_id>|all`: Alias to `/forceexit`
- `/performance`: Show performance of each finished trade grouped by pair
- `/balance`: Show account balance per currency.
- `/daily <n>`: Shows profit or loss per day, over the last n days.
- `/help`: Show help message.
- `/version`: Show version.


## Development branches

The project is currently setup in two main branches:

- `develop` - This branch has often new features, but might also contain breaking changes. We try hard to keep this branch as stable as possible.
- `stable` - This branch contains the latest stable release. This branch is generally well tested.
- `feat/*` - These are feature branches, which are being worked on heavily. Please don't use these unless you want to test a specific feature.

## Support

### Help / Discord

For any questions not covered by the documentation or for further information about the bot, or to simply engage with like-minded individuals, we encourage you to join the Freqtrade [discord server](https://discord.gg/p7nuUNVfP7).

### [Bugs / Issues](https://github.com/freqtrade/freqtrade/issues?q=is%3Aissue)

If you discover a bug in the bot, please
[search the issue tracker](https://github.com/freqtrade/freqtrade/issues?q=is%3Aissue)
first. If it hasn't been reported, please
[create a new issue](https://github.com/freqtrade/freqtrade/issues/new/choose) and
ensure you follow the template guide so that the team can assist you as
quickly as possible.

For every [issue](https://github.com/freqtrade/freqtrade/issues/new/choose) created, kindly follow up and mark satisfaction or reminder to close issue when equilibrium ground is reached.

--Maintain github's [community policy](https://docs.github.com/en/site-policy/github-terms/github-community-code-of-conduct)--

### [Feature Requests](https://github.com/freqtrade/freqtrade/labels/enhancement)

Have you a great idea to improve the bot you want to share? Please,
first search if this feature was not [already discussed](https://github.com/freqtrade/freqtrade/labels/enhancement).
If it hasn't been requested, please
[create a new request](https://github.com/freqtrade/freqtrade/issues/new/choose)
and ensure you follow the template guide so that it does not get lost
in the bug reports.

### [Pull Requests](https://github.com/freqtrade/freqtrade/pulls)

Feel like the bot is missing a feature? We welcome your pull requests!

Please read the
[Contributing document](https://github.com/freqtrade/freqtrade/blob/develop/CONTRIBUTING.md)
to understand the requirements before sending your pull-requests.

Coding is not a necessity to contribute - maybe start with improving the documentation?
Issues labeled [good first issue](https://github.com/freqtrade/freqtrade/labels/good%20first%20issue) can be good first contributions, and will help get you familiar with the codebase.

**Note** before starting any major new feature work, *please open an issue describing what you are planning to do* or talk to us on [discord](https://discord.gg/p7nuUNVfP7) (please use the #dev channel for this). This will ensure that interested parties can give valuable feedback on the feature, and let others know that you are working on it.

**Important:** Always create your PR against the `develop` branch, not `stable`.

## Requirements

### Up-to-date clock

The clock must be accurate, synchronized to a NTP server very frequently to avoid problems with communication to the exchanges.

### Minimum hardware required

To run this bot we recommend you a cloud instance with a minimum of:

- Minimal (advised) system requirements: 2GB RAM, 1GB disk space, 2vCPU

### Software requirements

- [Python >= 3.11](http://docs.python-guide.org/en/latest/starting/installation/)
- [pip](https://pip.pypa.io/en/stable/installing/)
- [git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
- [TA-Lib](https://ta-lib.github.io/ta-lib-python/)
- [virtualenv](https://virtualenv.pypa.io/en/stable/installation.html) (Recommended)
- [Docker](https://www.docker.com/products/docker) (Recommended)
