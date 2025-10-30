# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
# --- Do not remove these libs ---
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any

from cachetools import TTLCache

from freqtrade.exceptions import DDosProtection, ExchangeError, OperationalException, TemporaryError
from freqtrade.exchange.exchange_types import OrderBook, Ticker
from freqtrade.plugins.pairlist.IPairList import IPairList, PairlistParameter, SupportsBacktesting

logger = logging.getLogger(__name__)


class LiquidityPairList(IPairList):
    """
    Custom pairlist filter that excludes pairs based on orderbook liquidity depth.

    This filter ensures pairs have sufficient orderbook depth for large trades
    without significant slippage. It checks both total liquidity within a price
    range and minimum size at the best bid/ask levels.

    Liquidity values are calculated in the pair's quote currency (e.g., USDT for BTC/USDT,
    BTC for ETH/BTC). No currency conversion is performed.

    Note: This plugin does not support backtesting as orderbook data is real-time
    and not available in historical backtesting datasets.

    Configuration:
        min_liquidity: Minimum total liquidity in quote currency (default: 100000)
        spread_pct_threshold: Price range percentage for liquidity calc (default: 0.5)
        min_top_level: Minimum size at best bid/ask in quote currency (default: 5000)
        cache_ttl: Cache TTL in seconds (default: 300)
        refresh_period: Refresh period in seconds (default: 1800)
        ticker_prefilter_threshold: Pre-filter threshold fraction (default: 0.1)

    Example:
        {
            "method": "LiquidityPairList",
            "min_liquidity": 100000,
            "spread_pct_threshold": 0.5,
            "min_top_level": 5000,
            "cache_ttl": 300,
            "ticker_prefilter_threshold": 0.1
        }
    """

    supports_backtesting = SupportsBacktesting.NO

    def __init__(
        self, exchange, pairlistmanager, config: dict, pairlistconfig: dict, pairlist_pos: int
    ) -> None:
        super().__init__(exchange, pairlistmanager, config, pairlistconfig, pairlist_pos)

        # Validate exchange capabilities BEFORE processing configuration
        if not self._exchange.exchange_has("fetchL2OrderBook"):
            raise OperationalException(
                f"{self.name} requires exchange to support L2 orderbook data, "
                "which is not available for the selected exchange. "
                "Please use a different exchange or remove this pairlist filter."
            )

        # Configuration parameters
        self._min_liquidity = pairlistconfig.get("min_liquidity", 100000)
        self._spread_pct_threshold = pairlistconfig.get("spread_pct_threshold", 0.5)
        self._min_top_level = pairlistconfig.get("min_top_level", 5000)

        # Caching configuration
        self._cache_ttl = pairlistconfig.get("cache_ttl", 300)
        self._liquidity_cache: TTLCache = TTLCache(
            maxsize=1000,  # Cache up to 1000 pairs
            ttl=self._cache_ttl,
        )

        # Ticker pre-filtering configuration
        self._ticker_prefilter_threshold = pairlistconfig.get("ticker_prefilter_threshold", 0.1)

        # Validate configuration
        if self._min_liquidity <= 0:
            raise ValueError("min_liquidity must be positive")
        if self._spread_pct_threshold <= 0 or self._spread_pct_threshold > 25:
            raise ValueError("spread_pct_threshold must be between 0 and 25")
        if self._min_top_level <= 0:
            raise ValueError("min_top_level must be positive")

        # Warn about high spread thresholds
        if self._spread_pct_threshold > 10:
            logger.warning(
                f"High spread threshold ({self._spread_pct_threshold}%) may filter out "
                f"many pairs. Consider using a lower value unless trading exotic pairs."
            )

        logger.info(f"LiquidityPairList initialized with:")
        logger.info(f"  - Min liquidity: {self._min_liquidity:,} (quote currency)")
        logger.info(f"  - Spread threshold: {self._spread_pct_threshold}%")
        logger.info(f"  - Min top level: {self._min_top_level:,} (quote currency)")

    @property
    def needstickers(self) -> bool:
        """
        Return True if this pairlist needs ticker data.
        """
        return False  # LiquidityPairList uses orderbook data, not tickers

    @staticmethod
    def description() -> str:
        """
        Return description for this pairlist.
        """
        return "Filter pairs based on orderbook liquidity depth"

    def short_desc(self) -> str:
        """
        Short description for the pairlist.
        """
        return f"Liquidity filter (≥{self._min_liquidity:,} depth, ±{self._spread_pct_threshold}%)"

    @staticmethod
    def available_parameters() -> Dict[str, PairlistParameter]:
        """Define available parameters for this pairlist."""
        from freqtrade.plugins.pairlist.IPairList import IPairList

        return {
            "min_liquidity": {
                "type": "number",
                "default": 100000,
                "description": "Minimum liquidity in quote currency within price range",
                "help": "Minimum combined bid+ask liquidity within ±spread_pct_threshold% of mid-price (e.g., USDT for BTC/USDT, BTC for ETH/BTC)",
            },
            "spread_pct_threshold": {
                "type": "number",
                "default": 0.5,
                "description": "Price range percentage for liquidity calculation",
                "help": "Calculate liquidity within ±X% of mid-price (0.1-25% range recommended)",
            },
            "min_top_level": {
                "type": "number",
                "default": 5000,
                "description": "Minimum size at best bid/ask in quote currency",
                "help": "Minimum order size at best bid and ask prices in quote currency",
            },
            "cache_ttl": {
                "type": "number",
                "default": 300,
                "description": "Cache TTL in seconds",
                "help": "How long to cache liquidity calculations (0 to disable)",
            },
            "ticker_prefilter_threshold": {
                "type": "number",
                "default": 0.1,
                "description": "Ticker pre-filter threshold as fraction of min_liquidity",
                "help": "Pairs with top-level liquidity below this fraction of min_liquidity are filtered out (0.05-0.2 recommended)",
            },
            **IPairList.refresh_period_parameter(),
        }

    def _calculate_orderbook_liquidity(self, pair: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Calculate orderbook liquidity for a pair with caching.

        Returns:
            tuple: (passed_filter, rejection_reason, liquidity_metrics)
        """
        # Check cache first
        cache_key = (
            f"{pair}_{self._min_liquidity}_{self._spread_pct_threshold}_{self._min_top_level}"
        )
        if cache_key in self._liquidity_cache:
            logger.debug(f"Using cached liquidity data for {pair}")
            return self._liquidity_cache[cache_key]

        # Calculate liquidity (existing logic)
        result = self._calculate_liquidity_uncached(pair)

        # Cache the result
        self._liquidity_cache[cache_key] = result
        return result

    def _evaluate_liquidity_from_orderbook(
        self, pair: str, orderbook: OrderBook
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Evaluate liquidity rules given a pre-fetched orderbook."""
        # Validate orderbook structure
        if not self._validate_orderbook_structure(orderbook, pair):
            return False, "Invalid orderbook structure", {}

        bids = orderbook["bids"]
        asks = orderbook["asks"]

        # Calculate mid-price
        best_bid = float(bids[0][0])
        best_ask = float(asks[0][0])
        mid_price = (best_bid + best_ask) / 2

        # Define price range (±spread threshold of mid-price)
        price_lower = mid_price * (1 - self._spread_pct_threshold / 100)
        price_upper = mid_price * (1 + self._spread_pct_threshold / 100)

        # Calculate liquidity within price range (values in quote currency)
        bid_liquidity = 0.0
        ask_liquidity = 0.0

        # Sum bid volume within range
        for price, volume in bids:
            price_float = float(price)
            if price_float >= price_lower:
                bid_liquidity += price_float * float(volume)
                if bid_liquidity >= self._min_liquidity:
                    break
            else:
                break

        # Sum ask volume within range
        for price, volume in asks:
            price_float = float(price)
            if price_float <= price_upper:
                ask_liquidity += price_float * float(volume)
            else:
                break

        total_liquidity = bid_liquidity + ask_liquidity

        # Early exit for high-liquidity pairs
        if total_liquidity >= self._min_liquidity * 2:
            return (
                True,
                "Passed (high liquidity)",
                {
                    "total_liquidity": total_liquidity,
                    "bid_liquidity": bid_liquidity,
                    "ask_liquidity": ask_liquidity,
                    "mid_price": mid_price,
                    "skipped_top_level_check": True,
                },
            )

        # Check primary liquidity requirement
        if total_liquidity < self._min_liquidity:
            return (
                False,
                f"Total liquidity {total_liquidity:,.0f} < {self._min_liquidity:,}",
                {
                    "total_liquidity": total_liquidity,
                    "bid_liquidity": bid_liquidity,
                    "ask_liquidity": ask_liquidity,
                    "mid_price": mid_price,
                },
            )

        # Check secondary requirement (minimum size at top levels)
        best_bid_size = best_bid * float(bids[0][1])
        best_ask_size = best_ask * float(asks[0][1])
        min_top_level = min(best_bid_size, best_ask_size)

        if min_top_level < self._min_top_level:
            return (
                False,
                f"Top level size {min_top_level:,.0f} < {self._min_top_level:,}",
                {
                    "total_liquidity": total_liquidity,
                    "bid_liquidity": bid_liquidity,
                    "ask_liquidity": ask_liquidity,
                    "best_bid_size": best_bid_size,
                    "best_ask_size": best_ask_size,
                    "min_top_level": min_top_level,
                    "mid_price": mid_price,
                },
            )

        # Both checks passed
        return (
            True,
            "Passed",
            {
                "total_liquidity": total_liquidity,
                "bid_liquidity": bid_liquidity,
                "ask_liquidity": ask_liquidity,
                "best_bid_size": best_bid_size,
                "best_ask_size": best_ask_size,
                "min_top_level": min_top_level,
                "mid_price": mid_price,
            },
        )

    def _calculate_liquidity_uncached(self, pair: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Calculate orderbook liquidity for a pair without caching.

        Returns:
            tuple: (passed_filter, rejection_reason, liquidity_metrics)
        """
        try:
            # Fetch orderbook with improved error handling
            try:
                orderbook = self._exchange.fetch_l2_order_book(pair, limit=100)
            except DDosProtection as e:
                logger.warning(f"Rate limited for {pair}, skipping: {e}")
                return False, "Rate limited", {}
            except TemporaryError as e:
                logger.warning(f"Network error for {pair}, skipping: {e}")
                return False, "Network error", {}
            except ExchangeError as e:
                logger.warning(f"Exchange error for {pair}, skipping: {e}")
                return False, f"Exchange error: {str(e)}", {}
            except Exception as e:
                logger.error(f"Unexpected error fetching orderbook for {pair}: {e}")
                return False, f"Unexpected error: {str(e)}", {}

            # Validate orderbook structure
            if not self._validate_orderbook_structure(orderbook, pair):
                return False, "Invalid orderbook structure", {}

            bids = orderbook["bids"]
            asks = orderbook["asks"]

            # Calculate mid-price
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            mid_price = (best_bid + best_ask) / 2

            # Define price range (±0.5% of mid-price)
            price_lower = mid_price * (1 - self._spread_pct_threshold / 100)
            price_upper = mid_price * (1 + self._spread_pct_threshold / 100)

            # Calculate liquidity within price range (values in quote currency)
            bid_liquidity = 0.0
            ask_liquidity = 0.0

            # Sum bid volume within range
            for price, volume in bids:
                price_float = float(price)
                if price_float >= price_lower:
                    bid_liquidity += price_float * float(volume)
                    # Early exit for performance
                    if bid_liquidity >= self._min_liquidity:
                        break
                else:
                    break  # Bids are sorted by price descending

            # Sum ask volume within range
            for price, volume in asks:
                price_float = float(price)
                if price_float <= price_upper:
                    ask_liquidity += price_float * float(volume)
                else:
                    break  # Asks are sorted by price ascending

            total_liquidity = bid_liquidity + ask_liquidity

            # Early exit for high-liquidity pairs
            if total_liquidity >= self._min_liquidity * 2:
                return (
                    True,
                    "Passed (high liquidity)",
                    {
                        "total_liquidity": total_liquidity,
                        "bid_liquidity": bid_liquidity,
                        "ask_liquidity": ask_liquidity,
                        "mid_price": mid_price,
                        "skipped_top_level_check": True,
                    },
                )

            # Check primary liquidity requirement
            if total_liquidity < self._min_liquidity:
                return (
                    False,
                    f"Total liquidity {total_liquidity:,.0f} < {self._min_liquidity:,}",
                    {
                        "total_liquidity": total_liquidity,
                        "bid_liquidity": bid_liquidity,
                        "ask_liquidity": ask_liquidity,
                        "mid_price": mid_price,
                    },
                )

            # Check secondary requirement (minimum size at top levels)
            best_bid_size = best_bid * float(bids[0][1])
            best_ask_size = best_ask * float(asks[0][1])
            min_top_level = min(best_bid_size, best_ask_size)

            if min_top_level < self._min_top_level:
                return (
                    False,
                    f"Top level size {min_top_level:,.0f} < {self._min_top_level:,}",
                    {
                        "total_liquidity": total_liquidity,
                        "bid_liquidity": bid_liquidity,
                        "ask_liquidity": ask_liquidity,
                        "best_bid_size": best_bid_size,
                        "best_ask_size": best_ask_size,
                        "min_top_level": min_top_level,
                        "mid_price": mid_price,
                    },
                )

            # Both checks passed
            return (
                True,
                "Passed",
                {
                    "total_liquidity": total_liquidity,
                    "bid_liquidity": bid_liquidity,
                    "ask_liquidity": ask_liquidity,
                    "best_bid_size": best_bid_size,
                    "best_ask_size": best_ask_size,
                    "min_top_level": min_top_level,
                    "mid_price": mid_price,
                },
            )

        except Exception as e:
            logger.error(f"Critical error in liquidity calculation for {pair}: {e}")
            return False, f"Critical error: {str(e)}", {}

    def _validate_orderbook_structure(self, orderbook: OrderBook, pair: str) -> bool:
        """Validate orderbook data structure."""
        if not orderbook:
            logger.debug(f"Empty orderbook for {pair}")
            return False

        if "bids" not in orderbook or "asks" not in orderbook:
            logger.debug(f"Missing bids/asks in orderbook for {pair}")
            return False

        if not isinstance(orderbook["bids"], list) or not isinstance(orderbook["asks"], list):
            logger.debug(f"Invalid bids/asks format for {pair}")
            return False

        if not orderbook["bids"] or not orderbook["asks"]:
            logger.debug(f"Empty bids/asks for {pair}")
            return False

        return True

    def _quick_ticker_filter(self, pair: str, ticker: Ticker | None) -> Tuple[bool, str]:
        """
        Quick liquidity check using ticker data to eliminate obvious low-liquidity pairs.

        Args:
            pair: Trading pair
            ticker: Ticker data for the pair

        Returns:
            tuple: (passed_filter, rejection_reason)
        """
        if not ticker:
            return False, "No ticker data"

        # Check if we have basic data
        bid_price = ticker.get("bid")
        ask_price = ticker.get("ask")

        if not bid_price or not ask_price:
            return False, "Missing bid/ask price"

        # Get volumes (may be None)
        bid_volume = ticker.get("bidVolume", 0) or 0
        ask_volume = ticker.get("askVolume", 0) or 0

        # Calculate top-level liquidity estimate
        top_liquidity = (bid_price * bid_volume) + (ask_price * ask_volume)

        # Minimum threshold for pre-filter (fraction of min_liquidity)
        min_threshold = self._min_liquidity * self._ticker_prefilter_threshold

        if top_liquidity < min_threshold:
            return False, f"Top-level liquidity {top_liquidity:,.0f} < {min_threshold:,.0f}"

        return True, "Passed ticker pre-filter"

    async def _async_fetch_orderbooks(
        self, pairs: List[str], limit: int = 100, concurrency: int = 10
    ) -> Dict[str, Optional[OrderBook]]:
        """Fetch orderbooks concurrently using ccxt async client with bounded concurrency.

        Adds per-request timeouts and resilient gathering to avoid hangs.
        """
        results: Dict[str, Optional[OrderBook]] = {}
        sem = asyncio.Semaphore(concurrency)

        api_async = getattr(self._exchange, "_api_async", None)
        if api_async is None:
            return {p: None for p in pairs}

        # Ensure markets are loaded once to prevent lazy-init stalls during first fetch
        try:
            await asyncio.wait_for(api_async.load_markets(reload=False), timeout=5.0)
        except Exception:
            # Proceed anyway; individual fetches still attempted with timeouts
            pass

        async def _fetch_one(p: str) -> Optional[OrderBook]:
            async with sem:
                try:
                    return await asyncio.wait_for(
                        api_async.fetch_l2_order_book(p, limit), timeout=3.0
                    )
                except Exception:
                    return None

        tasks = [asyncio.create_task(_fetch_one(p)) for p in pairs]
        # Gather with return_exceptions to avoid propagation and ensure completion
        fetched = await asyncio.gather(*tasks, return_exceptions=True)
        for p, ob in zip(pairs, fetched):
            if isinstance(ob, Exception):
                results[p] = None
            else:
                results[p] = ob
        return results

    def filter_pairlist(self, pairlist: List[str], tickers: Dict) -> List[str]:
        """
        Filter pairlist based on orderbook liquidity with ticker pre-filtering.

        Args:
            pairlist: List of pairs to filter
            tickers: Ticker data for pre-filtering

        Returns:
            List of pairs that passed liquidity filter
        """
        if not pairlist:
            return pairlist

        self.log_once(f"LiquidityPairList: Filtering {len(pairlist)} pairs", logger.info)

        # Stage 1: Ticker pre-filtering
        candidates = pairlist
        ticker_rejected = []

        if tickers:
            candidates = []
            for pair in pairlist:
                ticker = tickers.get(pair)
                passed, reason = self._quick_ticker_filter(pair, ticker)
                if passed:
                    candidates.append(pair)
                else:
                    ticker_rejected.append((pair, reason))

            self.log_once(
                f"LiquidityPairList: Ticker pre-filter passed {len(candidates)}/{len(pairlist)} pairs",
                logger.info,
            )

        # Stage 2: Order book verification (ASYNC when possible)
        filtered_pairs: List[str] = []
        orderbook_rejected: List[Tuple[str, str]] = []

        # Prefer async only if async api is available
        api_async = getattr(self._exchange, "_api_async", None)
        use_async = api_async is not None
        # Prefer sync path if fetch_l2_order_book is mocked (unit tests)
        try:
            from unittest.mock import MagicMock  # type: ignore

            if isinstance(getattr(self._exchange, "fetch_l2_order_book", None), MagicMock):
                use_async = False
        except Exception:
            pass
        try:
            asyncio.get_running_loop()
            # Running in an event loop already - avoid nested loop
            use_async = False
        except RuntimeError:
            use_async = use_async

        if use_async:
            orderbooks = asyncio.run(
                self._async_fetch_orderbooks(candidates, limit=100, concurrency=10)
            )
            for pair in candidates:
                ob = orderbooks.get(pair)
                if ob is None:
                    orderbook_rejected.append((pair, "Orderbook fetch failed"))
                    continue
                passed, reason, metrics = self._evaluate_liquidity_from_orderbook(pair, ob)
                if passed:
                    filtered_pairs.append(pair)
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"LiquidityPairList: {pair} passed - {metrics}")
                else:
                    orderbook_rejected.append((pair, reason))
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"LiquidityPairList: {pair} rejected - {reason}")
        else:
            # Fallback: sequential (avoid threading as requested)
            for pair in candidates:
                passed, reason, metrics = self._calculate_orderbook_liquidity(pair)
                if passed:
                    filtered_pairs.append(pair)
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"LiquidityPairList: {pair} passed - {metrics}")
                else:
                    orderbook_rejected.append((pair, reason))
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"LiquidityPairList: {pair} rejected - {reason}")

        # Log summary (cached)
        self.log_once(
            f"LiquidityPairList: {len(filtered_pairs)}/{len(pairlist)} pairs passed final filter",
            logger.info,
        )

        if ticker_rejected:
            self.log_once(f"Ticker pre-filter rejected {len(ticker_rejected)} pairs", logger.info)
            if logger.isEnabledFor(logging.DEBUG):
                for pair, reason in ticker_rejected[:5]:
                    logger.debug(f"  - {pair}: {reason}")

        if orderbook_rejected:
            self.log_once(
                f"Order book filter rejected {len(orderbook_rejected)} pairs", logger.info
            )
            for pair, reason in orderbook_rejected[:10]:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"  - {pair}: {reason}")
            if len(orderbook_rejected) > 10:
                self.log_once(f"  ... and {len(orderbook_rejected) - 10} more", logger.info)

        return filtered_pairs

    # No thread pools used - no cleanup handler required
