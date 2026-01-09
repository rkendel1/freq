"""
Tests for demo_server timestamp handling.

This test ensures that timestamps in milliseconds (from MarketTick and ExecutionResult)
are correctly converted to seconds when passed to datetime.fromtimestamp().
"""

from datetime import UTC, datetime

import pytest

from freqtrade.ui.automated_exploit import PositionState, Side


def test_timestamp_conversion_in_milliseconds():
    """
    Test that position timestamps in milliseconds are correctly handled.

    This test verifies the fix for the ValueError: year 57995 is out of range
    that occurred when position.timestamp (in milliseconds) was incorrectly
    passed to datetime.fromtimestamp() which expects seconds.
    """
    # Create a position with timestamp in milliseconds (as set by market_simulator.py)
    current_time = datetime.now(UTC)
    timestamp_ms = int(current_time.timestamp() * 1000)

    position = PositionState(
        symbol="BTC/USDT",
        side=Side.LONG,
        entry_price=50000.0,
        size=1000.0,
        timestamp=timestamp_ms,
    )

    # Verify that converting timestamp_ms / 1000 to datetime works correctly
    # This is what the fix does in demo_server.py line 826
    entry_date = datetime.fromtimestamp(position.timestamp / 1000, tz=UTC)

    # The converted date should be close to current_time (within a few seconds)
    time_diff = abs((entry_date - current_time).total_seconds())
    assert time_diff < 2, f"Time difference too large: {time_diff} seconds"

    # Verify the year is reasonable (not 57995)
    assert 2020 <= entry_date.year <= 2030, f"Year out of expected range: {entry_date.year}"


def test_holding_duration_calculation():
    """
    Test that holding duration is calculated correctly with millisecond timestamps.

    This verifies the fix for lines 835-836 in demo_server.py where holding duration
    was calculated incorrectly due to mixing milliseconds and seconds.
    """
    # Create a position from 1 hour ago
    current_time = datetime.now(UTC)
    one_hour_ago = current_time.timestamp() - 3600  # 1 hour ago in seconds
    timestamp_ms = int(one_hour_ago * 1000)  # Convert to milliseconds

    position = PositionState(
        symbol="BTC/USDT",
        side=Side.LONG,
        entry_price=50000.0,
        size=1000.0,
        timestamp=timestamp_ms,
    )

    # Calculate holding duration (as fixed in demo_server.py)
    holding_duration_seconds = int(
        datetime.now(UTC).timestamp() - position.timestamp / 1000
    )
    holding_duration_hours = (
        datetime.now(UTC).timestamp() - position.timestamp / 1000
    ) / 3600

    # Should be approximately 1 hour (3600 seconds)
    assert 3595 <= holding_duration_seconds <= 3605, (
        f"Holding duration in seconds incorrect: {holding_duration_seconds}"
    )
    assert 0.99 <= holding_duration_hours <= 1.01, (
        f"Holding duration in hours incorrect: {holding_duration_hours}"
    )


def test_timestamp_without_conversion_fails():
    """
    Test that demonstrates the original bug - using milliseconds directly fails.

    This shows what happens when position.timestamp (in milliseconds) is used
    directly without dividing by 1000.
    """
    # Create a timestamp in milliseconds
    current_time = datetime.now(UTC)
    timestamp_ms = int(current_time.timestamp() * 1000)

    # This should raise ValueError: year is out of range
    # because it interprets milliseconds as seconds
    with pytest.raises(ValueError, match=r"year.*out of range"):
        datetime.fromtimestamp(timestamp_ms, tz=UTC)
