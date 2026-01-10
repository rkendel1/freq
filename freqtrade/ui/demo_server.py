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
from freqtrade.exploits.parameter_manager import ExploitParameterManager
from dspy.advisor import DSPyAdvisor
from freqtrade.metrics.attribution import TradeAttribution


logger = logging.getLogger(__name__)


class DemoServer:
    """Demo server for visualizing execution engine flow."""

    def __init__(self):
        """Initialize the demo server."""
        self.app = Flask(__name__, template_folder=str(Path(__file__).parent / "templates"))
        self.setup_routes()

        # Initial state
        self.initial_capital = 10000.0
        self.current_symbol = "BTC/USDT"
        self.current_price = 50000.0
        
        self.engine_state = create_initial_state(self.initial_capital)
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
        self.market_simulator = MarketSimulator(initial_price=self.current_price, condition="mixed")
        self.price_history: list[dict[str, Any]] = []  # For charting
        
        # DSPy Advisor integration
        self.dspy_advisor = DSPyAdvisor(min_trades_for_suggestion=5, suggestion_confidence_threshold=0.5)
        self.trade_counter = 0  # Track trades for attribution
        
        # Exploit Parameter Manager for all exploits
        self.exploit_manager = ExploitParameterManager({})

    def setup_routes(self):
        """Setup Flask routes."""

        @self.app.route("/")
        def index():
            """Render the main demo page."""
            try:
                return render_template("demo.html")
            except Exception as e:
                logger.error(f"Error rendering demo.html: {e}", exc_info=True)
                return f"Error rendering page: {e}", 500
        
        @self.app.route("/health")
        def health():
            """Health check endpoint."""
            return jsonify({"status": "ok", "message": "Demo server is running"})

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
            self.engine_state = create_initial_state(self.initial_capital)
            self.flow_history = []
            self.current_step = 0
            self.demo_positions = []
            self.exploit.clear_simulated_positions()
            self.automated_exploit.clear_simulated_positions()
            self.market_simulator.reset()
            self.market_simulator.current_price = self.current_price
            self.market_simulator.initial_price = self.current_price
            self.price_history = []
            self.automated_mode = False
            return jsonify({"status": "reset"})

        @self.app.route("/api/config/symbol", methods=["POST"])
        def config_symbol():
            """Update the trading symbol and price."""
            data = request.json or {}
            symbol = data.get("symbol", "BTC/USDT")
            initial_price = data.get("initial_price", 50000.0)
            
            self.current_symbol = symbol
            self.current_price = initial_price
            self.market_simulator.current_price = initial_price
            self.market_simulator.initial_price = initial_price
            
            logger.info(f"Symbol updated to {symbol} at ${initial_price}")
            return jsonify({"status": "updated", "symbol": symbol, "price": initial_price})
        
        @self.app.route("/api/config/capital", methods=["POST"])
        def config_capital():
            """Update the initial capital."""
            data = request.json or {}
            capital = data.get("capital", 10000.0)
            
            if capital < 1000 or capital > 1000000:
                return jsonify({"error": "Capital must be between 1000 and 1000000"}), 400
            
            self.initial_capital = capital
            self.engine_state = create_initial_state(capital)
            
            logger.info(f"Capital updated to ${capital}")
            return jsonify({"status": "updated", "capital": capital})

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

        @self.app.route("/api/dspy/suggestions")
        def get_dspy_suggestions():
            """Get DSPy parameter suggestions."""
            suggestions = self.dspy_advisor.generate_suggestions()
            logger.info(f"DSPy suggestions requested: {len(suggestions)} suggestions generated, {self.trade_counter} trades observed")
            return jsonify({
                "suggestions": [
                    {
                        "timestamp": s.timestamp.isoformat(),
                        "exploit_id": s.exploit_id,
                        "parameter_name": s.parameter_name,
                        "current_value": s.current_value,
                        "suggested_value": s.suggested_value,
                        "delta": s.delta,
                        "rationale": s.rationale,
                        "confidence": s.confidence,
                    }
                    for s in suggestions
                ],
                "total_trades_observed": self.trade_counter,
            })

        @self.app.route("/api/dspy/metrics")
        def get_dspy_metrics():
            """Get current DSPy metrics for all exploits."""
            all_metrics = self.dspy_advisor.get_all_metrics()
            return jsonify({
                "metrics": {
                    exploit_id: {
                        "timestamp": m.timestamp.isoformat(),
                        "sharpe_ratio": m.sharpe_ratio,
                        "drawdown_contribution": m.drawdown_contribution,
                        "capital_efficiency": m.capital_efficiency,
                        "total_trades": m.total_trades,
                        "win_rate": m.win_rate,
                        "avg_profit_per_trade": m.avg_profit_per_trade,
                        "max_drawdown": m.max_drawdown,
                        "deployed_capital_avg": m.deployed_capital_avg,
                    }
                    for exploit_id, m in all_metrics.items()
                }
            })

        @self.app.route("/api/dspy/parameters")
        def get_current_parameters():
            """Get current exploit parameters."""
            return jsonify({
                "parameters": {
                    "position_size": self.automated_exploit.position_size,
                    "profit_target": self.automated_exploit.profit_target,
                    "stop_loss": self.automated_exploit.stop_loss,
                    "min_ticks_between_actions": self.automated_exploit.min_ticks_between_actions,
                }
            })

        @self.app.route("/api/dspy/update-parameters", methods=["POST"])
        def update_parameters():
            """Update exploit parameters based on user input or DSPy suggestions."""
            data = request.json or {}
            
            # Validate and update parameters
            if "position_size" in data:
                value = float(data["position_size"])
                if 0.01 <= value <= 0.50:  # 1% to 50% range
                    self.automated_exploit.position_size = value
                else:
                    return jsonify({"error": "position_size must be between 0.01 and 0.50"}), 400
            
            if "profit_target" in data:
                value = float(data["profit_target"])
                if 0.01 <= value <= 0.20:  # 1% to 20% range
                    self.automated_exploit.profit_target = value
                else:
                    return jsonify({"error": "profit_target must be between 0.01 and 0.20"}), 400
            
            if "stop_loss" in data:
                value = float(data["stop_loss"])
                if 0.01 <= value <= 0.15:  # 1% to 15% range
                    self.automated_exploit.stop_loss = value
                else:
                    return jsonify({"error": "stop_loss must be between 0.01 and 0.15"}), 400
            
            if "min_ticks_between_actions" in data:
                value = int(data["min_ticks_between_actions"])
                if 1 <= value <= 20:  # 1 to 20 ticks range
                    self.automated_exploit.min_ticks_between_actions = value
                else:
                    return jsonify({"error": "min_ticks_between_actions must be between 1 and 20"}), 400
            
            logger.info(f"Parameters updated: {data}")
            return jsonify({
                "status": "updated",
                "parameters": {
                    "position_size": self.automated_exploit.position_size,
                    "profit_target": self.automated_exploit.profit_target,
                    "stop_loss": self.automated_exploit.stop_loss,
                    "min_ticks_between_actions": self.automated_exploit.min_ticks_between_actions,
                }
            })

        @self.app.route("/api/exploits/list")
        def list_exploits():
            """List all available exploits with their info."""
            exploits = self.exploit_manager.list_exploits()
            # Add the demo exploit to the list
            exploits.insert(0, {
                "name": "automated_demo",
                "display_name": "Automated Demo",
                "description": "Demo exploit for UI testing (currently active)",
            })
            return jsonify({"exploits": exploits})

        @self.app.route("/api/exploits/<exploit_name>/parameters")
        def get_exploit_parameters(exploit_name):
            """Get parameters for a specific exploit."""
            if exploit_name == "automated_demo":
                # Return demo exploit parameters
                return jsonify({
                    "parameters": {
                        "position_size": self.automated_exploit.position_size,
                        "profit_target": self.automated_exploit.profit_target,
                        "stop_loss": self.automated_exploit.stop_loss,
                        "min_ticks_between_actions": self.automated_exploit.min_ticks_between_actions,
                    },
                    "schema": {
                        "position_size": {"type": "float", "min": 0.01, "max": 0.50, "description": "Position size as fraction of capital"},
                        "profit_target": {"type": "float", "min": 0.01, "max": 0.20, "description": "Profit target percentage"},
                        "stop_loss": {"type": "float", "min": 0.01, "max": 0.15, "description": "Stop loss percentage"},
                        "min_ticks_between_actions": {"type": "int", "min": 1, "max": 20, "description": "Cooldown period in ticks"},
                    }
                })
            
            # Get parameters for production exploits
            parameters = self.exploit_manager.get_parameters(exploit_name)
            schema = self.exploit_manager.get_parameter_schema(exploit_name)
            
            if parameters is None:
                return jsonify({"error": f"Exploit '{exploit_name}' not found"}), 404
            
            return jsonify({
                "parameters": parameters,
                "schema": schema or {}
            })

        @self.app.route("/api/exploits/<exploit_name>/parameters", methods=["POST"])
        def update_exploit_parameters(exploit_name):
            """Update parameters for a specific exploit."""
            data = request.json or {}
            
            if exploit_name == "automated_demo":
                # Update demo exploit (same as existing endpoint)
                return update_parameters()
            
            # Update production exploit
            success = self.exploit_manager.update_parameters(exploit_name, data)
            
            if not success:
                return jsonify({"error": f"Failed to update exploit '{exploit_name}'"}), 400
            
            # Get updated parameters
            updated_params = self.exploit_manager.get_parameters(exploit_name)
            
            return jsonify({
                "status": "updated",
                "exploit": exploit_name,
                "parameters": updated_params
            })

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
            symbol=self.current_symbol,
            available_capital=self.engine_state.capital.available_capital,
            deployed_capital=self.engine_state.capital.deployed_capital,
            open_positions=list(self.engine_state.open_trades),
            recent_trades=list(self.engine_state.closed_trades[-5:]),
            current_price=self.current_price,
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
            symbol=self.current_symbol,
            available_capital=self.engine_state.capital.available_capital,
            deployed_capital=self.engine_state.capital.deployed_capital,
            open_positions=[],  # Using simulated positions
            recent_trades=[],
            current_price=tick.price,
            timestamp=timestamp,
        )
        
        # Step 3: Automated exploit generates Actions based on market analysis
        actions = self.automated_exploit.evaluate(exec_state)
        
        # Capture decision criteria that was used
        decision_criteria = self.automated_exploit.get_last_decision_criteria()
        
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
                    
                    # Feed trade to DSPy advisor
                    self._record_trade_for_dspy(position, tick.price, net_profit, pnl_pct)
                    
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
            "decision_criteria": decision_criteria,  # NEW: Show how decision was made
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

    def _record_trade_for_dspy(self, position, exit_price: float, realized_profit: float, profit_ratio: float):
        """
        Record a completed trade to DSPy advisor for analysis.
        
        Args:
            position: Position that was closed
            exit_price: Exit price
            realized_profit: Realized profit in currency
            profit_ratio: Profit ratio (percentage)
        """
        self.trade_counter += 1
        
        # Create a TradeAttribution for DSPy
        trade_attr = TradeAttribution(
            trade_id=self.trade_counter,
            exploit_id="automated_demo_exploit",
            capital_source="initial",
            pair=position.symbol,
            is_short=(position.side == Side.SHORT),
            entry_price=position.entry_price,
            entry_amount=position.size / position.entry_price,
            entry_stake=position.size,
            entry_date=datetime.fromtimestamp(position.timestamp / 1000, tz=timezone.utc),
            exit_price=exit_price,
            exit_date=datetime.now(timezone.utc),
            fee_open=position.size * 0.001,
            fee_close=(position.size + realized_profit) * 0.001,
            fee_open_cost=position.size * 0.001,
            fee_close_cost=(position.size + realized_profit) * 0.001,
            total_fees=position.size * 0.002,
            funding_fees=0.0,
            holding_duration_seconds=int((datetime.now(timezone.utc).timestamp() - position.timestamp / 1000)),
            holding_duration_hours=(datetime.now(timezone.utc).timestamp() - position.timestamp / 1000) / 3600,
            realized_profit=realized_profit,
            profit_ratio=profit_ratio,
            is_open=False,
            exit_reason="automated_exit",
        )
        
        # Feed to DSPy advisor
        self.dspy_advisor.observe_trade(trade_attr)
        logger.info(f"Recorded trade #{self.trade_counter} to DSPy advisor: P&L={realized_profit:.2f}")


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
    import os
    logging.basicConfig(level=logging.INFO)
    
    # Debug mode can cause 403 errors in Flask 3.1.0 due to debugger PIN protection
    # Default to False for production-like usage, can be enabled via environment variable
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() in ("true", "1", "yes")
    
    # Bind to 0.0.0.0 for cloud deployments (Render, etc.)
    # Use PORT environment variable if available (Render default)
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    
    server = DemoServer()
    server.run(host=host, port=port, debug=debug_mode)


if __name__ == "__main__":
    main()
