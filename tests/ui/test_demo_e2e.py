"""
End-to-end tests for the demo UI and execution flow.

These tests validate the complete flow from initial state through
action generation, risk checks, execution, and final state updates.
"""

import pytest
from datetime import datetime, timezone

from freqtrade.core.actions import Action, ActionType, Side
from freqtrade.core.risk import RiskLimits, RiskManager
from freqtrade.core.state import create_initial_state
from freqtrade.exploits.exploit_module import ExecutionState, ExecutionResult
from freqtrade.ui.demo_exploit import DemoExploit


class TestDemoEndToEnd:
    """End-to-end tests for the demo flow."""

    def test_complete_flow_open_long(self):
        """Test complete flow for opening a long position."""
        # Step 1: Initial state
        initial_capital = 10000.0
        engine_state = create_initial_state(initial_capital)
        
        assert engine_state.capital.available_capital == initial_capital
        assert engine_state.capital.deployed_capital == 0.0
        assert len(engine_state.open_trades) == 0
        
        # Step 2: Create execution state
        exec_state = ExecutionState(
            symbol="BTC/USDT",
            available_capital=engine_state.capital.available_capital,
            deployed_capital=engine_state.capital.deployed_capital,
            open_positions=list(engine_state.open_trades),
            recent_trades=[],
            current_price=50000.0,
            timestamp=int(datetime.now(timezone.utc).timestamp()),
        )
        
        # Step 3: Exploit generates action
        exploit = DemoExploit({})
        exploit.set_scenario("open_long")
        actions = exploit.evaluate(exec_state)
        
        assert len(actions) == 1
        action = actions[0]
        assert action.type == ActionType.OPEN
        assert action.side == Side.LONG
        assert action.symbol == "BTC/USDT"
        assert action.size == 0.1  # 10% of capital
        
        # Step 4: Risk check (simulated)
        required_capital = exec_state.available_capital * action.size
        can_allocate = required_capital <= engine_state.capital.available_capital
        assert can_allocate is True
        
        # Step 5: Execute (allocate capital)
        success = engine_state.capital.allocate(required_capital)
        assert success is True
        
        # Step 6: Verify final state
        expected_deployed = initial_capital * 0.1
        assert engine_state.capital.deployed_capital == expected_deployed
        assert engine_state.capital.available_capital == initial_capital - expected_deployed
        
        # Step 7: Callback to exploit
        result = ExecutionResult(
            success=True,
            order_ids=["test_order_1"],
            filled_size=action.size,
            fees=required_capital * 0.001,
            timestamp=int(datetime.now(timezone.utc).timestamp()),
        )
        exploit.on_execution_result(action, result)
        assert exploit.execution_count == 1

    def test_complete_flow_risk_rejection(self):
        """Test complete flow when action is rejected by risk limits."""
        # Step 1: Initial state
        initial_capital = 10000.0
        engine_state = create_initial_state(initial_capital)
        
        # Step 2: Create execution state
        exec_state = ExecutionState(
            symbol="BTC/USDT",
            available_capital=engine_state.capital.available_capital,
            deployed_capital=engine_state.capital.deployed_capital,
            open_positions=[],
            recent_trades=[],
            current_price=50000.0,
            timestamp=int(datetime.now(timezone.utc).timestamp()),
        )
        
        # Step 3: Exploit generates large action that should be rejected
        exploit = DemoExploit({})
        exploit.set_scenario("risk_rejection")
        actions = exploit.evaluate(exec_state)
        
        assert len(actions) == 1
        action = actions[0]
        assert action.size == 0.95  # 95% - too large
        
        # Step 4: Risk check - should fail
        required_capital = exec_state.available_capital * action.size
        
        # Create risk manager
        risk_limits = RiskLimits(
            max_position_size=0.2,  # 20% max
            max_total_exposure=0.8,
            max_open_positions=3,
            position_cooldown=0,
        )
        risk_manager = RiskManager(risk_limits)
        
        # Check if position size exceeds limit
        position_size_ratio = action.size
        exceeds_limit = position_size_ratio > risk_limits.max_position_size
        
        assert exceeds_limit is True
        
        # Step 5: Action should not be executed
        # (In real system, risk manager would reject before execution)
        
        # Step 6: Verify state unchanged
        assert engine_state.capital.available_capital == initial_capital
        assert engine_state.capital.deployed_capital == 0.0

    def test_complete_flow_multiple_positions(self):
        """Test complete flow for opening multiple positions."""
        # Step 1: Initial state
        initial_capital = 10000.0
        engine_state = create_initial_state(initial_capital)
        
        # Step 2: Create execution state
        exec_state = ExecutionState(
            symbol="BTC/USDT",
            available_capital=engine_state.capital.available_capital,
            deployed_capital=engine_state.capital.deployed_capital,
            open_positions=[],
            recent_trades=[],
            current_price=50000.0,
            timestamp=int(datetime.now(timezone.utc).timestamp()),
        )
        
        # Step 3: Exploit generates multiple actions
        exploit = DemoExploit({})
        exploit.set_scenario("multiple_positions")
        actions = exploit.evaluate(exec_state)
        
        assert len(actions) == 2
        
        # Step 4: Execute both actions
        total_deployed = 0.0
        for action in actions:
            required_capital = engine_state.capital.available_capital * action.size
            success = engine_state.capital.allocate(required_capital)
            assert success is True
            total_deployed += required_capital
            
            result = ExecutionResult(
                success=True,
                order_ids=[f"order_{action.symbol}"],
                filled_size=action.size,
                fees=required_capital * 0.001,
                timestamp=int(datetime.now(timezone.utc).timestamp()),
            )
            exploit.on_execution_result(action, result)
        
        # Step 5: Verify final state
        # First action: 10% of 10000 = 1000
        # Second action: 15% of 9000 = 1350
        # Total deployed should be 2350
        assert engine_state.capital.deployed_capital == pytest.approx(2350.0, rel=0.01)
        assert engine_state.capital.available_capital == pytest.approx(
            initial_capital - 2350.0, rel=0.01
        )
        assert exploit.execution_count == 2

    def test_complete_flow_no_action(self):
        """Test complete flow when exploit generates no actions."""
        # Step 1: Initial state
        initial_capital = 10000.0
        engine_state = create_initial_state(initial_capital)
        
        # Step 2: Create execution state
        exec_state = ExecutionState(
            symbol="BTC/USDT",
            available_capital=engine_state.capital.available_capital,
            deployed_capital=engine_state.capital.deployed_capital,
            open_positions=[],
            recent_trades=[],
            current_price=50000.0,
            timestamp=int(datetime.now(timezone.utc).timestamp()),
        )
        
        # Step 3: Exploit generates no actions
        exploit = DemoExploit({})
        exploit.set_scenario("no_action")
        actions = exploit.evaluate(exec_state)
        
        assert len(actions) == 0
        
        # Step 4: No risk checks needed
        
        # Step 5: No execution
        
        # Step 6: Verify state unchanged
        assert engine_state.capital.available_capital == initial_capital
        assert engine_state.capital.deployed_capital == 0.0
        assert len(engine_state.open_trades) == 0

    def test_capital_state_transitions(self):
        """Test capital state transitions through complete flow."""
        # Initial state
        engine_state = create_initial_state(10000.0)
        
        # Transition 1: Allocate capital
        assert engine_state.capital.allocate(1000.0) is True
        assert engine_state.capital.available_capital == 9000.0
        assert engine_state.capital.deployed_capital == 1000.0
        
        # Transition 2: Try to allocate more than available
        assert engine_state.capital.allocate(10000.0) is False
        assert engine_state.capital.available_capital == 9000.0
        assert engine_state.capital.deployed_capital == 1000.0
        
        # Transition 3: Release capital with profit
        engine_state.capital.release(1000.0, profit=100.0)
        assert engine_state.capital.available_capital == 10100.0
        assert engine_state.capital.deployed_capital == 0.0
        assert engine_state.capital.pnl_realized == 100.0
        
        # Transition 4: Release capital with loss
        engine_state.capital.allocate(1000.0)
        engine_state.capital.release(1000.0, profit=-50.0)
        assert engine_state.capital.available_capital == 10050.0
        assert engine_state.capital.deployed_capital == 0.0
        assert engine_state.capital.pnl_realized == 50.0

    def test_exploit_scenario_switching(self):
        """Test switching between different exploit scenarios."""
        exploit = DemoExploit({})
        
        exec_state = ExecutionState(
            symbol="BTC/USDT",
            available_capital=10000.0,
            deployed_capital=0.0,
            open_positions=[],
            recent_trades=[],
            current_price=50000.0,
            timestamp=int(datetime.now(timezone.utc).timestamp()),
        )
        
        # Test different scenarios
        scenarios = [
            ("open_long", 1, ActionType.OPEN, Side.LONG),
            ("open_short", 1, ActionType.OPEN, Side.SHORT),
            ("no_action", 0, None, None),
            ("multiple_positions", 2, ActionType.OPEN, Side.LONG),
        ]
        
        for scenario, expected_count, expected_type, expected_side in scenarios:
            exploit.set_scenario(scenario)
            actions = exploit.evaluate(exec_state)
            
            assert len(actions) == expected_count, f"Scenario {scenario} failed"
            
            if expected_count > 0:
                assert actions[0].type == expected_type
                assert actions[0].side == expected_side


class TestDemoIntegration:
    """Integration tests for demo components."""

    def test_full_position_lifecycle(self):
        """Test complete position lifecycle: open → hold → close."""
        # Setup
        engine_state = create_initial_state(10000.0)
        exploit = DemoExploit({})
        
        # Phase 1: Open position
        exec_state = ExecutionState(
            symbol="BTC/USDT",
            available_capital=engine_state.capital.available_capital,
            deployed_capital=engine_state.capital.deployed_capital,
            open_positions=[],
            recent_trades=[],
            current_price=50000.0,
            timestamp=int(datetime.now(timezone.utc).timestamp()),
        )
        
        exploit.set_scenario("open_long")
        actions = exploit.evaluate(exec_state)
        
        assert len(actions) == 1
        required_capital = exec_state.available_capital * actions[0].size
        success = engine_state.capital.allocate(required_capital)
        assert success is True
        
        # Simulate adding trade to state
        engine_state.total_actions += 1
        engine_state.successful_actions += 1
        
        # Phase 2: Position is open (simulated)
        assert engine_state.capital.deployed_capital > 0
        
        # Phase 3: Close position (simulated)
        profit = 100.0  # Made $100 profit
        engine_state.capital.release(required_capital, profit=profit)
        
        assert engine_state.capital.deployed_capital == 0.0
        assert engine_state.capital.pnl_realized == profit
        assert engine_state.capital.available_capital == 10100.0

    def test_demo_state_consistency(self):
        """Test that demo maintains consistent state across operations."""
        engine_state = create_initial_state(10000.0)
        
        # Execute multiple operations
        operations = [
            (1000.0, 50.0),   # Allocate 1000, release with 50 profit
            (2000.0, -100.0),  # Allocate 2000, release with 100 loss
            (500.0, 25.0),    # Allocate 500, release with 25 profit
        ]
        
        for capital, profit in operations:
            assert engine_state.capital.allocate(capital) is True
            engine_state.capital.release(capital, profit=profit)
        
        # Final state should be consistent
        expected_pnl = 50.0 - 100.0 + 25.0  # -25
        assert engine_state.capital.pnl_realized == expected_pnl
        assert engine_state.capital.deployed_capital == 0.0
        assert engine_state.capital.available_capital == 10000.0 + expected_pnl
