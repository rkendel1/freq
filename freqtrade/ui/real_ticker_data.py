"""
Real Ticker Data Source - Fetches live price data from cryptocurrency exchanges.

This module provides real-time ticker data for the demo UI, making it more
realistic and useful for testing strategies with current market prices.

Features:
- Fetches live ticker data from multiple exchanges (Binance, Bybit, Kraken)
- Automatic fallback between exchanges if one fails
- Caching to avoid API rate limits
- Graceful degradation to simulated data if all APIs fail
"""

import logging
import time
from dataclasses import dataclass
from typing import Literal

import ccxt


logger = logging.getLogger(__name__)


@dataclass
class TickerData:
    """Real-time ticker data from an exchange."""
    
    symbol: str
    price: float
    volume: float
    timestamp: int
    exchange: str


class RealTickerDataSource:
    """
    Fetches real ticker data from cryptocurrency exchanges.
    
    Uses CCXT to connect to multiple exchanges with automatic fallback:
    1. Try Binance (most liquid, reliable)
    2. Try Bybit (backup)
    3. Try Kraken (backup)
    4. Return None if all fail (caller should use simulated data)
    
    Implements caching to avoid hitting API rate limits.
    """
    
    def __init__(
        self,
        cache_duration_seconds: int = 30,
        timeout_ms: int = 5000,
    ):
        """
        Initialize real ticker data source.
        
        Args:
            cache_duration_seconds: How long to cache ticker data (default: 30s)
            timeout_ms: API timeout in milliseconds (default: 5000ms)
        """
        self.cache_duration_seconds = cache_duration_seconds
        self.timeout_ms = timeout_ms
        
        # Cache: {symbol: (TickerData, timestamp)}
        self._cache: dict[str, tuple[TickerData, float]] = {}
        
        # Exchange instances (created lazily)
        self._exchanges: dict[str, ccxt.Exchange | None] = {
            "binance": None,
            "bybit": None,
            "kraken": None,
        }
        
        logger.info(
            f"RealTickerDataSource initialized with {cache_duration_seconds}s cache duration"
        )
    
    def _get_exchange(self, exchange_name: str) -> ccxt.Exchange | None:
        """
        Get or create an exchange instance.
        
        Args:
            exchange_name: Name of exchange (binance, bybit, kraken)
            
        Returns:
            Exchange instance or None if creation failed
        """
        # Return cached instance if available
        if self._exchanges.get(exchange_name) is not None:
            return self._exchanges[exchange_name]
        
        try:
            # Create exchange instance
            exchange_class = getattr(ccxt, exchange_name)
            exchange = exchange_class({
                "enableRateLimit": True,  # Respect rate limits
                "timeout": self.timeout_ms,
                "options": {
                    "defaultType": "spot",  # Use spot market by default
                },
            })
            
            self._exchanges[exchange_name] = exchange
            logger.info(f"Created {exchange_name} exchange instance")
            return exchange
            
        except Exception as e:
            logger.warning(f"Failed to create {exchange_name} exchange: {e}")
            self._exchanges[exchange_name] = None
            return None
    
    def _convert_symbol_for_exchange(
        self, symbol: str, exchange_name: str
    ) -> str:
        """
        Convert symbol to exchange-specific format.
        
        Args:
            symbol: Symbol in format "BTC/USDT"
            exchange_name: Exchange name
            
        Returns:
            Exchange-specific symbol format
        """
        # Most exchanges use "BTC/USDT" format, but some need adjustments
        if exchange_name == "kraken":
            # Kraken uses different naming for some pairs
            # BTC/USDT -> XBT/USDT on Kraken
            if symbol.startswith("BTC/"):
                return symbol.replace("BTC/", "XBT/")
        
        return symbol
    
    def _fetch_from_exchange(
        self, symbol: str, exchange_name: str
    ) -> TickerData | None:
        """
        Fetch ticker from a specific exchange.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            exchange_name: Exchange to fetch from
            
        Returns:
            TickerData if successful, None otherwise
        """
        try:
            exchange = self._get_exchange(exchange_name)
            if exchange is None:
                return None
            
            # Convert symbol to exchange format
            exchange_symbol = self._convert_symbol_for_exchange(symbol, exchange_name)
            
            # Fetch ticker
            ticker = exchange.fetch_ticker(exchange_symbol)
            
            # Extract data
            price = ticker.get("last") or ticker.get("close")
            volume = ticker.get("baseVolume") or ticker.get("volume", 0.0)
            timestamp = ticker.get("timestamp", int(time.time() * 1000))
            
            if price is None:
                logger.warning(f"No price data from {exchange_name} for {symbol}")
                return None
            
            ticker_data = TickerData(
                symbol=symbol,
                price=float(price),
                volume=float(volume),
                timestamp=int(timestamp),
                exchange=exchange_name,
            )
            
            logger.info(
                f"Fetched {symbol} from {exchange_name}: "
                f"${ticker_data.price:,.2f}, volume: {ticker_data.volume:,.0f}"
            )
            
            return ticker_data
            
        except Exception as e:
            # Log detailed error for debugging, but don't expose full traceback
            error_type = type(e).__name__
            # Sanitize error message to avoid exposing sensitive information
            logger.debug(f"Failed to fetch {symbol} from {exchange_name}: {error_type}")
            return None
    
    def fetch_ticker(
        self, symbol: str, prefer_exchange: str | None = None
    ) -> TickerData | None:
        """
        Fetch ticker data with caching and fallback.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            prefer_exchange: Preferred exchange to try first (optional)
            
        Returns:
            TickerData if successful, None if all exchanges fail
        """
        # Check cache first
        current_time = time.time()
        if symbol in self._cache:
            cached_data, cache_time = self._cache[symbol]
            if current_time - cache_time < self.cache_duration_seconds:
                logger.debug(
                    f"Using cached data for {symbol} "
                    f"(age: {current_time - cache_time:.1f}s)"
                )
                return cached_data
        
        # Try exchanges in order
        exchanges = ["binance", "bybit", "kraken"]
        
        # Prefer specific exchange if requested
        if prefer_exchange and prefer_exchange in exchanges:
            exchanges.remove(prefer_exchange)
            exchanges.insert(0, prefer_exchange)
        
        # Try each exchange until one succeeds
        for exchange_name in exchanges:
            ticker_data = self._fetch_from_exchange(symbol, exchange_name)
            if ticker_data is not None:
                # Cache successful result
                self._cache[symbol] = (ticker_data, current_time)
                return ticker_data
        
        # All exchanges failed
        logger.error(f"Failed to fetch {symbol} from all exchanges")
        return None
    
    def get_current_price(self, symbol: str) -> float | None:
        """
        Get current price for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            
        Returns:
            Current price or None if fetch failed
        """
        ticker_data = self.fetch_ticker(symbol)
        return ticker_data.price if ticker_data else None
    
    def clear_cache(self):
        """Clear all cached ticker data."""
        self._cache.clear()
        logger.info("Ticker cache cleared")
