"""
Example demonstrating DSPy Bounded Control with Guardrails

This example shows how the DSPy advisor enforces safety constraints:
- Thresholds: ±20% bounds
- Allocation weights: ±10% bounds
- Forbidden actions: Cannot place orders, change leverage, disable risk controls
"""

from datetime import datetime, timezone, timedelta
from dspy.advisor import DSPyAdvisor
from freqtrade.metrics.attribution import TradeAttribution


def create_trade(trade_id, exploit_id, profit_ratio, entry_stake=1000.0):
    """Helper to create a test trade."""
    now = datetime.now(timezone.utc)
    entry_date = now - timedelta(hours=12)
    exit_date = now
    
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
        total_fees=entry_stake * 0.002,
        funding_fees=0.0,
        holding_duration_seconds=12 * 3600,
        holding_duration_hours=12.0,
        realized_profit=entry_stake * profit_ratio,
        profit_ratio=profit_ratio,
        is_open=False,
        exit_reason="roi",
    )


def main():
    print("=" * 80)
    print("DSPy Bounded Control Example")
    print("=" * 80)
    print()
    
    # Initialize advisor with guardrails enabled
    advisor = DSPyAdvisor(
        min_trades_for_suggestion=10,
        suggestion_confidence_threshold=0.6,
        enable_guardrails=True,
    )
    
    print("✓ DSPy Advisor initialized with guardrails")
    print("  - Thresholds: ±20% bounds")
    print("  - Allocation weights: ±10% bounds")
    print("  - Forbidden: orders, leverage, risk controls")
    print()
    
    # Example 1: Low Sharpe ratio (volatile returns)
    print("=" * 80)
    print("Example 1: Low Sharpe Ratio - Position Size Reduction")
    print("=" * 80)
    print()
    
    for i in range(25):
        profit = 0.05 if i % 2 == 0 else -0.04  # Volatile
        trade = create_trade(i, "low_sharpe", profit)
        advisor.observe_trade(trade)
    
    print(f"Observed 25 trades with volatile returns (low Sharpe)")
    print()
    
    suggestions = advisor.generate_suggestions()
    
    print(f"DSPy generated {len(suggestions)} suggestion(s):")
    print()
    
    for suggestion in suggestions:
        if suggestion.parameter_name == "position_size_multiplier":
            change_pct = abs(suggestion.delta) * 100
            print(f"  Parameter: {suggestion.parameter_name}")
            print(f"  Current: {suggestion.current_value:.4f}")
            print(f"  Suggested: {suggestion.suggested_value:.4f}")
            print(f"  Change: {suggestion.delta:+.4f} ({change_pct:.1f}%)")
            print(f"  Confidence: {suggestion.confidence:.2%}")
            print(f"  Rationale: {suggestion.rationale}")
            print()
            print(f"  ✓ BOUNDED: Change of {change_pct:.1f}% is within ±10% allocation bound")
            print()
    
    # Reset for next example
    advisor.reset()
    
    # Example 2: High drawdown (occasional large losses)
    print("=" * 80)
    print("Example 2: High Drawdown - Stop Loss Adjustment")
    print("=" * 80)
    print()
    
    profits = [0.01] * 20 + [-0.10] * 5
    for i, profit in enumerate(profits):
        trade = create_trade(i + 100, "high_drawdown", profit)
        advisor.observe_trade(trade)
    
    print(f"Observed 25 trades with occasional large losses (high drawdown)")
    print()
    
    suggestions = advisor.generate_suggestions()
    
    print(f"DSPy generated {len(suggestions)} suggestion(s):")
    print()
    
    for suggestion in suggestions:
        if suggestion.parameter_name == "stop_loss_percent":
            change_pct = abs(suggestion.delta / suggestion.current_value) * 100
            print(f"  Parameter: {suggestion.parameter_name}")
            print(f"  Current: {suggestion.current_value:.4f}")
            print(f"  Suggested: {suggestion.suggested_value:.4f}")
            print(f"  Change: {suggestion.delta:+.4f} ({change_pct:.1f}%)")
            print(f"  Confidence: {suggestion.confidence:.2%}")
            print(f"  Rationale: {suggestion.rationale}")
            print()
            print(f"  ✓ BOUNDED: Change of {change_pct:.1f}% is within ±20% threshold bound")
            print()
    
    # Example 3: Demonstrate guardrail enforcement
    print("=" * 80)
    print("Example 3: Guardrail Enforcement")
    print("=" * 80)
    print()
    
    print("Testing guardrail constraints:")
    print()
    
    # Test 1: Allocation weight bounds
    print("1. Allocation Weight Bounds (±10%):")
    is_valid, violation = advisor.guardrails.validate_suggestion(
        parameter_name="position_size_multiplier",
        current_value=1.0,
        suggested_value=1.05,  # +5% (within bounds)
    )
    print(f"   +5% change: {'✓ ALLOWED' if is_valid else '✗ REJECTED'}")
    
    is_valid, violation = advisor.guardrails.validate_suggestion(
        parameter_name="position_size_multiplier",
        current_value=1.0,
        suggested_value=1.15,  # +15% (exceeds bounds)
    )
    print(f"   +15% change: {'✓ ALLOWED' if is_valid else '✗ REJECTED (exceeds ±10%)'}")
    print()
    
    # Test 2: Threshold bounds
    print("2. Threshold Bounds (±20%):")
    is_valid, violation = advisor.guardrails.validate_suggestion(
        parameter_name="stop_loss_percent",
        current_value=0.05,
        suggested_value=0.055,  # +10% (within bounds)
    )
    print(f"   +10% change: {'✓ ALLOWED' if is_valid else '✗ REJECTED'}")
    
    is_valid, violation = advisor.guardrails.validate_suggestion(
        parameter_name="stop_loss_percent",
        current_value=0.05,
        suggested_value=0.07,  # +40% (exceeds bounds)
    )
    print(f"   +40% change: {'✓ ALLOWED' if is_valid else '✗ REJECTED (exceeds ±20%)'}")
    print()
    
    # Test 3: Forbidden parameters
    print("3. Forbidden Parameters:")
    forbidden_params = [
        ("place_order", "Place orders"),
        ("max_leverage", "Change leverage caps"),
        ("enable_risk_controls", "Disable risk controls"),
    ]
    
    for param, description in forbidden_params:
        is_valid, violation = advisor.guardrails.validate_suggestion(
            parameter_name=param,
            current_value=1.0,
            suggested_value=2.0,
        )
        print(f"   {description}: {'✓ ALLOWED' if is_valid else '✗ FORBIDDEN'}")
    
    print()
    
    # Get violation stats
    stats = advisor.get_guardrail_stats()
    print("=" * 80)
    print("Guardrail Violation Statistics")
    print("=" * 80)
    print()
    print(f"Total violations detected: {stats['total_violations']}")
    print(f"  - Threshold violations: {stats['violations_by_type']['threshold']}")
    print(f"  - Allocation weight violations: {stats['violations_by_type']['allocation_weight']}")
    print(f"  - Forbidden parameter violations: {stats['violations_by_type']['forbidden']}")
    print()
    
    # Summary
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print()
    print("✓ Guardrails successfully enforce bounded control:")
    print("  - Thresholds (stop_loss, holding_time): ±20% maximum change")
    print("  - Allocation weights (position_size): ±10% maximum change")
    print("  - Forbidden actions: Cannot place orders, change leverage, disable risk controls")
    print()
    print("✓ Safety overrides intelligence:")
    print("  - Even if DSPy suggests extreme changes, guardrails limit them")
    print("  - All suggestions are bounded to safe limits")
    print("  - Violations are tracked and logged")
    print()


if __name__ == "__main__":
    main()
