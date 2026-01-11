#!/usr/bin/env python3
"""
QuestDB Integration Example

This example demonstrates how to use QuestDB for logging trading metrics
and backtest results. It shows both the ExploitModule integration and
backtest adapter integration.

Requirements:
    1. Install QuestDB: pip install questdb
    2. Run QuestDB: docker run -d -p 9000:9000 -p 9009:9009 questdb/questdb
    3. View data: http://localhost:9000

Usage:
    python examples/questdb_example.py
"""

from freqtrade.exploits.exploit_module import (
    ExploitModule,
    ExecutionState,
    ExecutionResult,
    Action,
    ActionType,
    log_to_questdb,
)
from freqtrade.ui.backtest_adapter import run_quick_backtest


class QuestDBExampleExploit(ExploitModule):
    """
    Example exploit module that demonstrates QuestDB logging.
    
    This is a simple momentum-based strategy that logs metrics on every
    execution result.
    """
    
    def __init__(self, config: dict):
        self.config = config
        self._last_state = None
    
    def evaluate(self, state: ExecutionState) -> list[Action]:
        """Simple buy-and-hold example."""
        self._last_state = state
        
        # Simple logic: buy if no positions
        if len(state.open_positions) == 0 and state.available_capital > 100:
            return [
                Action(
                    type=ActionType.OPEN_LONG,
                    symbol=state.symbol,
                    size=0.1,  # 10% of capital
                    reason="example_entry",
                    metadata={"strategy": "questdb_example"}
                )
            ]
        
        return []
    
    def on_execution_result(self, action: Action, result: ExecutionResult) -> None:
        """
        Handle execution results and log to QuestDB.
        
        This is where QuestDB logging happens - completely optional and
        only active if questdb_enabled: true in config.
        """
        # Your custom result handling
        if result.success:
            print(f"✓ Action {action.type.name} executed successfully")
        else:
            print(f"✗ Action {action.type.name} failed: {result.error_message}")
        
        # Optional: Log to QuestDB if enabled
        if self._last_state:
            log_to_questdb(self.config, self._last_state, action, result)


def example_backtest_with_questdb():
    """
    Example 1: Run a backtest and log results to QuestDB.
    """
    print("=" * 70)
    print("Example 1: Backtest with QuestDB Logging")
    print("=" * 70)
    
    config = {
        "questdb_enabled": True,
        "questdb_host": "localhost",
        "questdb_port": 9009,
        "strategy_name": "example_momentum",
    }
    
    print("\nRunning backtest with QuestDB logging enabled...")
    print("Market condition: trending_up")
    print("Ticks: 100")
    
    results = run_quick_backtest(
        market_condition="trending_up",
        num_ticks=100,
        initial_capital=10000.0,
        verbose=False,
        config=config,
    )
    
    print(f"\n📊 Backtest Results:")
    print(f"  Initial Capital: ${results['initial_capital']:,.2f}")
    print(f"  Final Capital:   ${results['final_capital']:,.2f}")
    print(f"  Total Return:    {results['total_return_pct']:+.2f}%")
    print(f"  Total Trades:    {results['total_trades']}")
    print(f"  Win Rate:        {results['win_rate']:.2f}%")
    
    if config.get('questdb_enabled'):
        print(f"\n💾 Results logged to QuestDB!")
        print(f"   View at: http://localhost:9000")
        print(f"   Query:   SELECT * FROM backtest_results ORDER BY timestamp DESC LIMIT 10;")


def example_compare_market_conditions():
    """
    Example 2: Compare strategy performance across different market conditions.
    """
    print("\n" + "=" * 70)
    print("Example 2: Compare Market Conditions")
    print("=" * 70)
    
    config = {
        "questdb_enabled": True,
        "strategy_name": "example_momentum",
    }
    
    market_conditions = ["trending_up", "trending_down", "mixed", "volatile"]
    
    print("\nRunning backtests for different market conditions...")
    
    for condition in market_conditions:
        print(f"\n  Testing: {condition}...")
        results = run_quick_backtest(
            market_condition=condition,
            num_ticks=50,
            initial_capital=10000.0,
            verbose=False,
            config=config,
        )
        print(f"    Return: {results['total_return_pct']:+.2f}% | Trades: {results['total_trades']}")
    
    print(f"\n💾 All results logged to QuestDB!")
    print(f"   Compare with:")
    print(f"   SELECT market_condition, AVG(total_return_pct) as avg_return,")
    print(f"          AVG(win_rate) as avg_win_rate")
    print(f"   FROM backtest_results")
    print(f"   WHERE strategy = 'example_momentum'")
    print(f"   GROUP BY market_condition;")


def example_questdb_disabled():
    """
    Example 3: Show that backtesting works fine with QuestDB disabled.
    """
    print("\n" + "=" * 70)
    print("Example 3: Backtest WITHOUT QuestDB (normal operation)")
    print("=" * 70)
    
    # No config or questdb_enabled: false
    config = {"questdb_enabled": False}
    
    print("\nRunning backtest WITHOUT QuestDB logging...")
    
    results = run_quick_backtest(
        market_condition="mixed",
        num_ticks=50,
        initial_capital=10000.0,
        verbose=False,
        config=config,
    )
    
    print(f"\n📊 Backtest Results:")
    print(f"  Final Capital: ${results['final_capital']:,.2f}")
    print(f"  Total Return:  {results['total_return_pct']:+.2f}%")
    print(f"\n✓ No QuestDB logging - normal operation")


def check_questdb_available():
    """Check if QuestDB is available and provide setup instructions if not."""
    try:
        from questdb.ingress import Sender
        
        # Try to connect
        try:
            with Sender.from_conf('tcp::addr=localhost:9009;') as sender:
                # Just test connection
                pass
            return True
        except Exception:
            print("⚠️  QuestDB server not reachable at localhost:9009")
            print("\nTo start QuestDB:")
            print("  docker run -d -p 9000:9000 -p 9009:9009 questdb/questdb")
            print("\nOr install and run locally:")
            print("  https://questdb.io/docs/get-started/")
            return False
    except ImportError:
        print("⚠️  QuestDB client not installed")
        print("\nTo install:")
        print("  pip install questdb")
        return False


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("QuestDB Integration Examples")
    print("=" * 70)
    
    # Check if QuestDB is available
    questdb_available = check_questdb_available()
    
    if questdb_available:
        print("\n✓ QuestDB is available and running")
    else:
        print("\n⚠️  Continuing with examples (will show warnings if logging fails)")
    
    # Example 1: Basic backtest with QuestDB
    example_backtest_with_questdb()
    
    # Example 2: Compare market conditions
    example_compare_market_conditions()
    
    # Example 3: Show it works without QuestDB
    example_questdb_disabled()
    
    print("\n" + "=" * 70)
    print("Examples Complete!")
    print("=" * 70)
    
    if questdb_available:
        print("\n📊 View your data:")
        print("  1. Open http://localhost:9000 in your browser")
        print("  2. Try these queries:")
        print("\n     -- View recent trading metrics")
        print("     SELECT * FROM trading_metrics ORDER BY timestamp DESC LIMIT 10;")
        print("\n     -- View backtest results")
        print("     SELECT * FROM backtest_results ORDER BY timestamp DESC;")
        print("\n     -- Compare strategies")
        print("     SELECT strategy, market_condition, AVG(total_return_pct)")
        print("     FROM backtest_results GROUP BY strategy, market_condition;")
    else:
        print("\n💡 Install and run QuestDB to see the full functionality:")
        print("   docker run -d -p 9000:9000 -p 9009:9009 questdb/questdb")


if __name__ == "__main__":
    main()
