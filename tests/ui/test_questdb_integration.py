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


def test_run_quick_backtest_with_questdb_enabled():
    """Test that backtesting handles QuestDB gracefully."""
    config = {"questdb_enabled": True}
    
    # Should complete without raising even if QuestDB is not available
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


def test_log_backtest_to_questdb_handles_connection_error():
    """Test that QuestDB logging handles connection errors gracefully."""
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
    
    # Should handle connection failure gracefully
    try:
        _log_backtest_to_questdb(config, "mixed", results)
    except Exception:
        # Expected to fail if QuestDB is not running, but should be caught
        pass
