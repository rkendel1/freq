# Remaining Work - Critical Path to Completion

## Status: Phase 5-9 Remaining

We've completed the foundational work:
- ✅ Deleted non-essential modules
- ✅ Created core/risk.py and core/state.py
- ✅ Created ExploitModule interface (Action-based)
- ✅ Updated dependencies
- ✅ Documented architecture

## Critical Path Forward

### 1. Remove RPC Dependencies from FreqtradeBot (HIGH PRIORITY)

**File:** `freqtrade/freqtradebot.py`

**Required Changes:**
```python
# Remove imports:
- from freqtrade.rpc import RPCManager
- from freqtrade.rpc.external_message_consumer import ExternalMessageConsumer  
- from freqtrade.rpc.rpc_types import (...)

# Remove from __init__:
- self.rpc: RPCManager = RPCManager(self)
- Pass rpc to DataProvider

# Remove/stub methods:
- notify_status() → stub or remove
- All rpc.send_msg() calls → remove or log instead

# Remove enum:
- RPCMessageType from freqtrade/enums/
```

**Impact:** MEDIUM - Many rpc.send_msg() calls throughout

**Strategy:** Replace with logging instead of notifications

### 2. Fix Broken Imports Throughout Codebase

**Files with RPC imports:**
- freqtrade/worker.py
- freqtrade/data/dataprovider.py
- freqtrade/commands/* (some may reference RPC)

**Strategy:** Remove or stub RPC usage

### 3. Simplify Command Structure (OPTIONAL BUT RECOMMENDED)

**Keep:**
- trade_commands.py (core)
- data_commands.py (needed for backtesting)
- list_commands.py (utility)
- db_commands.py (utility)

**Already Deleted:**
- hyperopt_commands.py ✅
- plot_commands.py ✅
- webserver_commands.py ✅
- analyze_commands.py ✅
- pairlist_commands.py ✅
- deploy_ui.py ✅

### 4. Update Pairlist System to Keep Static Only

**File:** `freqtrade/plugins/pairlistmanager.py`

**Keep:**
- StaticPairList (essential)
- Basic filtering if needed

**Remove:** 
- Dynamic pairlists (Volume, Performance, etc.)
- Complex filters

**Status:** DEFER - Not blocking, pairlist system mostly works

### 5. Create Minimal Tests

**Required Tests:**
```
tests/core/
  test_risk.py - Test risk limits enforcement
  test_state.py - Test capital accounting

tests/exploits/
  test_exploit_module.py - Test interface
  test_null_exploit.py - Test NullExploitModule

tests/integration/
  test_no_strategy.py - Engine with NullExploitModule does nothing
  test_position_lifecycle.py - Open/hold/close/PnL
```

### 6. Update README

**New README should explain:**
- This is infrastructure, not a bot
- How to implement ExploitModule
- How to configure
- What was removed
- Link to ARCHITECTURE.md

## Minimal Viable Product (MVP)

To consider this "done", we need:

1. **FreqtradeBot compiles** without RPC imports ✓
2. **Worker can start** without crashing ✓
3. **NullExploitModule test** passes (engine does nothing) ✓
4. **Basic position test** passes (can open/close trade) ✓
5. **README updated** to reflect new purpose ✓

## Non-Blocking Items (Can Defer)

These can be done later without blocking the core refactor:

- Full pairlist cleanup
- Strategy removal (keep IStrategy for now, mark deprecated)
- Complete test coverage
- Backtest engine refactor
- Remove all old strategy files from tests/

## Estimated Effort

**High Priority (Must Do):**
- Remove RPC from FreqtradeBot: 2-3 hours
- Fix broken imports: 1-2 hours
- Create minimal tests: 1-2 hours
- Update README: 30 minutes

**Total MVP:** ~6 hours of focused work

**Nice to Have (Optional):**
- Pairlist cleanup: 1 hour
- Complete strategy removal: 3-4 hours
- Full test coverage: 4-6 hours

## Risk Areas

1. **RPC removal** - Many call sites, easy to miss one
2. **Import chains** - One broken import can cascade
3. **Tests** - Existing tests expect RPC/strategy system

## Mitigation

1. Use grep to find all RPC references
2. Test imports with: `python -m py_compile freqtrade/*.py`
3. Accept that many old tests will break (that's OK)
4. Focus on new tests for new architecture

## Next Steps (In Order)

1. Remove RPC from FreqtradeBot
2. Fix worker.py imports
3. Fix dataprovider.py imports
4. Test basic imports work
5. Create NullExploitModule test
6. Create position lifecycle test
7. Update README
8. Declare MVP complete

## Decision Point

**Should we:**
A. Complete MVP only (6 hours, basic functionality)
B. Full cleanup (15+ hours, everything perfect)

**Recommendation:** Start with MVP (A), validate it works, then iterate.

The goal is a working execution engine, not perfection.
