import logging
import time
from datetime import datetime
from typing import Any

import ccxt

from freqtrade.constants import BuySell, Config, ExchangeConfig
from freqtrade.enums import CandleType, MarginMode, TradingMode
from freqtrade.exceptions import DDosProtection, OperationalException, TemporaryError, ExchangeError
from freqtrade.exchange import Exchange
from freqtrade.exchange.common import retrier, retrier_async
from freqtrade.exchange.exchange_types import CcxtOrder, FtHas, OHLCVResponse

logger = logging.getLogger(__name__)


class Blofin(Exchange):
    """
    BloFin exchange class. Contains adjustments needed for Freqtrade to work
    with this exchange.
    """

    _ft_has: FtHas = {
        # "stoploss_on_exchange": True,  # BloFin supports stop-loss orders on exchange
        # "stop_price_param": "stopLossPrice",  # BloFin uses stopLossPrice parameter
        # "stop_price_prop": "stopLossPrice",  # Property name in order response
        # "stoploss_order_types": {"market": "market", "limit": "limit"},  # Supported stop order types
        "ohlcv_candle_limit": 5000,
        "trades_pagination": "id",
        "trades_pagination_arg": "fromId",
        "l2_limit_range": [1, 200],
        "l2_limit_range_required": False,
        # "ws_enabled": True,
    }

    _ft_has_futures: FtHas = {
        # "funding_fee_candle_limit": 1000,
        # "stoploss_order_types": {"limit": "stop", "market": "stop_market"},
        # "stoploss_blocks_assets": False,  # Stoploss orders do not block assets
        "order_time_in_force": ["GTC", "FOK", "IOC"],
        # "tickers_have_price": False,
        "floor_leverage": True,
        # "fetch_orders_limit_minutes": 7 * 1440,  # "fetch_orders" is limited to 7 days
        # "stop_price_type_field": "workingType",
        # Removing order_props_in_contracts entirely to let Freqtrade handle amounts as-is
        # "stop_price_type_value_mapping": {
        #     PriceType.LAST: "CONTRACT_PRICE",
        #     PriceType.MARK: "MARK_PRICE",
        # },
        # "ws_enabled": True,  # CCXT BloFin websockets ARE implemented and working
        # "proxy_coin_mapping": {
        #     "BNFCR": "USDC",
        #     "BFUSD": "USDT",
        # },
    }

    _supported_trading_mode_margin_pairs = [
        (TradingMode.SPOT, MarginMode.NONE), # Not tested yet
        (TradingMode.FUTURES, MarginMode.CROSS),
        (TradingMode.FUTURES, MarginMode.ISOLATED),
    ]

    def __init__(self, config: Config, exchange_config: ExchangeConfig | None = None, **kwargs):
        """
        Initialize BloFin exchange.
        """
        logger.info("Initializing BloFin exchange")
        # self._last_funding_fee_query = {}
        # # Simple cache for stoploss orders to avoid repeated API calls
        # self._stoploss_cache = {}
        # self._cache_timeout = 3  # seconds
        super().__init__(config, exchange_config=exchange_config, **kwargs)
        
        # Position sync tracking
        self._last_position_sync = 0
        self._position_sync_interval = 10  # Sync every 60 seconds
        self._position_sync_pairs = set()  # Track which pairs need sync
        
        # Override ccxt's fetchFundingHistory with our custom implementation that returns empty
        # self._api.fetchFundingHistory = self._ccxt_fetch_funding_history

    def _set_leverage(
        self,
        leverage: float,
        pair: str | None = None,
        accept_fail: bool = False,
    ):
        """
        Set leverage for BloFin exchange.
        TESTED
        """
        if self._config["dry_run"]:
            logger.debug("🔧 Skipping leverage setting: dry_run=%s", self._config['dry_run'])
            return

        try:
            logger.info("⚖️ Setting leverage for %s to %sx with marginMode=%s", pair, leverage, self.margin_mode)
            # BloFin API requires marginMode to be passed in params
            params = {'marginMode':self.margin_mode}
            res = self._api.set_leverage(symbol=pair, leverage=leverage, params=params)
            self._log_exchange_response("set_leverage", res)
            logger.info("🔧 Successfully set leverage for %s to %sx with marginMode=%s", pair, leverage, self.margin_mode)
        except ccxt.DDoSProtection as e:
            logger.warning("🔧 Rate limit exceeded when setting leverage for %s", pair)
            raise DDosProtection(e) from e
        except (ccxt.BadRequest, ccxt.OperationRejected, ccxt.InsufficientFunds) as e:
            logger.error("🔧 Failed to set leverage for %s: %s", pair, e)
            if not accept_fail:
                raise TemporaryError(
                    f"Could not set leverage due to {e.__class__.__name__}. Message: {e}"
                ) from e
        except ccxt.BaseError as e:
            logger.error("🔧 Unexpected error setting leverage for %s: %s", pair, e)
            if not accept_fail:
                raise OperationalException(e) from e

    def _lev_prep(self, pair: str, leverage: float, side: BuySell, accept_fail: bool = False):
        """
        Leverage preparation for BloFin.
        Ensures leverage is set before trades.
        TESTED
        """
        if self.trading_mode != TradingMode.SPOT:
            self.set_margin_mode(pair, self.margin_mode)
            self._set_leverage(leverage=leverage, pair=pair, accept_fail=accept_fail)

    def set_margin_mode(self, pair: str, margin_mode: MarginMode, accept_fail: bool = False):
        """
        Set margin mode for BloFin exchange.
        TESTED
        """
        if self._config["dry_run"]:
            logger.warning("🔧 Skipping margin mode setting: dry_run=%s", self._config['dry_run'])

        try:
            logger.info("🔧 Setting margin mode for %s to %s", pair, self.margin_mode)
            res = self._api.set_margin_mode(symbol=pair, marginMode=self.margin_mode)
            self._log_exchange_response("set_margin_mode", res)
            logger.info("🔧 Successfully set margin mode for %s to %s", pair, self.margin_mode)

        except ccxt.DDoSProtection as e:
            logger.warning("🔧 Rate limit exceeded when setting margin mode for %s", pair)
            raise DDosProtection(e) from e
        except (ccxt.BadRequest, ccxt.OperationRejected) as e:
            logger.error("🔧 Failed to set margin mode for %s: %s", pair, e)
            if not accept_fail:
                raise TemporaryError(
                    f"Could not set margin mode due to {e.__class__.__name__}. Message: {e}"
                ) from e
        except ccxt.BaseError as e:
            logger.error("🔧 Unexpected error setting margin mode for %s: %s", pair, e)
            if not accept_fail:
                raise OperationalException(e) from e

    def get_tickers(self, symbols=None, *, cached=False, market_type=None):
        """
        Override get_tickers for BloFin exchange.
        Fix quoteVolume by mapping from BloFin's volCurrency24h.
        """
        tickers = super().get_tickers(symbols, cached=cached, market_type=market_type)
        
        # Fix quoteVolume for BloFin tickers
        fixed_count = 0
        for symbol, ticker in tickers.items():
            if ticker.get('quoteVolume') is None and ticker.get('info'):
                # BloFin provides volume in volCurrency24h
                vol_currency = ticker['info'].get('volCurrency24h')
                if vol_currency is not None:
                    try:
                        ticker['quoteVolume'] = float(vol_currency)
                        fixed_count += 1
                    except (ValueError, TypeError):
                        # Fallback to baseVolume if conversion fails
                        ticker['quoteVolume'] = ticker.get('baseVolume', 0)
                        
        if fixed_count > 0:
            logger.debug("🔧 BloFin: Fixed quoteVolume for %d tickers", fixed_count)
        return tickers

    @retrier
    def fetch_order(self, order_id: str, pair: str, params: dict | None = None) -> CcxtOrder:
        """
        Fetch order from exchange.
        BloFin doesn't have a direct fetchOrder method, so we emulate it
        using fetchOpenOrders and fetchClosedOrders.
        Ensures returned order is normalized for Freqtrade.
        """
        if self._config["dry_run"]:
            return self.fetch_dry_run_order(order_id)

        if params is None:
            params = {}

        def _normalize_order(order: dict) -> dict:
            """Normalize BloFin order fields to CCXT standard format."""
            # Field mappings: BloFin -> CCXT standard
            order['amount'] = float(order.get('amount') or order.get('size') or 0)
            filled_value = (order.get('filled') or order.get('filledSize') or 
                          order.get('dealSize') or 0)
            order['filled'] = float(filled_value)
            
            # Calculate remaining if not provided
            if order.get('remaining') is not None:
                try:
                    order['remaining'] = float(order['remaining'])
                except (ValueError, TypeError):
                    order['remaining'] = 0.0
            else:
                order['remaining'] = max(0.0, order['amount'] - order['filled'])

            # Status normalization
            status_map = {
                'open': 'open', 'live': 'open', 'effective': 'open',
                'closed': 'closed', 'filled': 'closed', 'triggered': 'closed',
                'canceled': 'canceled', 'cancelled': 'canceled',
                'order_failed': 'rejected',
            }
            raw_status = order.get('status') or order.get('state')
            if raw_status:
                order['status'] = status_map.get(str(raw_status).lower(), raw_status)

            # Ensure required fields exist
            order.setdefault('fee', {})
            order.setdefault('info', {})
            order.setdefault('symbol', pair)
            return order

        def _search_orders(order_list, search_id):
            """Search for order in a list of orders."""
            for order in order_list:
                if order['id'] == search_id:
                    return order
            return None

        # Try multiple times with delays for better reliability
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                # Search in open orders first
                open_orders = self._api.fetch_open_orders(pair, params=params)
                found_order = _search_orders(open_orders, order_id)
                if found_order:
                    logger.info(f"🔧 Order {order_id} found in open orders (attempt {attempt + 1})")
                    norm = _normalize_order(found_order)
                    return norm

                # Search in closed orders
                closed_orders = self._api.fetch_closed_orders(pair, params=params)
                found_order = _search_orders(closed_orders, order_id)
                if found_order:
                    logger.info(f"🔧 Order {order_id} found in closed orders (attempt {attempt + 1})")
                    norm = _normalize_order(found_order)
                    return norm

                # If not found and not the last attempt, wait before retrying
                if attempt < max_attempts - 1:
                    logger.warning(f"🔧 Order {order_id} not found, retrying in {attempt + 1}s...")
                    import time
                    time.sleep(attempt + 1)  # Progressive delay: 1s, 2s
                    
            except ccxt.BaseError as e:
                if attempt < max_attempts - 1:
                    logger.warning(f"🔧 Error fetching order {order_id}: {e}, retrying...")
                    import time
                    time.sleep(attempt + 1)
                    continue
                else:
                    logger.error("Error fetching order %s for %s: %s", order_id, pair, e)
                    raise

        # Create synthetic closed order if not found after all attempts
        logger.warning(f"🔧 Order {order_id} not found after {max_attempts} attempts, "
                      "returning synthetic closed order")
        
        return {
            'id': order_id,
            'symbol': pair,
            'amount': 0.0,
            'filled': 0.0,
            'remaining': 0.0,
            'status': 'closed',
            'type': 'market',
            'side': 'unknown',
            'fee': {},
            'info': {'synthetic': True, 'reason': 'order_not_found'},
            'timestamp': None,
            'datetime': None,
            'lastTradeTimestamp': None,
            'average': None,
            'cost': None,
            'trades': []
        }
    
    @retrier
    def fetch_funding_rate_history(self, symbol: str, since: int | None = None, limit: int | None = None) -> list:
        """
        Fetch funding rate history for a symbol.
        This method uses CCXT's fetchFundingRateHistory which works reliably for BloFin.
        """

        #FIXME
        self.sync_trade_amount_from_position(pair=symbol)

        logger.debug("🔧 fetch_funding_rate_history called for %s, since: %s, limit: %s", symbol, since, limit)
        
        try:
            # Use CCXT's built-in method
            funding_rates = self._api.fetchFundingRateHistory(symbol, since=since, limit=limit)
            logger.debug("🔧 Retrieved %d funding rate records for %s", len(funding_rates), symbol)
            return funding_rates
            
        except Exception as e:
            logger.error("🔧 Error fetching funding rate history for %s: %s", symbol, e)
            # Return empty list to allow trading to continue
            return []
    
    def _get_params(
        self,
        side: str,
        ordertype: str,
        leverage: float,
        reduceOnly: bool,
        time_in_force: str = "GTC",
    ) -> dict:
        """
        Override _get_params to include BloFin-specific parameters like margin mode and leverage.
        TESTED
        """
        # Get base parameters from parent
        params = super()._get_params(side, ordertype, leverage, reduceOnly, time_in_force)
        
        # Add BloFin-specific parameters for futures trading
        if self.trading_mode == TradingMode.FUTURES:
            # Add margin mode parameter
            params['marginMode'] = self.margin_mode
            logger.info("🛒 Adding marginMode=%s to order parameters", self.margin_mode)
        
        return params

    def create_order(
        self,
        *,
        pair: str,
        ordertype: str,
        side: str,
        amount: float,
        rate: float,
        leverage: float,
        reduceOnly: bool = False,
        time_in_force: str = "GTC",
    ) -> CcxtOrder:
        """
        Override create_order to ensure leverage is set before creating the order.
        Margin mode is automatically included via _get_params() method.
        TESTED
        """
        logger.info(
            f"🛒 create_order called: pair={pair}, side={side}, "
            f"amount={amount}, rate={rate}, leverage={leverage} (type: {type(leverage)}) margin_mode={self.margin_mode}"
        )

        # Call parent create_order method
        result = super().create_order(
            pair=pair,
            ordertype=ordertype,
            side=side,
            amount=amount,
            rate=rate,
            leverage=int(leverage),
            reduceOnly=reduceOnly,
            time_in_force=time_in_force,
        )
        
        logger.info("🛒 Order created successfully: %s", result.get('id', 'unknown_id'))
        return result

    def get_max_leverage(self, pair: str, stake_amount: float | None) -> float:
        """
        Get maximum leverage for a trading pair from BloFin.
        TESTED
        """
        try:
            if self.trading_mode == TradingMode.FUTURES:
                max_leverage = self.markets[pair]["limits"]["leverage"]["max"]
                logger.info("🔧 Found max leverage %s for %s from market tiers", max_leverage, pair)
                return max_leverage
            else:
                return 1.0
        except Exception as e:
            logger.warning("🔧 Failed to fetch leverage info for %s: %s", pair, e)
            return 1.0

    def get_funding_fees(
        self, 
        pair: str, 
        amount: float, 
        is_short: bool, 
        open_date: datetime
    ) -> float:
        """
        Calculate funding fees for a BloFin position using funding rate history.
        
        This method fetches funding rate history and calculates the total funding fees
        paid/received for a position since it was opened.
        
        :param pair: The trading pair (e.g., "SUI/USDT:USDT")
        :param amount: Position size in base currency
        :param is_short: True if short position, False if long
        :param open_date: When the position was opened
        :return: Total funding fees (positive = paid, negative = received)
        """
        logger.info("🔧 get_funding_fees called for %s, amount: %s, is_short: %s", 
                    pair, amount, is_short)
        
        # Sync trade amount from position to fix any discrepancies
        try:
            self.sync_trade_amount_from_position(pair)
        except Exception as e:
            logger.debug(f"🔧 Error during trade amount sync in get_funding_fees: {e}")
        
        try:
            # Convert open_date to timestamp
            open_timestamp = int(open_date.timestamp() * 1000)
            
            # Fetch funding rate history since position opened
            funding_rates = self.fetch_funding_rate_history(pair, since=open_timestamp, limit=100)
            
            if not funding_rates:
                logger.warning("🔧 No funding rate history found for %s", pair)
                return 0.0
            
            logger.info("🔧 Found %d funding rate periods for %s", len(funding_rates), pair)
            
            total_funding_fee = 0.0
            applicable_rates = 0
            
            for rate_data in funding_rates:
                rate_timestamp = rate_data['timestamp']
                funding_rate = rate_data.get('fundingRate', 0.0)
                
                # Only include rates after position opened
                if rate_timestamp >= open_timestamp:
                    # Get mark price for accurate position value calculation
                    mark_price = rate_data.get('markPrice')
                    
                    if mark_price is None:
                        # Fallback: fetch current ticker for price estimate
                        try:
                            ticker = self.fetch_ticker(pair)
                            mark_price = ticker.get('last', ticker.get('close', 1.0))
                            logger.debug("🔧 Using ticker price as mark price: %s", mark_price)
                        except Exception:
                            # Last resort: use a reasonable estimate based on current market
                            mark_price = 3.8  # Rough estimate - should be improved
                            logger.warning("🔧 Using estimated mark price: %s", mark_price)
                    
                    # Calculate position value in quote currency (USDT)
                    position_value = amount * mark_price
                    
                    # Calculate funding fee for this period
                    # Formula: position_value * funding_rate * direction_multiplier
                    # Long positions: pay positive rates (positive fee = cost)
                    # Short positions: receive positive rates (negative fee = income)
                    direction_multiplier = 1 if is_short else -1
                    funding_fee = position_value * funding_rate * direction_multiplier
                    
                    total_funding_fee += funding_fee
                    applicable_rates += 1
                    
                    # Log each funding event for debugging
                    dt = datetime.fromtimestamp(rate_timestamp / 1000)
                    logger.info("🔧 Funding event: %s | Rate: %+.6f | Fee: %+.6f | Total: %+.6f",
                            dt.strftime('%Y-%m-%d %H:%M'), funding_rate, funding_fee, total_funding_fee)
            
            logger.info("🔧 Calculated funding fees for %s: %+.6f USDT (%d periods)",
                    pair, total_funding_fee, applicable_rates)
            
            return total_funding_fee
            
        except Exception as e:
            logger.error("🔧 Error calculating funding fees for %s: %s", pair, e)
            # Return 0.0 to allow trading to continue
            return 0.0

    # def _get_stop_params(self, side: BuySell, ordertype: str, stop_price: float) -> dict:
    #     """
    #     Get stop-loss parameters for BloFin exchange.
    #     BloFin uses stopLossPrice as the parameter name for stop orders.
    #     """
    #     params = self._params.copy()
        
    #     # BloFin requires stopLossPrice parameter
    #     params.update({
    #         "stopLossPrice": stop_price,
    #     })
        
    #     # Add margin mode if trading futures
    #     if self.trading_mode == TradingMode.FUTURES and self.margin_mode:
    #         params.update({
    #             "marginMode": "isolated" if self.margin_mode == MarginMode.ISOLATED else "cross"
    #         })
        
    #     return params

    # @retrier(retries=0)
    # def create_stoploss(
    #     self,
    #     pair: str,
    #     amount: float,
    #     stop_price: float,
    #     order_types: dict,
    #     side: BuySell,
    #     leverage: float,
    # ) -> CcxtOrder:
    #     """
    #     Custom stoploss implementation for BloFin.
    #     Uses BloFin's createStopLossOrder method directly to ensure proper order ID return.
    #     """
    #     from freqtrade.enums import PriceType
    #     from freqtrade.exceptions import InsufficientFundsError, InvalidOrderException
    #     import ccxt
        
    #     if not self._ft_has["stoploss_on_exchange"]:
    #         raise OperationalException(f"stoploss is not implemented for {self.name}.")

    #     user_order_type = order_types.get("stoploss", "market")
    #     ordertype, user_order_type = self._get_stop_order_type(user_order_type)
    #     round_mode = ccxt.ROUND_DOWN if side == "buy" else ccxt.ROUND_UP
    #     stop_price_norm = self.price_to_precision(pair, stop_price, rounding_mode=round_mode)
    #     limit_rate = None
        
    #     if user_order_type == "limit":
    #         limit_rate = self._get_stop_limit_rate(stop_price, order_types, side)
    #         limit_rate = self.price_to_precision(pair, limit_rate, rounding_mode=round_mode)

    #     if self._config["dry_run"]:
    #         dry_order = self.create_dry_run_order(
    #             pair,
    #             ordertype,
    #             side,
    #             amount,
    #             stop_price_norm,
    #             stop_loss=True,
    #             leverage=leverage,
    #         )
    #         return dry_order

    #     try:
    #         # Prepare parameters for BloFin stoploss order
    #         params = {}
            
    #         # Add reduceOnly for futures
    #         if self.trading_mode == TradingMode.FUTURES:
    #             params["reduceOnly"] = True
                
    #         # Add margin mode for BloFin - TP/SL orders use 'marginMode' parameter
    #         if self.trading_mode == TradingMode.FUTURES and self.margin_mode:
    #             params["marginMode"] = "isolated" if self.margin_mode == MarginMode.ISOLATED else "cross"
                
    #         # Add price type if specified
    #         if "stoploss_price_type" in order_types and "stop_price_type_field" in self._ft_has:
    #             price_type = self._ft_has["stop_price_type_value_mapping"][
    #                 order_types.get("stoploss_price_type", PriceType.LAST)
    #             ]
    #             params[self._ft_has["stop_price_type_field"]] = price_type

    #         amount_precise = self.amount_to_precision(pair, self._amount_to_contracts(pair, amount))

    #         # Set leverage before creating stoploss
    #         self._lev_prep(pair, leverage, side, accept_fail=True)
            
    #         # Use BloFin's createStopLossOrder method directly
    #         logger.info(f"🔧 Creating BloFin stoploss order: {pair}, {ordertype}, {side}, amount={amount_precise}, stopPrice={stop_price_norm}, params={params}")
            
    #         # Try BloFin's createStopLossOrder first
    #         try:
    #             order = self._api.createStopLossOrder(
    #                 symbol=pair,
    #                 type=ordertype,
    #                 side=side,
    #                 amount=amount_precise,
    #                 price=limit_rate,
    #                 stopLossPrice=stop_price_norm,
    #                 params=params,
    #             )
                
    #             # Debug: Log the raw order response
    #             logger.info(f"🔧 BloFin raw stoploss order response: {order}")
                
    #             # Check if the order creation was successful
    #             if order and (order.get('id') or order.get('info')):
    #                 logger.info(f"🔧 createStopLossOrder succeeded")
    #             else:
    #                 logger.warning(f"🔧 createStopLossOrder returned empty/invalid response, trying alternative method...")
    #                 raise Exception("createStopLossOrder returned invalid response")
                    
    #         except Exception as e:
    #             logger.warning(f"🔧 createStopLossOrder failed: {e}, trying conditional order approach...")
                
    #             # Alternative: Use createOrder with conditional parameters
    #             conditional_params = params.copy()
    #             conditional_params.update({
    #                 'stopPrice': stop_price_norm,
    #                 'orderType': 'conditional',
    #                 'triggerPrice': stop_price_norm,
    #                 'side': side  # Ensure side is explicitly set
    #             })
                
    #             logger.info(f"🔧 Creating conditional stoploss order with params: {conditional_params}")
                
    #             order = self._api.createOrder(
    #                 symbol=pair,
    #                 type='market',  # Conditional orders are usually market type
    #                 side=side,
    #                 amount=amount_precise,
    #                 price=None,  # No limit price for market conditional orders
    #                 params=conditional_params,
    #             )
                
    #             logger.info(f"🔧 Conditional stoploss order response: {order}")
            
    #         self._log_exchange_response("create_stoploss_order", order)
    #         order = self._order_contracts_to_amount(order)
            
    #         # Debug: Check order ID after processing
    #         order_id = order.get('id')
            
    #         # BloFin TP/SL orders might return tpslId instead of id
    #         if order_id is None:
    #             tpsl_id = order.get('tpslId')
    #             if not tpsl_id and order.get('info') is not None:
    #                 tpsl_id = order.get('info', {}).get('tpslId')
                
    #             if tpsl_id:
    #                 order['id'] = tpsl_id  # Fix the order ID
    #                 order_id = tpsl_id
    #                 logger.info(f"🔧 Fixed BloFin stoploss order ID: using tpslId {tpsl_id}")
    #             else:
    #                 # Fallback: check for algoId (compatibility)
    #                 algo_id = order.get('algoId')
    #                 if not algo_id and order.get('info') is not None:
    #                     algo_id = order.get('info', {}).get('algoId')
                    
    #                 if algo_id:
    #                     order['id'] = algo_id  # Fix the order ID
    #                     order_id = algo_id
    #                     logger.info(f"🔧 Fixed BloFin stoploss order ID: using algoId {algo_id}")
            
    #         logger.info(f"🔧 BloFin stoploss order ID after processing: {order_id}")
            
    #         if order_id is None:
    #             logger.error(f"🔧 BloFin stoploss order creation returned None ID: {order}")
    #             # Try to extract from info field - prioritize tpslId for TP/SL orders
    #             info = order.get('info')
    #             if info is not None:
    #                 for id_field in ['tpslId', 'algoId', 'ordId', 'id']:
    #                     if info.get(id_field):
    #                         order['id'] = info[id_field]
    #                         order_id = info[id_field]
    #                         logger.info(f"🔧 Recovered order ID from info.{id_field}: {order_id}")
    #                         break
                
    #             # If still no order ID found, this is a failed order creation
    #             if order_id is None:
    #                 logger.error(f"🔧 BloFin stoploss order creation completely failed - no valid order ID found")
    #                 raise InvalidOrderException(
    #                     f"BloFin stoploss order creation failed for {pair}. "
    #                     f"Exchange returned invalid response with no order ID. Response: {order}"
    #                 )
            
    #         logger.info(
    #             f"🔧 BloFin stoploss {user_order_type} order created: ID={order_id} for {pair}. "
    #             f"stop price: {stop_price_norm}. limit: {limit_rate}"
    #         )
    #         return order
            
    #     except ccxt.InsufficientFunds as e:
    #         raise InsufficientFundsError(
    #             f"Insufficient funds to create {ordertype} {side} stoploss order on market {pair}. "
    #             f"Tried to {side} amount {amount_precise} at rate {limit_rate} with "
    #             f"stop-price {stop_price_norm}. Message: {e}"
    #         ) from e
    #     except (ccxt.InvalidOrder, ccxt.BadRequest, ccxt.OperationRejected) as e:
    #         raise InvalidOrderException(
    #             f"Could not create {ordertype} {side} stoploss order on market {pair}. "
    #             f"Tried to {side} amount {amount_precise} at rate {limit_rate} with "
    #             f"stop-price {stop_price_norm}. Message: {e}"
    #         ) from e

    # def fetch_stoploss_order(self, order_id: str, pair: str, params: dict | None = None) -> CcxtOrder:
    #     """
    #     Custom fetch_stoploss_order for BloFin.
    #     BloFin stores stoploss orders as TP/SL orders that can only be fetched via TP/SL endpoints.
    #     Note: TP/SL orders are NOT visible in algo order lists, only in TP/SL order lists.
    #     """
    #     if params is None:
    #         params = {}
            
    #     # Handle None order_id gracefully
    #     if order_id is None:
    #         logger.error(f"🔧 Cannot fetch stoploss order: order_id is None for {pair}")
    #         raise ccxt.OrderNotFound(f"Cannot fetch stoploss order: order_id is None for {pair}")
            
    #     # Check cache first to avoid repeated API calls
    #     import time
    #     cache_key = f"{order_id}_{pair}"
    #     current_time = time.time()
        
    #     if cache_key in self._stoploss_cache:
    #         cached_order, cache_time = self._stoploss_cache[cache_key]
    #         if current_time - cache_time < self._cache_timeout:
    #             logger.debug(f"🔧 Returning cached stoploss order {order_id}")
    #             return cached_order
            
    #     logger.debug(f"🔧 Fetching BloFin stoploss order {order_id} for {pair}")
        
    #     try:
    #         # Convert freqtrade symbol to BloFin market ID
    #         market = self.markets[pair]
    #         market_id = market['id']
            
    #         # Check pending TP/SL orders first
    #         try:
    #             # Check pending TP/SL orders
    #             tpsl_pending_params = {'instId': market_id}
    #             tpsl_pending = self._api.private_get_trade_orders_tpsl_pending(tpsl_pending_params)
                
    #             for tpsl_order in tpsl_pending.get('data', []):
    #                 tpsl_id = tpsl_order.get('tpslId')
    #                 if tpsl_id == order_id:
    #                     # Convert TP/SL order to standard order format
    #                     converted_order = self._convert_tpsl_order_to_standard(tpsl_order)
    #                     # Cache the result
    #                     self._stoploss_cache[cache_key] = (converted_order, current_time)
    #                     logger.debug(f"🔧 Found stoploss order {order_id} in pending TP/SL orders")
    #                     return converted_order
                
    #             # Check TP/SL history if not found in pending
    #             tpsl_history_params = {'instId': market_id}
    #             tpsl_history = self._api.private_get_trade_orders_tpsl_history(tpsl_history_params)
                
    #             for tpsl_order in tpsl_history.get('data', []):
    #                 tpsl_id = tpsl_order.get('tpslId')
    #                 if tpsl_id == order_id:
    #                     # Convert TP/SL order to standard order format
    #                     converted_order = self._convert_tpsl_order_to_standard(tpsl_order)
    #                     # Cache the result
    #                     self._stoploss_cache[cache_key] = (converted_order, current_time)
    #                     logger.debug(f"🔧 Found stoploss order {order_id} in TP/SL order history")
    #                     return converted_order
                        
    #         except Exception as e:
    #             logger.warning(f"🔧 Error fetching TP/SL orders: {e}")
                
    #         # If still not found, check if position still exists
    #         try:
    #             positions = self.fetch_positions([pair])
    #             position = next((p for p in positions if p['symbol'] == pair), None)
                
    #             # Check if position is closed or very small
    #             position_size = 0
    #             if position:
    #                 position_size = abs(float(position.get('contracts', 0))) if position.get('contracts') else 0
                
    #             if position_size <= 0.001:  # Position is effectively closed
    #                 logger.info(f"🔧 Position for {pair} is closed (size: {position_size}), stoploss likely executed")
    #                 # Create a mock 'closed' order to indicate the stoploss was triggered
    #                 return {
    #                     'id': order_id,
    #                     'info': {'mock': True, 'reason': 'position_closed', 'position_size': position_size},
    #                     'timestamp': None,
    #                     'datetime': None,
    #                     'symbol': pair,
    #                     'type': 'market',
    #                     'side': 'sell',
    #                     'amount': None,
    #                     'price': None,
    #                     'filled': None,
    #                     'remaining': 0,
    #                     'status': 'closed',
    #                     'fee': None,
    #                     'cost': None,
    #                     'trades': None,
    #                 }
    #             else:
    #                 logger.info(f"🔧 Position for {pair} still exists (size: {position_size}), but stoploss order {order_id} not found")
    #         except Exception as e:
    #             logger.debug(f"🔧 Error checking position: {e}")
            
    #         # If still not found, return a mock 'canceled' order instead of crashing
    #         logger.info(f"🔧 Stoploss order {order_id} not found on exchange for {pair} - returning mock canceled order")
    #         return {
    #             'id': order_id,
    #             'info': {'mock': True, 'reason': 'not_found'},
    #             'timestamp': None,
    #             'datetime': None,
    #             'symbol': pair,
    #             'type': 'market',
    #             'side': 'sell',
    #             'amount': None,
    #             'price': None,
    #             'filled': None,
    #             'remaining': 0,
    #             'status': 'canceled',  # Mark as canceled instead of raising exception
    #             'fee': None,
    #             'cost': None,
    #             'trades': None,
    #         }
            
    #     except Exception as e:
    #         logger.error(f"🔧 Unexpected error fetching stoploss order {order_id}: {e}")
    #         # Return a mock 'error' order instead of crashing
    #         return {
    #             'id': order_id,
    #             'info': {'mock': True, 'reason': 'fetch_error', 'error': str(e)},
    #             'timestamp': None,
    #             'datetime': None,
    #             'symbol': pair,
    #             'type': 'market',
    #             'side': 'sell',
    #             'amount': None,
    #             'price': None,
    #             'filled': None,
    #             'remaining': 0,
    #             'status': 'canceled',
    #             'fee': None,
    #             'cost': None,
    #             'trades': None,
    #         }

    @retrier
    def sync_trade_amount_from_position(self, pair: str) -> float | None:
        """
        Sync trade amount from actual exchange position.
        This is useful when freqtrade's trade amount gets out of sync with the actual position.
        
        Returns:
        - float: Position size if position exists
        - 0.0: If no position exists (position was closed)
        - None: If there was an error or position data unavailable
        """
        try:
            # Fetch positions for the specific pair
            positions = self.fetch_positions(pair)
            position = next((p for p in positions if p['symbol'] == pair), None)
            
            if position:
                # BloFin uses 'contracts' field for position size
                position_size = abs(float(position.get('contracts', 0))) if position.get('contracts') else 0
                if position_size > 0:
                    logger.info(f"🔧 Found active position for {pair}: {position_size} contracts at entry {position.get('entryPrice', 'N/A')}")
                    logger.info(f"🔧 Position PnL: {position.get('unrealizedPnl', 'N/A')} USDT ({position.get('percentage', 'N/A')}%)")
                    
                    # Try to sync with freqtrade trade if available
                    try:
                        from freqtrade.persistence import Trade
                        open_trades = Trade.get_trades_proxy(pair=pair, is_open=True)
                        if open_trades:
                            trade = open_trades[0]  # Should only be one open trade per pair
                            if trade.amount != position_size:
                                old_amount = trade.amount
                                trade.amount = position_size
                                Trade.commit()
                                logger.warning(f"🔧 TRADE AMOUNT SYNCED: {pair} updated from {old_amount} to {position_size} contracts")
                            else:
                                logger.debug(f"🔧 Trade amount already in sync for {pair}: {position_size}")
                        else:
                            logger.debug(f"🔧 No open trade found in freqtrade for {pair}")
                    except Exception as sync_error:
                        logger.error(f"🔧 Error syncing trade amount to freqtrade for {pair}: {sync_error}")
                    
                    return position_size
                else:
                    logger.info(f"🔧 Position found but size is zero for {pair} - position was closed")
                    return 0.0
            else:
                logger.info(f"🔧 No position data found for {pair}")
                return 0.0
                
        except Exception as e:
            logger.error(f"🔧 Error syncing trade amount from position for {pair}: {e}")
            import traceback
            logger.error(f"🔧 Traceback: {traceback.format_exc()}")
            return None

    def _check_position_sync(self, current_pair: str | None = None) -> None:
        """
        Periodically check if positions are in sync with freqtrade trades.
        This helps detect manually closed positions.
        """
        current_time = time.time()
        
        # Only sync every 10 seconds to avoid excessive API calls
        if current_time - self._last_position_sync < self._position_sync_interval:
            return
            
        self._last_position_sync = current_time
        
        try:
            # If we have a specific pair being checked, prioritize it
            if current_pair:
                self._position_sync_pairs.add(current_pair)
            
            # Get all configured pairs that might have positions
            if hasattr(self._config, 'exchange') and 'pair_whitelist' in self._config['exchange']:
                whitelist = self._config['exchange']['pair_whitelist']
                self._position_sync_pairs.update(whitelist)
            
            # Check each pair for position mismatches
            for pair in list(self._position_sync_pairs):
                try:
                    position_size = self.sync_trade_amount_from_position(pair)
                    
                    if position_size == 0.0:
                        # Position was closed - freqtrade should be notified
                        logger.warning(f"🔧 POSITION SYNC: {pair} position was manually closed on exchange")
                        logger.warning(f"🔧 Freqtrade may still show this as an open trade - check your trades!")
                    elif position_size is None:
                        logger.debug(f"🔧 Position sync check failed for {pair}")
                    else:
                        logger.debug(f"🔧 Position sync OK for {pair}: {position_size} contracts")
                        
                except Exception as e:
                    logger.debug(f"🔧 Error checking position sync for {pair}: {e}")
                    
        except Exception as e:
            logger.error(f"🔧 Error in position sync check: {e}")

    @retrier_async
    async def _async_get_candle_history(
        self,
        pair: str,
        timeframe: str,
        candle_type: CandleType,
        since_ms: int | None = None,
    ) -> OHLCVResponse:
        """
        Override to handle Blofin-specific 429 errors that come as ExchangeNotAvailable.
        Blofin uses Cloudflare protection which causes CCXT to throw ExchangeNotAvailable
        instead of DDoSProtection for 429 errors.
        """
        try:
            return await super()._async_get_candle_history(pair, timeframe, candle_type, since_ms)
        except ccxt.ExchangeNotAvailable as e:
            error_msg = str(e)
            # Check if this is actually a 429 error disguised as ExchangeNotAvailable
            if "429" in error_msg or "Too Many Requests" in error_msg:
                logger.warning(
                    "🔧 Blofin 429 error detected as ExchangeNotAvailable, converting to DDosProtection: %s", 
                    error_msg
                )
                # Convert to DDosProtection so the retry mechanism can handle it properly
                raise DDosProtection(e) from e
            else:
                # If it's not a rate limit error, re-raise as is
                raise
            
    # def _convert_tpsl_order_to_standard(self, tpsl_order: dict) -> CcxtOrder:
    #     """
    #     Convert BloFin TP/SL order format to standard ccxt order format.
    #     """
    #     try:
    #         # Map BloFin TP/SL order fields to standard order format
    #         order_id = tpsl_order.get('tpslId')
            
    #         # Convert market ID back to symbol format
    #         inst_id = tpsl_order.get('instId')
    #         symbol = None
    #         for sym, market in self.markets.items():
    #             if market['id'] == inst_id:
    #                 symbol = sym
    #                 break
            
    #         if symbol is None:
    #             logger.error(f"🔧 Could not find symbol for instId: {inst_id}")
    #             raise ExchangeError(f"Could not find symbol for instId: {inst_id}")
            
    #         # Map order status
    #         status_map = {
    #             'live': 'open',
    #             'effective': 'open', 
    #             'canceled': 'canceled',
    #             'order_failed': 'rejected',
    #             'triggered': 'closed'
    #         }
    #         status = status_map.get(tpsl_order.get('state', ''), 'unknown')
            
    #         # Determine if this is a stop loss or take profit
    #         side = tpsl_order.get('side', 'sell')  # Stop loss is typically sell for long positions
    #         price = float(tpsl_order.get('slTriggerPrice', 0)) or float(tpsl_order.get('tpTriggerPrice', 0))
            
    #         converted = {
    #             'id': order_id,
    #             'info': tpsl_order,
    #             'timestamp': int(tpsl_order.get('createTime', 0)) if tpsl_order.get('createTime') else None,
    #             'datetime': self._api.iso8601(int(tpsl_order.get('createTime', 0))) if tpsl_order.get('createTime') else None,
    #             'symbol': symbol,
    #             'type': 'market',  # TP/SL orders are typically market orders when triggered
    #             'side': side,
    #             'amount': float(tpsl_order.get('size', 0)) if tpsl_order.get('size') else None,
    #             'price': price,
    #             'filled': 0.0,  # TP/SL orders are either pending or fully executed
    #             'remaining': float(tpsl_order.get('size', 0)) if tpsl_order.get('size') else None,
    #             'status': status,
    #             'fee': None,
    #             'cost': None,
    #             'trades': None,
    #             'timeInForce': None,
    #             'postOnly': None,
    #             'reduceOnly': True,  # TP/SL orders are always reduce-only
    #             'stopPrice': price,
    #         }
            
    #         return converted
            
    #     except Exception as e:
    #         logger.error(f"🔧 Error converting TP/SL order: {e}")
    #         raise

    # def cancel_stoploss_order(self, order_id: str, pair: str, params: dict | None = None) -> dict:
    #     """
    #     Custom cancel_stoploss_order for BloFin.
    #     BloFin stoploss orders are TP/SL orders and need to be canceled using cancel_tpsl endpoint.
    #     """
    #     if params is None:
    #         params = {}
            
    #     logger.info(f"🔧 Canceling BloFin stoploss order {order_id} for {pair}")
        
    #     try:
    #         # Get market ID format for BloFin
    #         market_id = self.markets[pair]['id'] if pair in self.markets else pair.replace('/', '-').replace(':USDT', '')
            
    #         # Based on testing, BloFin stoploss orders are best canceled using algo order endpoint
    #         # even though they appear in TP/SL pending list
    #         try:
    #             cancel_params = {
    #                 'algoId': order_id,
    #                 'instId': market_id,
    #             }
    #             cancel_params.update(params)
                
    #             result = self._api.private_post_trade_cancel_algo(cancel_params)
    #             logger.info(f"🔧 Canceled stoploss order {order_id} as algo order")
    #             return result
                
    #         except Exception as e:
    #             logger.warning(f"🔧 Failed to cancel as algo order: {e}")
                
    #             # Fallback: try TP/SL cancellation (though this often has JSON syntax issues)
    #             try:
    #                 cancel_params = {
    #                     'tpslIds': [order_id],  # BloFin expects tpslIds as array
    #                     'instId': market_id,
    #                 }
    #                 cancel_params.update(params)
                    
    #                 result = self._api.private_post_trade_cancel_tpsl(cancel_params)
    #                 logger.info(f"🔧 Canceled stoploss order {order_id} as TP/SL order")
    #                 return result
                    
    #             except Exception as e2:
    #                 logger.error(f"🔧 Failed to cancel order with both methods: algo={e}, tpsl={e2}")
    #                 raise
                    
    #     except Exception as e:
    #         logger.error(f"🔧 Error canceling stoploss order {order_id}: {e}")
    #         raise

    # def fetch_order_or_stoploss_order(self, order_id: str, pair: str, stoploss_order: bool = False, params: dict | None = None) -> CcxtOrder:
    #     """
    #     Custom fetch_order_or_stoploss_order for BloFin with better error handling.
    #     Handles None order IDs gracefully to prevent bot crashes.
    #     """
    #     if order_id is None:
    #         logger.warning(f"🔧 Cannot fetch order: order_id is None for {pair} (stoploss: {stoploss_order})")
    #         raise ccxt.OrderNotFound(f"Order {order_id} not found for {pair}")
            
    #     try:
    #         if stoploss_order:
    #             return self.fetch_stoploss_order(order_id, pair, params)
    #         else:
    #             return self.fetch_order(order_id, pair, params)
    #     except Exception as e:
    #         logger.warning(f"🔧 Error fetching order {order_id} for {pair}: {e}")
    #         raise

    # def _lev_prep(self, pair: str, leverage: float, side: str, accept_fail: bool = False):
    #     """
    #     Leverage preparation for BloFin.
    #     Ensures leverage is set before trades.
    #     """
    #     if self._config["dry_run"]:
    #         return

    #     logger.info("🔧 Preparing leverage for %s: %sx, side: %s", pair, leverage, side)

    #     try:
    #         # Ensure leverage is properly set for this pair
    #         self._set_leverage(leverage=leverage, pair=pair, accept_fail=accept_fail)
    #     except Exception as e:
    #         logger.error("🔧 Failed to prepare leverage for %s: %s", pair, e)
    #         if not accept_fail:
    #             raise


    # def get_margin_mode(self, pair: str) -> MarginMode:
    #     """
    #     Get current margin mode for a trading pair.
    #     """
    #     # logger.info("🔧 get_margin_mode called for pair=%s", pair)
        
    #     if self._config["dry_run"]:
    #         # In dry run, return the configured margin mode
    #         configured_mode = self._config.get("margin_mode", "cross")
    #         if configured_mode == "isolated":
    #             return MarginMode.ISOLATED
    #         else:
    #             return MarginMode.CROSS

    #     if not self.exchange_has("fetchMarginMode"):
    #         logger.warning("🔧 Exchange doesn't support fetchMarginMode, defaulting to cross")
    #         return MarginMode.CROSS

    #     try:
    #         logger.info("🔧 Fetching margin mode for %s", pair)
    #         margin_mode_data = self._api.fetch_margin_mode(symbol=pair)
            
    #         if margin_mode_data:
    #             # Parse the margin mode from the response
    #             margin_mode_str = margin_mode_data.get('marginMode', 'cross')
    #             if margin_mode_str == "isolated":
    #                 return MarginMode.ISOLATED
    #             else:
    #                 return MarginMode.CROSS
    #         else:
    #             logger.warning("🔧 No margin mode data for %s, defaulting to cross", pair)
    #             return MarginMode.CROSS
                
    #     except ccxt.BaseError as e:
    #         logger.warning("🔧 Error fetching margin mode for %s: %s, defaulting to cross", pair, e)
    #         return MarginMode.CROSS


    def dry_run_liquidation_price(
        self,
        pair: str,
        open_rate: float,
        is_short: bool,
        amount: float,
        stake_amount: float,
        leverage: float,
        wallet_balance: float,
        open_trades: list,
    ) -> float | None:
        """
        Important: Must be implemented to prevent errors in the margin mode

        Calculate the liquidation price for dry-run mode.
        In dry-run, we can return a reasonable estimate or None.
        """
        return None

    # def fetch_funding_rates(self, symbols: list[str] | None = None) -> dict[str, dict[str, float]]:
    #     """
    #     Fetch funding rates for the given symbols.
    #     :param symbols: List of symbols to fetch funding rates for
    #     :return: Dict of funding rates for the given symbols
    #     """
    #     logger.info("🔧 fetch_funding_rates called for symbols: %s", symbols)
        
    #     try:
    #         if self.trading_mode != TradingMode.FUTURES:
    #             logger.info("🔧 Not futures mode, returning empty funding rates")
    #             return {}
            
    #         if symbols is None:
    #             # If no symbols specified, use all available pairs
    #             symbols = list(self.markets.keys())
    #             logger.info("🔧 Using all available symbols: %s pairs", len(symbols))
            
    #         # BloFin supports fetchFundingRate but not fetchFundingRates (plural)
    #         # So we need to fetch each symbol individually
    #         funding_rates = {}
            
    #         for symbol in symbols:
    #             try:
    #                 logger.info("🔧 Fetching funding rate for %s", symbol)
    #                 rate_data = self._api.fetch_funding_rate(symbol)
                    
    #                 if rate_data:
    #                     funding_rates[symbol] = {
    #                         'fundingRate': rate_data.get('fundingRate', 0.0),
    #                         'fundingTimestamp': rate_data.get('fundingTimestamp'),
    #                         'nextFundingTime': rate_data.get('nextFundingTime'),
    #                         'info': rate_data.get('info', {})
    #                     }
    #                     logger.info("🔧 Got funding rate for %s: %s", symbol, rate_data.get('fundingRate', 0.0))
    #                 else:
    #                     logger.warning("🔧 No funding rate data for %s", symbol)
                        
    #             except ccxt.BaseError as e:
    #                 logger.warning("🔧 Failed to fetch funding rate for %s: %s", symbol, e)
    #                 continue
            
    #         logger.info("🔧 Successfully fetched funding rates for %s symbols", len(funding_rates))
    #         return funding_rates
            
    #     except ccxt.DDoSProtection as e:
    #         logger.warning("🔧 Rate limit exceeded when fetching funding rates")
    #         raise DDosProtection(e) from e
    #     except (ccxt.OperationFailed, ccxt.ExchangeError) as e:
    #         logger.error("🔧 Exchange error fetching funding rates: %s", e)
    #         raise TemporaryError(
    #             f"Error fetching funding rates due to {e.__class__.__name__}. Message: {e}"
    #         ) from e
    #     except ccxt.BaseError as e:
    #         logger.error("🔧 Unexpected error fetching funding rates: %s", e)
    #         raise OperationalException(e) from e

    # def fetchFundingHistory(self, symbol=None, since=None, limit=None, params={}):
    #     """
    #     Custom implementation of fetchFundingHistory for BloFin.
        
    #     BloFin's ccxt implementation reports fetchFundingHistory as supported but throws
    #     NotSupported error. This custom implementation uses the asset/bills endpoint
    #     to retrieve actual funding payments.
        
    #     Args:
    #         symbol: Trading pair symbol (e.g., 'BTC/USDT:USDT')
    #         since: Timestamp in milliseconds to start from
    #         limit: Maximum number of entries to return
    #         params: Additional parameters
            
    #     Returns:
    #         List of funding history entries with standardized format:
    #         [
    #             {
    #                 'info': {...},           # Raw API response
    #                 'symbol': 'BTC/USDT:USDT',
    #                 'code': 'USDT',
    #                 'timestamp': 1234567890000,
    #                 'datetime': '2023-01-01T00:00:00.000Z',
    #                 'id': 'bill_id',
    #                 'amount': -0.001,        # Funding fee amount (negative = paid)
    #                 'type': 'funding'
    #             }
    #         ]
    #     """
    #     logger.info("🔧 fetchFundingHistory called for %s, since: %s, limit: %s", symbol, since, limit)
        
    #     try:
    #         # BloFin uses asset/bills to get funding payments
    #         # We need to filter for funding-related bill types
    #         request_params = {}
    #         if since is not None:
    #             request_params['after'] = str(since)
    #         if limit is not None:
    #             request_params['limit'] = str(limit)
    #         else:
    #             request_params['limit'] = '100'  # Default limit
                
    #         # Get bills from BloFin
    #         response = self._api.private_get_asset_bills(request_params)
    #         bills = response.get('data', [])
            
    #         logger.info("🔧 Retrieved %s bills from BloFin", len(bills))
            
    #         # Log first few bills to understand structure
    #         if bills:
    #             logger.info("🔧 Sample bill structure: %s", bills[0])
                
    #             # Log bill types for debugging
    #             bill_types = set()
    #             account_transfers = 0
    #             instrument_bills = 0
                
    #             for bill in bills[:10]:  # Check first 10 bills
    #                 if 'type' in bill:
    #                     bill_types.add(bill['type'])
    #                 if 'fromAccount' in bill or 'toAccount' in bill:
    #                     account_transfers += 1
    #                 if 'instId' in bill and bill['instId']:
    #                     instrument_bills += 1
                
    #             logger.info("🔧 Bill analysis - Types found: %s, Account transfers: %d, Instrument bills: %d", 
    #                        list(bill_types), account_transfers, instrument_bills)
            
    #         # Filter for funding-related bills and parse them
    #         funding_history = []
    #         for bill in bills:
    #             # BloFin bills might not have a 'type' field, so check for funding indicators
    #             # Look for bills that are funding-related based on available fields
    #             is_funding_related = False
                
    #             # Check various possible indicators of funding payments
    #             if 'type' in bill:
    #                 bill_type = bill.get('type', '').lower()
    #                 is_funding_related = any(keyword in bill_type for keyword in ['funding', 'fund'])
    #             else:
    #                 # If no type field, look for other indicators
    #                 # Funding payments usually have instId (instrument) and specific patterns
    #                 has_instrument = bool(bill.get('instId'))
    #                 has_transfer_accounts = 'fromAccount' in bill or 'toAccount' in bill
                    
    #                 # Skip account transfers (funding <-> trading)
    #                 if has_transfer_accounts:
    #                     from_account = bill.get('fromAccount', '')
    #                     to_account = bill.get('toAccount', '')
    #                     if from_account in ['funding', 'trading'] or to_account in ['funding', 'trading']:
    #                         continue  # Skip account transfers
                    
    #                 # Look for funding-specific patterns
    #                 if has_instrument and not has_transfer_accounts:
    #                     # This might be a position-related bill (could include funding)
    #                     is_funding_related = True
                
    #             if is_funding_related:
    #                 inst_id = bill.get('instId', '')
    #                 if symbol is None or self.safe_symbol(inst_id) == symbol:
    #                     parsed_entry = self._parse_funding_history_entry(bill)
    #                     if parsed_entry:
    #                         funding_history.append(parsed_entry)
            
    #         logger.info("🔧 Found %s funding history entries after filtering", len(funding_history))
    #         return funding_history
            
    #     except Exception as e:
    #         logger.error("🔧 Error in custom fetchFundingHistory: %s", e)
    #         # Return empty list instead of raising exception to allow fallback
    #         return []

    # def _parse_funding_history_entry(self, bill):
    #     """Parse a bill entry into funding history format."""
    #     try:
    #         timestamp = self.safe_integer(bill, 'ts')
            
    #         # BloFin bills may use different fields for amount based on structure
    #         amount = (self.safe_float(bill, 'amount') or 
    #                  self.safe_float(bill, 'bal') or 
    #                  self.safe_float(bill, 'balChg') or 
    #                  self.safe_float(bill, 'size'))
            
    #         inst_id = bill.get('instId', '')
    #         symbol = self.safe_symbol(inst_id) if inst_id else None
            
    #         # Get currency from various possible fields
    #         currency = (bill.get('currency') or 
    #                    bill.get('ccy') or 
    #                    bill.get('settleCcy'))
            
    #         return {
    #             'info': bill,
    #             'symbol': symbol,
    #             'code': currency,
    #             'timestamp': timestamp,
    #             'datetime': self.iso8601(timestamp) if timestamp else None,
    #             'id': bill.get('transferId') or bill.get('billId') or bill.get('id'),
    #             'amount': amount,
    #             'type': bill.get('type', 'funding'),
    #         }
    #     except Exception as e:
    #         logger.warning("🔧 Error parsing funding history entry: %s", e)
    #         return None

    # def _get_funding_fees_from_exchange(
    #     self, pair: str, since: int | None
    # ) -> list[dict[str, Any]]:
    #     """
    #     Fetch funding fees from exchange using custom fetchFundingHistory.
    #     """
    #     logger.info("🔧 _get_funding_fees_from_exchange called for %s, since: %s", pair, since)
        
    #     try:
    #         # Use our custom fetchFundingHistory method directly
    #         funding_history = self.fetchFundingHistory(symbol=pair, since=since)
            
    #         if funding_history:
    #             logger.info("🔧 Found %s funding history entries for %s", len(funding_history), pair)
    #             return funding_history
    #         else:
    #             logger.info("🔧 No funding history found for %s", pair)
    #             return []
                
    #     except Exception as e:
    #         logger.warning("🔧 Error fetching funding history for %s: %s", pair, e)
    #         # Return empty list to fallback to calculation method
    #         return []
            
    #         if funding_history:
    #             logger.info("🔧 Found %s funding history entries for %s", len(funding_history), pair)
    #             return funding_history
    #         else:
    #             logger.info("🔧 No funding history found for %s", pair)
    #             return []
                
    #     except ccxt.BaseError as e:
    #         logger.warning("🔧 Error fetching funding history for %s: %s", pair, e)
    #         # Return empty list to fallback to calculation method
    #         return []


    # def fetch_my_trades(
    #     self,
    #     symbol: str | None = None,
    #     since: int | None = None,
    #     limit: int | None = None,
    #     params: dict | None = None
    # ):
    #     """
    #     Custom fetch_my_trades implementation for BloFin to handle None amounts.
    #     Also includes periodic position sync to detect manual position changes.
    #     """
    #     # Trigger periodic position sync check
    #     self._check_position_sync(symbol)
        
    #     try:
    #         trades = super().fetch_my_trades(symbol, since, limit, params)

    #         # Filter out trades with None amounts and log issues
    #         filtered_trades = []
    #         for trade in trades:
    #             if trade.get('amount') is None:
    #                 logger.warning(
    #                     "🔧 Trade with None amount found and filtered: %s",
    #                     trade.get('id', 'unknown')
    #                 )
    #                 continue
    #             if trade.get('cost') is None:
    #                 logger.warning(
    #                     "🔧 Trade with None cost found and filtered: %s",
    #                     trade.get('id', 'unknown')
    #                 )
    #                 continue

    #             # Ensure amount is a proper float
    #             try:
    #                 amount = float(trade['amount'])
    #                 trade['amount'] = amount
    #             except (ValueError, TypeError):
    #                 logger.warning(
    #                     "🔧 Trade with invalid amount found and filtered: %s",
    #                     trade.get('id', 'unknown')
    #                 )
    #                 continue

    #             filtered_trades.append(trade)

    #         if len(filtered_trades) != len(trades):
    #             logger.info(
    #                 "🔧 Filtered %d trades with invalid data out of %d total trades",
    #                 len(trades) - len(filtered_trades), len(trades)
    #             )

    #         return filtered_trades

    #     except Exception as e:
    #         logger.error("🔧 Error in fetch_my_trades: %s", e)
    #         return []
