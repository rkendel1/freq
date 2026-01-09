#!/usr/bin/env python3
"""
Example: Running automated backtest with the backtest adapter.

This script demonstrates how to use the BacktestAdapter to run realistic
automated simulations over different market conditions.
"""

import logging
from freqtrade.ui.backtest_adapter import BacktestAdapter, run_quick_backtest


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def example_basic():
    """Basic backtest example."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Backtest (Mixed Market)")
    print("="*70)
    
    results = run_quick_backtest(
        market_condition="mixed",
        num_ticks=500,
        initial_capital=10000.0,
        verbose=False  # Set to True to see detailed logs
    )
    
    print(f"\n📊 Results:")
    print(f"  Initial Capital:  ${results['initial_capital']:,.2f}")
    print(f"  Final Capital:    ${results['final_capital']:,.2f}")
    print(f"  Total Return:     ${results['total_return']:+,.2f} ({results['total_return_pct']:+.2f}%)")
    print(f"  Total Trades:     {results['total_trades']}")
    print(f"  Winning Trades:   {results['winning_trades']}")
    print(f"  Losing Trades:    {results['losing_trades']}")
    print(f"  Win Rate:         {results['win_rate']:.2f}%")
    print(f"  Avg Win:          ${results['avg_win']:+,.2f}")
    print(f"  Avg Loss:         ${results['avg_loss']:+,.2f}")
    print(f"  Market Change:    {results['price_change_pct']:+.2f}%")


def example_trending_market():
    """Backtest in trending market."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Trending Up Market")
    print("="*70)
    
    adapter = BacktestAdapter(
        initial_capital=10000.0,
        market_condition="trending_up",
        volatility=0.015,  # Lower volatility in trending market
    )
    
    results = adapter.run(num_ticks=1000, verbose=False)
    
    print(f"\n📊 Results:")
    print(f"  Initial Capital:  ${results['initial_capital']:,.2f}")
    print(f"  Final Capital:    ${results['final_capital']:,.2f}")
    print(f"  Total Return:     ${results['total_return']:+,.2f} ({results['total_return_pct']:+.2f}%)")
    print(f"  Total Trades:     {results['total_trades']}")
    print(f"  Win Rate:         {results['win_rate']:.2f}%")
    print(f"  Market Change:    {results['price_change_pct']:+.2f}%")
    
    # Get trades as DataFrame
    trades_df = adapter.get_trades_dataframe()
    if not trades_df.empty:
        print(f"\n📋 Trade Summary:")
        print(trades_df[['side', 'entry_price', 'exit_price', 'profit_pct']].head(10))


def example_volatile_market():
    """Backtest in volatile market."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Volatile Market")
    print("="*70)
    
    adapter = BacktestAdapter(
        initial_capital=10000.0,
        market_condition="volatile",
        volatility=0.03,  # Higher volatility
    )
    
    results = adapter.run(num_ticks=800, verbose=False)
    
    print(f"\n📊 Results:")
    print(f"  Initial Capital:  ${results['initial_capital']:,.2f}")
    print(f"  Final Capital:    ${results['final_capital']:,.2f}")
    print(f"  Total Return:     ${results['total_return']:+,.2f} ({results['total_return_pct']:+.2f}%)")
    print(f"  Total Trades:     {results['total_trades']}")
    print(f"  Win Rate:         {results['win_rate']:.2f}%")
    print(f"  Profit Factor:    {results['profit_factor']:.2f}")
    
    # Get equity curve
    equity_df = adapter.get_equity_curve_dataframe()
    if not equity_df.empty:
        max_equity = equity_df['equity'].max()
        min_equity = equity_df['equity'].min()
        print(f"\n📈 Equity Curve:")
        print(f"  Max Equity:   ${max_equity:,.2f}")
        print(f"  Min Equity:   ${min_equity:,.2f}")
        print(f"  Drawdown:     ${max_equity - min_equity:,.2f}")


def example_compare_conditions():
    """Compare performance across different market conditions."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Comparing Market Conditions")
    print("="*70)
    
    conditions = ["trending_up", "trending_down", "volatile", "ranging", "mixed"]
    comparison = []
    
    for condition in conditions:
        print(f"\nRunning backtest for {condition} market...")
        adapter = BacktestAdapter(
            initial_capital=10000.0,
            market_condition=condition,
        )
        results = adapter.run(num_ticks=500, verbose=False)
        comparison.append({
            "condition": condition,
            "return_pct": results['total_return_pct'],
            "win_rate": results['win_rate'],
            "total_trades": results['total_trades'],
        })
    
    print(f"\n📊 Comparison Results:")
    print(f"\n{'Condition':<15} {'Return %':>12} {'Win Rate':>12} {'Trades':>10}")
    print("-" * 53)
    for result in comparison:
        print(f"{result['condition']:<15} {result['return_pct']:>+11.2f}% "
              f"{result['win_rate']:>11.2f}% {result['total_trades']:>10}")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("AUTOMATED BACKTESTING EXAMPLES")
    print("="*70)
    print("\nThese examples demonstrate how to use the BacktestAdapter")
    print("to run realistic automated simulations.")
    print("\n" + "="*70)
    
    # Run examples
    example_basic()
    example_trending_market()
    example_volatile_market()
    example_compare_conditions()
    
    print("\n" + "="*70)
    print("✅ All examples completed!")
    print("="*70)
    print("\nYou can now:")
    print("  1. Integrate this adapter into your backtesting framework")
    print("  2. Run the web demo: python -m freqtrade.ui.demo_server")
    print("  3. Customize the AutomatedExploit strategy for your needs")
    print("\n" + "="*70 + "\n")
