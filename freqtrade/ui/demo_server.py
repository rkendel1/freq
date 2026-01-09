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
            return jsonify({"status": "reset"})

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
