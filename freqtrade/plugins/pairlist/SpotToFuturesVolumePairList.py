"""
Spot-to-Futures Volume PairList provider

Provides dynamic pair list based on spot trading volumes,
but validates pairs exist on futures market before adding them.
This leverages the spot market's screening (only quality pairs listed on spot)
while ensuring they're tradable on futures.

Supports multiple quote currencies dynamically (USDT, USDC, BUSD, etc.)
and respects blacklist patterns.
"""

import logging
import re
from datetime import timedelta
from typing import Any, Literal

import ccxt
from cachetools import TTLCache

from freqtrade.constants import ListPairsWithTimeframes
from freqtrade.exceptions import OperationalException
from freqtrade.exchange import timeframe_to_minutes, timeframe_to_prev_date
from freqtrade.exchange.exchange_types import Tickers
from freqtrade.plugins.pairlist.IPairList import IPairList, PairlistParameter, SupportsBacktesting
from freqtrade.util import dt_now, format_ms_time


logger = logging.getLogger(__name__)


SORT_VALUES = ["quoteVolume"]


class SpotToFuturesVolumePairList(IPairList):
    """
    PairList that fetches volume from spot market and validates pairs exist on futures.
    
    This is useful for futures trading where you want to use Binance's spot market
    as a quality filter - spot pairs are always available on futures (but not vice versa).
    
    Supports multiple quote currencies dynamically and respects blacklist patterns.
    """
    
    is_pairlist_generator = True
    supports_backtesting = SupportsBacktesting.NO

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        if "number_assets" not in self._pairlistconfig:
            raise OperationalException(
                "`number_assets` not specified. Please check your configuration "
                'for "pairlist.config.number_assets"'
            )

        self._stake_currency = self._config["stake_currency"]
        self._number_pairs = self._pairlistconfig["number_assets"]
        self._sort_key: Literal["quoteVolume"] = self._pairlistconfig.get("sort_key", "quoteVolume")
        self._min_value = self._pairlistconfig.get("min_value", 0)
        self._max_value = self._pairlistconfig.get("max_value", None)
        self._refresh_period = self._pairlistconfig.get("refresh_period", 1800)
        self._pair_cache: TTLCache = TTLCache(maxsize=1, ttl=self._refresh_period)
        self._lookback_days = self._pairlistconfig.get("lookback_days", 0)
        self._lookback_timeframe = self._pairlistconfig.get("lookback_timeframe", "1d")
        self._lookback_period = self._pairlistconfig.get("lookback_period", 0)
        self._def_candletype = self._config["candle_type_def"]
        
        # New parameter: source market type (spot, futures, etc.)
        self._source_market_type = self._pairlistconfig.get("source_market_type", "spot")
        
        # The trading mode from config (what we're actually trading on)
        self._trading_mode = self._config.get("trading_mode", "spot")
        
        # NEW: Quote currencies to include (empty = use stake_currency only)
        # If "all", it will fetch all quote currencies dynamically
        self._quote_currencies = self._pairlistconfig.get("quote_currencies", [])
        
        # NEW: Whether to use all quote currencies from the exchange
        self._use_all_quotes = self._pairlistconfig.get("use_all_quotes", False)
        
        # Compile blacklist patterns for efficient matching
        self._blacklist_patterns = self._compile_blacklist_patterns()

        if (self._lookback_days > 0) & (self._lookback_period > 0):
            raise OperationalException(
                "Ambiguous configuration: lookback_days and lookback_period both set in pairlist "
                "config. Please set lookback_days only or lookback_period and lookback_timeframe "
                "and restart the bot."
            )

        # overwrite lookback timeframe and days when lookback_days is set
        if self._lookback_days > 0:
            self._lookback_timeframe = "1d"
            self._lookback_period = self._lookback_days

        # get timeframe in minutes and seconds
        self._tf_in_min = timeframe_to_minutes(self._lookback_timeframe)
        _tf_in_sec = self._tf_in_min * 60

        # whether to use range lookback or not
        self._use_range = (self._tf_in_min > 0) & (self._lookback_period > 0)

        if self._use_range & (self._refresh_period < _tf_in_sec):
            raise OperationalException(
                f"Refresh period of {self._refresh_period} seconds is smaller than one "
                f"timeframe of {self._lookback_timeframe}. Please adjust refresh_period "
                f"to at least {_tf_in_sec} and restart the bot."
            )

        if not self._use_range and not (
            self._exchange.exchange_has("fetchTickers")
            and self._exchange.get_option("tickers_have_quoteVolume")
        ):
            raise OperationalException(
                "Exchange does not support dynamic whitelist in this configuration. "
                "Please edit your config and either remove SpotToFuturesVolumePairList, "
                "or switch to using candles and restart the bot."
            )

        if not self._validate_keys(self._sort_key):
            raise OperationalException(f"key {self._sort_key} not in {SORT_VALUES}")

        candle_limit = self._exchange.ohlcv_candle_limit(
            self._lookback_timeframe, self._def_candletype
        )
        if self._lookback_period < 0:
            raise OperationalException("SpotToFuturesVolumePairList requires lookback_period to be >= 0")
        if self._lookback_period > candle_limit:
            raise OperationalException(
                "SpotToFuturesVolumePairList requires lookback_period to not "
                f"exceed exchange max request size ({candle_limit})"
            )
        
        # Log configuration
        if self._source_market_type != self._trading_mode:
            logger.info(
                f"Initializing {self._source_market_type} market query for volume data "
                f"while trading on {self._trading_mode}"
            )
        
        if self._use_all_quotes:
            logger.info("Using ALL quote currencies from spot market (filtered by blacklist)")
        elif self._quote_currencies:
            logger.info(f"Using quote currencies: {self._quote_currencies}")
        else:
            logger.info(f"Using stake currency only: {self._stake_currency}")

    def _compile_blacklist_patterns(self) -> list:
        """
        Compile blacklist regex patterns from config for efficient matching.
        """
        try:
            blacklist = self._config.get('exchange', {}).get('pair_blacklist', [])
            compiled = []
            for pattern in blacklist:
                try:
                    compiled.append(re.compile(pattern))
                except re.error as e:
                    logger.warning(f"Invalid blacklist regex pattern '{pattern}': {e}")
            return compiled
        except Exception as e:
            logger.warning(f"Error compiling blacklist patterns: {e}")
            return []

    def _is_blacklisted(self, pair: str) -> bool:
        """
        Check if a pair matches any blacklist pattern.
        
        :param pair: Trading pair (e.g., 'BTC/USDT')
        :return: True if blacklisted, False otherwise
        """
        for pattern in self._blacklist_patterns:
            if pattern.match(pair) or pattern.fullmatch(pair):
                return True
        return False

    def _get_target_quote_currencies(self, spot_markets: dict) -> list[str]:
        """
        Determine which quote currencies to use.
        
        :param spot_markets: Markets from spot exchange
        :return: List of quote currencies to include
        """
        if self._use_all_quotes:
            # Extract all unique quote currencies from spot markets
            quote_currencies = set()
            for symbol, market in spot_markets.items():
                if '/' in symbol:
                    quote = symbol.split('/')[1]
                    # Only add if the pair wouldn't be blacklisted
                    if not self._is_blacklisted(f"TEST/{quote}"):
                        quote_currencies.add(quote)
            
            logger.info(f"Found {len(quote_currencies)} quote currencies in spot market")
            return list(quote_currencies)
        
        elif self._quote_currencies:
            # Use specified quote currencies
            return self._quote_currencies
        
        else:
            # Use only stake currency
            return [self._stake_currency]

    @property
    def needstickers(self) -> bool:
        """
        Boolean property defining if tickers are necessary.
        If no Pairlist requires tickers, an empty Dict is passed
        as tickers argument to filter_pairlist
        """
        return not self._use_range

    def _validate_keys(self, key):
        return key in SORT_VALUES

    def short_desc(self) -> str:
        """
        Short whitelist method description - used for startup-messages
        """
        quote_desc = "all quotes" if self._use_all_quotes else self._stake_currency
        return (
            f"{self.name} - top {self._pairlistconfig['number_assets']} volume pairs "
            f"from {self._source_market_type} market ({quote_desc}), validated for {self._trading_mode}."
        )

    @staticmethod
    def description() -> str:
        return (
            "Provides dynamic pair list based on spot trade volumes, "
            "validates pairs exist on futures market. "
            "Supports multiple quote currencies dynamically."
        )

    @staticmethod
    def available_parameters() -> dict[str, PairlistParameter]:
        return {
            "number_assets": {
                "type": "number",
                "default": 30,
                "description": "Number of assets",
                "help": "Number of assets to use from the pairlist",
            },
            "sort_key": {
                "type": "option",
                "default": "quoteVolume",
                "options": SORT_VALUES,
                "description": "Sort key",
                "help": "Sort key to use for sorting the pairlist.",
            },
            "min_value": {
                "type": "number",
                "default": 0,
                "description": "Minimum value",
                "help": "Minimum value to use for filtering the pairlist.",
            },
            "max_value": {
                "type": "number",
                "default": None,
                "description": "Maximum value",
                "help": "Maximum value to use for filtering the pairlist.",
            },
            **IPairList.refresh_period_parameter(),
            "lookback_days": {
                "type": "number",
                "default": 0,
                "description": "Lookback Days",
                "help": "Number of days to look back at.",
            },
            "lookback_timeframe": {
                "type": "string",
                "default": "",
                "description": "Lookback Timeframe",
                "help": "Timeframe to use for lookback.",
            },
            "lookback_period": {
                "type": "number",
                "default": 0,
                "description": "Lookback Period",
                "help": "Number of periods to look back at.",
            },
            "source_market_type": {
                "type": "option",
                "default": "spot",
                "options": ["spot", "futures", "margin"],
                "description": "Source Market Type",
                "help": "Market type to fetch volume data from (spot, futures, margin).",
            },
            "quote_currencies": {
                "type": "list",
                "default": [],
                "description": "Quote Currencies",
                "help": "List of quote currencies to include (e.g., ['USDT', 'USDC']). Empty = stake currency only.",
            },
            "use_all_quotes": {
                "type": "boolean",
                "default": False,
                "description": "Use All Quote Currencies",
                "help": "If true, use all quote currencies from spot market (filtered by blacklist).",
            },
        }

    def _get_spot_markets(self) -> dict:
        """
        Get markets from the source market type (e.g., spot).
        
        For exchanges like Binance, we need to query spot markets separately
        when trading on futures.
        """
        try:
            # Create a temporary exchange instance with spot market settings
            exchange_name = self._config['exchange']['name']
            
            # For CCXT, we can modify options to fetch spot markets
            ccxt_exchange = getattr(ccxt, exchange_name)({
                'apiKey': self._config['exchange'].get('key', ''),
                'secret': self._config['exchange'].get('secret', ''),
                'options': {
                    'defaultType': self._source_market_type,  # 'spot' or 'futures'
                }
            })
            
            # Load markets
            markets = ccxt_exchange.load_markets()
            
            logger.info(
                f"Loaded {len(markets)} markets from {self._source_market_type} "
                f"for volume filtering"
            )
            
            return markets
            
        except Exception as e:
            logger.error(
                f"Error loading {self._source_market_type} markets: {e}. "
                f"Falling back to default exchange markets."
            )
            return self._exchange.markets

    def _get_spot_tickers(self) -> Tickers:
        """
        Fetch tickers from spot market.
        """
        try:
            exchange_name = self._config['exchange']['name']
            
            ccxt_exchange = getattr(ccxt, exchange_name)({
                'apiKey': self._config['exchange'].get('key', ''),
                'secret': self._config['exchange'].get('secret', ''),
                'options': {
                    'defaultType': self._source_market_type,
                }
            })
            
            tickers = ccxt_exchange.fetch_tickers()
            logger.info(f"Fetched {len(tickers)} tickers from {self._source_market_type} market")
            
            return tickers
            
        except Exception as e:
            logger.error(f"Error fetching {self._source_market_type} tickers: {e}")
            return {}

    def _validate_pair_on_futures(self, pair: str) -> bool:
        """
        Validate that a pair exists and is tradable on the futures market.
        
        :param pair: Pair to validate (e.g., 'BTC/USDT')
        :return: True if pair exists on futures, False otherwise
        """
        try:
            # Check if pair exists in the actual trading markets
            markets = self._exchange.markets
            
            if pair not in markets:
                return False
            
            market = markets[pair]
            
            # Check if it's active and tradable
            if not market.get('active', False):
                return False
            
            # Additional futures-specific checks could go here
            return True
            
        except Exception as e:
            logger.warning(f"Error validating pair {pair} on futures: {e}")
            return False

    def _filter_by_quote_currencies(self, pairs: list[str], quote_currencies: list[str]) -> list[str]:
        """
        Filter pairs to only include those with specified quote currencies.
        Also excludes blacklisted pairs.
        
        :param pairs: List of pairs to filter
        :param quote_currencies: List of allowed quote currencies
        :return: Filtered list of pairs
        """
        filtered = []
        for pair in pairs:
            if '/' not in pair:
                continue
            
            quote = pair.split('/')[1]
            if quote in quote_currencies:
                # Check if not blacklisted
                if not self._is_blacklisted(pair):
                    filtered.append(pair)
        
        return filtered

    def gen_pairlist(self, tickers: Tickers) -> list[str]:
        """
        Generate the pairlist
        :param tickers: Tickers (from exchange.get_tickers). May be cached.
        :return: List of pairs
        """
        # Generate dynamic whitelist
        # Must always run if this pairlist is not the first in the list.
        pairlist = self._pair_cache.get("pairlist")
        if pairlist:
            # Item found - no refresh necessary
            return pairlist.copy()
        else:
            # Get spot markets and tickers for volume ranking
            if self._source_market_type != self._trading_mode:
                logger.info(
                    f"Fetching volume data from {self._source_market_type} market "
                    f"for {self._trading_mode} trading"
                )
                spot_markets = self._get_spot_markets()
                
                # Determine quote currencies to use
                quote_currencies = self._get_target_quote_currencies(spot_markets)
                logger.info(f"Using quote currencies: {quote_currencies}")
                
                # If not using range (using tickers mode)
                if not self._use_range:
                    spot_tickers = self._get_spot_tickers()
                else:
                    spot_tickers = {}
                
                # Get all pairs and filter by quote currencies
                all_pairs = list(spot_markets.keys())
                _pairlist = self._filter_by_quote_currencies(all_pairs, quote_currencies)
                logger.info(f"Found {len(_pairlist)} pairs with matching quote currencies")
                
            else:
                # Use default exchange markets (same market type)
                quote_currencies = self._get_target_quote_currencies(self._exchange.markets)
                
                _pairlist = [
                    k
                    for k in self._exchange.get_markets(
                        quote_currencies=quote_currencies,
                        tradable_only=True,
                        active_only=True
                    ).keys()
                ]
                spot_tickers = tickers

            # Apply Freqtrade's blacklist verification
            _pairlist = self.verify_blacklist(_pairlist, logger.info)
            
            if not self._use_range:
                # Filter tickers by our pairlist
                filtered_tickers = [
                    v
                    for k, v in spot_tickers.items()
                    if (
                        k in _pairlist
                        and (self._use_range or v.get(self._sort_key) is not None)
                    )
                ]
                pairlist = [s.get("symbol", s.get("symbol")) for s in filtered_tickers]
            else:
                pairlist = _pairlist

            pairlist = self.filter_pairlist(pairlist, spot_tickers if spot_tickers else tickers)
            
            # NOW THE KEY PART: Validate pairs exist on futures market
            if self._source_market_type != self._trading_mode:
                logger.info(
                    f"Validating {len(pairlist)} pairs from {self._source_market_type} "
                    f"against {self._trading_mode} market availability"
                )
                
                validated_pairlist = []
                skipped_pairs = []
                for pair in pairlist:
                    if self._validate_pair_on_futures(pair):
                        validated_pairlist.append(pair)
                    else:
                        skipped_pairs.append(pair)
                
                if skipped_pairs:
                    logger.debug(
                        f"Pairs not available on {self._trading_mode}: {skipped_pairs[:10]}..."
                    )
                
                logger.info(
                    f"Validated {len(validated_pairlist)}/{len(pairlist)} pairs "
                    f"are available on {self._trading_mode}"
                )
                pairlist = validated_pairlist
            
            self._pair_cache["pairlist"] = pairlist.copy()

        return pairlist

    def filter_pairlist(self, pairlist: list[str], tickers: dict) -> list[str]:
        """
        Filters and sorts pairlist and returns the whitelist again.
        Called on each bot iteration - please use internal caching if necessary
        :param pairlist: pairlist to filter or sort
        :param tickers: Tickers (from exchange.get_tickers). May be cached.
        :return: new whitelist
        """
        if self._use_range:
            # Create bare minimum from tickers structure.
            filtered_tickers: list[dict[str, Any]] = [{"symbol": k} for k in pairlist]

            # get lookback period in ms, for exchange ohlcv fetch
            since_ms = (
                int(
                    timeframe_to_prev_date(
                        self._lookback_timeframe,
                        dt_now()
                        + timedelta(
                            minutes=-(self._lookback_period * self._tf_in_min) - self._tf_in_min
                        ),
                    ).timestamp()
                )
                * 1000
            )

            to_ms = (
                int(
                    timeframe_to_prev_date(
                        self._lookback_timeframe, dt_now() - timedelta(minutes=self._tf_in_min)
                    ).timestamp()
                )
                * 1000
            )

            self.log_once(
                f"Using volume range of {self._lookback_period} candles, timeframe: "
                f"{self._lookback_timeframe}, starting from {format_ms_time(since_ms)} "
                f"till {format_ms_time(to_ms)}",
                logger.info,
            )
            
            # Fetch OHLCV data
            needed_pairs: ListPairsWithTimeframes = [
                (p, self._lookback_timeframe, self._def_candletype)
                for p in [s["symbol"] for s in filtered_tickers]
                if p not in self._pair_cache
            ]
            
            if self._source_market_type != self._trading_mode:
                logger.warning(
                    "OHLCV fetching from source market in range mode may not work correctly. "
                    "Consider using ticker mode (lookback_period=0) for cross-market queries."
                )
            
            candles = self._exchange.refresh_ohlcv_with_cache(needed_pairs, since_ms)

            for i, p in enumerate(filtered_tickers):
                contract_size = 1.0
                if p["symbol"] in self._exchange.markets:
                    contract_size = self._exchange.markets[p["symbol"]].get("contractSize", 1.0) or 1.0
                    
                pair_candles = (
                    candles[(p["symbol"], self._lookback_timeframe, self._def_candletype)]
                    if (p["symbol"], self._lookback_timeframe, self._def_candletype) in candles
                    else None
                )
                # in case of candle data calculate typical price and quoteVolume for candle
                if pair_candles is not None and not pair_candles.empty:
                    if self._exchange.get_option("ohlcv_volume_currency") == "base":
                        pair_candles["typical_price"] = (
                            pair_candles["high"] + pair_candles["low"] + pair_candles["close"]
                        ) / 3

                        pair_candles["quoteVolume"] = (
                            pair_candles["volume"] * pair_candles["typical_price"] * contract_size
                        )
                    else:
                        # Exchange ohlcv data is in quote volume already.
                        pair_candles["quoteVolume"] = pair_candles["volume"]
                    # ensure that a rolling sum over the lookback_period is built
                    # if pair_candles contains more candles than lookback_period
                    quoteVolume = (
                        pair_candles["quoteVolume"]
                        .rolling(self._lookback_period)
                        .sum()
                        .fillna(0)
                        .iloc[-1]
                    )

                    # replace quoteVolume with range quoteVolume sum calculated above
                    filtered_tickers[i]["quoteVolume"] = quoteVolume
                else:
                    filtered_tickers[i]["quoteVolume"] = 0
        else:
            # Tickers mode - filter based on incoming pairlist.
            filtered_tickers = [v for k, v in tickers.items() if k in pairlist]

        if self._min_value > 0:
            filtered_tickers = [v for v in filtered_tickers if v[self._sort_key] > self._min_value]
        if self._max_value is not None:
            filtered_tickers = [v for v in filtered_tickers if v[self._sort_key] < self._max_value]

        sorted_tickers = sorted(filtered_tickers, reverse=True, key=lambda t: t[self._sort_key])

        # Validate whitelist to only have active market pairs
        pairs = self._whitelist_for_active_markets([s["symbol"] for s in sorted_tickers])
        pairs = self.verify_blacklist(pairs, logmethod=logger.info)
        # Limit pairlist to the requested number of pairs
        pairs = pairs[: self._number_pairs]

        return pairs
