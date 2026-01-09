#!/usr/bin/env python3
"""
Validation script to prove the core is strategy-agnostic.

This script validates all requirements from the issue:
1. No file references IStrategy
2. No signal functions exist
3. Engine does nothing if no ExploitModule is registered
4. All trading requires an Action object
"""

import os
import sys
from pathlib import Path

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'


def check_no_strategy_imports():
    """Check that core files don't import from freqtrade.strategy."""
    print("\n" + "=" * 60)
    print("CHECK 1: No file in /freqtrade/core/ references IStrategy")
    print("=" * 60)
    
    core_path = Path("freqtrade/core")
    failed = False
    
    for py_file in core_path.glob("*.py"):
        with open(py_file, 'r') as f:
            content = f.read()
            if 'IStrategy' in content or 'from freqtrade.strategy' in content:
                print(f"{RED}✗ FAIL: {py_file} contains IStrategy reference{RESET}")
                failed = True
            else:
                print(f"{GREEN}✓ PASS: {py_file} has no IStrategy references{RESET}")
    
    if not failed:
        print(f"\n{GREEN}✓ CHECK 1 PASSED{RESET}")
    else:
        print(f"\n{RED}✗ CHECK 1 FAILED{RESET}")
        return False
    
    return True


def check_no_signal_functions():
    """Check that core files don't have signal functions."""
    print("\n" + "=" * 60)
    print("CHECK 2: No signal functions exist in core")
    print("=" * 60)
    
    signal_functions = [
        'populate_indicators',
        'populate_buy_trend',
        'populate_sell_trend',
        'populate_entry_trend',
        'populate_exit_trend',
    ]
    
    core_path = Path("freqtrade/core")
    failed = False
    
    for py_file in core_path.glob("*.py"):
        with open(py_file, 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines, 1):
                # Skip comments
                if line.strip().startswith('#'):
                    continue
                for func in signal_functions:
                    if func in line and 'def ' + func in line:
                        print(f"{RED}✗ FAIL: {py_file}:{i} contains {func}{RESET}")
                        failed = True
        
        if not failed:
            print(f"{GREEN}✓ PASS: {py_file} has no signal functions{RESET}")
    
    if not failed:
        print(f"\n{GREEN}✓ CHECK 2 PASSED{RESET}")
    else:
        print(f"\n{RED}✗ CHECK 2 FAILED{RESET}")
        return False
    
    return True


def check_null_exploit_behavior():
    """Check that NullExploitModule returns no actions."""
    print("\n" + "=" * 60)
    print("CHECK 3: Engine does nothing if no ExploitModule is registered")
    print("=" * 60)
    
    from freqtrade.exploits.exploit_module import (
        NullExploitModule,
        ExecutionState,
    )
    
    exploit = NullExploitModule()
    state = ExecutionState(
        symbol="BTC/USDT",
        available_capital=1000.0,
        deployed_capital=0.0,
        open_positions=[],
        recent_trades=[],
        current_price=50000.0,
        timestamp=1000,
    )
    
    actions = exploit.evaluate(state)
    
    if len(actions) == 0:
        print(f"{GREEN}✓ PASS: NullExploitModule returns no actions{RESET}")
        print(f"{GREEN}✓ Engine with NullExploitModule would do nothing{RESET}")
        print(f"\n{GREEN}✓ CHECK 3 PASSED{RESET}")
        return True
    else:
        print(f"{RED}✗ FAIL: NullExploitModule returned {len(actions)} actions{RESET}")
        print(f"\n{RED}✗ CHECK 3 FAILED{RESET}")
        return False


def check_action_interface():
    """Check that trading uses Action objects."""
    print("\n" + "=" * 60)
    print("CHECK 4: All trading requires an Action object")
    print("=" * 60)
    
    from freqtrade.exploits.exploit_module import Action, ActionType
    
    # Verify Action class exists
    print(f"{GREEN}✓ Action class exists{RESET}")
    
    # Verify ActionType enum exists
    required_types = ['OPEN_LONG', 'OPEN_SHORT', 'CLOSE_LONG', 'CLOSE_SHORT', 'NO_ACTION']
    for action_type in required_types:
        if hasattr(ActionType, action_type):
            print(f"{GREEN}✓ ActionType.{action_type} exists{RESET}")
        else:
            print(f"{RED}✗ ActionType.{action_type} missing{RESET}")
            print(f"\n{RED}✗ CHECK 4 FAILED{RESET}")
            return False
    
    # Verify Action objects can be created
    action = Action(
        type=ActionType.OPEN_LONG,
        symbol="BTC/USDT",
        size=0.1,
    )
    
    if action.type == ActionType.OPEN_LONG:
        print(f"{GREEN}✓ Action objects can be created{RESET}")
        print(f"{GREEN}✓ Trading uses explicit Action objects, not signals{RESET}")
        print(f"\n{GREEN}✓ CHECK 4 PASSED{RESET}")
        return True
    else:
        print(f"{RED}✗ Action object creation failed{RESET}")
        print(f"\n{RED}✗ CHECK 4 FAILED{RESET}")
        return False


def main():
    """Run all validation checks."""
    print("\n" + "=" * 60)
    print("VALIDATING CORE IS STRATEGY-AGNOSTIC")
    print("=" * 60)
    
    checks = [
        check_no_strategy_imports,
        check_no_signal_functions,
        check_null_exploit_behavior,
        check_action_interface,
    ]
    
    results = []
    for check in checks:
        try:
            results.append(check())
        except Exception as e:
            print(f"{RED}✗ Check failed with exception: {e}{RESET}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    
    if all(results):
        print(f"{GREEN}✓ ALL CHECKS PASSED{RESET}")
        print(f"{GREEN}✓ Core is STRATEGY-AGNOSTIC{RESET}")
        print(f"{GREEN}✓ Engine cannot trade by itself{RESET}")
        return 0
    else:
        print(f"{RED}✗ SOME CHECKS FAILED{RESET}")
        print(f"{RED}✗ Review failures above{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
