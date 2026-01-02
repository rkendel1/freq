import pytest
from unittest.mock import MagicMock

from pandas import DataFrame

from freqtrade.enums import CandleType, RunMode
from freqtrade.strategy import producer


class TestSimpleProducerDecorator:
    """Test simple producer decorator implementation."""

    def test_producer_decorator_basic(self):
        """Test basic producer decorator functionality."""
        
        @producer('1h')
        def test_producer_fn(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
            dataframe['rsi'] = 50.0
            return dataframe

        assert callable(test_producer_fn)

    def test_producer_wrapper_returns_original_df_when_disabled(self):
        """Test that wrapper returns original dataframe when producer disabled."""
        
        @producer('1h')
        def test_fn(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
            dataframe['rsi'] = 50.0
            return dataframe
        
        # Mock strategy with producer disabled
        strategy = MagicMock()
        strategy.config = {'producer': {'enabled': False}}
        
        result = test_fn(strategy, DataFrame({'test': [1]}), {'pair': 'BTC/USDT'})
        
        # Should return original dataframe
        assert 'rsi' not in result.columns

    def test_producer_wrapper_returns_original_df_in_backtest(self):
        """Test that wrapper returns original dataframe in backtest mode."""
        
        @producer('1h')
        def test_fn(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
            dataframe['rsi'] = 50.0
            return dataframe
        
        # Mock strategy in backtest mode
        strategy = MagicMock()
        strategy.config = {'producer': {'enabled': True}, 'runmode': 'backtest'}
        
        result = test_fn(strategy, DataFrame({'test': [1]}), {'pair': 'BTC/USDT'})
        
        # Should return original dataframe
        assert 'rsi' not in result.columns

    def test_producer_enabled_in_dry_run(self):
        """Test that producer works in dry run mode."""
        
        @producer('1h')
        def test_fn(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
            dataframe['rsi'] = 50.0
            return dataframe
        
        # Mock strategy in dry run mode with producer enabled
        strategy = MagicMock()
        strategy.config = {'producer': {'enabled': True}, 'runmode': RunMode.DRY_RUN}
        strategy.timeframe = '5m'
        strategy.dp = MagicMock()
        strategy._rpc = MagicMock()
        
        # Mock data provider methods
        strategy.dp.get_pair_dataframe.return_value = DataFrame({'rsi': [50.0], 'close': [100.0]})
        strategy.dp.market.return_value = {'base': 'BTC', 'quote': 'USDT'}
        
        result = test_fn(strategy, DataFrame({'test': [1]}), {'pair': 'BTC/USDT'})
        
        # Should return original dataframe unchanged
        assert 'test' in result.columns
        assert 'rsi' not in result.columns  # Not merged
        
        # Should have called RPC send_msg for broadcast
        strategy._rpc.send_msg.assert_called_once()

    def test_no_interface_changes_needed(self):
        """Test that no interface changes are needed."""
        from freqtrade.strategy.interface import IStrategy
        
        # IStrategy should be completely unchanged
        assert hasattr(IStrategy, 'advise_indicators')
        assert hasattr(IStrategy, '_ft_informative')
        
        # No new attributes needed
        assert not hasattr(IStrategy, '_ft_producer')
        assert not hasattr(IStrategy, 'process_producer_methods')

    def test_same_parameters_as_informative(self):
        """Test that @producer accepts same parameters as @informative."""
        
        # All these should work without errors
        @producer('1h')
        def fn1(self, df, meta): return df
        
        @producer('1h', asset='BTC/USDT')
        def fn2(self, df, meta): return df
        
        @producer('1h', fmt='custom_{column}')
        def fn3(self, df, meta): return df
        
        @producer('1h', candle_type='mark')
        def fn4(self, df, meta): return df
        
        @producer('1h', ffill=False)
        def fn5(self, df, meta): return df
        
        # All should be callable
        assert all(callable(fn) for fn in [fn1, fn2, fn3, fn4, fn5])