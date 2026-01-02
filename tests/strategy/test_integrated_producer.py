import pytest
from unittest.mock import MagicMock

from pandas import DataFrame

from freqtrade.enums import RunMode
from freqtrade.strategy import producer


class TestIntegratedProducerDecorator:
    """Test producer decorator that uses existing analyzed dataframe system."""

    def test_producer_decorator_basic(self):
        """Test basic producer decorator functionality."""
        
        @producer('1h')
        def test_producer_fn(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
            dataframe['test_indicator'] = 50.0
            return dataframe

        assert callable(test_producer_fn)

    def test_producer_wrapper_uses_analyzed_dataframe(self):
        """Test that wrapper leverages get_analyzed_dataframe system."""
        
        @producer('1h')
        def test_fn(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
            dataframe['indicator'] = 50.0
            return dataframe
        
        # Mock strategy with producer enabled
        strategy = MagicMock()
        strategy.config = {
            'runmode': 'dry_run',
            'producer': {'enabled': True},
            'candle_type_def': 'spot'
        }
        strategy.timeframe = '5m'
        strategy.dp = MagicMock()
        
        # Mock data provider methods
        strategy.dp.get_pair_dataframe.return_value = DataFrame({'indicator': [50.0]})
        strategy.dp.market.return_value = {'base': 'BTC', 'quote': 'USDT'}
        
        # Call wrapper
        result = test_fn(strategy, DataFrame({'test': [1]}), {'pair': 'BTC/USDT'})
        
        # Should have processed the producer dataframe
        strategy.dp.get_pair_dataframe.assert_called_once()

    def test_producer_skips_when_disabled(self):
        """Test that producer skips when not enabled."""
        
        @producer('1h')
        def test_fn(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
            dataframe['indicator'] = 50.0
            return dataframe
        
        # Mock strategy with producer disabled
        strategy = MagicMock()
        strategy.config = {
            'runmode': 'backtest',  # Wrong mode
            'producer': {'enabled': True},
            'candle_type_def': 'spot'
        }
        
        original_df = DataFrame({'test': [1]})
        
        # Call wrapper - should return original unchanged
        result = test_fn(strategy, original_df, {'pair': 'BTC/USDT'})
        
        assert result is original_df

    def test_producer_handles_different_timeframe(self):
        """Test producer with different timeframe gets appropriate data."""
        
        @producer('1h')
        def test_fn(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
            dataframe['hourly_indicator'] = 50.0
            return dataframe
        
        strategy = MagicMock()
        strategy.config = {
            'runmode': 'dry_run',
            'producer': {'enabled': True},
            'candle_type_def': 'spot'
        }
        strategy.timeframe = '5m'  # Strategy timeframe is 5m
        strategy.dp = MagicMock()
        
        # Mock different timeframe dataframe
        hourly_df = DataFrame({'hourly_data': [1, 2, 3]})
        strategy.dp.get_pair_dataframe.return_value = hourly_df
        strategy.dp.market.return_value = {'base': 'BTC', 'quote': 'USDT'}
        
        result = test_fn(strategy, DataFrame({'test': [1]}), {'pair': 'BTC/USDT'})
        
        # Should get 1h data (different from strategy's 5m)
        strategy.dp.get_pair_dataframe.assert_called_with(
            'BTC/USDT', '1h', 'spot'
        )

    def test_producer_handles_different_asset(self):
        """Test producer with different asset gets appropriate data."""
        
        @producer('1h', asset='ETH/USDT')
        def test_fn(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
            dataframe['eth_indicator'] = 50.0
            return dataframe
        
        strategy = MagicMock()
        strategy.config = {
            'runmode': 'dry_run',
            'producer': {'enabled': True},
            'candle_type_def': 'spot'
        }
        strategy.timeframe = '5m'
        strategy.dp = MagicMock()
        
        # Mock ETH dataframe
        eth_df = DataFrame({'eth_data': [1, 2, 3]})
        strategy.dp.get_pair_dataframe.return_value = eth_df
        strategy.dp.market.return_value = {'base': 'ETH', 'quote': 'USDT'}
        
        result = test_fn(strategy, DataFrame({'test': [1]}), {'pair': 'BTC/USDT'})
        
        # Should get ETH data (different from current pair)
        strategy.dp.get_pair_dataframe.assert_called_with(
            'ETH/USDT', '1h', 'spot'
        )

    def test_producer_with_custom_formatting(self):
        """Test producer with custom column formatting."""
        
        @producer('1h', fmt='custom_{base}_{column}_{timeframe}')
        def test_fn(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
            dataframe['indicator'] = 50.0
            return dataframe
        
        strategy = MagicMock()
        strategy.config = {
            'runmode': 'dry_run',
            'producer': {'enabled': True},
            'candle_type_def': 'spot'
        }
        strategy.timeframe = '5m'
        strategy.dp = MagicMock()
        
        df_with_indicator = DataFrame({'indicator': [50.0], 'close': [100.0]})
        strategy.dp.get_pair_dataframe.return_value = df_with_indicator
        strategy.dp.market.return_value = {'base': 'BTC', 'quote': 'USDT'}
        
        # Mock rename to test formatting
        with pytest.mock.patch.object(DataFrame, 'rename') as mock_rename:
            mock_rename.return_value = DataFrame({'custom_btc_indicator_1h': [50.0]})
            
            result = test_fn(strategy, DataFrame({'test': [1]}), {'pair': 'BTC/USDT'})
            
            # Should apply custom formatting
            mock_rename.assert_called_once()

    def test_no_interface_changes_needed(self):
        """Test that no interface modifications are required."""
        from freqtrade.strategy.interface import IStrategy
        
        # IStrategy should be completely unchanged
        assert hasattr(IStrategy, 'advise_indicators')
        assert hasattr(IStrategy, '_ft_informative')
        
        # No new attributes needed for producer
        assert not hasattr(IStrategy, '_ft_producer')
        assert not hasattr(IStrategy, 'process_producer_methods')