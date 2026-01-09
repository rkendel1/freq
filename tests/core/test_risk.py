"""
Tests for the risk management module.

Tests that risk limits are enforced properly before execution.
"""

import pytest
from freqtrade.core.risk import RiskLimits, RiskManager
from freqtrade.core.actions import Action, ActionType, Side


def test_risk_limits_creation():
    """Test that risk limits can be created with valid values."""
    limits = RiskLimits(
        max_position_size=0.1,
        max_total_exposure=0.95,
        max_open_positions=3,
        max_loss_per_trade=0.10,
        max_daily_loss=0.20,
        max_leverage=1.0,
        position_cooldown=0,
        global_cooldown=0,
    )
    assert limits.max_position_size == 0.1
    assert limits.max_open_positions == 3


def test_risk_manager_allows_valid_action():
    """Test that risk manager allows actions within limits."""
    limits = RiskLimits(
        max_position_size=0.1,
        max_total_exposure=0.95,
        max_open_positions=3,
        max_loss_per_trade=0.10,
        max_daily_loss=0.20,
    )
    manager = RiskManager(limits)

    action = Action(
        type=ActionType.OPEN,
        symbol="BTC/USDT",
        side=Side.LONG,
        size=0.05,  # 5% position size, within 10% limit
        reason="test_action",
    )

    allowed, reason = manager.check_action(
        action=action,
        available=1000.0,
        deployed=0.0,
        open_positions=0,
        current_timestamp=1000,
    )

    assert allowed is True
    assert reason is None


def test_risk_manager_rejects_oversized_position():
    """Test that risk manager rejects positions that are too large."""
    limits = RiskLimits(
        max_position_size=0.1,  # Max 10%
        max_total_exposure=0.95,
        max_open_positions=3,
        max_loss_per_trade=0.10,
        max_daily_loss=0.20,
    )
    manager = RiskManager(limits)

    action = Action(
        type=ActionType.OPEN,
        symbol="BTC/USDT",
        side=Side.LONG,
        size=0.15,  # 15% position size, exceeds 10% limit
        reason="test_action",
    )

    allowed, reason = manager.check_action(
        action=action,
        available=1000.0,
        deployed=0.0,
        open_positions=0,
        current_timestamp=1000,
    )

    assert allowed is False
    assert "exceeds limit" in reason


def test_risk_manager_rejects_too_many_positions():
    """Test that risk manager rejects opening too many positions."""
    limits = RiskLimits(
        max_position_size=0.1,
        max_total_exposure=0.95,
        max_open_positions=3,  # Max 3 positions
        max_loss_per_trade=0.10,
        max_daily_loss=0.20,
    )
    manager = RiskManager(limits)

    action = Action(
        type=ActionType.OPEN,
        symbol="BTC/USDT",
        side=Side.LONG,
        size=0.05,
        reason="test_action",
    )

    # Already have 3 positions open
    allowed, reason = manager.check_action(
        action=action,
        available=1000.0,
        deployed=500.0,
        open_positions=3,  # At limit
        current_timestamp=1000,
    )

    assert allowed is False
    assert "Max positions reached" in reason


def test_risk_manager_rejects_excessive_exposure():
    """Test that risk manager rejects when total exposure is too high."""
    limits = RiskLimits(
        max_position_size=0.5,
        max_total_exposure=0.95,  # Max 95% exposure
        max_open_positions=10,
        max_loss_per_trade=0.10,
        max_daily_loss=0.20,
    )
    manager = RiskManager(limits)

    action = Action(
        type=ActionType.OPEN,
        symbol="BTC/USDT",
        side=Side.LONG,
        size=0.1,
        reason="test_action",
    )

    # Already at 95% exposure
    allowed, reason = manager.check_action(
        action=action,
        available=50.0,  # Only 5% available
        deployed=950.0,  # 95% deployed
        open_positions=2,
        current_timestamp=1000,
    )

    assert allowed is False
    assert "Max exposure reached" in reason


def test_risk_manager_cooldown():
    """Test that risk manager enforces cooldown periods."""
    limits = RiskLimits(
        max_position_size=0.5,
        max_total_exposure=0.95,
        max_open_positions=10,
        max_loss_per_trade=0.10,
        max_daily_loss=0.20,
        position_cooldown=60,  # 60 second cooldown per symbol
    )
    manager = RiskManager(limits)

    action = Action(
        type=ActionType.OPEN,
        symbol="BTC/USDT",
        side=Side.LONG,
        size=0.1,
        reason="test_action",
    )

    # Record action at timestamp 1000
    manager.record_action(action, 1000)

    # Try again at timestamp 1030 (30 seconds later, within cooldown)
    allowed, reason = manager.check_action(
        action=action,
        available=1000.0,
        deployed=0.0,
        open_positions=0,
        current_timestamp=1030,
    )

    assert allowed is False
    assert "cooldown active" in reason

    # Try again at timestamp 1070 (70 seconds later, after cooldown)
    allowed, reason = manager.check_action(
        action=action,
        available=1000.0,
        deployed=0.0,
        open_positions=0,
        current_timestamp=1070,
    )

    assert allowed is True
    assert reason is None


def test_risk_manager_daily_loss_limit():
    """Test that risk manager enforces daily loss limits."""
    limits = RiskLimits(
        max_position_size=0.5,
        max_total_exposure=0.95,
        max_open_positions=10,
        max_loss_per_trade=0.10,
        max_daily_loss=0.20,  # Max 20% daily loss
    )
    manager = RiskManager(limits)

    # Record 20% loss
    manager.record_loss(0.20)

    action = Action(
        type=ActionType.OPEN,
        symbol="BTC/USDT",
        side=Side.LONG,
        size=0.1,
        reason="test_action",
    )

    allowed, reason = manager.check_action(
        action=action,
        available=1000.0,
        deployed=0.0,
        open_positions=0,
        current_timestamp=1000,
    )

    assert allowed is False
    assert "Daily loss limit reached" in reason

    # Reset daily loss
    manager.reset_daily_loss()

    allowed, reason = manager.check_action(
        action=action,
        available=1000.0,
        deployed=0.0,
        open_positions=0,
        current_timestamp=1000,
    )

    assert allowed is True
    assert reason is None
