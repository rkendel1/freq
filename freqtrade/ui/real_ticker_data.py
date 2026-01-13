"""
Real Ticker Data Source - Fetches live price data from cryptocurrency exchanges.

This module provides real-time ticker data for the demo UI, making it more
realistic and useful for testing strategies with current market prices.

Features:
- Fetches live ticker data from CoinPaprika (free, no API key needed)
- Fallback to CCXT exchanges (Binance, Bybit, Kraken) if CoinPaprika fails
- Automatic fallback between exchanges if one fails
- Caching to avoid API rate limits
- Graceful degradation to simulated data if all APIs fail
"""

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    import ccxt

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


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
    
    Uses multiple data sources with automatic fallback:
    1. Try CoinPaprika (free API, no key required)
    2. Try Binance (via CCXT)
    3. Try Bybit (via CCXT)
    4. Try Kraken (via CCXT)
    5. Return None if all fail (caller should use simulated data)
    
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
        # Type is object for runtime compatibility, represents ccxt.Exchange | None
        self._exchanges: dict[str, object | None] = {
            "binance": None,
            "bybit": None,
            "kraken": None,
        }
        
        # Cache ccxt module after first import to avoid repeated imports
        self._ccxt_module = None
        
        logger.info(
            f"RealTickerDataSource initialized with {cache_duration_seconds}s cache duration"
        )
    
    def _get_exchange(self, exchange_name: str) -> object | None:
        """
        Get or create an exchange instance.
        
        Args:
            exchange_name: Name of exchange (binance, bybit, kraken)
            
        Returns:
            Exchange instance (ccxt.Exchange) or None if creation failed
        """
        # Return cached instance if available
        if self._exchanges.get(exchange_name) is not None:
            return self._exchanges[exchange_name]
        
        try:
            # Import ccxt only when needed (lazy loading)
            # Cache the module to avoid repeated imports
            if self._ccxt_module is None:
                import ccxt
                self._ccxt_module = ccxt
            else:
                ccxt = self._ccxt_module
            
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
    
    def _convert_symbol_to_coinpaprika_id(self, symbol: str) -> str | None:
        """
        Convert trading pair symbol to CoinPaprika ticker ID.
        
        Args:
            symbol: Symbol in format "BTC/USDT" or "ETH/USD"
            
        Returns:
            CoinPaprika ticker ID (e.g., "btc-bitcoin") or None if not supported
        """
        # Validate symbol format
        if "/" not in symbol:
            logger.debug(f"Invalid symbol format: {symbol} (missing '/')")
            return None
        
        parts = symbol.split("/")
        if len(parts) != 2:
            logger.debug(f"Invalid symbol format: {symbol} (expected BASE/QUOTE)")
            return None
        
        # Extract base currency (e.g., BTC from BTC/USDT)
        base = parts[0].lower()
        
        # Map common symbols to CoinPaprika IDs
        # CoinPaprika uses format: {id}-{name}, e.g., btc-bitcoin
        symbol_map = {
            "btc": "btc-bitcoin",
            "eth": "eth-ethereum",
            "usdt": "usdt-tether",
            "bnb": "bnb-binance-coin",
            "sol": "sol-solana",
            "xrp": "xrp-xrp",
            "ada": "ada-cardano",
            "doge": "doge-dogecoin",
            "matic": "matic-polygon",
            "dot": "dot-polkadot",
            "ltc": "ltc-litecoin",
            "avax": "avax-avalanche",
            "link": "link-chainlink",
            "atom": "atom-cosmos",
            "uni": "uni-uniswap",
        }
        
        return symbol_map.get(base)
    
    def _fetch_from_coinpaprika(self, symbol: str) -> TickerData | None:
        """
        Fetch ticker from CoinPaprika API (free, no API key required).
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            
        Returns:
            TickerData if successful, None otherwise
        """
        if not REQUESTS_AVAILABLE:
            logger.debug("requests library not available, skipping CoinPaprika")
            return None
        
        try:
            # Get CoinPaprika ticker ID (also validates symbol format)
            ticker_id = self._convert_symbol_to_coinpaprika_id(symbol)
            if not ticker_id:
                logger.debug(f"Symbol {symbol} not supported by CoinPaprika")
                return None
            
            # Fetch from CoinPaprika
            url = f"https://api.coinpaprika.com/v1/tickers/{ticker_id}"
            response = requests.get(url, timeout=self.timeout_ms / 1000.0)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract quote currency (USD or USDT)
            # Symbol was already validated in _convert_symbol_to_coinpaprika_id
            parts = symbol.split("/")
            if len(parts) != 2:
                logger.warning(f"Invalid symbol format: {symbol}")
                return None
            
            quote = parts[1].upper()
            quotes = data.get("quotes", {})
            
            # Try to get the matching quote currency
            quote_data = None
            if quote == "USDT":
                # For USDT pairs, use USD as they're typically very close
                quote_data = quotes.get("USD")
            else:
                quote_data = quotes.get(quote)
            
            if not quote_data or "price" not in quote_data:
                logger.warning(f"No price data from CoinPaprika for {symbol}")
                return None
            
            price = quote_data["price"]
            volume = quote_data.get("volume_24h", 0.0)
            timestamp = int(time.time() * 1000)
            
            ticker_data = TickerData(
                symbol=symbol,
                price=float(price),
                volume=float(volume),
                timestamp=timestamp,
                exchange="coinpaprika",
            )
            
            logger.info(
                f"Fetched {symbol} from CoinPaprika: "
                f"${ticker_data.price:,.2f}, volume: {ticker_data.volume:,.0f}"
            )
            
            return ticker_data
            
        except Exception as e:
            error_type = type(e).__name__
            logger.debug(f"Failed to fetch {symbol} from CoinPaprika: {error_type}")
            return None
    
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
        
        Tries data sources in this order:
        1. CoinPaprika (free, no API key needed)
        2. Binance (CCXT)
        3. Bybit (CCXT)
        4. Kraken (CCXT)
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            prefer_exchange: Preferred exchange to try first (optional)
                           Can be "coinpaprika", "binance", "bybit", or "kraken"
            
        Returns:
            TickerData if successful, None if all sources fail
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
        
        # Build list of data sources to try
        sources = ["coinpaprika", "binance", "bybit", "kraken"]
        
        # Prefer specific source if requested
        if prefer_exchange and prefer_exchange in sources:
            sources.remove(prefer_exchange)
            sources.insert(0, prefer_exchange)
        
        # Try each source until one succeeds
        for source_name in sources:
            if source_name == "coinpaprika":
                ticker_data = self._fetch_from_coinpaprika(symbol)
            else:
                ticker_data = self._fetch_from_exchange(symbol, source_name)
            
            if ticker_data is not None:
                # Cache successful result
                self._cache[symbol] = (ticker_data, current_time)
                return ticker_data
        
        # All sources failed
        logger.error(f"Failed to fetch {symbol} from all data sources")
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
    
    def is_symbol_supported_by_coinpaprika(self, symbol: str) -> bool:
        """
        Check if a symbol is supported by CoinPaprika.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            
        Returns:
            True if symbol is supported by CoinPaprika, False otherwise
        """
        return self._convert_symbol_to_coinpaprika_id(symbol) is not None
    
    def get_coinpaprika_id(self, symbol: str) -> str | None:
        """
        Get the CoinPaprika ticker ID for a trading symbol.
        
        This is a public method for checking symbol support and getting
        the CoinPaprika ticker ID without making an API call.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            
        Returns:
            CoinPaprika ticker ID (e.g., "btc-bitcoin") or None if not supported
            
        Example:
            >>> source = RealTickerDataSource()
            >>> source.get_coinpaprika_id("BTC/USDT")
            'btc-bitcoin'
            >>> source.get_coinpaprika_id("ETH/USD")
            'eth-ethereum'
            >>> source.get_coinpaprika_id("UNKNOWN/USDT")
            None
        """
        return self._convert_symbol_to_coinpaprika_id(symbol)
    
    def clear_cache(self):
        """Clear all cached ticker data."""
        self._cache.clear()
        logger.info("Ticker cache cleared")
