"""
Backtesting Connector - Integrates automated exploit with freqtrade backtesting.

This connector allows the AutomatedExploit to be tested using real historical
data through the existing freqtrade backtesting infrastructure.

Usage:
    python -m freqtrade backtesting --strategy AutomatedStrategy --config config.json
"""

import logging
from datetime import datetime
from typing import Optional

import pandas as pd
from pandas import DataFrame

from freqtrade.strategy import IStrategy, informative
from freqtrade.core.actions import Action, ActionType, Side
from freqtrade.exploits.exploit_module import ExecutionState
from freqtrade.ui.automated_exploit import AutomatedExploit


logger = logging.getLogger(__name__)


class AutomatedStrategy(IStrategy):
    """
    Strategy wrapper that uses the AutomatedExploit for backtesting.
    
    This allows testing the automated exploit module with real historical
    data through freqtrade's backtesting infrastructure.
    """
    
    # Strategy configuration
    minimal_roi = {
        "0": 0.05  # 5% minimum ROI (overridden by exploit logic)
    }
    
    stoploss = -0.03  # 3% stop loss (overridden by exploit logic)
    
    # Trailing stop configuration
    trailing_stop = False
    
    # Optimal timeframe for the strategy
    timeframe = '5m'
    
    # Run "populate_indicators()" only for new candle
    process_only_new_candles = True
    
    # Use exit signal
    use_exit_signal = True
    exit_profit_only = False
    exit_profit_offset = 0.0
    
    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 20
    
    # Position sizing
    position_adjustment_enable = False
    
    def __init__(self, config: dict) -> None:
        """Initialize strategy with automated exploit."""
        super().__init__(config)
        
        # Initialize the automated exploit
        self.exploit = AutomatedExploit(config)
        
        # Track price history per pair
        self.price_history: dict[str, list[float]] = {}
        
        logger.info("AutomatedStrategy initialized with AutomatedExploit")
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate indicators for the strategy.
        
        The automated exploit uses simple moving averages, so we calculate those here.
        
        Args:
            dataframe: Raw OHLCV data
            metadata: Pair metadata
            
        Returns:
            DataFrame with indicators added
        """
        pair = metadata['pair']
        
        # Calculate moving averages for the exploit's analysis
        dataframe['fast_ma'] = dataframe['close'].rolling(window=5).mean()
        dataframe['slow_ma'] = dataframe['close'].rolling(window=10).mean()
        
        # Calculate momentum
        dataframe['momentum'] = dataframe['close'].pct_change(periods=5)
        
        # Store price history for the exploit
        if pair not in self.price_history:
            self.price_history[pair] = []
        
        # Keep last 20 prices for analysis
        self.price_history[pair] = dataframe['close'].tail(20).tolist()
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate entry signals using the automated exploit.
        
        Args:
            dataframe: DataFrame with indicators
            metadata: Pair metadata
            
        Returns:
            DataFrame with entry signals
        """
        pair = metadata['pair']
        
        # Initialize entry columns
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0
        dataframe['enter_tag'] = ''
        
        # Iterate through candles
        for idx in range(len(dataframe)):
            if idx < self.startup_candle_count:
                continue
            
            row = dataframe.iloc[idx]
            
            # Update exploit's price history
            if pair in self.price_history:
                # Keep rolling window of 20 prices
                self.exploit.price_history.clear()
                for price in self.price_history[pair][-20:]:
                    self.exploit.price_history.append(price)
            
            # Create execution state
            exec_state = ExecutionState(
                symbol=pair,
                available_capital=10000.0,  # Placeholder, actual capital managed by freqtrade
                deployed_capital=0.0,
                open_positions=[],
                recent_trades=[],
                current_price=float(row['close']),
                timestamp=int(row['date'].timestamp() * 1000) if hasattr(row['date'], 'timestamp') else 0,
            )
            
            # Get actions from exploit
            actions = self.exploit.evaluate(exec_state)
            
            # Process actions
            for action in actions:
                if action.type == ActionType.OPEN:
                    if action.side == Side.LONG:
                        dataframe.loc[idx, 'enter_long'] = 1
                        dataframe.loc[idx, 'enter_tag'] = action.reason[:50]  # Truncate reason
                    elif action.side == Side.SHORT:
                        dataframe.loc[idx, 'enter_short'] = 1
                        dataframe.loc[idx, 'enter_tag'] = action.reason[:50]
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate exit signals using the automated exploit.
        
        Args:
            dataframe: DataFrame with indicators
            metadata: Pair metadata
            
        Returns:
            DataFrame with exit signals
        """
        pair = metadata['pair']
        
        # Initialize exit columns
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0
        dataframe['exit_tag'] = ''
        
        # The exploit's exit logic is triggered when we have open positions
        # In backtesting, this is handled by custom_exit() which is called
        # for each open trade
        
        return dataframe
    
    def custom_exit(
        self,
        pair: str,
        trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs
    ) -> Optional[str]:
        """
        Custom exit logic using the automated exploit.
        
        This is called for each open trade to determine if it should be closed.
        
        Args:
            pair: Trading pair
            trade: Trade object
            current_time: Current timestamp
            current_rate: Current price
            current_profit: Current profit percentage
            **kwargs: Additional parameters
            
        Returns:
            Exit reason if trade should be closed, None otherwise
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()
        
        # Update exploit's price history
        if pair in self.price_history:
            self.exploit.price_history.clear()
            for price in self.price_history[pair][-20:]:
                self.exploit.price_history.append(price)
        
        # Add simulated position to exploit for exit analysis
        entry_price = trade.open_rate
        position_side = Side.LONG if trade.is_long else Side.SHORT
        
        # Temporarily add position
        self.exploit.add_simulated_position(
            symbol=pair,
            side=position_side,
            entry_price=entry_price,
            size=trade.stake_amount,
        )
        
        # Create execution state
        exec_state = ExecutionState(
            symbol=pair,
            available_capital=10000.0,
            deployed_capital=trade.stake_amount,
            open_positions=[],
            recent_trades=[],
            current_price=current_rate,
            timestamp=int(current_time.timestamp() * 1000),
        )
        
        # Get actions from exploit
        actions = self.exploit.evaluate(exec_state)
        
        # Clear the temporary position
        self.exploit.simulated_positions.clear()
        
        # Check if exploit wants to close
        for action in actions:
            if action.type == ActionType.CLOSE:
                return action.reason[:50]  # Return exit reason
        
        return None
    
    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: Optional[float],
        max_stake: float,
        leverage: float,
        entry_tag: Optional[str],
        side: str,
        **kwargs
    ) -> float:
        """
        Customize stake amount based on exploit's position sizing.
        
        The exploit uses 15% of capital per position.
        
        Args:
            pair: Trading pair
            current_time: Current timestamp
            current_rate: Current price
            proposed_stake: Proposed stake from freqtrade
            min_stake: Minimum stake
            max_stake: Maximum stake
            leverage: Leverage
            entry_tag: Entry tag
            side: Trade side (long/short)
            **kwargs: Additional parameters
            
        Returns:
            Stake amount to use
        """
        # Use 15% of available capital (as configured in exploit)
        wallet_balance = self.wallets.get_total_stake_amount()
        stake = wallet_balance * self.exploit.position_size
        
        # Ensure within bounds
        if min_stake and stake < min_stake:
            stake = min_stake
        if stake > max_stake:
            stake = max_stake
        
        return stake


def run_automated_backtest(
    config_path: str,
    data_dir: str = "user_data/data",
    timerange: str = "",
    pairs: list[str] = None,
):
    """
    Helper function to run backtest with automated strategy.
    
    Args:
        config_path: Path to config file
        data_dir: Directory with historical data
        timerange: Time range for backtest (e.g., "20230101-20230131")
        pairs: List of pairs to test (e.g., ["BTC/USDT", "ETH/USDT"])
    
    Example:
        run_automated_backtest(
            config_path="config.json",
            timerange="20230101-20230131",
            pairs=["BTC/USDT"]
        )
    """
    from freqtrade.configuration import Configuration
    from freqtrade.optimize.backtesting import Backtesting
    
    # Load configuration
    config = Configuration.from_files([config_path])
    
    # Override with automated strategy
    config['strategy'] = 'AutomatedStrategy'
    
    # Set data directory
    if data_dir:
        config['datadir'] = data_dir
    
    # Set timerange
    if timerange:
        config['timerange'] = timerange
    
    # Set pairs
    if pairs:
        config['pairs'] = pairs
    
    # Initialize backtesting
    backtesting = Backtesting(config)
    
    # Run backtest
    logger.info("Starting automated backtest with real historical data")
    backtesting.start()
    
    return backtesting
