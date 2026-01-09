"""
Backtesting Adapter - Easy integration with backtesting tools.

This adapter allows the automated exploit and market simulator to be easily
integrated with existing backtesting frameworks. It provides a simple interface
for running realistic automated simulations over historical or synthetic data.

Usage Example:
    ```python
    from freqtrade.ui.backtest_adapter import BacktestAdapter
    
    # Create adapter
    adapter = BacktestAdapter(
        initial_capital=10000.0,
        market_condition="trending_up",
    )
    
    # Run simulation
    results = adapter.run(num_ticks=1000)
    
    # Analyze results
    print(f"Final Capital: ${results['final_capital']:,.2f}")
    print(f"Total Return: {results['total_return_pct']:.2f}%")
    print(f"Total Trades: {results['total_trades']}")
    print(f"Win Rate: {results['win_rate']:.2f}%")
    ```
"""

import logging
from dataclasses import dataclass
from typing import Any, Literal

import pandas as pd

from freqtrade.core.actions import ActionType, Side
from freqtrade.core.state import create_initial_state
from freqtrade.ui.automated_exploit import AutomatedExploit
from freqtrade.ui.market_simulator import MarketCondition, MarketSimulator
from freqtrade.exploits.exploit_module import ExecutionState, ExecutionResult


logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """Record of a completed trade."""
    
    entry_timestamp: int
    exit_timestamp: int
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    size: float
    profit: float
    profit_pct: float
    fees: float
    duration_ticks: int


class BacktestAdapter:
    """
    Adapter for running automated simulations in backtesting tools.
    
    This class bridges the automated exploit module with backtesting frameworks,
    providing an easy interface for realistic simulations.
    """
    
    def __init__(
        self,
        initial_capital: float = 10000.0,
        market_condition: MarketCondition = "mixed",
        initial_price: float = 50000.0,
        volatility: float = 0.02,
        tick_interval_ms: int = 1000,
    ):
        """
        Initialize the backtesting adapter.
        
        Args:
            initial_capital: Starting capital for simulation
            market_condition: Type of market to simulate
            initial_price: Starting price for the asset
            volatility: Price volatility (0.02 = 2%)
            tick_interval_ms: Milliseconds between ticks
        """
        self.initial_capital = initial_capital
        
        # Initialize components
        self.engine_state = create_initial_state(initial_capital)
        self.exploit = AutomatedExploit({})
        self.market = MarketSimulator(
            initial_price=initial_price,
            condition=market_condition,
            volatility=volatility,
            tick_interval_ms=tick_interval_ms,
        )
        
        # Tracking
        self.trade_records: list[TradeRecord] = []
        self.tick_data: list[dict[str, Any]] = []
        self.equity_curve: list[dict[str, Any]] = []
        
    def run(
        self,
        num_ticks: int = 1000,
        verbose: bool = False,
    ) -> dict[str, Any]:
        """
        Run the backtest simulation.
        
        Args:
            num_ticks: Number of market ticks to simulate
            verbose: If True, log detailed information
            
        Returns:
            Dictionary with simulation results and statistics
        """
        if verbose:
            logger.setLevel(logging.INFO)
        
        logger.info(f"Starting backtest: {num_ticks} ticks, condition={self.market.condition}")
        
        for tick_num in range(num_ticks):
            # Generate market tick
            tick = self.market.generate_tick()
            
            # Create execution state
            exec_state = ExecutionState(
                symbol="BTC/USDT",
                available_capital=self.engine_state.capital.available_capital,
                deployed_capital=self.engine_state.capital.deployed_capital,
                open_positions=[],
                recent_trades=[],
                current_price=tick.price,
                timestamp=tick.timestamp,
            )
            
            # Get strategy decisions
            actions = self.exploit.evaluate(exec_state)
            
            # Execute actions
            for action in actions:
                if action.type == ActionType.OPEN:
                    # Open position
                    required_capital = exec_state.available_capital * action.size
                    if self.engine_state.capital.allocate(required_capital):
                        self.exploit.add_simulated_position(
                            action.symbol, action.side, tick.price, required_capital
                        )
                        
                        # Notify exploit
                        result = ExecutionResult(
                            success=True,
                            order_ids=[f"bt_{tick.timestamp}"],
                            filled_size=action.size,
                            fees=required_capital * 0.001,
                            timestamp=tick.timestamp,
                        )
                        self.exploit.on_execution_result(action, result)
                        
                        if verbose:
                            logger.info(
                                f"Tick {tick_num}: OPEN {action.side.name} @ ${tick.price:,.2f}, "
                                f"Size: ${required_capital:,.2f}"
                            )
                
                elif action.type == ActionType.CLOSE:
                    # Close position
                    if self.exploit.simulated_positions:
                        position = self.exploit.simulated_positions[0]
                        entry_capital = position.size
                        
                        # Calculate P&L
                        if position.side == Side.LONG:
                            pnl_pct = (tick.price - position.entry_price) / position.entry_price
                        else:
                            pnl_pct = (position.entry_price - tick.price) / position.entry_price
                        
                        profit_amount = entry_capital * pnl_pct
                        close_fee = abs(entry_capital + profit_amount) * 0.001
                        net_profit = profit_amount - close_fee
                        
                        # Return capital
                        self.engine_state.capital.release(entry_capital)
                        self.engine_state.capital.available_capital += net_profit
                        self.engine_state.capital.pnl_realized += net_profit
                        
                        # Record trade
                        trade_record = TradeRecord(
                            entry_timestamp=position.timestamp,
                            exit_timestamp=tick.timestamp,
                            symbol=position.symbol,
                            side=position.side.name,
                            entry_price=position.entry_price,
                            exit_price=tick.price,
                            size=entry_capital,
                            profit=net_profit,
                            profit_pct=pnl_pct * 100,
                            fees=close_fee,
                            duration_ticks=tick_num - position.timestamp,
                        )
                        self.trade_records.append(trade_record)
                        
                        # Notify exploit
                        result = ExecutionResult(
                            success=True,
                            order_ids=[f"bt_{tick.timestamp}"],
                            filled_size=1.0,
                            fees=close_fee,
                            timestamp=tick.timestamp,
                        )
                        self.exploit.on_execution_result(action, result)
                        
                        if verbose:
                            logger.info(
                                f"Tick {tick_num}: CLOSE {position.side.name} @ ${tick.price:,.2f}, "
                                f"P&L: {pnl_pct:+.2%} (${net_profit:+,.2f})"
                            )
            
            # Record tick data
            self.tick_data.append({
                "tick": tick_num,
                "timestamp": tick.timestamp,
                "price": tick.price,
                "volume": tick.volume,
                "condition": tick.condition,
            })
            
            # Record equity curve
            total_equity = (
                self.engine_state.capital.available_capital
                + self.engine_state.capital.deployed_capital
            )
            self.equity_curve.append({
                "tick": tick_num,
                "timestamp": tick.timestamp,
                "equity": total_equity,
                "available": self.engine_state.capital.available_capital,
                "deployed": self.engine_state.capital.deployed_capital,
                "pnl": self.engine_state.capital.pnl_realized,
            })
        
        # Calculate statistics
        results = self._calculate_statistics()
        
        logger.info(f"Backtest complete: {results['total_trades']} trades, "
                   f"Return: {results['total_return_pct']:+.2f}%")
        
        return results
    
    def _calculate_statistics(self) -> dict[str, Any]:
        """Calculate backtest statistics."""
        final_capital = (
            self.engine_state.capital.available_capital
            + self.engine_state.capital.deployed_capital
        )
        
        total_return = final_capital - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100
        
        # Trade statistics
        winning_trades = [t for t in self.trade_records if t.profit > 0]
        losing_trades = [t for t in self.trade_records if t.profit <= 0]
        
        win_rate = (
            (len(winning_trades) / len(self.trade_records) * 100)
            if self.trade_records
            else 0.0
        )
        
        avg_win = (
            sum(t.profit for t in winning_trades) / len(winning_trades)
            if winning_trades
            else 0.0
        )
        
        avg_loss = (
            sum(t.profit for t in losing_trades) / len(losing_trades)
            if losing_trades
            else 0.0
        )
        
        # Market statistics
        price_change_pct = self.market.get_price_change_percent()
        
        return {
            # Capital
            "initial_capital": self.initial_capital,
            "final_capital": final_capital,
            "total_return": total_return,
            "total_return_pct": total_return_pct,
            
            # Trades
            "total_trades": len(self.trade_records),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": abs(avg_win / avg_loss) if avg_loss != 0 else float('inf'),
            
            # Market
            "market_condition": self.market.condition,
            "initial_price": self.market.initial_price,
            "final_price": self.market.current_price,
            "price_change_pct": price_change_pct,
            "total_ticks": self.market.tick_count,
            
            # Strategy
            "strategy_stats": self.exploit.get_statistics(),
        }
    
    def get_trades_dataframe(self) -> pd.DataFrame:
        """
        Get trade records as a pandas DataFrame.
        
        Returns:
            DataFrame with all trade records
        """
        if not self.trade_records:
            return pd.DataFrame()
        
        data = [
            {
                "entry_timestamp": t.entry_timestamp,
                "exit_timestamp": t.exit_timestamp,
                "symbol": t.symbol,
                "side": t.side,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "size": t.size,
                "profit": t.profit,
                "profit_pct": t.profit_pct,
                "fees": t.fees,
                "duration_ticks": t.duration_ticks,
            }
            for t in self.trade_records
        ]
        
        return pd.DataFrame(data)
    
    def get_equity_curve_dataframe(self) -> pd.DataFrame:
        """
        Get equity curve as a pandas DataFrame.
        
        Returns:
            DataFrame with equity curve data
        """
        return pd.DataFrame(self.equity_curve)
    
    def get_tick_data_dataframe(self) -> pd.DataFrame:
        """
        Get tick data as a pandas DataFrame.
        
        Returns:
            DataFrame with tick data
        """
        return pd.DataFrame(self.tick_data)
    
    def reset(self):
        """Reset the adapter to initial state."""
        self.engine_state = create_initial_state(self.initial_capital)
        self.exploit = AutomatedExploit({})
        self.market.reset()
        self.trade_records = []
        self.tick_data = []
        self.equity_curve = []


def run_quick_backtest(
    market_condition: MarketCondition = "mixed",
    num_ticks: int = 1000,
    initial_capital: float = 10000.0,
    verbose: bool = True,
) -> dict[str, Any]:
    """
    Quick helper function to run a backtest with default settings.
    
    Args:
        market_condition: Market condition to simulate
        num_ticks: Number of ticks to simulate
        initial_capital: Starting capital
        verbose: Enable verbose logging
        
    Returns:
        Backtest results dictionary
    """
    adapter = BacktestAdapter(
        initial_capital=initial_capital,
        market_condition=market_condition,
    )
    
    return adapter.run(num_ticks=num_ticks, verbose=verbose)
