# WebSocket Ticker Integration

## Overview

The demo UI now supports **real-time price updates via WebSocket** connections to free public cryptocurrency exchange APIs. This provides millisecond-latency price updates without requiring authentication or API keys.

## Features

- ✅ **Real-time streaming**: Millisecond latency (vs 2-second polling with REST API)
- ✅ **Free public APIs**: No authentication or API keys required
- ✅ **Multiple exchanges**: Automatic fallback between Binance, Coinbase, and Kraken
- ✅ **Automatic reconnection**: Handles disconnects and reconnects automatically
- ✅ **Thread-safe**: Runs in background thread, safe for concurrent access
- ✅ **Graceful fallback**: Falls back to REST API if WebSocket unavailable

## Supported Exchanges

### 1. Binance (Default - Fastest)
- **WebSocket URL**: `wss://stream.binance.com:9443/ws/{symbol}@trade`
- **Latency**: ~50-100ms
- **Update frequency**: Multiple times per second
- **Advantages**: Lowest latency, highest update frequency
- **Supported pairs**: All major pairs (BTC/USDT, ETH/USDT, etc.)

### 2. Coinbase (USD Native)
- **WebSocket URL**: `wss://ws-feed.exchange.coinbase.com`
- **Latency**: ~100-200ms
- **Update frequency**: ~1 second
- **Advantages**: USD-native pricing, institutional-grade
- **Supported pairs**: BTC-USD, ETH-USD, etc.

### 3. Kraken (Fallback)
- **WebSocket URL**: `wss://ws.kraken.com`
- **Latency**: ~200-500ms
- **Update frequency**: ~1 second
- **Advantages**: Regulated, reliable
- **Supported pairs**: XBT/USD, ETH/USD, etc.

## Installation

```bash
# Install websockets library
pip install websockets>=13.0

# Or install all requirements
pip install -r requirements.txt
```

## Usage

### Option 1: Market Simulator (Recommended)

```python
from freqtrade.ui.market_simulator import MarketSimulator

# Create simulator with WebSocket enabled (default)
simulator = MarketSimulator(
    initial_price=50000.0,
    condition="real",
    symbol="BTC/USDT",
    use_websocket=True,  # Enable WebSocket (default: True)
)

# Generate ticks - automatically uses WebSocket for real-time data
for i in range(10):
    tick = simulator.generate_tick()
    print(f"Tick #{i+1}: ${tick.price:,.2f}")
    time.sleep(0.5)  # Can poll as fast as you want!

# Cleanup when done
simulator.cleanup()
```

### Option 2: Direct WebSocket Source

```python
from freqtrade.ui.websocket_ticker_data import WebSocketTickerSource

def on_price_update(ticker_data):
    print(f"Price: ${ticker_data.price:,.2f} from {ticker_data.exchange}")

# Create WebSocket source
source = WebSocketTickerSource(
    symbol="BTC/USDT",
    on_price_update=on_price_update,
    exchange="binance",
)

# Start streaming
source.start()

# Let it run...
time.sleep(60)

# Stop when done
source.stop()
```

### Option 3: Manager with Automatic Fallback

```python
from freqtrade.ui.websocket_ticker_data import WebSocketTickerManager

# Create manager (tries Binance -> Coinbase -> Kraken)
manager = WebSocketTickerManager(
    symbol="BTC/USDT",
    on_price_update=lambda data: print(f"${data.price:,.2f}"),
)

# Start connection with automatic fallback
manager.start()

# Get current price anytime
price = manager.get_current_price()
print(f"Current BTC price: ${price:,.2f}")

# Stop when done
manager.stop()
```

## Demo UI Integration

The WebSocket integration is **automatically enabled** in the demo UI when you select "Real (Live Tick Data)" market condition.

### Behavior

1. **WebSocket First**: Tries to connect to Binance WebSocket for real-time updates
2. **REST Fallback**: If WebSocket fails or unavailable, falls back to REST API (2s cache)
3. **Automatic**: No configuration needed - works out of the box

### Configuration

WebSocket can be disabled if needed:

```python
# In demo_server.py or custom scripts
simulator = MarketSimulator(
    condition="real",
    symbol="BTC/USDT",
    use_websocket=False,  # Disable WebSocket, use REST API only
)
```

## Performance Comparison

| Method | Latency | Updates/sec | API Calls/min | Network Usage |
|--------|---------|-------------|---------------|---------------|
| **WebSocket** | ~50-100ms | 10-20 | 1 connection | ~1 KB/s |
| **REST (2s cache)** | ~500-2000ms | 0.5 | ~30 | ~5 KB/min |
| **REST (no cache)** | ~500-2000ms | 2 | ~120 | ~20 KB/min |

### Real-World Impact

**Without WebSocket (REST with 2s cache):**
- Price updates every 2 seconds
- Visible lag in UI
- 30 API calls per minute

**With WebSocket:**
- Price updates 10-20 times per second
- Smooth, real-time updates in UI
- Single persistent connection
- 20x faster updates with less network traffic

## Error Handling

The implementation includes comprehensive error handling:

1. **Connection Failures**: Automatically reconnects after 1-second delay
2. **Library Missing**: Gracefully falls back to REST API if `websockets` not installed
3. **Exchange Down**: Tries fallback exchanges (Binance → Coinbase → Kraken)
4. **Malformed Data**: Logs errors and continues without crashing
5. **Thread Safety**: Safe to call from multiple threads

## Examples

See `freqtrade/ui/examples_websocket_ticker.py` for comprehensive examples:

```bash
# Run examples
python -m freqtrade.ui.examples_websocket_ticker
```

**Examples included:**
1. Basic WebSocket connection to Binance
2. WebSocket manager with automatic fallback
3. Market simulator with WebSocket
4. Performance comparison: WebSocket vs REST

## Testing

Run the WebSocket tests:

```bash
# Test WebSocket integration
pytest tests/ui/test_websocket_ticker.py -v

# Test market simulator
pytest tests/ui/test_real_ticker_data.py -v
```

## Troubleshooting

### WebSocket Not Connecting

**Issue**: WebSocket fails to connect or immediately disconnects

**Solutions**:
1. Check internet connectivity
2. Verify firewall allows WebSocket connections (ports 443, 9443)
3. Try different exchange: `exchange="coinbase"` or `exchange="kraken"`
4. Check logs for specific error messages

### High CPU Usage

**Issue**: WebSocket consuming too much CPU

**Solutions**:
1. Reduce callback processing in `on_price_update`
2. Use debouncing to limit update frequency
3. Consider using REST API instead for less frequent updates

### Memory Leaks

**Issue**: Memory usage grows over time

**Solutions**:
1. Always call `cleanup()` or `stop()` when done
2. Use context managers for automatic cleanup
3. Check for unbounded data structures in callbacks

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MarketSimulator                           │
│                                                              │
│  ┌─────────────┐                    ┌──────────────────┐   │
│  │  Real Mode  │ ───WebSocket OK──► │ WebSocketSource  │   │
│  │             │                     │  (Binance/etc)   │   │
│  └─────────────┘                     └──────────────────┘   │
│        │                                      │              │
│        │                                      ▼              │
│        │                            ┌──────────────────┐    │
│        └──WebSocket Fail/Disabled──►│ RealTickerData   │    │
│                                     │  (REST API)      │    │
│                                     └──────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Credits

WebSocket endpoints provided by:
- **Binance**: Free public WebSocket API
- **Coinbase**: Free public WebSocket API
- **Kraken**: Free public WebSocket API

## Related Documentation

- `REAL_TICKER_IMPLEMENTATION.md` - Original REST API implementation
- `examples_websocket_ticker.py` - Code examples
- `websocket_ticker_data.py` - WebSocket implementation
- `market_simulator.py` - Market simulator with WebSocket support
