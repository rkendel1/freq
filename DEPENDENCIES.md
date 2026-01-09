# Dependency Graph - Core Execution Paths

Generated: 2026-01-09
Updated: 2026-01-09 (Post RPC Removal)

This document maps the critical dependencies in the execution engine to ensure
we don't break core functionality during refactoring.

## Recent Changes (This PR)

### ✅ Completed Work
1. **RPC Module Completely Removed**
   - Removed all RPC imports from freqtradebot.py, worker.py, dataprovider.py
   - Created stub freqtrade/rpc/fiat_convert.py for test compatibility only
   - All rpc.send_msg() calls replaced with logging
   - RPCManager initialization removed from FreqtradeBot

2. **Stub Modules Created**
   - freqtrade/optimize/hyperopt_tools.py - Stub for HyperoptTools and HyperoptStateContainer
   - freqtrade/commands/analyze_commands.py - Stub for analyze functionality
   - freqtrade/commands/hyperopt_commands.py - Stub for hyperopt commands
   - freqtrade/commands/plot_commands.py - Stub for plotting commands
   - freqtrade/commands/pairlist_commands.py - Stub for pairlist testing
   - freqtrade/commands/webserver_commands.py - Stub for API/webserver

3. **Comprehensive Tests Added**
   - tests/core/test_risk.py - 7 tests for risk management
   - tests/core/test_state.py - 11 tests for capital state management
   - tests/exploits/test_exploit_module.py - 8 tests for ExploitModule interface
   - All 26 tests passing ✅

## Core Classes and Their Importers

### IStrategy (freqtrade/strategy/interface.py)
**Imported by:**
- freqtrade/freqtradebot.py - Main bot execution
- freqtrade/optimize/backtesting.py - Backtesting engine
- freqtrade/resolvers/strategy_resolver.py - Strategy loading
- freqtrade/strategy/__init__.py - Package exports

**Status:** FUTURE REFACTOR to ExploitModule interface (not blocking)
**Risk:** MEDIUM - Can coexist with ExploitModule for now

### FreqtradeBot (freqtrade/freqtradebot.py)
**Imported by:**
- freqtrade/worker.py - Main worker thread

**Status:** ✅ UPDATED - RPC coupling removed
**Risk:** LOW - Now uses logging instead of RPC
**Changes:**
- RPCManager removed
- All rpc.send_msg() calls replaced with logger.info/warning
- notify_status() now uses logging
- DataProvider no longer requires RPC parameter

### Trade (freqtrade/persistence/trade_model.py)
**Imported by:**
- freqtrade/commands/db_commands.py
- freqtrade/commands/list_commands.py
- freqtrade/core/state.py (NEW)
- freqtrade/exploits/example_exploit.py (NEW)
- freqtrade/exploits/exploit_module.py (NEW)
- freqtrade/freqtradebot.py
- freqtrade/leverage/liquidation_price.py
- freqtrade/persistence/*.py
- freqtrade/plugins/pairlist/FullTradesFilter.py
- freqtrade/plugins/pairlist/PerformanceFilter.py
- freqtrade/plugins/protections/*.py
- freqtrade/strategy/interface.py
- freqtrade/util/migrations/binance_mig.py
- freqtrade/wallets.py

**Status:** KEEP - Core persistence
**Risk:** LOW - Well isolated

### Order (freqtrade/persistence/trade_model.py)
**Imported by:**
- freqtrade/commands/db_commands.py
- freqtrade/exchange/exchange.py
- freqtrade/freqtradebot.py
- freqtrade/strategy/interface.py

**Status:** KEEP - Core persistence
**Risk:** LOW - Well isolated

### Wallets (freqtrade/wallets.py)
**Imported by:**
- freqtrade/freqtradebot.py
- freqtrade/leverage/liquidation_price.py
- freqtrade/optimize/backtesting.py
- freqtrade/strategy/interface.py

**Status:** KEEP - Core balance tracking
**Risk:** LOW - Well isolated

## New Core Modules (This PR)

### RiskManager (freqtrade/core/risk.py)
**Purpose:** Exploit-agnostic risk enforcement with hard bounds
**Imported by:**
- tests/core/test_risk.py
- (Future: FreqtradeBot for action validation)

**Status:** ✅ NEW - Tested and working
**Risk:** NONE - Isolated module with comprehensive tests

### CapitalState / ExecutionEngineState (freqtrade/core/state.py)
**Purpose:** Explicit capital tracking and state management
**Imported by:**
- tests/core/test_state.py
- (Future: FreqtradeBot for capital management)

**Status:** ✅ NEW - Tested and working
**Risk:** NONE - Isolated module with comprehensive tests

### ExploitModule (freqtrade/exploits/exploit_module.py)
**Purpose:** Strategy-agnostic intent interface
**Imported by:**
- freqtrade/core/risk.py - Uses Action type
- tests/exploits/test_exploit_module.py
- (Future: FreqtradeBot for action execution)

**Exports:**
- Action, ActionType, ExecutionState, ExecutionResult
- ExploitModule (abstract base)
- NullExploitModule (default implementation)

**Status:** ✅ NEW - Tested and working
**Risk:** NONE - Clean interface, NullExploitModule tested

## Deleted Modules and Their Impact

### freqtrade/rpc/ (✅ DELETED - Stubs created for compatibility)
**Was imported by:**
- freqtrade/freqtradebot.py - RPCManager usage ✅ REMOVED
- freqtrade/data/dataprovider.py - RPC message queue ✅ REMOVED
- freqtrade/worker.py - RPC cleanup ✅ REMOVED
- freqtrade/config_schema/config_schema.py - RPCMessageType ✅ REMOVED
- tests/conftest.py - fiat_convert mocking ✅ STUBBED

**Impact:** ✅ RESOLVED
**Changes Made:**
- Created stub freqtrade/rpc/fiat_convert.py for test compatibility
- All RPC functionality replaced with logging
- No RPC dependencies remain in production code

### freqtrade/freqai/ (DELETED)
**Was imported by:**
- freqtrade/strategy/interface.py (optional)

**Impact:** LOW - Already handled in previous PR

### freqtrade/plot/ (DELETED)
**Was imported by:**
- freqtrade/commands/ ✅ STUB CREATED (plot_commands.py)

**Impact:** ✅ RESOLVED with stub module

### freqtrade/optimize/hyperopt* (DELETED)
**Was imported by:**
- freqtrade/commands/ ✅ STUB CREATED (hyperopt_commands.py)
- freqtrade/strategy/hyper.py ✅ STUB CREATED (hyperopt_tools.py)
- freqtrade/strategy/parameters.py ✅ Uses stub

**Impact:** ✅ RESOLVED with stub modules

## Critical Execution Paths

### Path 1: Trade Execution Flow (✅ Updated)
```
worker.py 
  -> FreqtradeBot.__init__() [✅ No RPC]
  -> FreqtradeBot.process() [✅ Logs instead of RPC]
  -> FreqtradeBot.create_trade() [✅ Logs instead of RPC]
  -> exchange.create_order()
  -> Trade.add_order()
  -> persistence.save()
```

**Dependencies:**
- Exchange abstraction ✓ KEEP
- Trade model ✓ KEEP
- Persistence layer ✓ KEEP
- ✅ RPC removed - logs only

**Risks:**
- ✅ RPC notifications REMOVED (safe - uses logging)
- ⚠ Strategy signals (future refactor to ExploitModule)

### Path 2: Backtesting Flow
```
backtesting.py
  -> Backtesting.__init__()
  -> Backtesting.backtest()
  -> IStrategy.populate_*()
  -> Trade creation/management
```

**Dependencies:**
- Strategy interface ⚠ FUTURE REFACTOR
- Trade model ✓ KEEP
- Exchange mock ✓ KEEP

**Risks:**
- Strategy coupling ⚠ MEDIUM (future work)

### Path 3: Position Management (✅ Updated)
```
FreqtradeBot.handle_trade()
  -> IStrategy.should_exit()
  -> exchange.create_order()
  -> Trade.close() [✅ Logs instead of RPC]
  -> Wallets.update()
```

**Dependencies:**
- Strategy interface ⚠ FUTURE REFACTOR
- Trade model ✓ KEEP
- Wallets ✓ KEEP
- ✅ RPC removed - logs only

## Pairlist Dependencies (KEEP STATIC SUPPORT)

### Required Pairlist Components:
- freqtrade/plugins/pairlistmanager.py - Main manager
- freqtrade/plugins/pairlist/StaticPairList.py - Static universe
- freqtrade/plugins/pairlist/IPairList.py - Base interface

### Can Remove (Dynamic filters):
- AgeFilter, VolumePairList, PerformanceFilter, etc.

## Risk Assessment

### ✅ COMPLETED (This PR)
1. ✅ FreqtradeBot RPC removal
2. ✅ Import cleanup
3. ✅ Core module creation (risk.py, state.py)
4. ✅ ExploitModule interface implementation
5. ✅ Comprehensive testing

### FUTURE WORK (Not Blocking)
1. ⚠ IStrategy -> ExploitModule refactor (can coexist)
2. ⚠ Pairlist simplification
3. ⚠ Backtest engine refactor

### LOW RISK
1. ✓ Dependency updates
2. ✓ Dead code removal
3. ✓ Documentation

## Validation Status

### ✅ Tests Passing
- All imports work without RPC dependencies
- 26 new tests for core functionality all passing
- FreqtradeBot, Worker, DataProvider import successfully

### ✅ Architecture Validated
- Risk management tested with 7 test cases
- Capital state management tested with 11 test cases
- ExploitModule interface tested with 8 test cases including NullExploitModule

### ✅ No Security Vulnerabilities
- CodeQL scan: 0 alerts
- No RPC dependencies remain
- Clean separation of concerns

## Next Steps (Updated)

1. ✅ Document dependencies (this file)
2. ✅ Create core/risk.py for risk management
3. ✅ Create core/state.py for capital/state isolation
4. ✅ Create ExploitModule interface (Action-based)
5. ✅ Remove RPC from FreqtradeBot
6. ✅ Create comprehensive tests
7. ⏭ Update backtesting to use ExploitModule (future)
8. ⏭ Full IStrategy deprecation (future)
9. ✅ Architecture documented in ARCHITECTURE.md

