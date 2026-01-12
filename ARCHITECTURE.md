# Architecture - MYCELIUM Execution Engine

## Overview

MYCELIUM is a **minimal, deterministic execution engine** stripped down from Freqtrade. 
It is **strategy-agnostic** and **infrastructure-focused**.

**What this is:**
- Order execution engine
- Position tracking system
- PnL attribution
- Exchange abstraction layer
- Risk management primitives
- Backtesting/simulation framework

**What this is NOT:**
- A trading bot
- A strategy framework
- An indicator library
- A machine learning system
- A retail trading platform

## Core Philosophy

### Intent → Execution Separation

The engine follows a strict separation:

```
Exploit Module → Intent (Action) → Risk Check → Execution → Result
```

1. **Exploit Module** generates intent (Actions)
2. **Risk Manager** validates actions against hard bounds
3. **Execution Engine** executes approved actions deterministically
4. **Results** flow back to exploit for telemetry

**The engine NEVER:**
- Decides when to trade
- Infers intent from signals
- Generates trading signals
- Makes strategy decisions

**The engine ONLY:**
- Executes explicit actions
- Tracks positions and capital
- Enforces risk limits
- Records results

### Capital & State Isolation

All capital and state is **explicit** and **immutable**:

- No global mutable capital
- All state changes are tracked
- Capital accounting is validated
- Positions are explicitly managed

State structure:
```python
ExecutionEngineState:
  capital:
    - available_capital
    - deployed_capital
    - reserved_capital
    - pnl_realized
    - pnl_unrealized
  open_trades: [...]
  closed_trades: [...]
  cooldowns: {...}
```

## Module Structure

### `/freqtrade/core/` - Execution Infrastructure

Core execution primitives:
- `risk.py` - Risk management with hard bounds only
- `state.py` - Capital and state isolation

**These modules:**
- Are exploit-agnostic
- Enforce deterministic behavior
- Provide clean interfaces
- Have no strategy logic

### `/freqtrade/exploits/` - Intent Providers (Empty)

This module is **intentionally empty**. It's designed to hold custom trading logic 
that sits **on top of** the execution engine.

**Exploit modules:**
- Generate intent (Actions)
- Receive telemetry (ExecutionResults)
- Can connect to external systems (DSPy, MYCELIUM, etc.)
- Are completely decoupled from execution

**Example implementations:**
- `exploit_module.py` - Base interface
- `example_exploit.py` - Stub implementation

### `/freqtrade/exchange/` - Exchange Abstraction

Exchange connectors and utilities:
- Order placement
- Position queries
- Balance management
- Market data

**Kept clean of:**
- Strategy logic
- Signal generation
- Indicator calculations

### `/freqtrade/persistence/` - State Persistence

Database models and persistence:
- `Trade` - Position lifecycle
- `Order` - Order tracking
- Key-value store
- Migrations

### `/freqtrade/optimize/` - Backtesting Only

Backtesting engine for replay:
- `backtesting.py` - Price replay engine
- `optimize_reports/` - Result reporting

**Removed:**
- Hyperparameter optimization
- Strategy optimization
- Machine learning features
- Analysis tools

## Key Interfaces

### Action (Intent)

```python
@dataclass
class Action:
    type: ActionType  # OPEN_LONG, CLOSE_SHORT, etc.
    symbol: str
    size: Optional[float]
    reason: Optional[str]
    metadata: Optional[dict]
    stop_loss: Optional[float]
    take_profit: Optional[float]
```

### ExecutionState (Telemetry)

```python
@dataclass
class ExecutionState:
    symbol: str
    available_capital: float
    deployed_capital: float
    open_positions: list[Trade]
    recent_trades: list[Trade]
    current_price: float
    timestamp: int
    dataframe: Optional[DataFrame]  # Optional market data
```

### ExecutionResult (Outcome)

```python
@dataclass
class ExecutionResult:
    success: bool
    order_ids: list[str]
    filled_size: float
    fees: float
    timestamp: int
    error_message: Optional[str]
```

### ExploitModule (Intent Provider)

```python
class ExploitModule(ABC):
    def evaluate(self, state: ExecutionState) -> list[Action]:
        """Return zero or more Actions to execute."""
        
    def on_execution_result(self, action: Action, result: ExecutionResult) -> None:
        """Handle execution result (for telemetry/learning)."""
```

## What Was Removed

### Deleted Modules
- ✅ FreqAI (ML/AI features)
- ✅ Plotting (visualization)
- ✅ RPC/API/Telegram (communication)
- ✅ Hyperopt (optimization)
- ✅ Strategy templates
- ✅ Analysis tools
- ✅ Web UI client

### Deleted Dependencies
- ✅ TA-Lib (technical indicators)
- ✅ ft-pandas-ta (indicators)
- ✅ technical (indicators)
- ✅ python-telegram-bot
- ✅ FastAPI / uvicorn / websockets
- ✅ scipy / scikit-learn / optuna (ML/optimization)
- ✅ plotly (plotting)
- ✅ LightGBM / XGBoost (ML)
- ✅ torch / stable-baselines3 (RL)

### Kept Dependencies
- ✅ ccxt (exchange connectivity)
- ✅ SQLAlchemy (persistence)
- ✅ pandas / numpy (data handling)
- ✅ requests / aiohttp (networking)
- ✅ cryptography (security)

## Integration with External Systems

### DSPy Integration (Out of Scope)

DSPy sits **outside** this core. It would:
- Call ExploitModule.evaluate() with state
- Receive ExecutionResults for learning
- Make decisions externally
- Feed Actions back in

```
DSPy → ExploitModule → Actions → Engine → Results → DSPy
```

### MYCELIUM Exploits (Future)

MYCELIUM micro-exploits would implement ExploitModule:
- Each exploit is independent
- Exploits share telemetry via ExecutionResults
- Capital is explicitly managed
- No hidden state coupling

## Risk Management

Risk is enforced **before execution**, not during signal generation:

```python
RiskLimits:
  - max_position_size: 10%
  - max_total_exposure: 95%
  - max_open_positions: 3
  - max_loss_per_trade: 10%
  - max_daily_loss: 20%
  - position_cooldown: 0s
  - global_cooldown: 0s
```

All risk checks happen in `core/risk.py`, independently of exploits.

## Deterministic Behavior

The engine is **fully deterministic**:
- No randomness
- No sampling
- No ML inference (that's in exploits)
- Config-driven only

All parameters come from config, not code.

## Testing Requirements

### Required Tests
1. **No-Strategy Test** - Engine runs with NullExploitModule and does nothing
2. **Position Lifecycle** - Open → Hold → Close → PnL recorded
3. **Risk Enforcement** - Actions rejected when limits exceeded
4. **State Isolation** - Capital accounting is consistent
5. **Deterministic Replay** - Same inputs → same outputs

### Test Structure
```
tests/
  core/
    test_risk.py
    test_state.py
  exploits/
    test_exploit_module.py
  integration/
    test_position_lifecycle.py
    test_no_strategy.py
```

## Future Extensions

When you're ready to add trading logic:

1. **Implement ExploitModule**
   ```python
   class MyExploit(ExploitModule):
       def evaluate(self, state):
           # Your logic here
           return [Action(...)]
   ```

2. **Configure the engine**
   ```json
   {
     "exploit_module": "my_module.MyExploit",
     "max_position_size": 0.1,
     "max_open_trades": 3
   }
   ```

3. **Run**
   ```bash
   freqtrade trade --config config.json
   ```

The engine handles the rest.

## What Success Looks Like

After this refactor:
- ✅ No strategy logic driving trades
- ✅ Execution engine is invoked programmatically
- ✅ Trades can be simulated deterministically
- ✅ MYCELIUM exploits can plug in cleanly
- ✅ DSPy can sit outside this core
- ✅ Engine runs with zero exploits and does nothing
- ✅ All parameters come from config
- ✅ Capital is explicitly tracked
- ✅ Risk is enforced uniformly

## Comparison: Before vs After

| Aspect | Before | After |
|--------|--------|-------|
| **Decision Making** | Strategy class | ExploitModule (external) |
| **Signal Type** | boolean flags | Explicit Actions |
| **Capital** | Implicit/global | Explicit state |
| **Risk** | Strategy-aware | Hard bounds only |
| **Indicators** | Built-in TA-Lib | None (exploit's job) |
| **UI/API** | Full REST/WebSocket | None |
| **Optimization** | Hyperopt/ML | None |
| **Testing** | Strategy-dependent | Deterministic |

## Questions?

This is **infrastructure**, not a trading system.

If you want to:
- Add indicators → implement in your ExploitModule
- Optimize parameters → use external DSPy
- Run ML → feed Actions from your model
- Use TradingView → write an exploit that reads TV signals
- Add alpha → implement ExploitModule

The engine just executes. You provide the intent.
