import pytest
from unittest.mock import MagicMock, patch

from pandas import DataFrame

from freqtrade.enums import CandleType, RunMode
from freqtrade.strategy import producer


class TestIndependentProducerDecorator:
    """Test @producer decorator as independent implementation."""

    def test_producer_decorator_creates_metadata(self):
        """Test that @producer creates _ft_producer attribute."""
        
        @producer('1h')
        def test_producer_function(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
            return dataframe

        # Should have _ft_producer attribute (separate from _ft_informative)
        assert hasattr(test_producer_function, "_ft_producer")
        producer_data_list = getattr(test_producer_function, "_ft_producer", [])
        assert len(producer_data_list) == 1
        
        # Should NOT have _ft_informative attribute
        assert not hasattr(test_producer_function, "_ft_informative")

    def test_producer_with_same_parameters_as_informative(self):
        """Test that @producer accepts same parameters as @informative."""
        
        @producer('1h', asset='BTC/USDT', fmt='custom_{column}', candle_type='mark', ffill=False)
        def test_function(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
            return dataframe

        producer_data_list = getattr(test_function, "_ft_producer", [])
        data = producer_data_list[0]
        
        assert data.timeframe == '1h'
        assert data.asset == 'BTC/USDT'
        assert data.fmt == 'custom_{column}'
        assert data.candle_type == CandleType.MARK
        assert data.ffill is False

    def test_producer_mode_detection_function(self):
        """Test producer mode detection function."""
        from freqtrade.strategy.producer_decorator import is_producer_mode
        
        strategy_mock = MagicMock()
        
        # Test with producer enabled and dry run
        strategy_mock.config = {'runmode': RunMode.DRY_RUN, 'producer': {'enabled': True}}
        assert is_producer_mode(strategy_mock) is True
        
        # Test with producer enabled and live run
        strategy_mock.config = {'runmode': RunMode.LIVE, 'producer': {'enabled': True}}
        assert is_producer_mode(strategy_mock) is True
        
        # Test with producer disabled
        strategy_mock.config = {'runmode': RunMode.DRY_RUN, 'producer': {'enabled': False}}
        assert is_producer_mode(strategy_mock) is False
        
        # Test with backtest mode
        strategy_mock.config = {'runmode': 'backtest', 'producer': {'enabled': True}}
        assert is_producer_mode(strategy_mock) is False

    def test_process_producer_methods_no_change_when_disabled(self):
        """Test that process_producer_methods returns unchanged when disabled."""
        from freqtrade.strategy.producer_decorator import process_producer_methods
        
        strategy_mock = MagicMock()
        strategy_mock.config = {'runmode': 'backtest', 'producer': {'enabled': False}}
        
        test_df = DataFrame({'test': [1, 2, 3]})
        metadata = {'pair': 'BTC/USDT'}
        
        result = process_producer_methods(strategy_mock, test_df, metadata)
        
        # Should return unchanged dataframe
        assert result is test_df

    @patch('freqtrade.strategy.producer_decorator._broadcast_producer_data')
    def test_process_producer_methods_calls_broadcast_when_enabled(self, mock_broadcast):
        """Test that process_producer_methods calls broadcast when enabled."""
        from freqtrade.strategy.producer_decorator import process_producer_methods
        
        # Create a mock strategy class with producer method
        class MockStrategy:
            def __init__(self, config):
                self.config = config
                self.timeframe = '5m'
                self.dp = MagicMock()
            
            @producer('1h')
            def producer_method(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
                return dataframe
        
        strategy = MockStrategy({'runmode': RunMode.DRY_RUN, 'producer': {'enabled': True}})
        strategy.__class__ = MockStrategy
        
        test_df = DataFrame({'test': [1, 2, 3]})
        metadata = {'pair': 'BTC/USDT'}
        
        result = process_producer_methods(strategy, test_df, metadata)
        
        # Should call broadcast function
        mock_broadcast.assert_called()

    @patch('freqtrade.strategy.producer_decorator.dt_now')
    def test_broadcast_function_uses_existing_infrastructure(self, mock_dt_now):
        """Test that broadcast function uses existing RPC infrastructure."""
        mock_dt_now.return_value = '2023-01-01T00:00:00'
        
        from freqtrade.strategy.producer_decorator import _broadcast_producer_data
        
        strategy_mock = MagicMock()
        strategy_mock.config = {'runmode': RunMode.DRY_RUN, 'producer': {'enabled': True}}
        strategy_mock.timeframe = '5m'
        strategy_mock.dp = MagicMock()
        strategy_mock.dp.market.return_value = {'base': 'BTC', 'quote': 'USDT'}
        strategy_mock._rpc = MagicMock()
        
        from freqtrade.strategy.producer_decorator import ProducerData
        data = ProducerData(None, '1h', None, True, CandleType.SPOT)
        
        metadata_mock = {'pair': 'BTC/USDT'}
        
        # Mock dataframe and function
        sample_df = DataFrame({'rsi': [50.0], 'date': ['2023-01-01']})
        strategy_mock.dp.get_pair_dataframe.return_value = sample_df
        mock_function = MagicMock(return_value=sample_df)
        
        # Call broadcast function
        _broadcast_producer_data(strategy_mock, DataFrame(), metadata_mock, data, mock_function)
        
        # Should have called RPC send_msg
        strategy_mock._rpc.send_msg.assert_called_once()
        
        # Check message format
        call_args = strategy_mock._rpc.send_msg.call_args[0][0]
        assert call_args['type'] == 'analyzed_df'
        assert 'key' in call_args['data']
        assert 'df' in call_args['data']
        assert 'la' in call_args['data']

    def test_no_interface_modifications_needed(self):
        """Test that no interface modifications are needed."""
        from freqtrade.strategy.interface import IStrategy
        
        # IStrategy should still work normally
        assert hasattr(IStrategy, 'advise_indicators')
        assert hasattr(IStrategy, '_ft_informative')
        
        # Should NOT have _ft_producer (that's from our independent decorator)
        assert not hasattr(IStrategy, '_ft_producer')

    def test_drop_in_replacement_compatibility(self):
        """Test that @producer can replace @informative with same interface."""
        
        # Original informative decorator
        @producer('1h')  # Same parameters, different behavior
        def drop_in_producer(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
            dataframe['rsi'] = 50.0
            return dataframe
        
        # Should have producer metadata
        producer_info = getattr(drop_in_producer, "_ft_producer")
        assert len(producer_info) == 1
        assert producer_info[0].timeframe == '1h'

    def test_multiple_producers_on_same_method(self):
        """Test multiple producer decorators on same method."""
        
        @producer('1h')
        @producer('4h')
        def multi_producer(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
            return dataframe

        producer_list = getattr(multi_producer, "_ft_producer")
        assert len(producer_list) == 2
        
        timeframes = [data.timeframe for data in producer_list]
        assert '1h' in timeframes
        assert '4h' in timeframes