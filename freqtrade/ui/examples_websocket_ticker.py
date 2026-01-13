#!/usr/bin/env python3
"""
WebSocket Ticker Example - Demonstrates real-time price streaming.

This example shows how to use the WebSocket ticker data source to get
live price updates from Binance, Coinbase, or Kraken.

Usage:
    python -m freqtrade.ui.examples_websocket_ticker
"""

import time
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_1_basic_websocket():
    """Example 1: Basic WebSocket connection to Binance."""
    print("\n" + "="*70)
    print("Example 1: Basic WebSocket Connection (Binance)")
    print("="*70)
    
    try:
        from freqtrade.ui.websocket_ticker_data import WebSocketTickerSource
        
        def on_price_update(ticker_data):
            print(f"📊 {ticker_data.symbol}: ${ticker_data.price:,.2f} "
                  f"(Volume: ${ticker_data.volume:,.0f}) from {ticker_data.exchange}")
        
        # Create WebSocket source
        source = WebSocketTickerSource(
            symbol="BTC/USDT",
            on_price_update=on_price_update,
            exchange="binance",
        )
        
        # Start connection
        print("🔌 Connecting to Binance WebSocket...")
        source.start()
        
        # Let it run for 10 seconds
        print("⏱️  Listening for 10 seconds...")
        time.sleep(10)
        
        # Stop connection
        print("🛑 Stopping WebSocket...")
        source.stop()
        
        print("✅ Example 1 complete!\n")
        
    except ImportError:
        print("❌ websockets library not installed. Install with: pip install websockets")
    except Exception as e:
        print(f"❌ Error: {e}")


def example_2_multiple_exchanges():
    """Example 2: WebSocket manager with automatic fallback."""
    print("\n" + "="*70)
    print("Example 2: WebSocket Manager with Fallback")
    print("="*70)
    
    try:
        from freqtrade.ui.websocket_ticker_data import WebSocketTickerManager
        
        def on_price_update(ticker_data):
            print(f"📊 {ticker_data.symbol}: ${ticker_data.price:,.2f} from {ticker_data.exchange}")
        
        # Create manager (tries Binance -> Coinbase -> Kraken)
        manager = WebSocketTickerManager(
            symbol="BTC/USDT",
            on_price_update=on_price_update,
        )
        
        # Start connection
        print("🔌 Connecting to exchanges (with fallback)...")
        manager.start()
        
        # Let it run for 10 seconds
        print("⏱️  Listening for 10 seconds...")
        time.sleep(10)
        
        # Get current price
        current_price = manager.get_current_price()
        if current_price:
            print(f"\n💰 Final price: ${current_price:,.2f}")
        
        # Stop connection
        print("🛑 Stopping WebSocket...")
        manager.stop()
        
        print("✅ Example 2 complete!\n")
        
    except ImportError:
        print("❌ websockets library not installed. Install with: pip install websockets")
    except Exception as e:
        print(f"❌ Error: {e}")


def example_3_market_simulator_with_websocket():
    """Example 3: Market simulator using WebSocket for real data."""
    print("\n" + "="*70)
    print("Example 3: Market Simulator with WebSocket")
    print("="*70)
    
    try:
        from freqtrade.ui.market_simulator import MarketSimulator
        
        # Create simulator with WebSocket enabled
        simulator = MarketSimulator(
            initial_price=50000.0,
            condition="real",
            symbol="BTC/USDT",
            use_websocket=True,
        )
        
        print("🔌 Market simulator started with WebSocket")
        print("⏱️  Generating 10 ticks...")
        
        # Generate 10 ticks
        for i in range(10):
            tick = simulator.generate_tick()
            print(f"Tick #{i+1}: ${tick.price:,.2f} at {tick.timestamp}")
            time.sleep(1)
        
        # Cleanup
        simulator.cleanup()
        
        print("✅ Example 3 complete!\n")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


def example_4_comparison_websocket_vs_rest():
    """Example 4: Compare WebSocket vs REST API latency."""
    print("\n" + "="*70)
    print("Example 4: WebSocket vs REST API Comparison")
    print("="*70)
    
    try:
        from freqtrade.ui.market_simulator import MarketSimulator
        import time
        
        # Test WebSocket
        print("\n📡 Testing WebSocket...")
        ws_simulator = MarketSimulator(
            initial_price=50000.0,
            condition="real",
            symbol="BTC/USDT",
            use_websocket=True,
        )
        
        ws_times = []
        for i in range(5):
            start = time.time()
            tick = ws_simulator.generate_tick()
            elapsed = (time.time() - start) * 1000
            ws_times.append(elapsed)
            print(f"  Tick #{i+1}: {elapsed:.2f}ms - ${tick.price:,.2f}")
            time.sleep(0.5)
        
        ws_simulator.cleanup()
        
        # Test REST API
        print("\n🌐 Testing REST API...")
        rest_simulator = MarketSimulator(
            initial_price=50000.0,
            condition="real",
            symbol="BTC/USDT",
            use_websocket=False,
        )
        
        rest_times = []
        for i in range(5):
            start = time.time()
            tick = rest_simulator.generate_tick()
            elapsed = (time.time() - start) * 1000
            rest_times.append(elapsed)
            print(f"  Tick #{i+1}: {elapsed:.2f}ms - ${tick.price:,.2f}")
            time.sleep(0.5)
        
        # Results
        print("\n📊 Performance Comparison:")
        print(f"  WebSocket avg: {sum(ws_times)/len(ws_times):.2f}ms")
        print(f"  REST API avg: {sum(rest_times)/len(rest_times):.2f}ms")
        print(f"  Speedup: {(sum(rest_times)/sum(ws_times)):.1f}x faster")
        
        print("✅ Example 4 complete!\n")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("\n" + "🚀 WebSocket Ticker Examples" + "\n")
    print("This demonstrates real-time price streaming from cryptocurrency exchanges")
    print("using free public WebSocket APIs (no authentication required).\n")
    
    try:
        # Run examples
        example_1_basic_websocket()
        example_2_multiple_exchanges()
        example_3_market_simulator_with_websocket()
        example_4_comparison_websocket_vs_rest()
        
        print("\n" + "="*70)
        print("✨ All examples complete!")
        print("="*70 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Cleaning up...")
    except Exception as e:
        logger.exception("Error running examples")
        print(f"\n❌ Fatal error: {e}")
