"""
Tests for the Action contract.

Verifies that:
1. Valid actions can be created
2. Invalid actions are rejected
3. Validation logic works correctly
4. Actions are immutable
"""

import pytest

from freqtrade.core.actions import Action, ActionType, Side, validate_action


def test_valid_action_creation():
    """Test that a valid action can be created."""
    action = Action(
        type=ActionType.OPEN,
        symbol="BTC/USDT",
        side=Side.LONG,
        size=100.0,
        reason="test_signal",
    )

    assert action.type == ActionType.OPEN
    assert action.symbol == "BTC/USDT"
    assert action.side == Side.LONG
    assert action.size == 100.0
    assert action.reason == "test_signal"
    assert action.ttl is None


def test_valid_action_with_ttl():
    """Test that a valid action with ttl can be created."""
    action = Action(
        type=ActionType.CLOSE,
        symbol="ETH/USDT",
        side=Side.SHORT,
        size=50.0,
        reason="profit_target",
        ttl=300,
    )

    assert action.type == ActionType.CLOSE
    assert action.symbol == "ETH/USDT"
    assert action.side == Side.SHORT
    assert action.size == 50.0
    assert action.reason == "profit_target"
    assert action.ttl == 300


def test_action_types():
    """Test all action types can be used."""
    for action_type in [ActionType.OPEN, ActionType.CLOSE, ActionType.ADJUST]:
        action = Action(
            type=action_type,
            symbol="BTC/USDT",
            side=Side.LONG,
            size=100.0,
            reason="test",
        )
        assert action.type == action_type


def test_action_sides():
    """Test all sides can be used."""
    for side in [Side.LONG, Side.SHORT]:
        action = Action(
            type=ActionType.OPEN,
            symbol="BTC/USDT",
            side=side,
            size=100.0,
            reason="test",
        )
        assert action.side == side


def test_action_immutable():
    """Test that actions are immutable (frozen dataclass)."""
    action = Action(
        type=ActionType.OPEN,
        symbol="BTC/USDT",
        side=Side.LONG,
        size=100.0,
        reason="test",
    )

    # Attempt to modify should raise an error
    with pytest.raises(AttributeError):
        action.size = 200.0  # type: ignore

    with pytest.raises(AttributeError):
        action.symbol = "ETH/USDT"  # type: ignore


def test_invalid_type():
    """Test that invalid type is rejected."""
    with pytest.raises(ValueError, match="type must be ActionType enum"):
        Action(
            type="OPEN",  # type: ignore  # String instead of enum
            symbol="BTC/USDT",
            side=Side.LONG,
            size=100.0,
            reason="test",
        )


def test_invalid_symbol_type():
    """Test that invalid symbol type is rejected."""
    with pytest.raises(ValueError, match="symbol must be str"):
        Action(
            type=ActionType.OPEN,
            symbol=123,  # type: ignore  # Number instead of string
            side=Side.LONG,
            size=100.0,
            reason="test",
        )


def test_empty_symbol():
    """Test that empty symbol is rejected."""
    with pytest.raises(ValueError, match="symbol cannot be empty"):
        Action(
            type=ActionType.OPEN,
            symbol="",
            side=Side.LONG,
            size=100.0,
            reason="test",
        )


def test_whitespace_symbol():
    """Test that whitespace-only symbol is rejected."""
    with pytest.raises(ValueError, match="symbol cannot be empty"):
        Action(
            type=ActionType.OPEN,
            symbol="   ",
            side=Side.LONG,
            size=100.0,
            reason="test",
        )


def test_invalid_side():
    """Test that invalid side is rejected."""
    with pytest.raises(ValueError, match="side must be Side enum"):
        Action(
            type=ActionType.OPEN,
            symbol="BTC/USDT",
            side="LONG",  # type: ignore  # String instead of enum
            size=100.0,
            reason="test",
        )


def test_invalid_size_type():
    """Test that invalid size type is rejected."""
    with pytest.raises(ValueError, match="size must be numeric"):
        Action(
            type=ActionType.OPEN,
            symbol="BTC/USDT",
            side=Side.LONG,
            size="100",  # type: ignore  # String instead of number
            reason="test",
        )


def test_negative_size():
    """Test that negative size is rejected."""
    with pytest.raises(ValueError, match="size must be positive"):
        Action(
            type=ActionType.OPEN,
            symbol="BTC/USDT",
            side=Side.LONG,
            size=-100.0,
            reason="test",
        )


def test_zero_size():
    """Test that zero size is rejected."""
    with pytest.raises(ValueError, match="size must be positive"):
        Action(
            type=ActionType.OPEN,
            symbol="BTC/USDT",
            side=Side.LONG,
            size=0.0,
            reason="test",
        )


def test_invalid_reason_type():
    """Test that invalid reason type is rejected."""
    with pytest.raises(ValueError, match="reason must be str"):
        Action(
            type=ActionType.OPEN,
            symbol="BTC/USDT",
            side=Side.LONG,
            size=100.0,
            reason=123,  # type: ignore  # Number instead of string
        )


def test_empty_reason():
    """Test that empty reason is rejected."""
    with pytest.raises(ValueError, match="reason cannot be empty"):
        Action(
            type=ActionType.OPEN,
            symbol="BTC/USDT",
            side=Side.LONG,
            size=100.0,
            reason="",
        )


def test_whitespace_reason():
    """Test that whitespace-only reason is rejected."""
    with pytest.raises(ValueError, match="reason cannot be empty"):
        Action(
            type=ActionType.OPEN,
            symbol="BTC/USDT",
            side=Side.LONG,
            size=100.0,
            reason="   ",
        )


def test_invalid_ttl_type():
    """Test that invalid ttl type is rejected."""
    with pytest.raises(ValueError, match="ttl must be int or None"):
        Action(
            type=ActionType.OPEN,
            symbol="BTC/USDT",
            side=Side.LONG,
            size=100.0,
            reason="test",
            ttl="300",  # type: ignore  # String instead of int
        )


def test_negative_ttl():
    """Test that negative ttl is rejected."""
    with pytest.raises(ValueError, match="ttl must be positive"):
        Action(
            type=ActionType.OPEN,
            symbol="BTC/USDT",
            side=Side.LONG,
            size=100.0,
            reason="test",
            ttl=-300,
        )


def test_zero_ttl():
    """Test that zero ttl is rejected."""
    with pytest.raises(ValueError, match="ttl must be positive"):
        Action(
            type=ActionType.OPEN,
            symbol="BTC/USDT",
            side=Side.LONG,
            size=100.0,
            reason="test",
            ttl=0,
        )


def test_validate_action_valid():
    """Test that validate_action accepts valid actions."""
    action = Action(
        type=ActionType.OPEN,
        symbol="BTC/USDT",
        side=Side.LONG,
        size=100.0,
        reason="test",
    )

    # Should not raise
    validate_action(action)


def test_validate_action_invalid_type():
    """Test that validate_action rejects non-Action objects."""
    with pytest.raises(TypeError, match="Expected Action object"):
        validate_action("not an action")  # type: ignore


def test_validate_action_dict():
    """Test that validate_action rejects dictionaries."""
    fake_action = {
        "type": ActionType.OPEN,
        "symbol": "BTC/USDT",
        "side": Side.LONG,
        "size": 100.0,
        "reason": "test",
    }

    with pytest.raises(TypeError, match="Expected Action object"):
        validate_action(fake_action)  # type: ignore


def test_int_size_accepted():
    """Test that integer size is accepted (converted to float internally)."""
    action = Action(
        type=ActionType.OPEN,
        symbol="BTC/USDT",
        side=Side.LONG,
        size=100,  # Integer
        reason="test",
    )

    assert action.size == 100


def test_float_ttl_rejected():
    """Test that float ttl is rejected (must be int)."""
    with pytest.raises(ValueError, match="ttl must be int or None"):
        Action(
            type=ActionType.OPEN,
            symbol="BTC/USDT",
            side=Side.LONG,
            size=100.0,
            reason="test",
            ttl=300.5,  # type: ignore  # Float instead of int
        )
