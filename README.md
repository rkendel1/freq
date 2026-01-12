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
- ✅ Open the platform at http://127.0.0.1:5000

📖 **[Complete Local Development Guide](LOCAL_DEVELOPMENT.md)** - Full setup instructions, troubleshooting, and development workflow

---

## 🎯 Demo UI - See It In Action

**Interactive demo with TWO modes:**

```bash
# Quick start - just run this script
./start_demo.sh         # Linux/Mac
./start_demo.ps1        # Windows

# Then open your browser to:
# http://127.0.0.1:5000
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

## 🔧 Production Dashboards

**NEW: Production-ready Streamlit dashboards for configuration and monitoring**

### ⚙️ Configuration Dashboard

Secure interface to manage `config.prod.json` with:
- 🎯 **Dynamic ExploitModule discovery** - Auto-detect and select modules
- 🔌 **Full CCXT exchange support** - All CEX and DEX venues (Binance, Hyperliquid, etc.)
- 🛡️ **Risk limits configuration** - Position sizes, exposure, stop losses
- 💰 **Capital management** - Set initial capital and stake currency
- 🔑 **API credentials** - Secure input for exchange keys
- 🔒 **Password protection** - Environment-based authentication

![Configuration Dashboard](https://github.com/user-attachments/assets/7c833cc3-cc7c-4c00-a3e7-13202473834d)

**Run:**
```bash
# Set password (optional but recommended)
export STREAMLIT_PASSWORD=your_secure_password

# Start configuration dashboard
streamlit run freqtrade/ui/prod_config.py

# Access at: http://localhost:8501
```

**Install dependencies:**
```bash
pip install streamlit plotly pandas
```

### 📊 Monitoring Dashboard

Real-time production monitoring with:
- 💰 **Capital state overview** - Available, deployed, total with PnL metrics
- 📊 **Open positions table** - Live position tracking from database
- 📋 **Recent orders** - Order history and status
- 📈 **Cumulative PnL chart** - Visual profit/loss over time
- 📜 **Live logs** - Tail of production log file
- 🔄 **Auto-refresh** - Updates every 10 seconds

![Monitoring Dashboard](https://github.com/user-attachments/assets/6a469d6d-6834-415f-b87d-536cbf8e0c5b)

**Run:**
```bash
# Start monitoring dashboard
streamlit run freqtrade/ui/prod_monitor.py

# Access at: http://localhost:8502
```

**Features:**
- ✅ **No dependencies on running engine** - Reads directly from SQLite DB
- ✅ **Production-safe** - Read-only access to database and logs
- ✅ **CCXT agnostic** - Works with any exchange
- ✅ **Module agnostic** - Shows results regardless of ExploitModules used

**Security Notes:**
- 🔒 Set `STREAMLIT_PASSWORD` environment variable for config dashboard
- 🚫 Do not expose dashboards to public internet without additional authentication
- 📁 Use firewall rules to restrict access to localhost or trusted IPs
- 🔐 API credentials in config are masked in the UI

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
- [docs/dspy.md](docs/dspy.md) - DSPy LM-based insights for external analysis

## Analysis Tools

### DSPy LM-Based Insights (External)

Generate manual insights and parameter adjustment suggestions using a local LLM:

```bash
# Install dependencies
pip install dspy-ai ollama

# Run Ollama
ollama run llama3.2

# Generate insights from metrics
python analysis/dspy_insights.py
```

**Key features:**
- Uses local LLM (Ollama) for privacy and zero cost
- Analyzes deployed capital, PnL, Sharpe ratio, win rate
- Outputs manual adjustment suggestions
- **External only** - NO automatic application to engine
- **Manual review required** - suggestions are logged only

📖 **[Complete DSPy Setup Guide](docs/dspy.md)**

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

---

## 🐳 Docker Quick Start - All-in-One Development Environment

**Single-container setup with demo UI, configuration dashboard, and monitoring dashboard.**

### Quick Start (One Command)

```bash
# Clone repository
git clone https://github.com/rkendel1/freq.git
cd freq

# Start everything with Docker Compose
docker compose -f docker-compose.dev.yml up

# Or build and start in one command
docker compose -f docker-compose.dev.yml up --build
```

**That's it!** After a few moments, you'll have:

- **Demo UI**: http://localhost:5000 - Interactive execution engine demo
- **Configuration Dashboard**: http://localhost:8501 - Manage configs, ExploitModules, exchanges
- **Monitoring Dashboard**: http://localhost:8502 - Real-time position tracking, PnL, logs

### What You Get

✅ **Auto-initialization** - Directories, config, and database created automatically  
✅ **No manual setup** - Everything configured out-of-the-box  
✅ **Persistent data** - Volume-mounted `user_data/` directory  
✅ **Multi-process** - All services running via supervisor  
✅ **QuestDB-ready** - Prepared for time-series metrics (optional)  

### Environment Variables

Set these in `docker/.env` or pass via `-e`:

```bash
# Security (RECOMMENDED)
STREAMLIT_PASSWORD=your_secure_password

# Configuration
DRY_RUN=true                    # Safe mode (default)
INITIAL_CAPITAL=10000.0         # Starting capital
EXCHANGE_NAME=binance           # Any CCXT exchange
LOG_LEVEL=INFO                  # DEBUG, INFO, WARNING, ERROR
```

### Custom ExploitModules

Mount your custom modules:

```yaml
# In docker-compose.dev.yml, add volume:
volumes:
  - ./user_data:/freqtrade/user_data
  - ./my_exploits:/freqtrade/custom_exploits:ro
```

Or copy them to `user_data/exploits/` - they'll be auto-discovered by the config dashboard.

### Docker Commands Reference

```bash
# Start services
docker compose -f docker-compose.dev.yml up

# Start in background
docker compose -f docker-compose.dev.yml up -d

# View logs
docker compose -f docker-compose.dev.yml logs -f

# Stop services
docker compose -f docker-compose.dev.yml down

# Rebuild after code changes
docker compose -f docker-compose.dev.yml up --build

# Access shell in container
docker compose -f docker-compose.dev.yml exec freqtrade-dev /bin/bash
```

### Data Persistence

All data is stored in `./user_data/`:
- `config.prod.json` - Configuration
- `tradesv3.sqlite` - Trade database
- `logs/` - Application logs
- `exploits/` - Custom ExploitModules
- `strategies/` - Custom strategies (if using)

The directory is created automatically on first run with sensible defaults.

### Troubleshooting

**Q: Port already in use?**  
Change ports in `docker-compose.dev.yml` under the `ports:` section.

**Q: How to enable QuestDB?**  
Uncomment the `questdb` service in `docker-compose.dev.yml`.

**Q: Services not starting?**  
Check logs: `docker compose -f docker-compose.dev.yml logs`

**Q: Need to run a single service?**  
See supervisor logs inside container: `docker compose -f docker-compose.dev.yml exec freqtrade-dev tail -f /var/log/supervisor/*.log`

### Development Mode

For active development, mount source code:

```yaml
volumes:
  - ./user_data:/freqtrade/user_data
  - ./freqtrade:/freqtrade/freqtrade:ro  # Read-only source mount
```

Then use `docker compose restart` to pick up changes.

📖 **More details**: See [docker/README.md](docker/README.md) for advanced Docker usage.

---
## Available Commands

### Core Commands (Functional)

```bash
# Trading
freqtrade trade --config config.prod.json         # Run trading engine

# Configuration
freqtrade create-userdir --userdir user_data      # Create user directory structure
freqtrade new-config --config config.json         # Interactive config generator
freqtrade show-config --config config.json        # Display resolved configuration

# Data Management
freqtrade download-data --exchange binance --pairs BTC/USDT ETH/USDT
freqtrade list-data --datadir user_data/data
freqtrade convert-data --format-from json --format-to feather

# Exchange Information
freqtrade list-exchanges                          # Show supported exchanges
freqtrade list-markets --exchange binance         # Show available markets
freqtrade list-pairs --exchange binance           # Show tradable pairs
freqtrade list-timeframes --exchange binance      # Show available timeframes

# Database
freqtrade show-trades --db-url sqlite:///tradesv3.sqlite
freqtrade convert-db --from-url sqlite:///old.db --to-url sqlite:///new.db

# Backtesting (Price Replay Only)
freqtrade backtesting --config config.json --strategy-path exploits/
freqtrade backtesting-show                        # Show backtest results
freqtrade backtesting-analysis                    # Analyze backtest results
```

### Legacy Commands (Not Functional - Raise NotImplementedError)

These commands still appear in help but are **removed** and will fail:

- ❌ `hyperopt` / `hyperopt-list` / `hyperopt-show` - Optimization removed
- ❌ `list-hyperoptloss` - Hyperopt removed
- ❌ `list-freqaimodels` - FreqAI removed
- ❌ `install-ui` - FreqUI removed (use Streamlit dashboards instead)
- ❌ `plot-dataframe` / `plot-profit` - Plotting removed
- ❌ `webserver` - API server removed
- ❌ `test-pairlist` - Pairlist testing removed
- ❌ `lookahead-analysis` / `recursive-analysis` - Analysis tools removed
- ❌ `edge` - Edge module removed

### Recommended Workflow

**Local Development:**
```bash
./start.sh              # Demo UI at http://localhost:5000
```

**Production Dashboards:**
```bash
streamlit run freqtrade/ui/prod_config.py     # Port 8501
streamlit run freqtrade/ui/prod_monitor.py    # Port 8502
```

**Docker (All-in-One):**
```bash
docker compose -f docker-compose.dev.yml up   # All services
```

---


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
