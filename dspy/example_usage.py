"""
Example: DSPy Advisory Layer Usage

This example demonstrates how to use the DSPy advisory layer
to observe trading metrics and generate parameter suggestions.

The advisor operates in READ-ONLY mode:
- It observes trade data
- It generates suggestions
- Suggestions are LOGGED ONLY, never applied

This has ZERO impact on trading execution.
"""

from datetime import datetime, timezone, timedelta
from dspy.advisor import DSPyAdvisor, MetricsSnapshot, ParameterSuggestion
from freqtrade.metrics.attribution import TradeAttribution


def create_example_trade(
    trade_id: int,
    exploit_id: str,
    profit_ratio: float,
    entry_stake: float,
    hours_held: float,
) -> TradeAttribution:
    """Create an example trade attribution for demonstration."""
    now = datetime.now(timezone.utc)
    entry_date = now - timedelta(hours=hours_held)
    exit_date = now
    
    realized_profit = entry_stake * profit_ratio
    
    return TradeAttribution(
        trade_id=trade_id,
        exploit_id=exploit_id,
        capital_source="initial",
        pair="BTC/USDT",
        is_short=False,
        entry_price=50000.0,
        entry_amount=entry_stake / 50000.0,
        entry_stake=entry_stake,
        entry_date=entry_date,
        exit_price=50000.0 * (1 + profit_ratio),
        exit_date=exit_date,
        fee_open=0.001,
        fee_close=0.001,
        fee_open_cost=entry_stake * 0.001,
        fee_close_cost=entry_stake * (1 + profit_ratio) * 0.001,
        total_fees=entry_stake * 0.002 * (1 + profit_ratio),
        funding_fees=0.0,
        holding_duration_seconds=hours_held * 3600,
        holding_duration_hours=hours_held,
        realized_profit=realized_profit,
        profit_ratio=profit_ratio,
        is_open=False,
        exit_reason="roi",
    )


def example_low_sharpe_exploit():
    """
    Example 1: Exploit with low Sharpe ratio
    
    DSPy should suggest reducing position size due to inconsistent returns.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Low Sharpe Ratio Exploit")
    print("=" * 80)
    
    advisor = DSPyAdvisor(min_trades_for_suggestion=20)
    
    # Simulate an exploit with highly volatile, low Sharpe returns
    # Mix of large wins and large losses
    trade_id = 1
    for i in range(30):
        if i % 3 == 0:
            # Big win
            profit = 0.15
        elif i % 3 == 1:
            # Big loss
            profit = -0.12
        else:
            # Small profit
            profit = 0.02
        
        trade = create_example_trade(
            trade_id=trade_id,
            exploit_id="volatile_momentum",
            profit_ratio=profit,
            entry_stake=1000.0,
            hours_held=12.0,
        )
        advisor.observe_trade(trade)
        trade_id += 1
    
    # Generate suggestions
    print("\nObserved 30 trades with volatile returns (low Sharpe ratio)")
    suggestions = advisor.generate_suggestions()
    
    print(f"\nDSPy generated {len(suggestions)} suggestion(s):\n")
    for suggestion in suggestions:
        print(f"  Parameter: {suggestion.parameter_name}")
        print(f"  Current Value: {suggestion.current_value:.4f}")
        print(f"  Suggested Value: {suggestion.suggested_value:.4f}")
        print(f"  Delta: {suggestion.delta:+.4f} ({suggestion.delta * 100:+.1f}%)")
        print(f"  Confidence: {suggestion.confidence:.2%}")
        print(f"  Rationale: {suggestion.rationale}")
        print()
    
    # Show metrics
    metrics = advisor.get_metrics_snapshot("volatile_momentum")
    if metrics:
        print("Observed Metrics:")
        print(f"  Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
        print(f"  Drawdown Contribution: {metrics.drawdown_contribution:.2%}")
        print(f"  Capital Efficiency: {metrics.capital_efficiency:.2%}")
        print(f"  Win Rate: {metrics.win_rate:.2%}")


def example_high_drawdown_exploit():
    """
    Example 2: Exploit with high drawdown contribution
    
    DSPy should suggest tighter stop loss to reduce drawdown risk.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 2: High Drawdown Contribution Exploit")
    print("=" * 80)
    
    advisor = DSPyAdvisor(min_trades_for_suggestion=20)
    
    # Simulate an exploit with occasional large losses (high drawdown)
    trade_id = 1
    for i in range(25):
        if i % 10 == 0 and i > 0:
            # Occasional large loss
            profit = -0.25
        else:
            # Consistent small profits
            profit = 0.03
        
        trade = create_example_trade(
            trade_id=trade_id,
            exploit_id="mean_reversion",
            profit_ratio=profit,
            entry_stake=1000.0,
            hours_held=8.0,
        )
        advisor.observe_trade(trade)
        trade_id += 1
    
    # Generate suggestions
    print("\nObserved 25 trades with occasional large losses (high drawdown)")
    suggestions = advisor.generate_suggestions()
    
    print(f"\nDSPy generated {len(suggestions)} suggestion(s):\n")
    for suggestion in suggestions:
        print(f"  Parameter: {suggestion.parameter_name}")
        print(f"  Current Value: {suggestion.current_value:.4f}")
        print(f"  Suggested Value: {suggestion.suggested_value:.4f}")
        print(f"  Delta: {suggestion.delta:+.4f}")
        print(f"  Confidence: {suggestion.confidence:.2%}")
        print(f"  Rationale: {suggestion.rationale}")
        print()
    
    # Show metrics
    metrics = advisor.get_metrics_snapshot("mean_reversion")
    if metrics:
        print("Observed Metrics:")
        print(f"  Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
        print(f"  Drawdown Contribution: {metrics.drawdown_contribution:.2%}")
        print(f"  Capital Efficiency: {metrics.capital_efficiency:.2%}")
        print(f"  Max Drawdown: ${metrics.max_drawdown:.2f}")


def example_high_performance_exploit():
    """
    Example 3: High-performance exploit
    
    DSPy should suggest increasing position size due to strong metrics.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 3: High-Performance Exploit")
    print("=" * 80)
    
    advisor = DSPyAdvisor(min_trades_for_suggestion=20)
    
    # Simulate a consistently profitable exploit with high Sharpe
    trade_id = 1
    for i in range(40):
        # Consistently profitable with low variance
        if i % 10 == 0:
            profit = 0.08
        else:
            profit = 0.05
        
        trade = create_example_trade(
            trade_id=trade_id,
            exploit_id="funding_capture",
            profit_ratio=profit,
            entry_stake=1000.0,
            hours_held=6.0,
        )
        advisor.observe_trade(trade)
        trade_id += 1
    
    # Generate suggestions
    print("\nObserved 40 trades with consistent profitability (high Sharpe)")
    suggestions = advisor.generate_suggestions()
    
    print(f"\nDSPy generated {len(suggestions)} suggestion(s):\n")
    for suggestion in suggestions:
        print(f"  Parameter: {suggestion.parameter_name}")
        print(f"  Current Value: {suggestion.current_value:.4f}")
        print(f"  Suggested Value: {suggestion.suggested_value:.4f}")
        print(f"  Delta: {suggestion.delta:+.4f} ({suggestion.delta * 100:+.1f}%)")
        print(f"  Confidence: {suggestion.confidence:.2%}")
        print(f"  Rationale: {suggestion.rationale}")
        print()
    
    # Show metrics
    metrics = advisor.get_metrics_snapshot("funding_capture")
    if metrics:
        print("Observed Metrics:")
        print(f"  Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
        print(f"  Drawdown Contribution: {metrics.drawdown_contribution:.2%}")
        print(f"  Capital Efficiency: {metrics.capital_efficiency:.2%}")
        print(f"  Win Rate: {metrics.win_rate:.2%}")


def example_multiple_exploits():
    """
    Example 4: Multiple exploits with different characteristics
    
    DSPy should provide different suggestions for each exploit.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Multiple Exploits")
    print("=" * 80)
    
    advisor = DSPyAdvisor(min_trades_for_suggestion=15)
    
    # Exploit 1: Good performer
    for i in range(20):
        trade = create_example_trade(
            trade_id=100 + i,
            exploit_id="exploit_a",
            profit_ratio=0.04 if i % 5 != 0 else 0.08,
            entry_stake=1000.0,
            hours_held=10.0,
        )
        advisor.observe_trade(trade)
    
    # Exploit 2: Poor performer
    for i in range(20):
        trade = create_example_trade(
            trade_id=200 + i,
            exploit_id="exploit_b",
            profit_ratio=-0.05 if i % 4 == 0 else 0.02,
            entry_stake=1000.0,
            hours_held=15.0,
        )
        advisor.observe_trade(trade)
    
    # Generate suggestions
    print("\nObserved trades from 2 different exploits")
    suggestions = advisor.generate_suggestions()
    
    print(f"\nDSPy generated {len(suggestions)} suggestion(s):\n")
    
    for suggestion in suggestions:
        print(f"Exploit: {suggestion.exploit_id}")
        print(f"  Parameter: {suggestion.parameter_name}")
        print(f"  Current Value: {suggestion.current_value:.4f}")
        print(f"  Suggested Value: {suggestion.suggested_value:.4f}")
        print(f"  Delta: {suggestion.delta:+.4f}")
        print(f"  Confidence: {suggestion.confidence:.2%}")
        print(f"  Rationale: {suggestion.rationale}")
        print()
    
    # Show all metrics
    all_metrics = advisor.get_all_metrics()
    print("Metrics Summary:")
    for exploit_id, metrics in all_metrics.items():
        print(f"\n  {exploit_id}:")
        print(f"    Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
        print(f"    Capital Efficiency: {metrics.capital_efficiency:.2%}")
        print(f"    Win Rate: {metrics.win_rate:.2%}")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("DSPy READ-ONLY ADVISORY LAYER - EXAMPLE DEMONSTRATIONS")
    print("=" * 80)
    print("\nAll suggestions are LOGGED ONLY and have NO IMPACT on execution.")
    print("This is a pure observational/advisory layer.")
    
    # Run examples
    example_low_sharpe_exploit()
    example_high_drawdown_exploit()
    example_high_performance_exploit()
    example_multiple_exploits()
    
    print("\n" + "=" * 80)
    print("IMPORTANT: All suggestions above are READ-ONLY")
    print("They are logged for analysis but NEVER applied to trading execution.")
    print("=" * 80 + "\n")
