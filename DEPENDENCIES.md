# Dependency Graph - Core Execution Paths

Generated: 2026-01-09

This document maps the critical dependencies in the execution engine to ensure
we don't break core functionality during refactoring.

## Core Classes and Their Importers

### IStrategy (freqtrade/strategy/interface.py)
**Imported by:**
- freqtrade/freqtradebot.py - Main bot execution
- freqtrade/optimize/backtesting.py - Backtesting engine
- freqtrade/resolvers/strategy_resolver.py - Strategy loading
- freqtrade/strategy/__init__.py - Package exports

**Status:** MUST REFACTOR to ExploitModule interface
**Risk:** HIGH - Central to execution flow

### FreqtradeBot (freqtrade/freqtradebot.py)
**Imported by:**
- freqtrade/worker.py - Main worker thread

**Status:** KEEP - Core execution engine
**Risk:** MEDIUM - Must remove RPC/strategy coupling

### Trade (freqtrade/persistence/trade_model.py)
**Imported by:**
- freqtrade/commands/db_commands.py
- freqtrade/commands/list_commands.py
- freqtrade/data/btanalysis/bt_fileutils.py
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

## Deleted Modules and Their Impact

### freqtrade/rpc/ (DELETED)
**Was imported by:**
- freqtrade/freqtradebot.py - RPCManager usage
- freqtrade/data/dataprovider.py - RPC message queue
- freqtrade/worker.py - RPC cleanup

**Impact:** MEDIUM
**Required Changes:**
- Remove RPCManager from FreqtradeBot.__init__
- Remove rpc.send_msg() calls
- Remove notify_status() method or stub it
- Remove RPC types from enums

### freqtrade/freqai/ (DELETED)
**Was imported by:**
- freqtrade/strategy/interface.py (optional)

**Impact:** LOW
**Required Changes:**
- Remove freqai imports from strategy interface

### freqtrade/plot/ (DELETED)
**Was imported by:**
- freqtrade/commands/ (plot commands - also deleted)

**Impact:** NONE

### freqtrade/optimize/hyperopt* (DELETED)
**Was imported by:**
- freqtrade/commands/ (hyperopt commands - also deleted)

**Impact:** NONE

## Critical Execution Paths

### Path 1: Trade Execution Flow
```
worker.py 
  -> FreqtradeBot.__init__()
  -> FreqtradeBot.process()
  -> FreqtradeBot.create_trade()
  -> exchange.create_order()
  -> Trade.add_order()
  -> persistence.save()
```

**Dependencies:**
- Exchange abstraction ✓ KEEP
- Trade model ✓ KEEP
- Persistence layer ✓ KEEP

**Risks:**
- RPC notifications ✗ REMOVED (safe - not critical)
- Strategy signals ⚠ MUST REFACTOR

### Path 2: Backtesting Flow
```
backtesting.py
  -> Backtesting.__init__()
  -> Backtesting.backtest()
  -> IStrategy.populate_*()
  -> Trade creation/management
```

**Dependencies:**
- Strategy interface ⚠ MUST REFACTOR
- Trade model ✓ KEEP
- Exchange mock ✓ KEEP

**Risks:**
- Strategy coupling ⚠ HIGH

### Path 3: Position Management
```
FreqtradeBot.handle_trade()
  -> IStrategy.should_exit()
  -> exchange.create_order()
  -> Trade.close()
  -> Wallets.update()
```

**Dependencies:**
- Strategy interface ⚠ MUST REFACTOR
- Trade model ✓ KEEP
- Wallets ✓ KEEP

## Pairlist Dependencies (KEEP STATIC SUPPORT)

### Required Pairlist Components:
- freqtrade/plugins/pairlistmanager.py - Main manager
- freqtrade/plugins/pairlist/StaticPairList.py - Static universe
- freqtrade/plugins/pairlist/IPairList.py - Base interface

### Can Remove (Dynamic filters):
- AgeFilter, VolumePairList, PerformanceFilter, etc.

## Risk Assessment

### HIGH RISK
1. IStrategy -> ExploitModule refactor
2. FreqtradeBot RPC removal
3. Signal -> Intent conversion

### MEDIUM RISK
1. Pairlist simplification
2. Command cleanup
3. Import cleanup

### LOW RISK
1. Dependency updates
2. Dead code removal
3. Documentation

## Next Steps (In Order)

1. ✅ Document dependencies (this file)
2. ⏭ Create core/risk.py for risk management
3. ⏭ Create core/state.py for capital/state isolation
4. ⏭ Refactor ExploitModule interface to Action-based
5. ⏭ Remove RPC from FreqtradeBot
6. ⏭ Update backtesting to use ExploitModule
7. ⏭ Create no-strategy test
8. ⏭ Create ARCHITECTURE.md
