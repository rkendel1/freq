"""
FastAPI Demo Server - Vercel Deployment

This is a FastAPI version of the demo server for Vercel deployment.
It provides the same demo UI functionality but uses FastAPI for compatibility with Vercel.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# Import demo components
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

# Initialize FastAPI app
app = FastAPI(
    title="Freqtrade Execution Engine Demo",
    description="Minimal Trading Execution Engine - Infrastructure Core",
    version="1.0.0",
)

# Add CORS middleware for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Server state (similar to Flask DemoServer class)
class DemoState:
    """Global state for the demo server."""
    
    def __init__(self):
        """Initialize the demo state."""
        # Initial state
        self.initial_capital = 10000.0
        self.current_symbol = "BTC/USDT"
        self.current_price = 50000.0
        
        self.engine_state = create_initial_state(self.initial_capital)
        self.risk_limits = RiskLimits(
            max_position_size=0.2,
            max_total_exposure=0.8,
            max_open_positions=3,
            max_loss_per_trade=0.1,
            max_daily_loss=0.2,
            position_cooldown=0,
        )
        self.risk_manager = RiskManager(self.risk_limits)
        self.exploit = DemoExploit({})
        
        # Flow tracking
        self.flow_history: list[dict[str, Any]] = []
        self.current_step = 0
        
        # Track simulated open positions
        self.demo_positions: list[dict[str, Any]] = []
        
        # Automated mode
        self.automated_mode = False
        self.automated_exploit = AutomatedExploit({})
        self.market_simulator = MarketSimulator(initial_price=self.current_price, condition="mixed")
        self.price_history: list[dict[str, Any]] = []
        
        # DSPy Advisor integration
        self.dspy_advisor = DSPyAdvisor(min_trades_for_suggestion=5, suggestion_confidence_threshold=0.5)
        self.trade_counter = 0
        
        # Exploit Parameter Manager
        self.exploit_manager = ExploitParameterManager({})

# Global state instance
demo_state = DemoState()


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the demo UI HTML page."""
    template_path = Path(__file__).parent.parent / "freqtrade" / "ui" / "templates" / "demo.html"
    
    if template_path.exists():
        with open(template_path, "r") as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(
            content="""
            <html>
                <head><title>Freqtrade Demo</title></head>
                <body>
                    <h1>Freqtrade Execution Engine Demo</h1>
                    <p>Demo UI is available. API documentation: <a href="/docs">/docs</a></p>
                    <p>Note: Template file not found. Please check deployment.</p>
                </body>
            </html>
            """
        )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "message": "Demo server is running"}


@app.get("/api/state")
async def get_state():
    """Get current engine state."""
    return {
        "capital": {
            "available": demo_state.engine_state.capital.available_capital,
            "deployed": demo_state.engine_state.capital.deployed_capital,
            "pnl_realized": demo_state.engine_state.capital.pnl_realized,
            "pnl_unrealized": demo_state.engine_state.capital.pnl_unrealized,
        },
        "open_trades": len(demo_state.engine_state.open_trades),
        "closed_trades": len(demo_state.engine_state.closed_trades),
        "total_actions": demo_state.engine_state.total_actions,
        "successful_actions": demo_state.engine_state.successful_actions,
        "failed_actions": demo_state.engine_state.failed_actions,
    }


@app.post("/api/reset")
async def reset():
    """Reset the demo to initial state."""
    demo_state.engine_state = create_initial_state(demo_state.initial_capital)
    demo_state.flow_history = []
    demo_state.current_step = 0
    demo_state.demo_positions = []
    demo_state.exploit.clear_simulated_positions()
    demo_state.automated_exploit.clear_simulated_positions()
    demo_state.market_simulator.reset()
    demo_state.market_simulator.current_price = demo_state.current_price
    demo_state.market_simulator.initial_price = demo_state.current_price
    demo_state.price_history = []
    demo_state.automated_mode = False
    return {"status": "reset"}


@app.post("/api/config/symbol")
async def config_symbol(request: Request):
    """Update the trading symbol and price."""
    data = await request.json()
    symbol = data.get("symbol", "BTC/USDT")
    initial_price = data.get("initial_price", 50000.0)
    
    demo_state.current_symbol = symbol
    demo_state.current_price = initial_price
    demo_state.market_simulator.current_price = initial_price
    demo_state.market_simulator.initial_price = initial_price
    
    logger.info(f"Symbol updated to {symbol} at ${initial_price}")
    return {"status": "updated", "symbol": symbol, "price": initial_price}


@app.post("/api/config/capital")
async def config_capital(request: Request):
    """Update the initial capital."""
    data = await request.json()
    capital = data.get("capital", 10000.0)
    
    if capital < 1000 or capital > 1000000:
        raise HTTPException(status_code=400, detail="Capital must be between 1000 and 1000000")
    
    demo_state.initial_capital = capital
    demo_state.engine_state = create_initial_state(capital)
    
    logger.info(f"Capital updated to ${capital}")
    return {"status": "updated", "capital": capital}


@app.post("/api/automated/start")
async def start_automated(request: Request):
    """Start automated mode."""
    data = await request.json()
    condition = data.get("condition", "mixed")
    
    valid_conditions = ["mixed", "trending_up", "trending_down", "volatile", "ranging"]
    if condition not in valid_conditions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid condition. Must be one of: {valid_conditions}"
        )
    
    demo_state.automated_mode = True
    demo_state.market_simulator.reset(condition=condition)
    demo_state.automated_exploit.clear_simulated_positions()
    demo_state.price_history = []
    
    logger.info(f"Automated mode started with {condition} market condition")
    return {"status": "started", "condition": condition}


@app.post("/api/automated/stop")
async def stop_automated():
    """Stop automated mode."""
    demo_state.automated_mode = False
    logger.info("Automated mode stopped")
    return {"status": "stopped"}


@app.post("/api/automated/tick")
async def automated_tick():
    """Execute one automated tick (price update + decision)."""
    if not demo_state.automated_mode:
        raise HTTPException(status_code=400, detail="Automated mode not active")
    
    # Generate market tick
    tick = demo_state.market_simulator.generate_tick()
    
    # Record price for charting
    demo_state.price_history.append({
        "timestamp": tick.timestamp,
        "price": tick.price,
    })
    
    # Execute automated tick logic (simplified version)
    flow_trace = _execute_automated_tick(tick)
    demo_state.flow_history.append(flow_trace)
    
    return flow_trace


@app.get("/api/automated/status")
async def automated_status():
    """Get automated mode status."""
    return {
        "active": demo_state.automated_mode,
        "condition": demo_state.market_simulator.condition,
        "current_price": demo_state.market_simulator.current_price,
        "price_change_pct": demo_state.market_simulator.get_price_change_percent(),
        "tick_count": demo_state.market_simulator.tick_count,
        "process_stats": demo_state.automated_exploit.get_statistics(),
    }


@app.get("/api/price-history")
async def price_history():
    """Get price history for charting."""
    return {"prices": demo_state.price_history[-100:]}


@app.get("/api/history")
async def get_history():
    """Get flow execution history."""
    return {"history": demo_state.flow_history}


@app.post("/api/execute-step")
async def execute_step(request: Request):
    """Execute one step of the flow and return the trace."""
    data = await request.json()
    scenario = data.get("scenario", "open_long")
    
    # Execute flow step logic (simplified version)
    flow_trace = _execute_flow_step(scenario)
    demo_state.flow_history.append(flow_trace)
    
    return flow_trace


def _execute_flow_step(scenario: str) -> Dict[str, Any]:
    """Execute one flow step and return detailed trace."""
    timestamp = int(datetime.now(timezone.utc).timestamp())
    
    # Initial state
    initial_state = {
        "available_capital": demo_state.engine_state.capital.available_capital,
        "deployed_capital": demo_state.engine_state.capital.deployed_capital,
        "pnl_realized": demo_state.engine_state.capital.pnl_realized,
        "open_positions": len(demo_state.engine_state.open_trades),
    }
    
    # Create execution state
    exec_state = ExecutionState(
        symbol=demo_state.current_symbol,
        available_capital=demo_state.engine_state.capital.available_capital,
        deployed_capital=demo_state.engine_state.capital.deployed_capital,
        open_positions=list(demo_state.engine_state.open_trades),
        recent_trades=list(demo_state.engine_state.closed_trades[-5:]),
        current_price=demo_state.current_price,
        timestamp=timestamp,
    )
    
    # Exploit generates actions
    demo_state.exploit.set_scenario(scenario)
    actions = demo_state.exploit.evaluate(exec_state)
    
    actions_data = []
    for action in actions:
        actions_data.append({
            "type": action.type.name if hasattr(action, "type") else str(action.type),
            "symbol": action.symbol,
            "size": action.size if hasattr(action, "size") else None,
            "reason": action.reason if hasattr(action, "reason") else "N/A",
        })
    
    # Risk checks
    risk_checks = []
    approved_actions = []
    for action in actions:
        if isinstance(action, Action):
            required_capital = exec_state.available_capital * action.size
            can_allocate = required_capital <= demo_state.engine_state.capital.available_capital
            
            risk_result = {
                "action": f"{action.type.name} {action.symbol}",
                "required_capital": required_capital,
                "available_capital": demo_state.engine_state.capital.available_capital,
                "approved": can_allocate,
                "reason": "Approved" if can_allocate else "Insufficient capital",
            }
            risk_checks.append(risk_result)
            
            if can_allocate:
                approved_actions.append(action)
    
    # Execute approved actions
    execution_results = []
    for action in approved_actions:
        if action.type == ActionType.OPEN:
            required_capital = exec_state.available_capital * action.size
            success = demo_state.engine_state.capital.allocate(required_capital)
            
            if success:
                demo_state.engine_state.total_actions += 1
                demo_state.engine_state.successful_actions += 1
                
                demo_state.demo_positions.append({
                    "symbol": action.symbol,
                    "side": action.side,
                    "entry_price": exec_state.current_price,
                    "size": required_capital,
                    "timestamp": timestamp,
                })
                
                demo_state.exploit.add_simulated_position(
                    action.symbol, action.side, exec_state.current_price, required_capital
                )
                
                result = ExecutionResult(
                    success=True,
                    order_ids=["demo_order_123"],
                    filled_size=action.size,
                    fees=required_capital * 0.001,
                    timestamp=timestamp,
                )
            else:
                demo_state.engine_state.total_actions += 1
                demo_state.engine_state.failed_actions += 1
                
                result = ExecutionResult(
                    success=False,
                    order_ids=[],
                    filled_size=0.0,
                    fees=0.0,
                    timestamp=timestamp,
                    error_message="Capital allocation failed",
                )
            
            execution_results.append({
                "action": f"{action.type.name} {action.symbol}",
                "success": result.success,
                "filled_size": result.filled_size,
                "fees": result.fees,
                "error": result.error_message,
            })
            
            demo_state.exploit.on_execution_result(action, result)
            
        elif action.type == ActionType.CLOSE:
            if demo_state.demo_positions:
                position = demo_state.demo_positions.pop(0)
                entry_capital = position["size"]
                
                profit_pct = 0.08
                profit_amount = entry_capital * profit_pct
                exit_capital = entry_capital + profit_amount
                close_fee = exit_capital * 0.001
                net_profit = profit_amount - close_fee
                
                demo_state.engine_state.capital.release(entry_capital)
                demo_state.engine_state.capital.available_capital += net_profit
                demo_state.engine_state.capital.pnl_realized += net_profit
                
                if demo_state.exploit.simulated_positions:
                    demo_state.exploit.simulated_positions.pop(0)
                
                demo_state.engine_state.total_actions += 1
                demo_state.engine_state.successful_actions += 1
                
                result = ExecutionResult(
                    success=True,
                    order_ids=["demo_order_456"],
                    filled_size=1.0,
                    fees=close_fee,
                    timestamp=timestamp,
                )
                
                execution_results.append({
                    "action": f"{action.type.name} {action.symbol}",
                    "success": result.success,
                    "filled_size": result.filled_size,
                    "fees": result.fees,
                    "profit": net_profit,
                    "profit_pct": profit_pct * 100,
                    "error": result.error_message,
                })
                
                demo_state.exploit.on_execution_result(action, result)
    
    # Final state
    final_state = {
        "available_capital": demo_state.engine_state.capital.available_capital,
        "deployed_capital": demo_state.engine_state.capital.deployed_capital,
        "pnl_realized": demo_state.engine_state.capital.pnl_realized,
        "open_positions": len(demo_state.engine_state.open_trades),
    }
    
    demo_state.current_step += 1
    return {
        "step": demo_state.current_step,
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
            "capital_change": final_state["available_capital"] - initial_state["available_capital"],
            "deployed_change": final_state["deployed_capital"] - initial_state["deployed_capital"],
        },
    }


def _execute_automated_tick(tick) -> Dict[str, Any]:
    """Execute one automated tick with market data."""
    timestamp = tick.timestamp
    
    # Initial state
    initial_state = {
        "available_capital": demo_state.engine_state.capital.available_capital,
        "deployed_capital": demo_state.engine_state.capital.deployed_capital,
        "pnl_realized": demo_state.engine_state.capital.pnl_realized,
        "open_positions": len(demo_state.automated_exploit.simulated_positions),
        "current_price": tick.price,
    }
    
    # Create execution state
    exec_state = ExecutionState(
        symbol=demo_state.current_symbol,
        available_capital=demo_state.engine_state.capital.available_capital,
        deployed_capital=demo_state.engine_state.capital.deployed_capital,
        open_positions=[],
        recent_trades=[],
        current_price=tick.price,
        timestamp=timestamp,
    )
    
    # Generate actions
    actions = demo_state.automated_exploit.evaluate(exec_state)
    decision_criteria = demo_state.automated_exploit.get_last_decision_criteria()
    
    actions_data = []
    for action in actions:
        actions_data.append({
            "type": action.type.name,
            "symbol": action.symbol,
            "side": action.side.name,
            "size": action.size,
            "reason": action.reason,
        })
    
    # Risk checks and execution (simplified - similar to manual mode)
    risk_checks = []
    approved_actions = []
    execution_results = []
    
    for action in actions:
        if action.type == ActionType.OPEN:
            required_capital = exec_state.available_capital * action.size
            can_allocate = required_capital <= demo_state.engine_state.capital.available_capital
            
            risk_checks.append({
                "action": f"{action.type.name} {action.side.name} {action.symbol}",
                "required_capital": required_capital,
                "available_capital": demo_state.engine_state.capital.available_capital,
                "approved": can_allocate,
                "reason": "Approved" if can_allocate else "Insufficient capital",
            })
            
            if can_allocate:
                approved_actions.append(action)
                success = demo_state.engine_state.capital.allocate(required_capital)
                
                if success:
                    demo_state.engine_state.total_actions += 1
                    demo_state.engine_state.successful_actions += 1
                    
                    demo_state.automated_exploit.add_simulated_position(
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
                    
                    demo_state.automated_exploit.on_execution_result(action, result)
                    
        elif action.type == ActionType.CLOSE:
            risk_checks.append({
                "action": f"{action.type.name} {action.side.name} {action.symbol}",
                "approved": True,
                "reason": "Close position",
            })
            approved_actions.append(action)
            
            if demo_state.automated_exploit.simulated_positions:
                position = demo_state.automated_exploit.simulated_positions[0]
                entry_capital = position.size
                
                if position.side == Side.LONG:
                    pnl_pct = (tick.price - position.entry_price) / position.entry_price
                else:
                    pnl_pct = (position.entry_price - tick.price) / position.entry_price
                
                profit_amount = entry_capital * pnl_pct
                close_fee = (entry_capital + profit_amount) * 0.001
                net_profit = profit_amount - close_fee
                
                demo_state.engine_state.capital.release(entry_capital)
                demo_state.engine_state.capital.available_capital += net_profit
                demo_state.engine_state.capital.pnl_realized += net_profit
                
                demo_state.engine_state.total_actions += 1
                demo_state.engine_state.successful_actions += 1
                
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
                
                # Record trade for DSPy
                _record_trade_for_dspy(position, tick.price, net_profit, pnl_pct)
                
                demo_state.automated_exploit.on_execution_result(action, result)
    
    # Final state
    final_state = {
        "available_capital": demo_state.engine_state.capital.available_capital,
        "deployed_capital": demo_state.engine_state.capital.deployed_capital,
        "pnl_realized": demo_state.engine_state.capital.pnl_realized,
        "open_positions": len(demo_state.automated_exploit.simulated_positions),
        "current_price": tick.price,
    }
    
    demo_state.current_step += 1
    
    scenario_label = "automated_tick"
    if actions_data:
        action_type = actions_data[0].get("type", "").lower()
        if action_type == "open":
            side = actions_data[0].get("side", "").lower()
            scenario_label = f"automated_open_{side}"
        elif action_type == "close":
            scenario_label = "automated_close"
    
    return {
        "step": demo_state.current_step,
        "mode": "automated",
        "scenario": scenario_label,
        "timestamp": timestamp,
        "market_data": {
            "price": tick.price,
            "volume": tick.volume,
            "condition": tick.condition,
        },
        "decision_criteria": decision_criteria,
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
            "price_change": tick.price - initial_state["current_price"] if demo_state.price_history else 0,
        },
    }


def _record_trade_for_dspy(position, exit_price: float, realized_profit: float, profit_ratio: float):
    """Record a completed trade to DSPy advisor."""
    demo_state.trade_counter += 1
    
    trade_attr = TradeAttribution(
        trade_id=demo_state.trade_counter,
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
    
    demo_state.dspy_advisor.observe_trade(trade_attr)
    logger.info(f"Recorded trade #{demo_state.trade_counter} to DSPy advisor: P&L={realized_profit:.2f}")


# Additional endpoints for DSPy and exploit management
@app.get("/api/dspy/suggestions")
async def get_dspy_suggestions():
    """Get DSPy parameter suggestions."""
    suggestions = demo_state.dspy_advisor.generate_suggestions()
    return {
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
        "total_trades_observed": demo_state.trade_counter,
    }


@app.get("/api/dspy/metrics")
async def get_dspy_metrics():
    """Get current DSPy metrics."""
    all_metrics = demo_state.dspy_advisor.get_all_metrics()
    return {
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
    }


@app.get("/api/dspy/parameters")
async def get_current_parameters():
    """Get current exploit parameters."""
    return {
        "parameters": {
            "position_size": demo_state.automated_exploit.position_size,
            "profit_target": demo_state.automated_exploit.profit_target,
            "stop_loss": demo_state.automated_exploit.stop_loss,
            "min_ticks_between_actions": demo_state.automated_exploit.min_ticks_between_actions,
        }
    }


@app.post("/api/dspy/update-parameters")
async def update_parameters(request: Request):
    """Update exploit parameters."""
    data = await request.json()
    
    if "position_size" in data:
        value = float(data["position_size"])
        if 0.01 <= value <= 0.50:
            demo_state.automated_exploit.position_size = value
        else:
            raise HTTPException(status_code=400, detail="position_size must be between 0.01 and 0.50")
    
    if "profit_target" in data:
        value = float(data["profit_target"])
        if 0.01 <= value <= 0.20:
            demo_state.automated_exploit.profit_target = value
        else:
            raise HTTPException(status_code=400, detail="profit_target must be between 0.01 and 0.20")
    
    if "stop_loss" in data:
        value = float(data["stop_loss"])
        if 0.01 <= value <= 0.15:
            demo_state.automated_exploit.stop_loss = value
        else:
            raise HTTPException(status_code=400, detail="stop_loss must be between 0.01 and 0.15")
    
    if "min_ticks_between_actions" in data:
        value = int(data["min_ticks_between_actions"])
        if 1 <= value <= 20:
            demo_state.automated_exploit.min_ticks_between_actions = value
        else:
            raise HTTPException(status_code=400, detail="min_ticks_between_actions must be between 1 and 20")
    
    return {
        "status": "updated",
        "parameters": {
            "position_size": demo_state.automated_exploit.position_size,
            "profit_target": demo_state.automated_exploit.profit_target,
            "stop_loss": demo_state.automated_exploit.stop_loss,
            "min_ticks_between_actions": demo_state.automated_exploit.min_ticks_between_actions,
        }
    }


@app.get("/api/exploits/list")
async def list_exploits():
    """List all available exploits."""
    exploits = demo_state.exploit_manager.list_exploits()
    exploits.insert(0, {
        "name": "automated_demo",
        "display_name": "Automated Demo",
        "description": "Demo exploit for UI testing (currently active)",
    })
    return {"exploits": exploits}


@app.get("/api/exploits/{exploit_name}/parameters")
async def get_exploit_parameters(exploit_name: str):
    """Get parameters for a specific exploit."""
    if exploit_name == "automated_demo":
        return {
            "parameters": {
                "position_size": demo_state.automated_exploit.position_size,
                "profit_target": demo_state.automated_exploit.profit_target,
                "stop_loss": demo_state.automated_exploit.stop_loss,
                "min_ticks_between_actions": demo_state.automated_exploit.min_ticks_between_actions,
            },
            "schema": {
                "position_size": {"type": "float", "min": 0.01, "max": 0.50, "description": "Position size as fraction of capital"},
                "profit_target": {"type": "float", "min": 0.01, "max": 0.20, "description": "Profit target percentage"},
                "stop_loss": {"type": "float", "min": 0.01, "max": 0.15, "description": "Stop loss percentage"},
                "min_ticks_between_actions": {"type": "int", "min": 1, "max": 20, "description": "Cooldown period in ticks"},
            }
        }
    
    parameters = demo_state.exploit_manager.get_parameters(exploit_name)
    schema = demo_state.exploit_manager.get_parameter_schema(exploit_name)
    
    if parameters is None:
        raise HTTPException(status_code=404, detail=f"Exploit '{exploit_name}' not found")
    
    return {
        "parameters": parameters,
        "schema": schema or {}
    }


@app.post("/api/exploits/{exploit_name}/parameters")
async def update_exploit_parameters(exploit_name: str, request: Request):
    """Update parameters for a specific exploit."""
    data = await request.json()
    
    if exploit_name == "automated_demo":
        return await update_parameters(request)
    
    success = demo_state.exploit_manager.update_parameters(exploit_name, data)
    
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to update exploit '{exploit_name}'")
    
    updated_params = demo_state.exploit_manager.get_parameters(exploit_name)
    
    return {
        "status": "updated",
        "exploit": exploit_name,
        "parameters": updated_params
    }
