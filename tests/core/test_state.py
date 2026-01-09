"""
Tests for the state management module.

Tests that capital accounting is properly tracked and validated.
"""

import pytest
from datetime import datetime
from freqtrade.core.state import CapitalState, ExecutionEngineState, create_initial_state


def test_capital_state_creation():
    """Test that capital state can be created with valid values."""
    state = CapitalState(
        available=1000.0,
        deployed=0.0,
    )
    assert state.available == 1000.0
    assert state.deployed == 0.0
    assert state.pnl_realized == 0.0
    assert state.pnl_unrealized == 0.0
    assert state.cooldowns == {}


def test_capital_state_allocate():
    """Test that capital can be allocated from available to deployed."""
    state = CapitalState(
        available=1000.0,
        deployed=0.0,
    )

    # Allocate 100
    success = state.allocate(100.0)
    assert success is True
    assert state.available == 900.0
    assert state.deployed == 100.0


def test_capital_state_allocate_insufficient():
    """Test that allocation fails when insufficient capital available."""
    state = CapitalState(
        available=100.0,
        deployed=900.0,
    )

    # Try to allocate more than available
    success = state.allocate(200.0)
    assert success is False
    assert state.available == 100.0  # Unchanged
    assert state.deployed == 900.0  # Unchanged


def test_capital_state_release():
    """Test that capital can be released from deployed back to available."""
    state = CapitalState(
        available=700.0,
        deployed=300.0,
    )

    # Release 100 with 10 profit
    state.release(100.0, profit=10.0)
    assert state.available == 810.0  # 700 + 100 + 10
    assert state.deployed == 200.0  # 300 - 100
    assert state.pnl_realized == 10.0


def test_capital_state_release_with_loss():
    """Test that capital release works correctly with losses."""
    state = CapitalState(
        available=700.0,
        deployed=300.0,
    )

    # Release 100 with -20 loss
    state.release(100.0, profit=-20.0)
    assert state.available == 780.0  # 700 + 100 - 20
    assert state.deployed == 200.0  # 300 - 100
    assert state.pnl_realized == -20.0


def test_capital_state_update_unrealized_pnl():
    """Test that unrealized PnL can be updated."""
    state = CapitalState(
        available=1000.0,
        deployed=0.0,
    )

    # Update unrealized PnL
    state.update_unrealized_pnl(50.0)
    assert state.pnl_unrealized == 50.0
    
    # Update again with negative value
    state.update_unrealized_pnl(-25.0)
    assert state.pnl_unrealized == -25.0


def test_capital_state_cooldowns():
    """Test that cooldowns work properly."""
    state = CapitalState(
        available=1000.0,
        deployed=0.0,
    )

    # Not in cooldown initially
    assert state.is_in_cooldown("BTC/USDT", 1000, 60) is False

    # Update cooldown
    state.update_cooldown("BTC/USDT", 1000)

    # Now in cooldown within 60 seconds
    assert state.is_in_cooldown("BTC/USDT", 1030, 60) is True

    # Not in cooldown after 60 seconds
    assert state.is_in_cooldown("BTC/USDT", 1070, 60) is False


def test_execution_engine_state_creation():
    """Test that execution engine state can be created."""
    state = create_initial_state(total_capital=1000.0)

    assert state.capital.available == 1000.0
    assert state.capital.deployed == 0.0
    assert len(state.open_trades) == 0
    assert len(state.closed_trades) == 0
    assert state.total_actions == 0


def test_execution_engine_state_cooldown():
    """Test that symbol cooldowns work properly."""
    state = create_initial_state(total_capital=1000.0)

    # Not in cooldown initially
    assert state.is_in_cooldown("BTC/USDT", 1000, 60) is False

    # Update cooldown
    state.update_cooldown("BTC/USDT", 1000)

    # Now in cooldown within 60 seconds
    assert state.is_in_cooldown("BTC/USDT", 1030, 60) is True

    # Not in cooldown after 60 seconds
    assert state.is_in_cooldown("BTC/USDT", 1070, 60) is False


def test_capital_accounting_consistency():
    """Test that capital accounting remains consistent through operations."""
    state = CapitalState(
        available=1000.0,
        deployed=0.0,
    )

    # Allocate some capital
    state.allocate(300.0)

    # Total should be accounted for
    total_accounted = state.available + state.deployed
    assert total_accounted == 1000.0

    # Release with profit (profit adds to available but increases total)
    state.release(100.0, profit=20.0)

    # After release with profit
    # available now includes the profit: 700 + 100 + 20 = 820
    # deployed: 200
    # total with profit: 820 + 200 = 1020
    assert abs(state.available - 820.0) < 0.01
    assert abs(state.deployed - 200.0) < 0.01


def test_exploit_must_request_capital():
    """
    Test that exploits must request capital and receive allocation or rejection.
    
    This is the key requirement: exploits cannot touch balances directly,
    they must request capital through allocate() and handle rejection.
    """
    state = CapitalState(
        available=1000.0,
        deployed=0.0,
    )
    
    # Simulate exploit requesting capital
    # Request 1: Should succeed
    requested_amount = 300.0
    allocated = state.allocate(requested_amount)
    assert allocated is True, "Allocation should succeed when capital is available"
    assert state.available == 700.0
    assert state.deployed == 300.0
    
    # Request 2: Should succeed
    requested_amount = 400.0
    allocated = state.allocate(requested_amount)
    assert allocated is True, "Allocation should succeed when capital is available"
    assert state.available == 300.0
    assert state.deployed == 700.0
    
    # Request 3: Should be rejected (insufficient capital)
    requested_amount = 500.0
    allocated = state.allocate(requested_amount)
    assert allocated is False, "Allocation should be rejected when insufficient capital"
    assert state.available == 300.0, "Available capital should not change on rejected allocation"
    assert state.deployed == 700.0, "Deployed capital should not change on rejected allocation"
    
    # Request 4: Should succeed (exactly available amount)
    requested_amount = 300.0
    allocated = state.allocate(requested_amount)
    assert allocated is True, "Allocation should succeed for exact available amount"
    assert state.available == 0.0
    assert state.deployed == 1000.0
