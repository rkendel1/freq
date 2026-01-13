"""
Real Ticker Data - Usage Examples

This file demonstrates how to use the real ticker data feature in the demo UI.

Data Sources (in priority order):
1. CoinPaprika (free API, no key required)
2. Binance (CCXT fallback)
3. Bybit (CCXT fallback)
4. Kraken (CCXT fallback)
5. Simulated data (if all fail)
"""

# Example 1: Fetch current real price for a symbol
# ================================================

import requests

# Start demo server first: python -m freqtrade.ui.demo_server

# Fetch BTC/USDT price (will try CoinPaprika first)
response = requests.get("http://127.0.0.1:5000/api/real-price/BTC-USDT")
if response.ok:
    data = response.json()
    print(f"BTC/USDT Price: ${data['price']:,.2f}")
    print(f"Exchange: {data['exchange']}")  # e.g., "coinpaprika" or "binance"
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

# Fetch BTC/USDT (tries CoinPaprika first, then CCXT exchanges)
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


# Example 4a: CoinPaprika-specific features
# =========================================

# Check supported symbols using public API
supported_symbols = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT",
    "DOGE/USDT", "ADA/USDT", "MATIC/USDT", "DOT/USDT"
]

ticker_source = RealTickerDataSource()

print("\nCoinPaprika Supported Symbols:")
for symbol in supported_symbols:
    cp_id = ticker_source.get_coinpaprika_id(symbol)  # Using public method
    if cp_id:
        print(f"  {symbol:12} → {cp_id}")


# Example 4b: Direct CoinPaprika API usage
# ========================================

import requests

# Fetch directly from CoinPaprika API
response = requests.get("https://api.coinpaprika.com/v1/tickers/btc-bitcoin")
if response.ok:
    data = response.json()
    price = data["quotes"]["USD"]["price"]
    volume = data["quotes"]["USD"]["volume_24h"]
    print(f"\nDirect CoinPaprika fetch:")
    print(f"  BTC Price: ${price:,.2f}")
    print(f"  24h Volume: ${volume:,.0f}")


# Example 4c: Prefer specific exchange
# ====================================

ticker_source = RealTickerDataSource()

# Prefer CoinPaprika (default, but showing explicit preference)
ticker = ticker_source.fetch_ticker("BTC/USDT", prefer_exchange="coinpaprika")
if ticker:
    print(f"\nPreferred source: {ticker.exchange}")

# Prefer Binance (skip CoinPaprika)
ticker = ticker_source.fetch_ticker("BTC/USDT", prefer_exchange="binance")
if ticker:
    print(f"Preferred source: {ticker.exchange}")


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

# CoinPaprika supported pairs (15+ major cryptocurrencies)
coinpaprika_pairs = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT",
    "DOGE/USDT", "ADA/USDT", "MATIC/USDT", "DOT/USDT"
]

# Additional pairs available via CCXT fallback
all_pairs = coinpaprika_pairs + ["XRP/USDT", "AVAX/USDT", "LINK/USDT"]

ticker_source = RealTickerDataSource()

print("\nFetching prices for multiple pairs:")
for pair in all_pairs:
    ticker = ticker_source.fetch_ticker(pair)
    if ticker:
        source = "🌐 CP" if ticker.exchange == "coinpaprika" else f"📊 {ticker.exchange}"
        print(f"  {source} | {pair:12} ${ticker.price:,.2f}")
    else:
        print(f"  ❌    | {pair:12} Unable to fetch")


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


# Example 9: Understanding the fallback chain
# ===========================================

from freqtrade.ui.real_ticker_data import RealTickerDataSource
import logging

# Enable debug logging to see fallback in action
logging.basicConfig(level=logging.DEBUG)

ticker_source = RealTickerDataSource()

# This demonstrates the fallback order:
# 1. Try CoinPaprika (fast, free, no auth)
# 2. If CoinPaprika fails, try Binance (CCXT)
# 3. If Binance fails, try Bybit (CCXT)
# 4. If Bybit fails, try Kraken (CCXT)
# 5. If all fail, return None (MarketSimulator uses simulated data)

print("\nFallback chain demonstration:")
print("Attempting to fetch BTC/USDT...")
print("(Check logs to see which source succeeds)")

ticker = ticker_source.fetch_ticker("BTC/USDT")
if ticker:
    print(f"\n✓ Successfully fetched from: {ticker.exchange}")
    print(f"  Price: ${ticker.price:,.2f}")
else:
    print(f"\n✗ All sources failed - will use simulated data")
    print(f"  This is expected in sandboxed/restricted environments")

