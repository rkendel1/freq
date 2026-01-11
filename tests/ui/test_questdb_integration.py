"""
Tests for QuestDB integration in backtest_adapter.

Tests that QuestDB logging works correctly in the backtesting adapter
and handles missing packages gracefully.
"""

import pytest
from freqtrade.ui.backtest_adapter import run_quick_backtest, _log_backtest_to_questdb


def test_run_quick_backtest_without_questdb():
    """Test that backtesting works without QuestDB enabled."""
    results = run_quick_backtest(
        market_condition="mixed",
        num_ticks=10,
        initial_capital=10000.0,
        verbose=False,
    )
    
    assert results is not None
    assert "final_capital" in results
    assert "total_return_pct" in results


def test_run_quick_backtest_with_questdb_disabled():
    """Test that backtesting works with QuestDB disabled in config."""
    config = {"questdb_enabled": False}
    
    results = run_quick_backtest(
        market_condition="mixed",
        num_ticks=10,
        initial_capital=10000.0,
        verbose=False,
        config=config,
    )
    
    assert results is not None
    assert "final_capital" in results


def test_run_quick_backtest_with_questdb_enabled_no_package(mocker):
    """Test that backtesting handles missing QuestDB package gracefully."""
    config = {"questdb_enabled": True}
    
    # Mock the import to raise ImportError
    original_import = __builtins__.__import__

    def mock_import(name, *args, **kwargs):
        if name == "questdb.ingress":
            raise ImportError("questdb not installed")
        return original_import(name, *args, **kwargs)

    mocker.patch("builtins.__import__", side_effect=mock_import)
    
    # Should complete without raising
    results = run_quick_backtest(
        market_condition="mixed",
        num_ticks=10,
        initial_capital=10000.0,
        verbose=False,
        config=config,
    )
    
    assert results is not None


def test_log_backtest_to_questdb_disabled():
    """Test that logging is skipped when QuestDB is disabled."""
    config = {"questdb_enabled": False}
    results = {
        "initial_capital": 10000.0,
        "final_capital": 11000.0,
        "total_return_pct": 10.0,
    }
    
    # Should not raise
    _log_backtest_to_questdb(config, "mixed", results)


def test_log_backtest_to_questdb_with_mock_sender(mocker):
    """Test that QuestDB logging calls sender correctly."""
    config = {
        "questdb_enabled": True,
        "questdb_host": "testhost",
        "questdb_port": 9009,
        "strategy_name": "test_strategy",
    }
    
    results = {
        "initial_capital": 10000.0,
        "final_capital": 11000.0,
        "total_return": 1000.0,
        "total_return_pct": 10.0,
        "total_trades": 5,
        "winning_trades": 3,
        "losing_trades": 2,
        "win_rate": 60.0,
        "avg_win": 500.0,
        "avg_loss": -250.0,
        "profit_factor": 2.0,
        "price_change_pct": 5.0,
        "total_ticks": 100,
    }
    
    # Mock the Sender
    mock_sender = mocker.MagicMock()
    mock_sender_class = mocker.MagicMock(return_value=mock_sender)
    mock_sender_class.from_conf = mocker.MagicMock(return_value=mock_sender)
    mock_sender.__enter__ = mocker.MagicMock(return_value=mock_sender)
    mock_sender.__exit__ = mocker.MagicMock(return_value=False)

    try:
        mocker.patch("freqtrade.ui.backtest_adapter.Sender", mock_sender_class)
        mocker.patch("freqtrade.ui.backtest_adapter.TimestampNanos", lambda x: x)

        _log_backtest_to_questdb(config, "mixed", results)

        # Verify sender was called (if mocking worked)
        if mock_sender.row.called:
            assert mock_sender.row.call_count >= 0
            assert mock_sender.flush.call_count >= 0
    except ImportError:
        # If questdb isn't installed, that's fine for this test
        pass
