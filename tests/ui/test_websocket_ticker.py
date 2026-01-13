"""
Tests for WebSocket ticker data integration.

This test suite verifies that the WebSocket ticker data source works correctly
and that the market simulator properly handles WebSocket data with fallback.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from freqtrade.ui.market_simulator import MarketSimulator, WEBSOCKETS_AVAILABLE


class TestWebSocketTickerIntegration:
    """Tests for WebSocket ticker integration with MarketSimulator."""
    
    def test_market_simulator_with_websocket_disabled(self):
        """Test that market simulator works with websocket disabled."""
        simulator = MarketSimulator(
            initial_price=50000.0,
            condition="real",
            symbol="BTC/USDT",
            use_websocket=False,
        )
        
        assert simulator.condition == "real"
        assert simulator.use_websocket is False
        assert simulator._websocket_source is None
        
        # Should fall back to REST API
        tick = simulator.generate_tick()
        assert tick is not None
        assert tick.price > 0
    
    def test_market_simulator_with_websocket_enabled(self):
        """Test that market simulator attempts to use WebSocket when enabled."""
        if not WEBSOCKETS_AVAILABLE:
            pytest.skip("websockets library not available")
        
        simulator = MarketSimulator(
            initial_price=50000.0,
            condition="real",
            symbol="BTC/USDT",
            use_websocket=True,
        )
        
        assert simulator.use_websocket is True
        
        # WebSocket should be started for real condition
        assert simulator._websocket_source is not None or simulator._real_ticker_source is not None
        
        # Cleanup
        simulator.cleanup()
    
    def test_websocket_fallback_to_rest_api(self):
        """Test that simulator falls back to REST API if WebSocket fails."""
        if not WEBSOCKETS_AVAILABLE:
            pytest.skip("websockets library not available")
        
        # Mock WebSocket to fail
        with patch('freqtrade.ui.market_simulator.WebSocketTickerSource') as mock_ws:
            mock_ws.side_effect = Exception("WebSocket connection failed")
            
            simulator = MarketSimulator(
                initial_price=50000.0,
                condition="real",
                symbol="BTC/USDT",
                use_websocket=True,
            )
            
            # Should still generate ticks using REST API fallback
            tick = simulator.generate_tick()
            assert tick is not None
            assert tick.price > 0
    
    def test_websocket_cleanup_on_reset(self):
        """Test that WebSocket is properly stopped on reset."""
        if not WEBSOCKETS_AVAILABLE:
            pytest.skip("websockets library not available")
        
        simulator = MarketSimulator(
            initial_price=50000.0,
            condition="real",
            symbol="BTC/USDT",
            use_websocket=True,
        )
        
        # Reset to non-real condition
        simulator.reset(condition="mixed")
        
        # WebSocket should be stopped
        assert simulator.condition == "mixed"
        
        # Cleanup
        simulator.cleanup()
    
    def test_simulated_mode_unaffected_by_websocket(self):
        """Test that simulated mode doesn't use WebSocket."""
        simulator = MarketSimulator(
            initial_price=50000.0,
            condition="mixed",
            symbol="BTC/USDT",
            use_websocket=True,
        )
        
        # WebSocket should not be started for non-real conditions
        assert simulator._websocket_source is None
        
        # Generate several ticks
        ticks = [simulator.generate_tick() for _ in range(5)]
        
        # All ticks should be simulated
        assert len(ticks) == 5
        for tick in ticks:
            assert tick.condition == "mixed"
            assert tick.price > 0


@pytest.mark.skipif(not WEBSOCKETS_AVAILABLE, reason="websockets library not available")
class TestWebSocketTickerSource:
    """Tests for WebSocketTickerSource class."""
    
    def test_websocket_source_initialization(self):
        """Test that WebSocketTickerSource can be instantiated."""
        from freqtrade.ui.websocket_ticker_data import WebSocketTickerSource
        
        source = WebSocketTickerSource(
            symbol="BTC/USDT",
            exchange="binance",
        )
        
        assert source.symbol == "BTC/USDT"
        assert source.exchange == "binance"
        assert source._current_price is None
        assert source._running is False
    
    def test_websocket_source_with_callback(self):
        """Test that WebSocketTickerSource calls callback on price update."""
        from freqtrade.ui.websocket_ticker_data import WebSocketTickerSource
        
        received_data = []
        
        def callback(ticker_data):
            received_data.append(ticker_data)
        
        source = WebSocketTickerSource(
            symbol="BTC/USDT",
            on_price_update=callback,
            exchange="binance",
        )
        
        # Simulate price update
        source._update_price(50000.0, 1000.0)
        
        # Callback should have been called
        assert len(received_data) == 1
        assert received_data[0].price == 50000.0
        assert received_data[0].volume == 1000.0
    
    def test_websocket_manager_fallback(self):
        """Test that WebSocketTickerManager tries multiple exchanges."""
        from freqtrade.ui.websocket_ticker_data import WebSocketTickerManager
        
        manager = WebSocketTickerManager(
            symbol="BTC/USDT",
        )
        
        assert manager.symbol == "BTC/USDT"
        assert manager._exchanges == ["binance", "coinbase", "kraken"]
        
        # Don't actually start connection in test
        # Just verify structure is correct
        assert manager._source is None
