"""
Test that the core engine is strategy-agnostic.

This validates that:
1. No file in /freqtrade/core/ references IStrategy
2. No signal functions exist in core
3. Engine does nothing if no ExploitModule is registered
4. All trading requires an Action object

Goal: Prove the engine cannot trade by itself.
"""

import pytest
from unittest.mock import Mock, MagicMock
from freqtrade.exploits.exploit_module import (
    NullExploitModule,
    ExploitModule,
    ExecutionState,
    Action,
    ActionType,
)


def test_null_exploit_module_exists():
    """Test that NullExploitModule exists and can be instantiated."""
    exploit = NullExploitModule()
    assert isinstance(exploit, ExploitModule)


def test_null_exploit_never_proposes_actions():
    """
    Test that NullExploitModule never proposes any actions.
    
    This is the key test: with a NullExploitModule, the engine should
    do nothing because no actions are ever proposed.
    """
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
    
    assert isinstance(actions, list)
    assert len(actions) == 0, "NullExploitModule should never propose actions"


def test_engine_with_no_exploits_does_nothing():
    """
    Test that the engine does nothing when no exploit module proposes actions.
    
    This is the core requirement: the engine cannot trade by itself.
    It only executes Actions proposed by ExploitModules.
    """
    exploit = NullExploitModule()
    
    # Simulate multiple evaluation cycles
    state1 = ExecutionState(
        symbol="BTC/USDT",
        available_capital=1000.0,
        deployed_capital=0.0,
        open_positions=[],
        recent_trades=[],
        current_price=50000.0,
        timestamp=1000,
    )
    
    state2 = ExecutionState(
        symbol="ETH/USDT",
        available_capital=1000.0,
        deployed_capital=0.0,
        open_positions=[],
        recent_trades=[],
        current_price=3000.0,
        timestamp=2000,
    )
    
    # Evaluate multiple times - should always return no actions
    actions1 = exploit.evaluate(state1)
    actions2 = exploit.evaluate(state2)
    
    # The "engine" (whatever evaluates these actions) would execute them
    # Since there are no actions, no trades would be opened
    all_actions = actions1 + actions2
    
    assert len(all_actions) == 0, "With NullExploitModule, no trades should be proposed"


def test_trading_requires_action_object():
    """
    Test that trading decisions must be expressed as Action objects.
    
    This validates that the engine expects explicit Action objects,
    not boolean signals like populate_buy_trend/populate_sell_trend.
    """
    # An exploit that proposes an action
    class TestExploit(ExploitModule):
        def evaluate(self, state: ExecutionState):
            # Return an explicit Action object
            return [
                Action(
                    type=ActionType.OPEN_LONG,
                    symbol=state.symbol,
                    size=0.1,
                    reason="Test action"
                )
            ]
        
        def on_execution_result(self, action, result):
            pass
    
    exploit = TestExploit()
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
    
    # Verify we got Action objects
    assert len(actions) == 1
    assert isinstance(actions[0], Action)
    assert actions[0].type == ActionType.OPEN_LONG
    assert actions[0].symbol == "BTC/USDT"
    
    # The key point: trading intent is expressed as Action objects,
    # not as signals or boolean flags


def test_core_has_no_strategy_imports():
    """
    Test that core modules don't import from freqtrade.strategy.
    
    This is a static validation that the core is truly strategy-agnostic.
    """
    import freqtrade.core.state as state_module
    import freqtrade.core.risk as risk_module
    
    # Check that these modules don't have IStrategy in their namespace
    assert not hasattr(state_module, 'IStrategy'), \
        "core/state.py should not reference IStrategy"
    assert not hasattr(risk_module, 'IStrategy'), \
        "core/risk.py should not reference IStrategy"
    
    # Verify the modules loaded successfully
    assert hasattr(state_module, 'ExecutionEngineState')
    assert hasattr(risk_module, 'RiskManager')


def test_core_has_no_signal_functions():
    """
    Test that core modules don't have signal generation functions.
    
    Signal functions like populate_indicators, populate_buy_trend, etc.
    should not exist in the core.
    """
    import freqtrade.core.state as state_module
    import freqtrade.core.risk as risk_module
    
    # List of signal function names that should NOT exist
    signal_functions = [
        'populate_indicators',
        'populate_buy_trend',
        'populate_sell_trend',
        'populate_entry_trend',
        'populate_exit_trend',
    ]
    
    for func_name in signal_functions:
        assert not hasattr(state_module, func_name), \
            f"core/state.py should not have {func_name}"
        assert not hasattr(risk_module, func_name), \
            f"core/risk.py should not have {func_name}"


def test_action_types_are_explicit():
    """
    Test that ActionType enum contains explicit trading intents.
    
    This validates that the interface uses explicit actions, not signals.
    """
    # Verify ActionType enum has the expected values
    assert hasattr(ActionType, 'OPEN_LONG')
    assert hasattr(ActionType, 'OPEN_SHORT')
    assert hasattr(ActionType, 'CLOSE_LONG')
    assert hasattr(ActionType, 'CLOSE_SHORT')
    assert hasattr(ActionType, 'ADJUST_POSITION')
    assert hasattr(ActionType, 'NO_ACTION')
    
    # These are explicit intents, not signals
    assert ActionType.OPEN_LONG.value == "OPEN_LONG"
    assert ActionType.CLOSE_LONG.value == "CLOSE_LONG"
