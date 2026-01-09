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


def test_emergency_stop_halts_all_trading():
    """Test that emergency stop prevents all trading actions."""
    limits = RiskLimits(
        max_position_size=0.5,
        max_total_exposure=0.95,
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

    # First, verify action is allowed
    allowed, reason = manager.check_action(
        action=action,
        available=1000.0,
        deployed=0.0,
        open_positions=0,
        current_timestamp=1000,
    )
    assert allowed is True

    # Activate emergency stop
    manager.activate_emergency_stop()
    assert manager.is_emergency_stop_active()

    # Now action should be blocked
    allowed, reason = manager.check_action(
        action=action,
        available=1000.0,
        deployed=0.0,
        open_positions=0,
        current_timestamp=1000,
    )
    assert allowed is False
    assert "EMERGENCY STOP ACTIVE" in reason

    # Deactivate emergency stop
    manager.deactivate_emergency_stop()
    assert not manager.is_emergency_stop_active()

    # Action should be allowed again
    allowed, reason = manager.check_action(
        action=action,
        available=1000.0,
        deployed=0.0,
        open_positions=0,
        current_timestamp=1000,
    )
    assert allowed is True


def test_emergency_stop_cannot_be_bypassed():
    """Test that emergency stop cannot be bypassed by any means."""
    limits = RiskLimits(
        max_position_size=1.0,  # Very permissive limits
        max_total_exposure=1.0,
        max_open_positions=1000,
        max_loss_per_trade=1.0,
        max_daily_loss=1.0,
    )
    manager = RiskManager(limits)

    # Activate emergency stop
    manager.activate_emergency_stop()

    # Try with various action types
    for action_type in [ActionType.OPEN, ActionType.CLOSE, ActionType.ADJUST]:
        action = Action(
            type=action_type,
            symbol="BTC/USDT",
            side=Side.LONG,
            size=0.01,
            reason="test_bypass",
        )

        allowed, reason = manager.check_action(
            action=action,
            available=1000000.0,
            deployed=0.0,
            open_positions=0,
            current_timestamp=1000,
        )
        assert allowed is False
        assert "EMERGENCY STOP ACTIVE" in reason


def test_exchange_disconnect_halts_trading():
    """Test that exchange disconnect prevents trading."""
    limits = RiskLimits(
        max_position_size=0.5,
        max_total_exposure=0.95,
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

    # Initially connected, action should be allowed
    assert manager.is_exchange_connected()
    allowed, reason = manager.check_action(
        action=action,
        available=1000.0,
        deployed=0.0,
        open_positions=0,
        current_timestamp=1000,
    )
    assert allowed is True

    # Disconnect exchange
    manager.set_exchange_connected(False, 1000)
    assert not manager.is_exchange_connected()

    # Action should be blocked
    allowed, reason = manager.check_action(
        action=action,
        available=1000.0,
        deployed=0.0,
        open_positions=0,
        current_timestamp=1005,
    )
    assert allowed is False
    assert "Exchange disconnected" in reason

    # Reconnect exchange
    manager.set_exchange_connected(True, 1010)
    assert manager.is_exchange_connected()

    # Action should be allowed again
    allowed, reason = manager.check_action(
        action=action,
        available=1000.0,
        deployed=0.0,
        open_positions=0,
        current_timestamp=1015,
    )
    assert allowed is True


def test_exchange_disconnect_timeout():
    """Test that trading remains halted while exchange is disconnected."""
    limits = RiskLimits(
        max_position_size=0.5,
        max_total_exposure=0.95,
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

    # Disconnect exchange at timestamp 1000
    manager.set_exchange_connected(False, 1000)

    # Reconnect at timestamp 1020 (20 seconds later)
    manager.set_exchange_connected(True, 1020)

    # Action should be allowed (reconnected)
    allowed, reason = manager.check_action(
        action=action,
        available=1000.0,
        deployed=0.0,
        open_positions=0,
        current_timestamp=1025,
    )
    assert allowed is True

    # Disconnect again at timestamp 1100
    manager.set_exchange_connected(False, 1100)

    # Try action at timestamp 1140 (40 seconds later - still disconnected)
    allowed, reason = manager.check_action(
        action=action,
        available=1000.0,
        deployed=0.0,
        open_positions=0,
        current_timestamp=1140,
    )
    assert allowed is False
    assert "disconnect" in reason.lower()


def test_funding_rate_anomaly_detection():
    """Test that funding rate anomalies are detected."""
    limits = RiskLimits(
        max_position_size=0.5,
        max_total_exposure=0.95,
        max_open_positions=10,
        max_loss_per_trade=0.10,
        max_daily_loss=0.20,
        max_funding_rate=0.01,  # 1% max
        funding_rate_change_threshold=0.005,  # 0.5% max change
    )
    manager = RiskManager(limits)

    # Normal funding rate should be safe
    safe, reason = manager.check_funding_rate("BTC/USDT", 0.0005)
    assert safe is True
    assert reason is None

    # High funding rate should be detected
    safe, reason = manager.check_funding_rate("ETH/USDT", 0.015)  # 1.5% > 1% limit
    assert safe is False
    assert "exceeds limit" in reason

    # Negative high funding rate should also be detected
    safe, reason = manager.check_funding_rate("SOL/USDT", -0.012)
    assert safe is False
    assert "exceeds limit" in reason


def test_funding_rate_sudden_change_detection():
    """Test that sudden funding rate changes are detected."""
    limits = RiskLimits(
        max_position_size=0.5,
        max_total_exposure=0.95,
        max_open_positions=10,
        max_loss_per_trade=0.10,
        max_daily_loss=0.20,
        max_funding_rate=0.01,
        funding_rate_change_threshold=0.005,  # 0.5% max change
    )
    manager = RiskManager(limits)

    # First funding rate reading
    safe, reason = manager.check_funding_rate("BTC/USDT", 0.0002)
    assert safe is True

    # Small change should be OK
    safe, reason = manager.check_funding_rate("BTC/USDT", 0.0004)
    assert safe is True

    # Large sudden change should be detected (0.008 - 0.0004 = 0.0076 change > 0.005 threshold)
    safe, reason = manager.check_funding_rate("BTC/USDT", 0.008)
    assert safe is False
    assert "change" in reason.lower()


def test_daily_loss_limit_cannot_be_bypassed():
    """Test that daily loss limit is enforced before all other checks."""
    limits = RiskLimits(
        max_position_size=1.0,  # Very permissive
        max_total_exposure=1.0,
        max_open_positions=1000,
        max_loss_per_trade=1.0,
        max_daily_loss=0.10,  # 10% daily loss limit - strict
    )
    manager = RiskManager(limits)

    # Record loss at daily limit
    manager.record_loss(0.10)

    action = Action(
        type=ActionType.OPEN,
        symbol="BTC/USDT",
        side=Side.LONG,
        size=0.01,  # Tiny position
        reason="test_bypass",
    )

    # Even with permissive other limits, daily loss should block
    allowed, reason = manager.check_action(
        action=action,
        available=1000000.0,
        deployed=0.0,
        open_positions=0,
        current_timestamp=1000,
    )
    assert allowed is False
    assert "Daily loss limit reached" in reason


def test_all_kill_switches_checked_first():
    """Test that kill switches (emergency stop, exchange disconnect, daily loss) are checked before other limits."""
    limits = RiskLimits(
        max_position_size=0.05,  # 5% - will be violated
        max_total_exposure=0.95,
        max_open_positions=3,
        max_loss_per_trade=0.10,
        max_daily_loss=0.20,
    )
    manager = RiskManager(limits)

    # Create an action that would violate position size limit
    action = Action(
        type=ActionType.OPEN,
        symbol="BTC/USDT",
        side=Side.LONG,
        size=0.15,  # 15% > 5% limit
        reason="test_action",
    )

    # Without kill switches, should fail on position size
    allowed, reason = manager.check_action(
        action=action,
        available=1000.0,
        deployed=0.0,
        open_positions=0,
        current_timestamp=1000,
    )
    assert allowed is False
    assert "exceeds limit" in reason  # Position size violation

    # With emergency stop, should fail on emergency stop (checked first)
    manager.activate_emergency_stop()
    allowed, reason = manager.check_action(
        action=action,
        available=1000.0,
        deployed=0.0,
        open_positions=0,
        current_timestamp=1000,
    )
    assert allowed is False
    assert "EMERGENCY STOP" in reason  # Emergency stop checked before position size

    # Deactivate emergency stop, activate exchange disconnect
    manager.deactivate_emergency_stop()
    manager.set_exchange_connected(False, 1000)
    allowed, reason = manager.check_action(
        action=action,
        available=1000.0,
        deployed=0.0,
        open_positions=0,
        current_timestamp=1000,
    )
    assert allowed is False
    assert "Exchange disconnected" in reason  # Exchange disconnect checked before position size

    # Reconnect exchange, hit daily loss limit
    manager.set_exchange_connected(True, 1010)
    manager.record_loss(0.20)
    allowed, reason = manager.check_action(
        action=action,
        available=1000.0,
        deployed=0.0,
        open_positions=0,
        current_timestamp=1020,
    )
    assert allowed is False
    assert "Daily loss limit" in reason  # Daily loss checked before position size
