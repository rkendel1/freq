"""
WebSocket Ticker Data Source - Real-time price streaming from exchanges.

This module provides live ticker data via WebSocket connections to free public APIs.
Supports Binance, Coinbase, and Kraken with automatic fallback.

Features:
- Real-time price updates (millisecond latency)
- Free public WebSocket APIs (no authentication needed)
- Automatic reconnection on disconnect
- Fallback between multiple exchanges
- Thread-safe price updates
"""

import asyncio
import json
import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False


logger = logging.getLogger(__name__)


@dataclass
class WebSocketTickerData:
    """Real-time ticker data from WebSocket stream."""
    
    symbol: str
    price: float
    volume: float
    timestamp: int
    exchange: str


class WebSocketTickerSource:
    """
    Fetches real-time ticker data via WebSocket connections.
    
    Uses free public WebSocket APIs with automatic fallback:
    1. Binance - wss://stream.binance.com:9443/ws/{symbol}@trade
    2. Coinbase - wss://ws-feed.exchange.coinbase.com
    3. Kraken - wss://ws.kraken.com
    
    Runs in a background thread and calls a callback when new prices arrive.
    """
    
    def __init__(
        self,
        symbol: str = "BTC/USDT",
        on_price_update: Callable[[WebSocketTickerData], None] | None = None,
        exchange: str = "binance",
    ):
        """
        Initialize WebSocket ticker source.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            on_price_update: Callback function called when price updates
            exchange: Exchange to connect to ("binance", "coinbase", or "kraken")
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError(
                "websockets library not available. "
                "Install with: pip install websockets"
            )
        
        self.symbol = symbol
        self.on_price_update = on_price_update
        self.exchange = exchange
        
        # Current price data
        self._current_price: float | None = None
        self._current_volume: float = 0.0
        self._last_update_time: int = 0
        
        # Connection state
        self._running = False
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        
        logger.info(f"WebSocketTickerSource initialized for {symbol} on {exchange}")
    
    def start(self):
        """Start the WebSocket connection in a background thread."""
        if self._running:
            logger.warning("WebSocket already running")
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._run_websocket_loop,
            name=f"ws-{self.exchange}-{self.symbol}",
            daemon=True,
        )
        self._thread.start()
        logger.info(f"WebSocket thread started for {self.symbol}")
    
    def stop(self):
        """Stop the WebSocket connection and cleanup."""
        if not self._running:
            return
        
        self._running = False
        
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._loop.stop)
        
        if self._thread:
            self._thread.join(timeout=5.0)
        
        logger.info(f"WebSocket stopped for {self.symbol}")
    
    def get_current_price(self) -> float | None:
        """
        Get the most recent price from the WebSocket stream.
        
        Returns:
            Current price or None if no data received yet
        """
        return self._current_price
    
    def get_ticker_data(self) -> WebSocketTickerData | None:
        """
        Get the most recent ticker data.
        
        Returns:
            WebSocketTickerData or None if no data received yet
        """
        if self._current_price is None:
            return None
        
        return WebSocketTickerData(
            symbol=self.symbol,
            price=self._current_price,
            volume=self._current_volume,
            timestamp=self._last_update_time,
            exchange=self.exchange,
        )
    
    def _run_websocket_loop(self):
        """Run the WebSocket event loop in the background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        try:
            if self.exchange == "binance":
                self._loop.run_until_complete(self._connect_binance())
            elif self.exchange == "coinbase":
                self._loop.run_until_complete(self._connect_coinbase())
            elif self.exchange == "kraken":
                self._loop.run_until_complete(self._connect_kraken())
            else:
                logger.error(f"Unsupported exchange: {self.exchange}")
        except Exception as e:
            logger.error(f"WebSocket loop error: {e}", exc_info=True)
        finally:
            if self._loop and not self._loop.is_closed():
                self._loop.close()
    
    async def _connect_binance(self):
        """Connect to Binance WebSocket."""
        # Convert BTC/USDT -> btcusdt
        ws_symbol = self.symbol.replace("/", "").lower()
        url = f"wss://stream.binance.com:9443/ws/{ws_symbol}@trade"
        
        logger.info(f"Connecting to Binance WebSocket: {url}")
        
        while self._running:
            try:
                async with websockets.connect(url) as websocket:
                    logger.info(f"Connected to Binance WebSocket for {self.symbol}")
                    
                    while self._running:
                        message = await websocket.recv()
                        data = json.loads(message)
                        
                        # Binance trade message format
                        # {"e":"trade","s":"BTCUSDT","p":"47251.89","q":"0.001",...}
                        if data.get("e") == "trade":
                            price = float(data["p"])
                            quantity = float(data.get("q", 0))
                            
                            self._update_price(price, quantity * price)
                            
            except websockets.exceptions.WebSocketException as e:
                logger.warning(f"Binance WebSocket disconnected: {e}")
                if self._running:
                    await asyncio.sleep(1)  # Wait before reconnecting
            except Exception as e:
                logger.error(f"Binance WebSocket error: {e}", exc_info=True)
                if self._running:
                    await asyncio.sleep(1)
    
    async def _connect_coinbase(self):
        """Connect to Coinbase WebSocket."""
        # Convert BTC/USDT -> BTC-USD (Coinbase uses USD)
        ws_symbol = self.symbol.replace("/", "-").replace("USDT", "USD")
        url = "wss://ws-feed.exchange.coinbase.com"
        
        logger.info(f"Connecting to Coinbase WebSocket: {url}")
        
        subscribe_message = {
            "type": "subscribe",
            "channels": ["ticker"],
            "product_ids": [ws_symbol],
        }
        
        while self._running:
            try:
                async with websockets.connect(url) as websocket:
                    # Subscribe to ticker channel
                    await websocket.send(json.dumps(subscribe_message))
                    logger.info(f"Connected to Coinbase WebSocket for {ws_symbol}")
                    
                    while self._running:
                        message = await websocket.recv()
                        data = json.loads(message)
                        
                        # Coinbase ticker message format
                        # {"type":"ticker","price":"47250.23","volume_24h":"12345.67",...}
                        if data.get("type") == "ticker" and "price" in data:
                            price = float(data["price"])
                            volume = float(data.get("volume_24h", 0))
                            
                            self._update_price(price, volume)
                            
            except websockets.exceptions.WebSocketException as e:
                logger.warning(f"Coinbase WebSocket disconnected: {e}")
                if self._running:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Coinbase WebSocket error: {e}", exc_info=True)
                if self._running:
                    await asyncio.sleep(1)
    
    async def _connect_kraken(self):
        """Connect to Kraken WebSocket."""
        # Convert BTC/USDT -> XBT/USD (Kraken uses XBT and USD)
        ws_symbol = self.symbol.replace("BTC", "XBT").replace("USDT", "USD")
        url = "wss://ws.kraken.com"
        
        logger.info(f"Connecting to Kraken WebSocket: {url}")
        
        subscribe_message = {
            "event": "subscribe",
            "pair": [ws_symbol],
            "subscription": {"name": "ticker"},
        }
        
        while self._running:
            try:
                async with websockets.connect(url) as websocket:
                    # Subscribe to ticker channel
                    await websocket.send(json.dumps(subscribe_message))
                    logger.info(f"Connected to Kraken WebSocket for {ws_symbol}")
                    
                    while self._running:
                        message = await websocket.recv()
                        data = json.loads(message)
                        
                        # Kraken ticker is an array: [channelID, data, "ticker", pair]
                        if isinstance(data, list) and len(data) >= 2:
                            ticker_data = data[1]
                            if isinstance(ticker_data, dict) and "c" in ticker_data:
                                # "c" is last trade closed array [price, volume]
                                price = float(ticker_data["c"][0])
                                volume = float(ticker_data.get("v", [0, 0])[1])  # 24h volume
                                
                                self._update_price(price, volume)
                                
            except websockets.exceptions.WebSocketException as e:
                logger.warning(f"Kraken WebSocket disconnected: {e}")
                if self._running:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Kraken WebSocket error: {e}", exc_info=True)
                if self._running:
                    await asyncio.sleep(1)
    
    def _update_price(self, price: float, volume: float):
        """
        Update the current price and call callback.
        
        Args:
            price: New price
            volume: Trading volume
        """
        self._current_price = price
        self._current_volume = volume
        self._last_update_time = int(time.time() * 1000)
        
        # Call callback if provided
        if self.on_price_update:
            ticker_data = WebSocketTickerData(
                symbol=self.symbol,
                price=price,
                volume=volume,
                timestamp=self._last_update_time,
                exchange=self.exchange,
            )
            try:
                self.on_price_update(ticker_data)
            except Exception as e:
                logger.error(f"Error in price update callback: {e}", exc_info=True)
        
        logger.debug(
            f"Price update: {self.symbol} = ${price:,.2f} "
            f"(volume: {volume:,.2f}) from {self.exchange}"
        )


class WebSocketTickerManager:
    """
    Manages multiple WebSocket ticker sources with automatic fallback.
    
    Tries to connect to exchanges in order: Binance -> Coinbase -> Kraken
    Falls back to next exchange if connection fails.
    """
    
    def __init__(
        self,
        symbol: str = "BTC/USDT",
        on_price_update: Callable[[WebSocketTickerData], None] | None = None,
    ):
        """
        Initialize WebSocket manager with fallback.
        
        Args:
            symbol: Trading pair symbol
            on_price_update: Callback for price updates
        """
        self.symbol = symbol
        self.on_price_update = on_price_update
        self._source: WebSocketTickerSource | None = None
        self._exchanges = ["binance", "coinbase", "kraken"]
        self._current_exchange_idx = 0
    
    def start(self):
        """Start WebSocket connection with automatic fallback."""
        for exchange in self._exchanges:
            try:
                logger.info(f"Attempting to connect to {exchange}...")
                self._source = WebSocketTickerSource(
                    symbol=self.symbol,
                    on_price_update=self.on_price_update,
                    exchange=exchange,
                )
                self._source.start()
                
                # Wait a bit to see if connection succeeds
                time.sleep(2)
                
                # Check if we got a price
                if self._source.get_current_price() is not None:
                    logger.info(f"Successfully connected to {exchange}")
                    return
                else:
                    logger.warning(f"{exchange} connected but no data yet, trying next...")
                    self._source.stop()
                    
            except Exception as e:
                logger.warning(f"Failed to connect to {exchange}: {e}")
                if self._source:
                    self._source.stop()
        
        logger.error("Failed to connect to all exchanges")
    
    def stop(self):
        """Stop the current WebSocket connection."""
        if self._source:
            self._source.stop()
    
    def get_current_price(self) -> float | None:
        """Get current price from active connection."""
        if self._source:
            return self._source.get_current_price()
        return None
    
    def get_ticker_data(self) -> WebSocketTickerData | None:
        """Get current ticker data from active connection."""
        if self._source:
            return self._source.get_ticker_data()
        return None
