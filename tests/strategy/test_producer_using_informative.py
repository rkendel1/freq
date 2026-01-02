import pytest
from unittest.mock import MagicMock, patch

from pandas import DataFrame

from freqtrade.enums import CandleType, RunMode
from freqtrade.strategy import producer


class TestProducerUsesInformativeSystem:
    """Test @producer decorator using existing informative discovery system."""

    def test_producer_uses_ft_informative_attribute(self):
        """Test that @producer uses _ft_informative attribute like @informative."""
        
        @producer('1h')
        def test_producer_function(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
            return dataframe

        # Should have _ft_informative attribute (reuse existing system)
        assert hasattr(test_producer_function, "_ft_informative")
        assert hasattr(test_producer_function, "_ft_is_producer")
        
        informative_data_list = getattr(test_producer_function, "_ft_informative", [])
        assert len(informative_data_list) == 1
        
        # Should NOT have separate _ft_producer attribute
        assert not hasattr(test_producer_function, "_ft_producer")

    def test_producer_with_same_parameters_as_informative(self):
        """Test that @producer accepts same parameters as @informative."""
        
        @producer('1h', asset='BTC/USDT', fmt='custom_{column}', candle_type='mark', ffill=False)
        def test_function(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
            return dataframe

        informative_data_list = getattr(test_function, "_ft_informative", [])
        data = informative_data_list[0]
        
        assert data.timeframe == '1h'
        assert data.asset == 'BTC/USDT'
        assert data.fmt == 'custom_{column}'
        assert data.candle_type == CandleType.MARK
        assert data.ffill is False
        assert getattr(test_function, "_ft_is_producer", False) is True

    def test_interface_discovers_producer_automatically(self):
        """Test that strategy interface discovers producer methods automatically."""
        from freqtrade.strategy.interface import IStrategy
        
        class TestProducerStrategy(IStrategy):
            
            @producer('1h')
            def populate_producer_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
                dataframe['rsi'] = 50.0
                return dataframe
            
            def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
                return dataframe
            
            def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
                return dataframe
            
            def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
                return dataframe
        
        # Mock minimal dependencies to avoid full initialization
        mock_config = {
            'timeframe': '5m',
            'candle_type_def': CandleType.SPOT,
            'stake_currency': 'USDT'
        }
        
        # Test that discovery works
        assert hasattr(TestProducerStrategy.populate_producer_indicators_1h, '_ft_informative')
        assert hasattr(TestProducerStrategy.populate_producer_indicators_1h, '_ft_is_producer')
        
        # Check the data structure
        info_list = getattr(TestProducerStrategy.populate_producer_indicators_1h, '_ft_informative')
        assert len(info_list) == 1
        assert info_list[0].timeframe == '1h'

    @patch('freqtrade.strategy.producer_decorator._broadcast_informative_data')
    def test_interface_processes_producer_when_enabled(self, mock_broadcast):
        """Test that strategy interface processes producer methods when enabled."""
        from freqtrade.strategy.interface import IStrategy
        
        class TestProducerStrategy(IStrategy):
            
            @producer('1h')
            def populate_producer_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
                dataframe['rsi'] = 50.0
                return dataframe
            
            def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
                return dataframe
            
            def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
                return dataframe
            
            def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
                return dataframe
        
        # Mock strategy with producer config enabled
        strategy = TestProducerStrategy.__new__(TestProducerStrategy)
        strategy.config = {
            'timeframe': '5m',
            'candle_type_def': CandleType.SPOT,
            'stake_currency': 'USDT',
            'runmode': RunMode.DRY_RUN,
            'producer': {'enabled': True}
        }
        strategy._ft_informative = []
        
        # Manually trigger discovery (normally done in __init__)
        for attr_name in dir(strategy.__class__):
            cls_method = getattr(strategy.__class__, attr_name)
            if not callable(cls_method):
                continue
            informative_data_list = getattr(cls_method, "_ft_informative", None)
            if isinstance(informative_data_list, list):
                strategy._ft_informative.append((informative_data_list[0], cls_method))
        
        # Mock dependencies
        strategy.dp = MagicMock()
        strategy.dp.market.return_value = {'base': 'BTC', 'quote': 'USDT'}
        sample_df = DataFrame({'rsi': [50.0], 'date': ['2023-01-01']})
        strategy.dp.get_pair_dataframe.return_value = sample_df
        
        metadata = {'pair': 'BTC/USDT'}
        
        # Call advise_indicators to trigger processing
        result_df = strategy.advise_indicators(DataFrame(), metadata)
        
        # Should have called broadcast function
        mock_broadcast.assert_called_once()

    def test_interface_skips_producer_when_disabled(self):
        """Test that strategy interface skips producer when disabled."""
        from freqtrade.strategy.interface import IStrategy
        
        class TestProducerStrategy(IStrategy):
            
            @producer('1h')
            def populate_producer_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
                dataframe['rsi'] = 50.0
                return dataframe
            
            def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
                return dataframe
            
            def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
                return dataframe
            
            def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
                return dataframe
        
        # Mock strategy with producer config disabled
        strategy = TestProducerStrategy.__new__(TestProducerStrategy)
        strategy.config = {
            'timeframe': '5m',
            'candle_type_def': CandleType.SPOT,
            'stake_currency': 'USDT',
            'runmode': RunMode.DRY_RUN,
            'producer': {'enabled': False}
        }
        strategy._ft_informative = []
        
        # Manually trigger discovery
        for attr_name in dir(strategy.__class__):
            cls_method = getattr(strategy.__class__, attr_name)
            if not callable(cls_method):
                continue
            informative_data_list = getattr(cls_method, "_ft_informative", None)
            if isinstance(informative_data_list, list):
                strategy._ft_informative.append((informative_data_list[0], cls_method))
        
        # Mock merge function to track calls
        with patch('freqtrade.strategy.informative_decorator._create_and_merge_informative_pair') as mock_merge:
            metadata = {'pair': 'BTC/USDT'}
            
            # Call advise_indicators
            result_df = strategy.advise_indicators(DataFrame(), metadata)
            
            # Should have called normal merge (not broadcast)
            mock_merge.assert_called_once()

    def test_drop_in_replacement_compatibility(self):
        """Test that @producer can drop-replace @informative."""
        
        # Original informative decorator
        @producer('1h')  # Using producer decorator with informative interface
        def drop_in_function(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
            dataframe['rsi'] = 50.0
            return dataframe
        
        # Should have the same metadata structure as informative
        info_list = getattr(drop_in_function, "_ft_informative")
        assert len(info_list) == 1
        assert info_list[0].timeframe == '1h'
        assert getattr(drop_in_function, "_ft_is_producer", False) is True

    def test_no_interface_modifications_needed(self):
        """Test that no interface modifications are needed beyond existing changes."""
        from freqtrade.strategy.interface import IStrategy
        
        # IStrategy should still work normally
        assert hasattr(IStrategy, 'advise_indicators')
        assert hasattr(IStrategy, '_ft_informative')
        
        # Should NOT need new attributes for producer (we reuse existing system)
        assert not hasattr(IStrategy, '_ft_producer')
        assert not hasattr(IStrategy, 'process_producer_methods')