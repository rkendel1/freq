"""
Producer decorator that integrates with existing analyzed dataframe broadcasting.
No interface modifications needed - uses existing get_analyzed_dataframe() system.
"""

from collections.abc import Callable
from typing import Any

from pandas import DataFrame


def producer(
    timeframe: str,
    asset: str = "",
    fmt: str | Callable[[str], str] | None = None,
    *,
    candle_type: str | None = None,
    ffill: bool = True,
) -> Callable[[Callable], Callable]:
    """
    Producer decorator with same interface as @informative.
    
    Works by ensuring producer indicators are included in the analyzed dataframe
    that gets broadcasted automatically by the existing DataProvider system.
    
    Example usage:
    
        @producer('1h')
        def populate_producer_indicators_1h(self, dataframe, metadata) -> DataFrame:
            dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
            return dataframe
    
    :param timeframe: Producer timeframe. Must be equal or higher than strategy timeframe.
    :param asset: Producer asset, for example BTC, BTC/USDT, ETH/BTC.
    :param fmt: Column format (str) or column formatter (callable).
    :param candle_type: Candle type for producer data.
    :param ffill: Forward fill parameter (kept for compatibility).
    """
    def decorator(fn: Callable) -> Callable:
        def wrapper(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
            # Only process if we're in dry-run/live mode with producer enabled
            runmode = self.config.get("runmode", "")
            producer_enabled = self.config.get("producer", {}).get("enabled", False)
            
            if runmode not in ["dry_run", "live"] or not producer_enabled:
                return fn(self, dataframe, metadata)
            
            # Get the dataframe for producer timeframe/asset
            target_asset = asset or metadata["pair"]
            target_timeframe = timeframe
            target_candle_type = candle_type or self.config.get("candle_type_def", "spot")
            
            if target_asset != metadata["pair"] or target_timeframe != self.timeframe:
                # Different pair or timeframe - get from exchange
                producer_df = self.dp.get_pair_dataframe(target_asset, target_timeframe, target_candle_type)
            else:
                # Same pair/timeframe - use current dataframe but process for producer
                producer_df = dataframe.copy()
            
            if producer_df.empty:
                return dataframe
            
            # Apply the producer function to calculate indicators
            result_df = fn(self, producer_df, metadata)
            
            # If we processed a different dataframe, don't modify the main one
            # The indicators will be available through dp.get_analyzed_dataframe()
            if target_asset != metadata["pair"] or target_timeframe != self.timeframe:
                return dataframe
            
            # Format columns if specified
            if fmt:
                if callable(fmt):
                    formatter = fmt
                else:
                    formatter = fmt.format
                
                # Get market info for formatting
                market = self.dp.market(target_asset) or {}
                base = market.get("base", "base").lower()
                quote = market.get("quote", "quote").lower()
                
                # Apply formatting
                new_columns = {}
                for col in result_df.columns:
                    if col in ["date", "open", "high", "low", "close", "volume"]:
                        new_columns[col] = col
                    else:
                        new_columns[col] = formatter(
                            column=col,
                            asset=target_asset,
                            timeframe=target_timeframe,
                            base=base,
                            quote=quote
                        )
                
                result_df = result_df.rename(columns=new_columns)
            
            return result_df
        
        return wrapper