"""
Tests for DSPy Advisory Layer

These tests verify that the DSPy advisor:
1. Correctly observes metrics (Sharpe, drawdown, capital efficiency)
2. Generates appropriate parameter suggestions
3. Operates in read-only mode (no execution impact)
4. Logs suggestions without applying them
"""

from datetime import datetime, timezone, timedelta
import pytest

from dspy.advisor import DSPyAdvisor, MetricsSnapshot, ParameterSuggestion
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
        total_fees=entry_stake * 0.002,
        funding_fees=0.0,
        holding_duration_seconds=hours_held * 3600,
        holding_duration_hours=hours_held,
        realized_profit=realized_profit,
        profit_ratio=profit_ratio,
        is_open=False,
        exit_reason="roi",
    )


class TestDSPyAdvisor:
    """Test suite for DSPyAdvisor."""
    
    def test_advisor_initialization(self):
        """Test that advisor initializes correctly."""
        advisor = DSPyAdvisor(min_trades_for_suggestion=10, suggestion_confidence_threshold=0.5)
        
        assert advisor.min_trades_for_suggestion == 10
        assert advisor.suggestion_confidence_threshold == 0.5
        assert advisor.trades_by_exploit == {}
        assert advisor.suggestion_history == []
    
    def test_observe_trade(self):
        """Test that advisor can observe trades."""
        advisor = DSPyAdvisor()
        
        trade = create_test_trade(1, "test_exploit", 0.05)
        advisor.observe_trade(trade)
        
        assert "test_exploit" in advisor.trades_by_exploit
        assert len(advisor.trades_by_exploit["test_exploit"]) == 1
        assert advisor.trades_by_exploit["test_exploit"][0].trade_id == 1
    
    def test_observe_multiple_trades(self):
        """Test observing multiple trades for different exploits."""
        advisor = DSPyAdvisor()
        
        # Add trades for exploit A
        for i in range(3):
            trade = create_test_trade(i, "exploit_a", 0.02)
            advisor.observe_trade(trade)
        
        # Add trades for exploit B
        for i in range(5):
            trade = create_test_trade(100 + i, "exploit_b", 0.03)
            advisor.observe_trade(trade)
        
        assert len(advisor.trades_by_exploit["exploit_a"]) == 3
        assert len(advisor.trades_by_exploit["exploit_b"]) == 5
    
    def test_sharpe_ratio_calculation(self):
        """Test Sharpe ratio calculation."""
        advisor = DSPyAdvisor()
        
        # Create trades with consistent returns (high Sharpe)
        trades = [create_test_trade(i, "test", 0.05) for i in range(20)]
        sharpe = advisor._calculate_sharpe_ratio(trades)
        
        # Should be positive for consistent profits
        assert sharpe > 0
        
        # Create trades with volatile returns (low Sharpe)
        volatile_trades = []
        for i in range(20):
            profit = 0.10 if i % 2 == 0 else -0.08
            volatile_trades.append(create_test_trade(i, "test", profit))
        
        sharpe_volatile = advisor._calculate_sharpe_ratio(volatile_trades)
        
        # Consistent returns should have higher Sharpe than volatile
        assert sharpe > sharpe_volatile
    
    def test_sharpe_ratio_empty_trades(self):
        """Test Sharpe ratio with no trades."""
        advisor = DSPyAdvisor()
        sharpe = advisor._calculate_sharpe_ratio([])
        assert sharpe == 0.0
    
    def test_drawdown_contribution_calculation(self):
        """Test drawdown contribution calculation."""
        advisor = DSPyAdvisor()
        
        # Create trades with a drawdown pattern
        trades = []
        profits = [0.05, 0.03, -0.10, -0.05, 0.02, 0.04]
        for i, profit in enumerate(profits):
            trades.append(create_test_trade(i, "test", profit))
        
        drawdown_contrib = advisor._calculate_drawdown_contribution(trades)
        
        # Should be between 0 and 1
        assert 0.0 <= drawdown_contrib <= 1.0
        
        # Should be positive (there was a drawdown)
        assert drawdown_contrib > 0
    
    def test_capital_efficiency_calculation(self):
        """Test capital efficiency calculation."""
        advisor = DSPyAdvisor()
        
        # Create trades with various profits
        trades = [
            create_test_trade(1, "test", 0.10, entry_stake=1000.0),
            create_test_trade(2, "test", 0.05, entry_stake=1000.0),
            create_test_trade(3, "test", 0.08, entry_stake=1000.0),
        ]
        
        capital_eff = advisor._calculate_capital_efficiency(trades)
        
        # Total profit = 100 + 50 + 80 = 230
        # Average deployed = 1000
        # Efficiency = 230 / 1000 = 0.23
        assert abs(capital_eff - 0.23) < 0.01
    
    def test_metrics_snapshot(self):
        """Test creating a metrics snapshot."""
        advisor = DSPyAdvisor()
        
        # Create some trades
        trades = [create_test_trade(i, "test", 0.05) for i in range(10)]
        
        metrics = advisor._create_metrics_snapshot("test", trades)
        
        assert isinstance(metrics, MetricsSnapshot)
        assert metrics.exploit_id == "test"
        assert metrics.total_trades == 10
        assert metrics.sharpe_ratio > 0
        assert 0.0 <= metrics.drawdown_contribution <= 1.0
        assert metrics.capital_efficiency >= 0
        assert 0.0 <= metrics.win_rate <= 1.0
    
    def test_no_suggestions_with_insufficient_trades(self):
        """Test that no suggestions are generated with too few trades."""
        advisor = DSPyAdvisor(min_trades_for_suggestion=20)
        
        # Add only 10 trades
        for i in range(10):
            trade = create_test_trade(i, "test", 0.05)
            advisor.observe_trade(trade)
        
        suggestions = advisor.generate_suggestions()
        
        # Should not generate suggestions
        assert len(suggestions) == 0
    
    def test_low_sharpe_generates_position_size_reduction(self):
        """Test that low Sharpe ratio generates position size reduction suggestion."""
        advisor = DSPyAdvisor(min_trades_for_suggestion=20)
        
        # Create volatile trades (low Sharpe)
        for i in range(30):
            profit = 0.15 if i % 3 == 0 else -0.10
            trade = create_test_trade(i, "volatile", profit)
            advisor.observe_trade(trade)
        
        suggestions = advisor.generate_suggestions()
        
        # Should generate at least one suggestion
        assert len(suggestions) > 0
        
        # Should suggest reducing position size
        position_suggestions = [
            s for s in suggestions if s.parameter_name == "position_size_multiplier"
        ]
        if position_suggestions:
            # Delta should be negative (reduction)
            assert position_suggestions[0].delta < 0
    
    def test_high_drawdown_generates_stop_loss_suggestion(self):
        """Test that high drawdown generates stop loss tightening suggestion."""
        advisor = DSPyAdvisor(min_trades_for_suggestion=20)
        
        # Create trades with occasional large losses
        for i in range(25):
            profit = -0.25 if i % 10 == 0 and i > 0 else 0.03
            trade = create_test_trade(i, "drawdown", profit)
            advisor.observe_trade(trade)
        
        suggestions = advisor.generate_suggestions()
        
        # Should generate suggestions
        assert len(suggestions) > 0
        
        # Should suggest tightening stop loss
        stop_loss_suggestions = [
            s for s in suggestions if s.parameter_name == "stop_loss_percent"
        ]
        if stop_loss_suggestions:
            # Delta should be negative (tighter stop)
            assert stop_loss_suggestions[0].delta < 0
    
    def test_high_performance_generates_size_increase(self):
        """Test that high performance generates position size increase suggestion."""
        advisor = DSPyAdvisor(min_trades_for_suggestion=20)
        
        # Create consistently profitable trades
        for i in range(40):
            profit = 0.08 if i % 10 == 0 else 0.05
            trade = create_test_trade(i, "winner", profit)
            advisor.observe_trade(trade)
        
        suggestions = advisor.generate_suggestions()
        
        # Should generate suggestions
        assert len(suggestions) > 0
        
        # Should suggest increasing position size
        increase_suggestions = [
            s
            for s in suggestions
            if s.parameter_name == "position_size_multiplier" and s.delta > 0
        ]
        assert len(increase_suggestions) > 0
    
    def test_confidence_threshold_filtering(self):
        """Test that suggestions are filtered by confidence threshold."""
        advisor = DSPyAdvisor(
            min_trades_for_suggestion=20, suggestion_confidence_threshold=0.95
        )
        
        # Create trades that would generate low-confidence suggestions
        for i in range(25):
            trade = create_test_trade(i, "test", 0.02)
            advisor.observe_trade(trade)
        
        suggestions = advisor.generate_suggestions()
        
        # All suggestions should meet confidence threshold
        for suggestion in suggestions:
            assert suggestion.confidence >= 0.95
    
    def test_get_metrics_snapshot(self):
        """Test getting metrics snapshot for a specific exploit."""
        advisor = DSPyAdvisor()
        
        # Add trades
        for i in range(10):
            trade = create_test_trade(i, "test", 0.05)
            advisor.observe_trade(trade)
        
        metrics = advisor.get_metrics_snapshot("test")
        
        assert metrics is not None
        assert metrics.exploit_id == "test"
        assert metrics.total_trades == 10
        
        # Non-existent exploit should return None
        assert advisor.get_metrics_snapshot("nonexistent") is None
    
    def test_get_all_metrics(self):
        """Test getting metrics for all exploits."""
        advisor = DSPyAdvisor()
        
        # Add trades for multiple exploits
        for i in range(5):
            advisor.observe_trade(create_test_trade(i, "exploit_a", 0.05))
            advisor.observe_trade(create_test_trade(10 + i, "exploit_b", 0.03))
        
        all_metrics = advisor.get_all_metrics()
        
        assert len(all_metrics) == 2
        assert "exploit_a" in all_metrics
        assert "exploit_b" in all_metrics
        assert all_metrics["exploit_a"].total_trades == 5
        assert all_metrics["exploit_b"].total_trades == 5
    
    def test_reset(self):
        """Test resetting the advisor state."""
        advisor = DSPyAdvisor()
        
        # Add some data
        for i in range(5):
            advisor.observe_trade(create_test_trade(i, "test", 0.05))
        
        advisor.generate_suggestions()
        
        # Verify data exists
        assert len(advisor.trades_by_exploit) > 0
        
        # Reset
        advisor.reset()
        
        # Verify data is cleared
        assert len(advisor.trades_by_exploit) == 0
        assert len(advisor.suggestion_history) == 0
    
    def test_suggestion_history(self):
        """Test that suggestions are stored in history."""
        advisor = DSPyAdvisor(min_trades_for_suggestion=20)
        
        # Create trades that will generate suggestions
        for i in range(30):
            profit = 0.15 if i % 3 == 0 else -0.10
            trade = create_test_trade(i, "test", profit)
            advisor.observe_trade(trade)
        
        suggestions = advisor.generate_suggestions()
        
        # History should contain the suggestions
        assert len(advisor.suggestion_history) == len(suggestions)
        
        # Generate again (should append to history)
        suggestions2 = advisor.generate_suggestions()
        assert len(advisor.suggestion_history) == len(suggestions) + len(suggestions2)
    
    def test_read_only_behavior(self):
        """
        Test that advisor operates in read-only mode.
        
        This test verifies that calling generate_suggestions() does not
        modify the observed trade data.
        """
        advisor = DSPyAdvisor(min_trades_for_suggestion=20)
        
        # Add trades
        original_trades = []
        for i in range(25):
            trade = create_test_trade(i, "test", 0.05)
            advisor.observe_trade(trade)
            original_trades.append(trade)
        
        # Generate suggestions
        suggestions = advisor.generate_suggestions()
        
        # Verify trade data is unchanged
        assert len(advisor.trades_by_exploit["test"]) == 25
        
        # Verify original trades are not modified
        for i, trade in enumerate(advisor.trades_by_exploit["test"]):
            assert trade.trade_id == original_trades[i].trade_id
            assert trade.profit_ratio == original_trades[i].profit_ratio


class TestMetricsSnapshot:
    """Test MetricsSnapshot dataclass."""
    
    def test_metrics_snapshot_creation(self):
        """Test creating a MetricsSnapshot."""
        snapshot = MetricsSnapshot(
            timestamp=datetime.now(),
            exploit_id="test",
            sharpe_ratio=1.5,
            drawdown_contribution=0.2,
            capital_efficiency=0.3,
            total_trades=100,
            win_rate=0.6,
            avg_profit_per_trade=50.0,
            max_drawdown=500.0,
            deployed_capital_avg=1000.0,
        )
        
        assert snapshot.exploit_id == "test"
        assert snapshot.sharpe_ratio == 1.5
        assert snapshot.drawdown_contribution == 0.2
        assert snapshot.capital_efficiency == 0.3


class TestParameterSuggestion:
    """Test ParameterSuggestion dataclass."""
    
    def test_parameter_suggestion_creation(self):
        """Test creating a ParameterSuggestion."""
        metrics = MetricsSnapshot(
            timestamp=datetime.now(),
            exploit_id="test",
            sharpe_ratio=1.5,
            drawdown_contribution=0.2,
            capital_efficiency=0.3,
            total_trades=100,
            win_rate=0.6,
            avg_profit_per_trade=50.0,
            max_drawdown=500.0,
            deployed_capital_avg=1000.0,
        )
        
        suggestion = ParameterSuggestion(
            timestamp=datetime.now(),
            exploit_id="test",
            parameter_name="position_size_multiplier",
            current_value=1.0,
            suggested_value=0.8,
            delta=-0.2,
            rationale="Test rationale",
            confidence=0.8,
            metrics_snapshot=metrics,
        )
        
        assert suggestion.exploit_id == "test"
        assert suggestion.parameter_name == "position_size_multiplier"
        assert suggestion.delta == -0.2
        assert suggestion.confidence == 0.8
