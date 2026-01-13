"""
Real Ticker Data - Usage Examples

This file demonstrates how to use the real ticker data feature in the demo UI.
"""

# Example 1: Fetch current real price for a symbol
# ================================================

import requests

# Start demo server first: python -m freqtrade.ui.demo_server

# Fetch BTC/USDT price
response = requests.get("http://127.0.0.1:5000/api/real-price/BTC-USDT")
if response.ok:
    data = response.json()
    print(f"BTC/USDT Price: ${data['price']:,.2f}")
    print(f"Exchange: {data['exchange']}")
    print(f"Volume: {data['volume']:,.0f}")
else:
    print(f"Error: {response.json()['error']}")

# Example 2: Start automated mode with real ticker data
# =====================================================

# Start automated mode with real market data
response = requests.post(
    "http://127.0.0.1:5000/api/automated/start",
    json={"condition": "real"}
)
if response.ok:
    data = response.json()
    print(f"Automated mode started: {data['condition']} for {data['symbol']}")
else:
    print(f"Error: {response.json()['error']}")

# Generate ticks (this will fetch real prices from exchanges)
for i in range(5):
    response = requests.post("http://127.0.0.1:5000/api/automated/tick")
    if response.ok:
        tick_data = response.json()
        price = tick_data["market_data"]["price"]
        print(f"Tick {i+1}: ${price:,.2f}")

# Example 3: Configure symbol with real price
# ===========================================

# Set trading pair and fetch its current real price
response = requests.post(
    "http://127.0.0.1:5000/api/config/symbol",
    json={
        "symbol": "ETH/USDT",
        "use_real_price": True
    }
)
if response.ok:
    data = response.json()
    print(f"Symbol: {data['symbol']}")
    print(f"Current Price: ${data['price']:,.2f}")


# Example 4: Using RealTickerDataSource directly in Python
# ========================================================

from freqtrade.ui.real_ticker_data import RealTickerDataSource

# Create ticker data source
ticker_source = RealTickerDataSource(cache_duration_seconds=30)

# Fetch BTC/USDT
ticker = ticker_source.fetch_ticker("BTC/USDT")
if ticker:
    print(f"BTC/USDT: ${ticker.price:,.2f} from {ticker.exchange}")
    print(f"Volume: {ticker.volume:,.0f}")
else:
    print("Failed to fetch ticker data (may be due to network restrictions)")

# Fetch ETH/USDT
price = ticker_source.get_current_price("ETH/USDT")
if price:
    print(f"ETH/USDT: ${price:,.2f}")


# Example 5: Using MarketSimulator with real data
# ===============================================

from freqtrade.ui.market_simulator import MarketSimulator

# Create simulator in real mode
simulator = MarketSimulator(
    initial_price=50000.0,  # Fallback price if API fails
    condition="real",
    symbol="BTC/USDT",
)

# Generate ticks (will fetch real data or fallback to simulation)
for i in range(5):
    tick = simulator.generate_tick()
    print(f"Tick {i+1}: ${tick.price:,.2f}, volume: {tick.volume:,.0f}, source: {tick.condition}")


# Example 6: Comparing real vs simulated data
# ===========================================

# Real mode
real_simulator = MarketSimulator(
    initial_price=50000.0,
    condition="real",
    symbol="BTC/USDT",
)

# Simulated mode
sim_simulator = MarketSimulator(
    initial_price=50000.0,
    condition="mixed",
    symbol="BTC/USDT",
)

print("\nReal Mode:")
for i in range(3):
    tick = real_simulator.generate_tick()
    print(f"  Tick {i+1}: ${tick.price:,.2f}")

print("\nSimulated Mode:")
for i in range(3):
    tick = sim_simulator.generate_tick()
    print(f"  Tick {i+1}: ${tick.price:,.2f}")


# Example 7: Using different trading pairs
# ========================================

# Supported pairs (any pair available on Binance, Bybit, or Kraken)
pairs = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"]

ticker_source = RealTickerDataSource()

for pair in pairs:
    ticker = ticker_source.fetch_ticker(pair)
    if ticker:
        print(f"{pair}: ${ticker.price:,.2f} from {ticker.exchange}")
    else:
        print(f"{pair}: Unable to fetch (may not be available on all exchanges)")


# Example 8: Error handling and fallback
# ======================================

from freqtrade.ui.market_simulator import MarketSimulator

# Create simulator with real mode but invalid symbol
simulator = MarketSimulator(
    initial_price=100.0,
    condition="real",
    symbol="INVALID/PAIR",
)

# This will automatically fallback to simulated data
tick = simulator.generate_tick()
print(f"Fallback tick: ${tick.price:,.2f}")
print(f"Note: Used simulation because invalid symbol couldn't be fetched")
