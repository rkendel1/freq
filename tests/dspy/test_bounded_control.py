"""
Tests for DSPy Advisor with Bounded Control

These tests verify that the DSPy advisor properly uses guardrails to:
1. Generate suggestions within bounded limits
2. Respect ±20% threshold bounds
3. Respect ±10% allocation weight bounds
4. Reject forbidden parameter adjustments
"""

from datetime import datetime, timezone, timedelta
import pytest

from dspy.advisor import DSPyAdvisor
from freqtrade.metrics.attribution import TradeAttribution


def create_test_trade(
    trade_id: int,
    exploit_id: str,
    profit_ratio: float,
    entry_stake: float = 1000.0,
    hours_held: float = 12.0,
) -> TradeAttribution:
    """Helper to create a test trade attribution."""
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
        total_fees=entry_stake * 0.001 + entry_stake * (1 + profit_ratio) * 0.001,
        funding_fees=0.0,
        holding_duration_seconds=hours_held * 3600,
        holding_duration_hours=hours_held,
        realized_profit=realized_profit,
        profit_ratio=profit_ratio,
        is_open=False,
        exit_reason="roi",
    )


class TestAdvisorWithGuardrails:
    """Test advisor integration with guardrails."""
    
    def test_advisor_initializes_with_guardrails(self):
        """Test that advisor initializes with guardrails enabled."""
        advisor = DSPyAdvisor(enable_guardrails=True)
        
        assert advisor.guardrails is not None
        assert advisor.guardrails.enforce_bounds is True
    
    def test_advisor_can_disable_guardrails(self):
        """Test that guardrails can be disabled for testing."""
        advisor = DSPyAdvisor(enable_guardrails=False)
        
        assert advisor.guardrails is not None
        assert advisor.guardrails.enforce_bounds is False
    
    def test_position_size_reduction_respects_allocation_bounds(self):
        """Test that position size reductions respect ±10% bounds."""
        advisor = DSPyAdvisor(min_trades_for_suggestion=5, enable_guardrails=True)
        
        # Create trades with low Sharpe (volatile returns)
        for i in range(25):
            profit = 0.05 if i % 2 == 0 else -0.04
            trade = create_test_trade(i, "test_exploit", profit)
            advisor.observe_trade(trade)
        
        suggestions = advisor.generate_suggestions()
        
        # Should suggest position size reduction
        position_suggestions = [s for s in suggestions if s.parameter_name == "position_size_multiplier"]
        assert len(position_suggestions) > 0
        
        for suggestion in position_suggestions:
            # Change should be within ±10% (allocation weight bound)
            change_pct = abs(suggestion.delta)
            assert change_pct <= 0.10, f"Position size change {change_pct:.2%} exceeds ±10% bound"
    
    def test_stop_loss_adjustment_respects_threshold_bounds(self):
        """Test that stop loss adjustments respect ±20% bounds."""
        advisor = DSPyAdvisor(min_trades_for_suggestion=5, enable_guardrails=True)
        
        # Create trades with high drawdown (occasional large losses)
        profits = [0.01] * 20 + [-0.10] * 5  # Mostly small wins, few large losses
        for i, profit in enumerate(profits):
            trade = create_test_trade(i, "test_exploit", profit)
            advisor.observe_trade(trade)
        
        suggestions = advisor.generate_suggestions()
        
        # Should suggest stop loss tightening
        stop_loss_suggestions = [s for s in suggestions if s.parameter_name == "stop_loss_percent"]
        
        for suggestion in stop_loss_suggestions:
            # Calculate change as percentage of current value
            change_pct = abs(suggestion.delta / suggestion.current_value)
            assert change_pct <= 0.20, f"Stop loss change {change_pct:.2%} exceeds ±20% bound"
    
    def test_holding_time_adjustment_respects_threshold_bounds(self):
        """Test that holding time adjustments respect ±20% bounds."""
        advisor = DSPyAdvisor(min_trades_for_suggestion=5, enable_guardrails=True)
        
        # Create many trades with low capital efficiency
        for i in range(35):
            trade = create_test_trade(i, "test_exploit", 0.005, entry_stake=1000.0)
            advisor.observe_trade(trade)
        
        suggestions = advisor.generate_suggestions()
        
        # Should suggest reducing holding time
        holding_suggestions = [s for s in suggestions if s.parameter_name == "max_holding_hours"]
        
        for suggestion in holding_suggestions:
            # Calculate change as percentage of current value
            change_pct = abs(suggestion.delta / suggestion.current_value)
            assert change_pct <= 0.20, f"Holding time change {change_pct:.2%} exceeds ±20% bound"
    
    def test_position_size_increase_respects_allocation_bounds(self):
        """Test that position size increases respect ±10% bounds."""
        advisor = DSPyAdvisor(min_trades_for_suggestion=5, enable_guardrails=True)
        
        # Create trades with high Sharpe and capital efficiency
        for i in range(30):
            trade = create_test_trade(i, "test_exploit", 0.05, entry_stake=1000.0)
            advisor.observe_trade(trade)
        
        suggestions = advisor.generate_suggestions()
        
        # Should suggest position size increase
        position_suggestions = [s for s in suggestions if s.parameter_name == "position_size_multiplier"]
        
        for suggestion in position_suggestions:
            # Change should be within ±10% (allocation weight bound)
            change_pct = abs(suggestion.delta)
            assert change_pct <= 0.10, f"Position size change {change_pct:.2%} exceeds ±10% bound"
    
    def test_all_suggestions_respect_bounds(self):
        """Test that all suggestions from advisor respect bounds."""
        advisor = DSPyAdvisor(min_trades_for_suggestion=5, enable_guardrails=True)
        
        # Create diverse set of trades for multiple exploits
        exploits = ["exploit_a", "exploit_b", "exploit_c"]
        
        for exploit in exploits:
            for i in range(25):
                profit = 0.02 if i % 3 == 0 else -0.01
                trade = create_test_trade(i * 10 + exploits.index(exploit), exploit, profit)
                advisor.observe_trade(trade)
        
        suggestions = advisor.generate_suggestions()
        
        # Verify all suggestions respect bounds
        for suggestion in suggestions:
            if suggestion.parameter_name == "position_size_multiplier":
                # Allocation weight: ±10%
                change_pct = abs(suggestion.delta)
                assert change_pct <= 0.10
            elif suggestion.parameter_name in ["stop_loss_percent", "max_holding_hours"]:
                # Threshold: ±20%
                change_pct = abs(suggestion.delta / suggestion.current_value)
                assert change_pct <= 0.20
    
    def test_guardrail_stats_accessible_from_advisor(self):
        """Test that guardrail statistics can be accessed from advisor."""
        advisor = DSPyAdvisor(enable_guardrails=True)
        
        stats = advisor.get_guardrail_stats()
        
        assert "total_violations" in stats
        assert "violations_by_type" in stats
        assert "recent_violations" in stats
    
    def test_advisor_reset_resets_guardrails(self):
        """Test that resetting advisor also resets guardrails."""
        advisor = DSPyAdvisor(min_trades_for_suggestion=5, enable_guardrails=True)
        
        # Generate some violations (we don't care about trades here, just validation)
        advisor.guardrails.validate_suggestion("leverage", 1.0, 2.0)
        
        stats = advisor.get_guardrail_stats()
        assert stats["total_violations"] > 0
        
        # Reset
        advisor.reset()
        
        stats = advisor.get_guardrail_stats()
        assert stats["total_violations"] == 0


class TestBoundedControlScenarios:
    """Test specific scenarios for bounded control."""
    
    def test_extreme_suggestion_gets_bounded(self):
        """Test that extreme suggestions are properly bounded.
        
        This simulates DSPy trying to suggest a very large change,
        which should be clamped by guardrails.
        """
        advisor = DSPyAdvisor(enable_guardrails=True)
        
        # Manually test the bounded suggestion creation
        from dspy.advisor import (
            DEFAULT_POSITION_SIZE,
            SHARPE_LOW_THRESHOLD,
            MetricsSnapshot,
        )
        
        metrics = MetricsSnapshot(
            timestamp=datetime.now(),
            exploit_id="test",
            sharpe_ratio=0.1,  # Very low
            drawdown_contribution=0.5,
            capital_efficiency=0.2,
            total_trades=100,
            win_rate=0.5,
            avg_profit_per_trade=0.01,
            max_drawdown=100.0,
            deployed_capital_avg=1000.0,
        )
        
        # Try to create a suggestion with 50% reduction (extreme)
        suggestion = advisor._create_bounded_suggestion(
            exploit_id="test",
            parameter_name="position_size_multiplier",
            current_value=DEFAULT_POSITION_SIZE,
            suggested_value=0.5,  # -50% change (extreme)
            rationale="Test extreme change",
            confidence=0.9,
            metrics=metrics,
        )
        
        # Should be bounded to -10% max for allocation weights
        if suggestion:  # May be None if no change after bounding
            assert suggestion.suggested_value >= DEFAULT_POSITION_SIZE * 0.90
            assert abs(suggestion.delta) <= 0.10
    
    def test_multiple_violations_tracked(self):
        """Test that multiple violations are tracked across suggestions."""
        advisor = DSPyAdvisor(min_trades_for_suggestion=5, enable_guardrails=True)
        
        # Create scenarios that would trigger multiple violations if unbounded
        # (In practice, the advisor doesn't create suggestions that violate,
        # but we can test the guardrail validation directly)
        
        advisor.guardrails.validate_suggestion("stop_loss_percent", 0.05, 0.10)  # Exceeds
        advisor.guardrails.validate_suggestion("position_size_multiplier", 1.0, 1.30)  # Exceeds
        advisor.guardrails.validate_suggestion("leverage", 1.0, 2.0)  # Forbidden
        
        stats = advisor.get_guardrail_stats()
        assert stats["total_violations"] == 3
    
    def test_safety_overrides_intelligence_in_advisor(self):
        """Test that safety (guardrails) overrides intelligence (DSPy suggestions).
        
        This is the key principle: even if DSPy calculates that a 30% change would
        be optimal, guardrails should limit it to the safe bound.
        """
        advisor = DSPyAdvisor(enable_guardrails=True)
        
        # Test with position_size_multiplier (±10% bound)
        bounded_value = advisor.guardrails.apply_bounds(
            parameter_name="position_size_multiplier",
            current_value=1.0,
            suggested_value=1.30,  # DSPy suggests +30%
        )
        
        # Should be clamped to +10%
        assert bounded_value == pytest.approx(1.10)
        
        # Test with stop_loss_percent (±20% bound)
        bounded_value = advisor.guardrails.apply_bounds(
            parameter_name="stop_loss_percent",
            current_value=0.05,
            suggested_value=0.10,  # DSPy suggests +100% (doubling)
        )
        
        # Should be clamped to +20%
        assert bounded_value == pytest.approx(0.05 * 1.20)


class TestForbiddenActions:
    """Test that forbidden actions are prevented."""
    
    def test_cannot_place_orders(self):
        """Test that DSPy cannot place orders."""
        advisor = DSPyAdvisor(enable_guardrails=True)
        
        is_valid, violation = advisor.guardrails.validate_suggestion(
            parameter_name="place_order",
            current_value=0.0,
            suggested_value=1.0,
        )
        
        assert not is_valid
        assert violation is not None
        assert "forbidden" in violation.reason.lower()
    
    def test_cannot_change_leverage_caps(self):
        """Test that DSPy cannot change leverage caps."""
        advisor = DSPyAdvisor(enable_guardrails=True)
        
        is_valid, violation = advisor.guardrails.validate_suggestion(
            parameter_name="max_leverage",
            current_value=3.0,
            suggested_value=5.0,
        )
        
        assert not is_valid
        assert violation is not None
        assert "forbidden" in violation.reason.lower()
    
    def test_cannot_disable_risk_controls(self):
        """Test that DSPy cannot disable risk controls."""
        advisor = DSPyAdvisor(enable_guardrails=True)
        
        is_valid, violation = advisor.guardrails.validate_suggestion(
            parameter_name="enable_risk_controls",
            current_value=1.0,
            suggested_value=0.0,
        )
        
        assert not is_valid
        assert violation is not None
        assert "forbidden" in violation.reason.lower()


class TestBoundsComplianceSummary:
    """Comprehensive test to prove all bounds are respected."""
    
    def test_comprehensive_bounds_compliance(self):
        """Comprehensive test proving all suggestions respect bounds.
        
        This test creates a variety of trading scenarios and verifies that
        ALL suggestions generated by the advisor comply with the guardrails:
        - Thresholds: ±20%
        - Allocation weights: ±10%
        - Forbidden parameters: Cannot be adjusted
        """
        advisor = DSPyAdvisor(min_trades_for_suggestion=10, enable_guardrails=True)
        
        # Scenario 1: Low Sharpe (should suggest position size reduction)
        for i in range(25):
            profit = 0.05 if i % 2 == 0 else -0.04
            trade = create_test_trade(i, "low_sharpe", profit)
            advisor.observe_trade(trade)
        
        # Scenario 2: High drawdown (should suggest stop loss tightening)
        profits = [0.01] * 20 + [-0.10] * 5
        for i, profit in enumerate(profits):
            trade = create_test_trade(i + 100, "high_drawdown", profit)
            advisor.observe_trade(trade)
        
        # Scenario 3: Low capital efficiency (should suggest reducing holding time)
        for i in range(35):
            trade = create_test_trade(i + 200, "low_cap_eff", 0.005, entry_stake=1000.0)
            advisor.observe_trade(trade)
        
        # Scenario 4: High performance (should suggest position size increase)
        for i in range(30):
            trade = create_test_trade(i + 300, "high_perf", 0.05, entry_stake=1000.0)
            advisor.observe_trade(trade)
        
        # Generate all suggestions
        suggestions = advisor.generate_suggestions()
        
        # Verify bounds compliance for ALL suggestions
        violations = []
        for suggestion in suggestions:
            if suggestion.parameter_name == "position_size_multiplier":
                # Allocation weight: ±10% bound
                max_change = 0.10
                change_pct = abs(suggestion.delta)
                if change_pct > max_change:
                    violations.append(
                        f"{suggestion.parameter_name}: {change_pct:.2%} > {max_change:.0%}"
                    )
            
            elif suggestion.parameter_name in ["stop_loss_percent", "max_holding_hours"]:
                # Threshold: ±20% bound
                max_change = 0.20
                change_pct = abs(suggestion.delta / suggestion.current_value)
                if change_pct > max_change:
                    violations.append(
                        f"{suggestion.parameter_name}: {change_pct:.2%} > {max_change:.0%}"
                    )
        
        # Assert no violations
        assert len(violations) == 0, f"Bound violations detected: {violations}"
        
        # Verify we got some suggestions (otherwise test is trivial)
        assert len(suggestions) > 0, "No suggestions generated - test may be invalid"
        
        # Log summary
        print(f"\nBounds Compliance Summary:")
        print(f"  Total suggestions: {len(suggestions)}")
        print(f"  Violations: {len(violations)}")
        print(f"  Compliance: 100%")
