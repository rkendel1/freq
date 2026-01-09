"""
Demo Server - Web UI for visualizing execution engine flow.

This provides a step-by-step visualization of how data flows through the system:
1. Initial State (capital, positions, market data)
2. Exploit Evaluation (generate Actions)
3. Risk Checks (validate Actions)
4. Execution (execute approved Actions)
5. Results (update state, show PnL)

Run with: python -m freqtrade.ui.demo_server
"""

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request

from freqtrade.core.actions import Action, ActionType, Side
from freqtrade.core.risk import RiskLimits, RiskManager
from freqtrade.core.state import CapitalState, ExecutionEngineState, create_initial_state
from freqtrade.exploits.exploit_module import ExecutionState, ExecutionResult
from freqtrade.ui.demo_exploit import DemoExploit
from freqtrade.ui.automated_exploit import AutomatedExploit
from freqtrade.ui.market_simulator import MarketSimulator, MarketCondition


logger = logging.getLogger(__name__)


class DemoServer:
    """Demo server for visualizing execution engine flow."""

    def __init__(self):
        """Initialize the demo server."""
        self.app = Flask(__name__, template_folder=str(Path(__file__).parent / "templates"))
        self.setup_routes()

        # Initial state
        self.engine_state = create_initial_state(10000.0)
        self.risk_limits = RiskLimits(
            max_position_size=0.2,  # 20% max per position
            max_total_exposure=0.8,  # 80% max total
            max_open_positions=3,
            max_loss_per_trade=0.1,  # 10% max loss per trade
            max_daily_loss=0.2,  # 20% max daily loss
            position_cooldown=0,
        )
        self.risk_manager = RiskManager(self.risk_limits)
        self.exploit = DemoExploit({})

        # Flow tracking
        self.flow_history: list[dict[str, Any]] = []
        self.current_step = 0
        
        # Track simulated open positions for profit calculation
        self.demo_positions: list[dict[str, Any]] = []
        
        # Automated mode
        self.automated_mode = False
        self.automated_exploit = AutomatedExploit({})
        self.market_simulator = MarketSimulator(initial_price=50000.0, condition="mixed")
        self.price_history: list[dict[str, Any]] = []  # For charting

    def setup_routes(self):
        """Setup Flask routes."""

        @self.app.route("/")
        def index():
            """Render the main demo page."""
            return render_template("demo.html")

        @self.app.route("/api/state")
        def get_state():
            """Get current engine state."""
            return jsonify(
                {
                    "capital": {
                        "available": self.engine_state.capital.available_capital,
                        "deployed": self.engine_state.capital.deployed_capital,
                        "pnl_realized": self.engine_state.capital.pnl_realized,
                        "pnl_unrealized": self.engine_state.capital.pnl_unrealized,
                    },
                    "open_trades": len(self.engine_state.open_trades),
                    "closed_trades": len(self.engine_state.closed_trades),
                    "total_actions": self.engine_state.total_actions,
                    "successful_actions": self.engine_state.successful_actions,
                    "failed_actions": self.engine_state.failed_actions,
                }
            )

        @self.app.route("/api/reset", methods=["POST"])
        def reset():
            """Reset the demo to initial state."""
            self.engine_state = create_initial_state(10000.0)
            self.flow_history = []
            self.current_step = 0
            self.demo_positions = []
            self.exploit.clear_simulated_positions()
            self.automated_exploit.clear_simulated_positions()
            self.market_simulator.reset()
            self.price_history = []
            self.automated_mode = False
            return jsonify({"status": "reset"})

        @self.app.route("/api/automated/start", methods=["POST"])
        def start_automated():
            """Start automated mode."""
            data = request.json or {}
            condition = data.get("condition", "mixed")
            
            # Validate market condition
            valid_conditions = ["mixed", "trending_up", "trending_down", "volatile", "ranging"]
            if condition not in valid_conditions:
                return jsonify({"error": f"Invalid condition. Must be one of: {valid_conditions}"}), 400
            
            # Reset and configure
            self.automated_mode = True
            self.market_simulator.reset(condition=condition)
            self.automated_exploit.clear_simulated_positions()
            self.price_history = []
            
            logger.info(f"Automated mode started with {condition} market condition")
            return jsonify({"status": "started", "condition": condition})

        @self.app.route("/api/automated/stop", methods=["POST"])
        def stop_automated():
            """Stop automated mode."""
            self.automated_mode = False
            logger.info("Automated mode stopped")
            return jsonify({"status": "stopped"})

        @self.app.route("/api/automated/tick", methods=["POST"])
        def automated_tick():
            """Execute one automated tick (price update + decision)."""
            if not self.automated_mode:
                return jsonify({"error": "Automated mode not active"}), 400
            
            # Generate market tick
            tick = self.market_simulator.generate_tick()
            
            # Record price for charting
            self.price_history.append({
                "timestamp": tick.timestamp,
                "price": tick.price,
            })
            
            # Create flow trace with automated exploit
            flow_trace = self._execute_automated_tick(tick)
            self.flow_history.append(flow_trace)
            
            return jsonify(flow_trace)

        @self.app.route("/api/automated/status")
        def automated_status():
            """Get automated mode status."""
            return jsonify({
                "active": self.automated_mode,
                "condition": self.market_simulator.condition,
                "current_price": self.market_simulator.current_price,
                "price_change_pct": self.market_simulator.get_price_change_percent(),
                "tick_count": self.market_simulator.tick_count,
                "process_stats": self.automated_exploit.get_statistics(),
            })

        @self.app.route("/api/price-history")
        def price_history():
            """Get price history for charting."""
            return jsonify({"prices": self.price_history[-100:]})  # Last 100 ticks

        @self.app.route("/api/execute-step", methods=["POST"])
        def execute_step():
            """Execute one step of the flow and return the trace."""
            data = request.json or {}
            scenario = data.get("scenario", "open_long")

            # Create flow trace
            flow_trace = self._execute_flow_step(scenario)
            self.flow_history.append(flow_trace)

            return jsonify(flow_trace)

        @self.app.route("/api/history")
        def get_history():
            """Get flow execution history."""
            return jsonify({"history": self.flow_history})

    def _execute_flow_step(self, scenario: str) -> dict[str, Any]:
        """
        Execute one flow step and return detailed trace.

        Args:
            scenario: Scenario to execute (open_long, close_position, etc.)

        Returns:
            Flow trace showing all intermediate values
        """
        timestamp = int(datetime.now(timezone.utc).timestamp())

        # Step 1: Initial State
        initial_state = {
            "available_capital": self.engine_state.capital.available_capital,
            "deployed_capital": self.engine_state.capital.deployed_capital,
            "pnl_realized": self.engine_state.capital.pnl_realized,
            "open_positions": len(self.engine_state.open_trades),
        }

        # Step 2: Create ExecutionState for exploit
        exec_state = ExecutionState(
            symbol="BTC/USDT",
            available_capital=self.engine_state.capital.available_capital,
            deployed_capital=self.engine_state.capital.deployed_capital,
            open_positions=list(self.engine_state.open_trades),
            recent_trades=list(self.engine_state.closed_trades[-5:]),
            current_price=50000.0,
            timestamp=timestamp,
        )

        # Step 3: Exploit generates Actions
        self.exploit.set_scenario(scenario)
        actions = self.exploit.evaluate(exec_state)

        actions_data = []
        for action in actions:
            actions_data.append(
                {
                    "type": action.type.name if hasattr(action, "type") else str(action.type),
                    "symbol": action.symbol,
                    "size": action.size if hasattr(action, "size") else None,
                    "reason": action.reason if hasattr(action, "reason") else "N/A",
                }
            )

        # Step 4: Risk checks
        risk_checks = []
        approved_actions = []
        for action in actions:
            # For demo purposes, simulate risk check
            if isinstance(action, Action):
                # Check if we have enough capital
                required_capital = exec_state.available_capital * action.size
                can_allocate = required_capital <= self.engine_state.capital.available_capital

                risk_result = {
                    "action": f"{action.type.name} {action.symbol}",
                    "required_capital": required_capital,
                    "available_capital": self.engine_state.capital.available_capital,
                    "approved": can_allocate,
                    "reason": "Approved" if can_allocate else "Insufficient capital",
                }
                risk_checks.append(risk_result)

                if can_allocate:
                    approved_actions.append(action)

        # Step 5: Execute approved actions
        execution_results = []
        for action in approved_actions:
            # Simulate execution
            if action.type == ActionType.OPEN:
                required_capital = exec_state.available_capital * action.size
                success = self.engine_state.capital.allocate(required_capital)

                if success:
                    self.engine_state.total_actions += 1
                    self.engine_state.successful_actions += 1
                    
                    # Track position for later closing with profit
                    self.demo_positions.append({
                        "symbol": action.symbol,
                        "side": action.side,
                        "entry_price": exec_state.current_price,
                        "size": required_capital,
                        "timestamp": timestamp,
                    })
                    
                    # Also track in exploit for scenario logic
                    self.exploit.add_simulated_position(
                        action.symbol, action.side, exec_state.current_price, required_capital
                    )

                    result = ExecutionResult(
                        success=True,
                        order_ids=["demo_order_123"],
                        filled_size=action.size,
                        fees=required_capital * 0.001,  # 0.1% fee
                        timestamp=timestamp,
                    )
                else:
                    self.engine_state.total_actions += 1
                    self.engine_state.failed_actions += 1

                    result = ExecutionResult(
                        success=False,
                        order_ids=[],
                        filled_size=0.0,
                        fees=0.0,
                        timestamp=timestamp,
                        error_message="Capital allocation failed",
                    )

                execution_results.append(
                    {
                        "action": f"{action.type.name} {action.symbol}",
                        "success": result.success,
                        "filled_size": result.filled_size,
                        "fees": result.fees,
                        "error": result.error_message,
                    }
                )

                # Callback to exploit
                self.exploit.on_execution_result(action, result)
                
            elif action.type == ActionType.CLOSE:
                # Simulate closing position with profit
                if self.demo_positions:
                    # Retrieve and remove the first position atomically
                    position = self.demo_positions.pop(0)
                    entry_capital = position["size"]
                    
                    # Simulate 8% profit on the position
                    # This is a demo value chosen to clearly show profitable outcomes
                    # In real trading, profit depends on market movement
                    profit_pct = 0.08
                    profit_amount = entry_capital * profit_pct
                    exit_capital = entry_capital + profit_amount
                    close_fee = exit_capital * 0.001  # 0.1% fee
                    net_profit = profit_amount - close_fee
                    
                    # Return capital plus profit
                    self.engine_state.capital.release(entry_capital)
                    # Add profit to available capital
                    self.engine_state.capital.available_capital += net_profit
                    self.engine_state.capital.pnl_realized += net_profit
                    
                    # Also remove from exploit tracking (maintains sync with demo_positions)
                    if self.exploit.simulated_positions:
                        self.exploit.simulated_positions.pop(0)
                    
                    self.engine_state.total_actions += 1
                    self.engine_state.successful_actions += 1
                    
                    result = ExecutionResult(
                        success=True,
                        order_ids=["demo_order_456"],
                        filled_size=1.0,
                        fees=close_fee,
                        timestamp=timestamp,
                    )
                    
                    execution_results.append(
                        {
                            "action": f"{action.type.name} {action.symbol}",
                            "success": result.success,
                            "filled_size": result.filled_size,
                            "fees": result.fees,
                            "profit": net_profit,
                            "profit_pct": profit_pct * 100,
                            "error": result.error_message,
                        }
                    )
                    
                    # Callback to exploit
                    self.exploit.on_execution_result(action, result)

        # Step 6: Final State
        final_state = {
            "available_capital": self.engine_state.capital.available_capital,
            "deployed_capital": self.engine_state.capital.deployed_capital,
            "pnl_realized": self.engine_state.capital.pnl_realized,
            "open_positions": len(self.engine_state.open_trades),
        }

        # Build complete flow trace
        self.current_step += 1
        return {
            "step": self.current_step,
            "scenario": scenario,
            "timestamp": timestamp,
            "flow": {
                "1_initial_state": initial_state,
                "2_execution_state": {
                    "symbol": exec_state.symbol,
                    "available_capital": exec_state.available_capital,
                    "deployed_capital": exec_state.deployed_capital,
                    "current_price": exec_state.current_price,
                },
                "3_actions_generated": actions_data,
                "4_risk_checks": risk_checks,
                "5_execution_results": execution_results,
                "6_final_state": final_state,
            },
            "state_changes": {
                "capital_change": final_state["available_capital"]
                - initial_state["available_capital"],
                "deployed_change": final_state["deployed_capital"]
                - initial_state["deployed_capital"],
            },
        }

    def _execute_automated_tick(self, tick) -> dict[str, Any]:
        """
        Execute one automated tick with market data and process evaluations.
        
        Args:
            tick: MarketTick from simulator
            
        Returns:
            Flow trace for this tick
        """
        timestamp = tick.timestamp
        
        # Step 1: Initial State
        initial_state = {
            "available_capital": self.engine_state.capital.available_capital,
            "deployed_capital": self.engine_state.capital.deployed_capital,
            "pnl_realized": self.engine_state.capital.pnl_realized,
            "open_positions": len(self.automated_exploit.simulated_positions),
            "current_price": tick.price,
        }
        
        # Step 2: Create ExecutionState for exploit
        exec_state = ExecutionState(
            symbol="BTC/USDT",
            available_capital=self.engine_state.capital.available_capital,
            deployed_capital=self.engine_state.capital.deployed_capital,
            open_positions=[],  # Using simulated positions
            recent_trades=[],
            current_price=tick.price,
            timestamp=timestamp,
        )
        
        # Step 3: Automated exploit generates Actions based on market analysis
        actions = self.automated_exploit.evaluate(exec_state)
        
        actions_data = []
        for action in actions:
            actions_data.append({
                "type": action.type.name,
                "symbol": action.symbol,
                "side": action.side.name,
                "size": action.size,
                "reason": action.reason,
            })
        
        # Step 4: Risk checks
        risk_checks = []
        approved_actions = []
        for action in actions:
            if action.type == ActionType.OPEN:
                required_capital = exec_state.available_capital * action.size
                can_allocate = required_capital <= self.engine_state.capital.available_capital
                
                risk_result = {
                    "action": f"{action.type.name} {action.side.name} {action.symbol}",
                    "required_capital": required_capital,
                    "available_capital": self.engine_state.capital.available_capital,
                    "approved": can_allocate,
                    "reason": "Approved" if can_allocate else "Insufficient capital",
                }
                risk_checks.append(risk_result)
                
                if can_allocate:
                    approved_actions.append(action)
            else:
                # CLOSE actions don't need capital check
                risk_checks.append({
                    "action": f"{action.type.name} {action.side.name} {action.symbol}",
                    "approved": True,
                    "reason": "Close position",
                })
                approved_actions.append(action)
        
        # Step 5: Execute approved actions
        execution_results = []
        for action in approved_actions:
            if action.type == ActionType.OPEN:
                required_capital = exec_state.available_capital * action.size
                success = self.engine_state.capital.allocate(required_capital)
                
                if success:
                    self.engine_state.total_actions += 1
                    self.engine_state.successful_actions += 1
                    
                    # Track position
                    self.automated_exploit.add_simulated_position(
                        action.symbol, action.side, tick.price, required_capital
                    )
                    
                    result = ExecutionResult(
                        success=True,
                        order_ids=[f"auto_order_{timestamp}"],
                        filled_size=action.size,
                        fees=required_capital * 0.001,
                        timestamp=timestamp,
                    )
                    
                    execution_results.append({
                        "action": f"{action.type.name} {action.side.name} {action.symbol}",
                        "success": True,
                        "filled_size": result.filled_size,
                        "fees": result.fees,
                        "entry_price": tick.price,
                    })
                    
                    self.automated_exploit.on_execution_result(action, result)
                    
            elif action.type == ActionType.CLOSE:
                if self.automated_exploit.simulated_positions:
                    position = self.automated_exploit.simulated_positions[0]
                    entry_capital = position.size
                    
                    # Calculate realistic P&L based on actual price movement
                    if position.side == Side.LONG:
                        pnl_pct = (tick.price - position.entry_price) / position.entry_price
                    else:  # SHORT
                        pnl_pct = (position.entry_price - tick.price) / position.entry_price
                    
                    profit_amount = entry_capital * pnl_pct
                    close_fee = (entry_capital + profit_amount) * 0.001
                    net_profit = profit_amount - close_fee
                    
                    # Return capital plus profit
                    self.engine_state.capital.release(entry_capital)
                    self.engine_state.capital.available_capital += net_profit
                    self.engine_state.capital.pnl_realized += net_profit
                    
                    # Remove position (handled in exploit on_execution_result)
                    
                    self.engine_state.total_actions += 1
                    self.engine_state.successful_actions += 1
                    
                    result = ExecutionResult(
                        success=True,
                        order_ids=[f"auto_order_{timestamp}"],
                        filled_size=1.0,
                        fees=close_fee,
                        timestamp=timestamp,
                    )
                    
                    execution_results.append({
                        "action": f"{action.type.name} {action.side.name} {action.symbol}",
                        "success": True,
                        "filled_size": 1.0,
                        "fees": close_fee,
                        "profit": net_profit,
                        "profit_pct": pnl_pct * 100,
                        "exit_price": tick.price,
                        "entry_price": position.entry_price,
                    })
                    
                    self.automated_exploit.on_execution_result(action, result)
        
        # Step 6: Final State
        final_state = {
            "available_capital": self.engine_state.capital.available_capital,
            "deployed_capital": self.engine_state.capital.deployed_capital,
            "pnl_realized": self.engine_state.capital.pnl_realized,
            "open_positions": len(self.automated_exploit.simulated_positions),
            "current_price": tick.price,
        }
        
        # Build flow trace
        self.current_step += 1
        
        # Generate a descriptive scenario label based on actions
        scenario_label = "automated_tick"
        if actions_data:
            action_type = actions_data[0].get("type", "").lower()
            if action_type == "open":
                side = actions_data[0].get("side", "").lower()
                scenario_label = f"automated_open_{side}"
            elif action_type == "close":
                scenario_label = "automated_close"
        
        return {
            "step": self.current_step,
            "mode": "automated",
            "scenario": scenario_label,
            "timestamp": timestamp,
            "market_data": {
                "price": tick.price,
                "volume": tick.volume,
                "condition": tick.condition,
            },
            "flow": {
                "1_initial_state": initial_state,
                "2_execution_state": {
                    "symbol": exec_state.symbol,
                    "available_capital": exec_state.available_capital,
                    "deployed_capital": exec_state.deployed_capital,
                    "current_price": tick.price,
                },
                "3_actions_generated": actions_data,
                "4_risk_checks": risk_checks,
                "5_execution_results": execution_results,
                "6_final_state": final_state,
            },
            "state_changes": {
                "capital_change": final_state["available_capital"] - initial_state["available_capital"],
                "deployed_change": final_state["deployed_capital"] - initial_state["deployed_capital"],
                "price_change": tick.price - initial_state["current_price"] if self.price_history else 0,
            },
        }

    def run(self, host: str = "127.0.0.1", port: int = 5000, debug: bool = True):
        """
        Run the demo server.

        Args:
            host: Host to bind to
            port: Port to bind to
            debug: Enable debug mode
        """
        logger.info(f"Starting demo server on http://{host}:{port}")
        self.app.run(host=host, port=port, debug=debug)


def main():
    """Run the demo server."""
    logging.basicConfig(level=logging.INFO)
    server = DemoServer()
    server.run()


if __name__ == "__main__":
    main()
