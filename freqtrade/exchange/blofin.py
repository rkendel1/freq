import logging
import time
from datetime import datetime
from typing import Any

import ccxt

from freqtrade.constants import BuySell, Config, ExchangeConfig
from freqtrade.enums import MarginMode, TradingMode
from freqtrade.exceptions import DDosProtection, OperationalException, TemporaryError, ExchangeError
from freqtrade.exchange import Exchange
from freqtrade.exchange.common import retrier
from freqtrade.exchange.exchange_types import CcxtOrder


logger = logging.getLogger(__name__)


class Blofin(Exchange):
    """
    BloFin exchange class. Contains adjustments needed for Freqtrade to work
    with this exchange.
    """

    _ft_has: dict = {
        "stoploss_on_exchange": True,  # BloFin supports stop-loss orders on exchange
        "stop_price_param": "stopLossPrice",  # BloFin uses stopLossPrice parameter
        "stop_price_prop": "stopLossPrice",  # Property name in order response
        "stoploss_order_types": {"market": "market", "limit": "limit"},  # Supported stop order types
        "ohlcv_candle_limit": 5000,
        "trades_pagination": "id",
        "trades_pagination_arg": "fromId",
        "l2_limit_range": [1, 200],
        "l2_limit_range_required": False,
    }

    _supported_trading_mode_margin_pairs = [
        (TradingMode.FUTURES, MarginMode.CROSS),
        (TradingMode.FUTURES, MarginMode.ISOLATED),
    ]

    def __init__(self, config: Config, exchange_config: ExchangeConfig | None = None, **kwargs):
        """
        Initialize BloFin exchange.
        """
        logger.info("Initializing BloFin exchange")
        self._last_funding_fee_query = {}
        # Simple cache for stoploss orders to avoid repeated API calls
        self._stoploss_cache = {}
        self._cache_timeout = 3  # seconds
        super().__init__(config, exchange_config=exchange_config, **kwargs)
        
        # Override ccxt's fetchFundingHistory with our custom implementation
        self._api.fetchFundingHistory = self._ccxt_fetch_funding_history

    def _ccxt_fetch_funding_history(self, symbol=None, since=None, limit=None, params={}):
        """
        Wrapper method to make our custom fetchFundingHistory compatible with ccxt calls.
        """
        return self.fetchFundingHistory(symbol, since, limit, params)

    def _get_stop_params(self, side: BuySell, ordertype: str, stop_price: float) -> dict:
        """
        Get stop-loss parameters for BloFin exchange.
        BloFin uses stopLossPrice as the parameter name for stop orders.
        """
        params = self._params.copy()
        
        # BloFin requires stopLossPrice parameter
        params.update({
            "stopLossPrice": stop_price,
        })
        
        # Add margin mode if trading futures
        if self.trading_mode == TradingMode.FUTURES and self.margin_mode:
            params.update({
                "tdMode": "isolated" if self.margin_mode == MarginMode.ISOLATED else "cross"
            })
        
        return params

    @retrier(retries=0)
    def create_stoploss(
        self,
        pair: str,
        amount: float,
        stop_price: float,
        order_types: dict,
        side: BuySell,
        leverage: float,
    ) -> CcxtOrder:
        """
        Custom stoploss implementation for BloFin.
        Uses BloFin's createStopLossOrder method directly to ensure proper order ID return.
        """
        from freqtrade.enums import PriceType
        from freqtrade.exceptions import InsufficientFundsError, InvalidOrderException
        import ccxt
        
        if not self._ft_has["stoploss_on_exchange"]:
            raise OperationalException(f"stoploss is not implemented for {self.name}.")

        user_order_type = order_types.get("stoploss", "market")
        ordertype, user_order_type = self._get_stop_order_type(user_order_type)
        round_mode = ccxt.ROUND_DOWN if side == "buy" else ccxt.ROUND_UP
        stop_price_norm = self.price_to_precision(pair, stop_price, rounding_mode=round_mode)
        limit_rate = None
        
        if user_order_type == "limit":
            limit_rate = self._get_stop_limit_rate(stop_price, order_types, side)
            limit_rate = self.price_to_precision(pair, limit_rate, rounding_mode=round_mode)

        if self._config["dry_run"]:
            dry_order = self.create_dry_run_order(
                pair,
                ordertype,
                side,
                amount,
                stop_price_norm,
                stop_loss=True,
                leverage=leverage,
            )
            return dry_order

        try:
            # Prepare parameters for BloFin stoploss order
            params = {}
            
            # Add reduceOnly for futures
            if self.trading_mode == TradingMode.FUTURES:
                params["reduceOnly"] = True
                
            # Add margin mode for BloFin
            if self.trading_mode == TradingMode.FUTURES and self.margin_mode:
                params["tdMode"] = "isolated" if self.margin_mode == MarginMode.ISOLATED else "cross"
                
            # Add price type if specified
            if "stoploss_price_type" in order_types and "stop_price_type_field" in self._ft_has:
                price_type = self._ft_has["stop_price_type_value_mapping"][
                    order_types.get("stoploss_price_type", PriceType.LAST)
                ]
                params[self._ft_has["stop_price_type_field"]] = price_type

            amount_precise = self.amount_to_precision(pair, self._amount_to_contracts(pair, amount))

            # Set leverage before creating stoploss
            self._lev_prep(pair, leverage, side, accept_fail=True)
            
            # Use BloFin's createStopLossOrder method directly
            logger.info(f"🔧 Creating BloFin stoploss order: {pair}, {ordertype}, {side}, amount={amount_precise}, stopPrice={stop_price_norm}, params={params}")
            
            # Try the direct method call first
            try:
                order = self._api.createStopLossOrder(
                    symbol=pair,
                    type=ordertype,
                    side=side,
                    amount=amount_precise,
                    price=limit_rate,
                    stopLossPrice=stop_price_norm,
                    params=params,
                )
                
                # Debug: Log the raw order response
                logger.info(f"🔧 BloFin raw stoploss order response: {order}")
                
                # If response is empty/None, try alternative approach
                if not order.get('id') and not order.get('info'):
                    logger.warning(f"🔧 createStopLossOrder returned empty response, trying alternative method...")
                    
                    # Try using the conditional order approach
                    alt_params = params.copy()
                    alt_params.update({
                        'stopPrice': stop_price_norm,
                        'orderType': 'conditional',
                        'triggerPrice': stop_price_norm
                    })
                    
                    order = self._api.createOrder(
                        symbol=pair,
                        type='market',  # BloFin conditional orders are usually market
                        side=side,
                        amount=amount_precise,
                        price=None,
                        params=alt_params,
                    )
                    logger.info(f"🔧 Alternative stoploss order response: {order}")
                    
            except Exception as e:
                logger.error(f"🔧 Error creating stoploss order: {e}")
                raise
            
            self._log_exchange_response("create_stoploss_order", order)
            order = self._order_contracts_to_amount(order)
            
            # Debug: Check order ID after processing
            order_id = order.get('id')
            
            # BloFin TP/SL orders might return tpslId instead of id
            if order_id is None:
                tpsl_id = order.get('tpslId') or order.get('info', {}).get('tpslId')
                if tpsl_id:
                    order['id'] = tpsl_id  # Fix the order ID
                    order_id = tpsl_id
                    logger.info(f"🔧 Fixed BloFin stoploss order ID: using tpslId {tpsl_id}")
                else:
                    # Fallback: check for algoId (compatibility)
                    algo_id = order.get('algoId') or order.get('info', {}).get('algoId')
                    if algo_id:
                        order['id'] = algo_id  # Fix the order ID
                        order_id = algo_id
                        logger.info(f"🔧 Fixed BloFin stoploss order ID: using algoId {algo_id}")
            
            logger.info(f"🔧 BloFin stoploss order ID after processing: {order_id}")
            
            if order_id is None:
                logger.error(f"🔧 BloFin stoploss order creation returned None ID: {order}")
                # Try to extract from info field - prioritize tpslId for TP/SL orders
                info = order.get('info', {})
                for id_field in ['tpslId', 'algoId', 'ordId', 'id']:
                    if info.get(id_field):
                        order['id'] = info[id_field]
                        order_id = info[id_field]
                        logger.info(f"🔧 Recovered order ID from info.{id_field}: {order_id}")
                        break
            
            logger.info(
                f"🔧 BloFin stoploss {user_order_type} order created: ID={order_id} for {pair}. "
                f"stop price: {stop_price_norm}. limit: {limit_rate}"
            )
            return order
            
        except ccxt.InsufficientFunds as e:
            raise InsufficientFundsError(
                f"Insufficient funds to create {ordertype} {side} stoploss order on market {pair}. "
                f"Tried to {side} amount {amount_precise} at rate {limit_rate} with "
                f"stop-price {stop_price_norm}. Message: {e}"
            ) from e
        except (ccxt.InvalidOrder, ccxt.BadRequest, ccxt.OperationRejected) as e:
            raise InvalidOrderException(
                f"Could not create {ordertype} {side} stoploss order on market {pair}. "
                f"Tried to {side} amount {amount_precise} at rate {limit_rate} with "
                f"stop-price {stop_price_norm}. Message: {e}"
            ) from e

    def fetch_stoploss_order(self, order_id: str, pair: str, params: dict | None = None) -> CcxtOrder:
        """
        Custom fetch_stoploss_order for BloFin.
        BloFin stores stoploss orders as TP/SL orders that can only be fetched via TP/SL endpoints.
        Note: TP/SL orders are NOT visible in algo order lists, only in TP/SL order lists.
        """
        if params is None:
            params = {}
            
        # Handle None order_id gracefully
        if order_id is None:
            logger.error(f"🔧 Cannot fetch stoploss order: order_id is None for {pair}")
            raise ccxt.OrderNotFound(f"Cannot fetch stoploss order: order_id is None for {pair}")
            
        # Check cache first to avoid repeated API calls
        import time
        cache_key = f"{order_id}_{pair}"
        current_time = time.time()
        
        if cache_key in self._stoploss_cache:
            cached_order, cache_time = self._stoploss_cache[cache_key]
            if current_time - cache_time < self._cache_timeout:
                logger.debug(f"🔧 Returning cached stoploss order {order_id}")
                return cached_order
            
        logger.debug(f"🔧 Fetching BloFin stoploss order {order_id} for {pair}")
        
        try:
            # First try regular fetch_order (might work for some order types)
            try:
                order = self.fetch_order(order_id, pair, params)
                logger.debug(f"🔧 Found stoploss order {order_id} in regular orders")
                return order
            except ccxt.OrderNotFound:
                logger.debug(f"🔧 Stoploss order {order_id} not found in regular orders, checking TP/SL orders...")
            except Exception as e:
                logger.debug(f"🔧 Error fetching from regular orders: {e}, checking TP/SL orders...")
                
            # If not found in regular orders, check TP/SL orders
            try:
                # Convert freqtrade symbol to BloFin market ID
                market = self.markets[pair]
                market_id = market['id']
                
                # First try TP/SL orders since the create response had 'tpslId'
                try:
                    market = self.markets[pair]
                    market_id = market['id']
                    
                    # Check pending TP/SL orders
                    tpsl_pending_params = {'instId': market_id}
                    tpsl_pending = self._api.private_get_trade_orders_tpsl_pending(tpsl_pending_params)
                    
                    for tpsl_order in tpsl_pending.get('data', []):
                        tpsl_id = tpsl_order.get('tpslId')
                        if tpsl_id == order_id:
                            # Convert TP/SL order to standard order format
                            converted_order = self._convert_tpsl_order_to_standard(tpsl_order)
                            # Cache the result
                            self._stoploss_cache[cache_key] = (converted_order, current_time)
                            logger.debug(f"🔧 Found stoploss order {order_id} in pending TP/SL orders")
                            return converted_order
                    
                    # Check TP/SL history if not found in pending
                    tpsl_history_params = {'instId': market_id}
                    tpsl_history = self._api.private_get_trade_orders_tpsl_history(tpsl_history_params)
                    
                    for tpsl_order in tpsl_history.get('data', []):
                        tpsl_id = tpsl_order.get('tpslId')
                        if tpsl_id == order_id:
                            # Convert TP/SL order to standard order format
                            converted_order = self._convert_tpsl_order_to_standard(tpsl_order)
                            # Cache the result
                            self._stoploss_cache[cache_key] = (converted_order, current_time)
                            logger.debug(f"🔧 Found stoploss order {order_id} in TP/SL order history")
                            return converted_order
                            
                except Exception as e:
                    logger.warning(f"🔧 Error fetching TP/SL orders: {e}")
                    
            except Exception as e:
                logger.warning(f"🔧 Error fetching TP/SL orders: {e}")
                
            # If still not found, check if position still exists
            try:
                positions = self.fetch_positions([pair])
                position = next((p for p in positions if p['symbol'] == pair), None)
                
                if position and position.get('contracts', 0) == 0:
                    # No position exists, the stoploss might have been triggered
                    logger.info(f"🔧 No position found for {pair}, stoploss may have been executed")
                    # Create a mock 'closed' order to indicate the stoploss was triggered
                    return {
                        'id': order_id,
                        'info': {'mock': True, 'reason': 'position_closed'},
                        'timestamp': None,
                        'datetime': None,
                        'symbol': pair,
                        'type': 'market',
                        'side': 'sell',
                        'amount': None,
                        'price': None,
                        'filled': None,
                        'remaining': 0,
                        'status': 'closed',
                        'fee': None,
                        'cost': None,
                        'trades': None,
                    }
            except Exception as e:
                logger.debug(f"🔧 Error checking position: {e}")
            
            # If still not found, raise OrderNotFound
            logger.info(f"🔧 Stoploss order {order_id} not found on exchange for {pair} - may have been executed or canceled")
            raise ccxt.OrderNotFound(f"Stoploss order {order_id} not found for {pair}")
            
        except ccxt.OrderNotFound:
            # Re-raise OrderNotFound without additional logging to avoid confusion
            raise
        except Exception as e:
            logger.error(f"🔧 Unexpected error fetching stoploss order {order_id}: {e}")
            raise
            
    def _convert_tpsl_order_to_standard(self, tpsl_order: dict) -> CcxtOrder:
        """
        Convert BloFin TP/SL order format to standard ccxt order format.
        """
        try:
            # Map BloFin TP/SL order fields to standard order format
            order_id = tpsl_order.get('tpslId')
            
            # Convert market ID back to symbol format
            inst_id = tpsl_order.get('instId')
            symbol = None
            for sym, market in self.markets.items():
                if market['id'] == inst_id:
                    symbol = sym
                    break
            
            if symbol is None:
                logger.error(f"🔧 Could not find symbol for instId: {inst_id}")
                raise ExchangeError(f"Could not find symbol for instId: {inst_id}")
            
            # Map order status
            status_map = {
                'live': 'open',
                'effective': 'open', 
                'canceled': 'canceled',
                'order_failed': 'rejected',
                'triggered': 'closed'
            }
            status = status_map.get(tpsl_order.get('state', ''), 'unknown')
            
            # Determine if this is a stop loss or take profit
            side = tpsl_order.get('side', 'sell')  # Stop loss is typically sell for long positions
            price = float(tpsl_order.get('slTriggerPrice', 0)) or float(tpsl_order.get('tpTriggerPrice', 0))
            
            converted = {
                'id': order_id,
                'info': tpsl_order,
                'timestamp': int(tpsl_order.get('createTime', 0)) if tpsl_order.get('createTime') else None,
                'datetime': self._api.iso8601(int(tpsl_order.get('createTime', 0))) if tpsl_order.get('createTime') else None,
                'symbol': symbol,
                'type': 'market',  # TP/SL orders are typically market orders when triggered
                'side': side,
                'amount': float(tpsl_order.get('size', 0)) if tpsl_order.get('size') else None,
                'price': price,
                'filled': 0.0,  # TP/SL orders are either pending or fully executed
                'remaining': float(tpsl_order.get('size', 0)) if tpsl_order.get('size') else None,
                'status': status,
                'fee': None,
                'cost': None,
                'trades': None,
                'timeInForce': None,
                'postOnly': None,
                'reduceOnly': True,  # TP/SL orders are always reduce-only
                'stopPrice': price,
            }
            
            return converted
            
        except Exception as e:
            logger.error(f"🔧 Error converting TP/SL order: {e}")
            raise

    def cancel_stoploss_order(self, order_id: str, pair: str, params: dict | None = None) -> dict:
        """
        Custom cancel_stoploss_order for BloFin.
        BloFin stoploss orders are TP/SL orders and need to be canceled using cancel_tpsl endpoint.
        """
        if params is None:
            params = {}
            
        logger.info(f"🔧 Canceling BloFin stoploss order {order_id} for {pair}")
        
        try:
            # Get market ID format for BloFin
            market_id = self.markets[pair]['id'] if pair in self.markets else pair.replace('/', '-').replace(':USDT', '')
            
            # Based on testing, BloFin stoploss orders are best canceled using algo order endpoint
            # even though they appear in TP/SL pending list
            try:
                cancel_params = {
                    'algoId': order_id,
                    'instId': market_id,
                }
                cancel_params.update(params)
                
                result = self._api.private_post_trade_cancel_algo(cancel_params)
                logger.info(f"🔧 Canceled stoploss order {order_id} as algo order")
                return result
                
            except Exception as e:
                logger.warning(f"🔧 Failed to cancel as algo order: {e}")
                
                # Fallback: try TP/SL cancellation (though this often has JSON syntax issues)
                try:
                    cancel_params = {
                        'tpslIds': [order_id],  # BloFin expects tpslIds as array
                        'instId': market_id,
                    }
                    cancel_params.update(params)
                    
                    result = self._api.private_post_trade_cancel_tpsl(cancel_params)
                    logger.info(f"🔧 Canceled stoploss order {order_id} as TP/SL order")
                    return result
                    
                except Exception as e2:
                    logger.error(f"🔧 Failed to cancel order with both methods: algo={e}, tpsl={e2}")
                    raise
                    
        except Exception as e:
            logger.error(f"🔧 Error canceling stoploss order {order_id}: {e}")
            raise

    def fetch_order_or_stoploss_order(self, order_id: str, pair: str, stoploss_order: bool = False, params: dict | None = None) -> CcxtOrder:
        """
        Custom fetch_order_or_stoploss_order for BloFin with better error handling.
        Handles None order IDs gracefully to prevent bot crashes.
        """
        if order_id is None:
            logger.warning(f"🔧 Cannot fetch order: order_id is None for {pair} (stoploss: {stoploss_order})")
            raise ccxt.OrderNotFound(f"Order {order_id} not found for {pair}")
            
        try:
            if stoploss_order:
                return self.fetch_stoploss_order(order_id, pair, params)
            else:
                return self.fetch_order(order_id, pair, params)
        except Exception as e:
            logger.warning(f"🔧 Error fetching order {order_id} for {pair}: {e}")
            raise

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
        For stoploss orders, we also check TP/SL orders.
        """
        if params is None:
            params = {}

        try:
            # First try to find in open orders
            open_orders = self._api.fetch_open_orders(pair, params=params)
            for order in open_orders:
                if order['id'] == order_id:
                    return order

            # If not found in open orders, try closed orders
            closed_orders = self._api.fetch_closed_orders(pair, params=params)
            for order in closed_orders:
                if order['id'] == order_id:
                    return order

            # If still not found, try to fetch as stoploss order (TP/SL orders)
            try:
                logger.debug(f"🔧 Order {order_id} not found in regular orders, checking TP/SL orders...")
                return self.fetch_stoploss_order(order_id, pair, params)
            except ccxt.OrderNotFound:
                logger.debug(f"🔧 Order {order_id} not found in TP/SL orders either")
                pass
            except Exception as e:
                logger.debug(f"🔧 Error checking TP/SL orders for {order_id}: {e}")
                pass

            # If still not found, raise an error
            raise ccxt.OrderNotFound(f"Order {order_id} not found for {pair}")

        except ccxt.BaseError as e:
            logger.error("Error fetching order %s for %s: %s", order_id, pair, e)
            raise

    def _set_leverage(
        self,
        leverage: float,
        pair: str | None = None,
        accept_fail: bool = False,
    ):
        """
        Set leverage for BloFin exchange.
        BloFin requires integer leverage values.
        """
        logger.info("🔧 _set_leverage called with leverage=%s (type: %s) for pair=%s", leverage, type(leverage), pair)
        
        if self._config["dry_run"] or not self.exchange_has("setLeverage"):
            logger.info("🔧 Skipping leverage setting: dry_run=%s, "
                       "has_setLeverage=%s", self._config['dry_run'],
                       self.exchange_has('setLeverage'))
            return

        try:
            # Ensure leverage is an integer for BloFin (this is the key fix)
            leverage_int = int(round(leverage))
            logger.info("🔧 Converting leverage %s -> %s (integer)", leverage, leverage_int)
            
            # Get margin mode for BloFin API (required parameter)
            configured_margin_mode = self._config.get("margin_mode", "cross")
            if configured_margin_mode == "isolated":
                blofin_margin_mode = "isolated"
            else:
                blofin_margin_mode = "cross"

            logger.info("⚖️ Setting leverage for %s to %sx with marginMode=%s", pair, leverage_int, blofin_margin_mode)
            # BloFin API requires marginMode to be passed in params
            params = {'marginMode': blofin_margin_mode}
            res = self._api.set_leverage(symbol=pair, leverage=leverage_int, params=params)
            self._log_exchange_response("set_leverage", res)
            logger.info("🔧 Successfully set leverage for %s to %sx with marginMode=%s", pair, leverage_int, blofin_margin_mode)
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

    def _lev_prep(self, pair: str, leverage: float, side: str, accept_fail: bool = False):
        """
        Leverage preparation for BloFin.
        Ensures leverage is set before trades.
        """
        if self._config["dry_run"]:
            return

        logger.info("🔧 Preparing leverage for %s: %sx, side: %s", pair, leverage, side)

        try:
            # Ensure leverage is properly set for this pair
            self._set_leverage(leverage=leverage, pair=pair, accept_fail=accept_fail)
        except Exception as e:
            logger.error("🔧 Failed to prepare leverage for %s: %s", pair, e)
            if not accept_fail:
                raise

    def set_margin_mode(self, pair: str, margin_mode: MarginMode, accept_fail: bool = False):
        """
        Set margin mode for BloFin exchange.
        """
        logger.info("🔧 set_margin_mode called: pair=%s, margin_mode=%s", pair, margin_mode)
        
        if self._config["dry_run"]:
            logger.info("🔧 Dry run mode, skipping margin mode setting")
            return

        if not self.exchange_has("setMarginMode"):
            logger.warning("🔧 Exchange doesn't support setMarginMode")
            return

        try:
            # Convert freqtrade MarginMode to BloFin margin mode string
            if margin_mode == MarginMode.ISOLATED:
                blofin_margin_mode = "isolated"
            elif margin_mode == MarginMode.CROSS:
                blofin_margin_mode = "cross"
            else:
                logger.error("🔧 Unsupported margin mode: %s", margin_mode)
                if not accept_fail:
                    raise OperationalException(f"Unsupported margin mode: {margin_mode}")
                return

            logger.info("🔧 Setting margin mode for %s to %s", pair, blofin_margin_mode)
            res = self._api.set_margin_mode(symbol=pair, marginMode=blofin_margin_mode)
            self._log_exchange_response("set_margin_mode", res)
            logger.info("🔧 Successfully set margin mode for %s to %s", pair, blofin_margin_mode)
                        
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

    def get_margin_mode(self, pair: str) -> MarginMode:
        """
        Get current margin mode for a trading pair.
        """
        logger.info("🔧 get_margin_mode called for pair=%s", pair)
        
        if self._config["dry_run"]:
            # In dry run, return the configured margin mode
            configured_mode = self._config.get("margin_mode", "cross")
            if configured_mode == "isolated":
                return MarginMode.ISOLATED
            else:
                return MarginMode.CROSS

        if not self.exchange_has("fetchMarginMode"):
            logger.warning("🔧 Exchange doesn't support fetchMarginMode, defaulting to cross")
            return MarginMode.CROSS

        try:
            logger.info("🔧 Fetching margin mode for %s", pair)
            margin_mode_data = self._api.fetch_margin_mode(symbol=pair)
            
            if margin_mode_data:
                # Parse the margin mode from the response
                margin_mode_str = margin_mode_data.get('marginMode', 'cross')
                if margin_mode_str == "isolated":
                    return MarginMode.ISOLATED
                else:
                    return MarginMode.CROSS
            else:
                logger.warning("🔧 No margin mode data for %s, defaulting to cross", pair)
                return MarginMode.CROSS
                
        except ccxt.BaseError as e:
            logger.warning("🔧 Error fetching margin mode for %s: %s, defaulting to cross", pair, e)
            return MarginMode.CROSS

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
        """
        # Get base parameters from parent
        params = super()._get_params(side, ordertype, leverage, reduceOnly, time_in_force)
        
        # Add BloFin-specific parameters for futures trading
        if self.trading_mode == TradingMode.FUTURES:
            # Add margin mode parameter
            configured_margin_mode = self._config.get("margin_mode", "cross")
            if configured_margin_mode == "isolated":
                blofin_margin_mode = "isolated"
            else:
                blofin_margin_mode = "cross"
            
            params['marginMode'] = blofin_margin_mode
            logger.info("🛒 Adding marginMode=%s to order parameters", blofin_margin_mode)
            
            # # Add leverage parameter if leverage > 1
            # if leverage and leverage > 1:
            #     # Ensure leverage is an integer for BloFin
            #     leverage_int = int(round(leverage))
            #     leverage_int = max(1, min(leverage_int, 100))  # Clamp to reasonable range
            #     params['leverage'] = leverage_int
            #     logger.info("🛒 Adding leverage=%s to order parameters", leverage_int)
        
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
        """
        logger.info(
            f"🛒 create_order called: pair={pair}, side={side}, "
            f"amount={amount}, rate={rate}, leverage={leverage} (type: {type(leverage)})"
        )
        
        # Ensure leverage is set before creating order
        if leverage and leverage > 1:
            logger.info("⚖️ Setting leverage %sx for %s before creating order", leverage, pair)
            self._set_leverage(leverage=leverage, pair=pair, accept_fail=True)
        else:
            logger.info("🛒 No leverage setting needed (leverage=%s)", leverage)

        # Call parent create_order method - margin mode will be added via _get_params()
        result = super().create_order(
            pair=pair,
            ordertype=ordertype,
            side=side,
            amount=amount,
            rate=rate,
            leverage=leverage,
            reduceOnly=reduceOnly,
            time_in_force=time_in_force,
        )
        
        logger.info("🛒 Order created successfully: %s", result.get('id', 'unknown_id'))
        return result

    def get_max_leverage(self, pair: str, stake_amount: float | None) -> float:
        """
        Get maximum leverage for a trading pair from BloFin.
        Tries to fetch real leverage limits, falls back to conservative defaults.
        """
        logger.info("🔧 get_max_leverage called for pair=%s, stake_amount=%s", pair, stake_amount)
        
        if self.trading_mode != TradingMode.FUTURES:
            logger.info("🔧 Not futures mode, returning 1.0")
            return 1.0
        
        # First check if we have leverage tiers loaded
        if hasattr(self, '_leverage_tiers') and pair in self._leverage_tiers:
            logger.info("🔧 Using cached leverage tiers for %s", pair)
            return super().get_max_leverage(pair, stake_amount)
        
        # Try to fetch leverage information directly from BloFin
        try:
            logger.info("🔧 Attempting to fetch leverage info for %s from BloFin", pair)
            
            # Method 1: Try fetchMarketLeverageTiers if supported
            if self.exchange_has("fetchMarketLeverageTiers"):
                logger.info("🔧 Fetching market leverage tiers for %s", pair)
                tiers = self._api.fetch_market_leverage_tiers(pair)
                if tiers:
                    # Extract max leverage from tiers
                    max_leverage = max(tier.get('maxLeverage', 1.0) for tier in tiers)
                    logger.info("🔧 Found max leverage %s for %s from market tiers", max_leverage, pair)
                    return float(max_leverage)
            
            # Method 2: Try fetchLeverageTiers if supported
            if self.exchange_has("fetchLeverageTiers"):
                logger.info("🔧 Fetching all leverage tiers from BloFin")
                all_tiers = self._api.fetch_leverage_tiers()
                if pair in all_tiers:
                    pair_tiers = all_tiers[pair]
                    max_leverage = max(tier.get('maxLeverage', 1.0) for tier in pair_tiers)
                    logger.info("🔧 Found max leverage %s for %s from leverage tiers", max_leverage, pair)
                    return float(max_leverage)
            
            # Method 3: Check market limits
            if pair in self.markets:
                market = self.markets[pair]
                if 'limits' in market and 'leverage' in market['limits']:
                    leverage_limit = market['limits']['leverage']
                    if leverage_limit and 'max' in leverage_limit and leverage_limit['max']:
                        max_leverage = float(leverage_limit['max'])
                        logger.info("🔧 Found max leverage %s for %s from market limits", max_leverage, pair)
                        return max_leverage
            
            # Method 4: Try to get from market info
            if pair in self.markets:
                market = self.markets[pair]
                if 'info' in market and market['info']:
                    market_info = market['info']
                    # Look for common leverage fields in market info
                    for field in ['maxLeverage', 'max_leverage', 'leverageMax', 'leverage_max']:
                        if field in market_info and market_info[field]:
                            max_leverage = float(market_info[field])
                            logger.info("🔧 Found max leverage %s for %s from market info field %s", 
                                       max_leverage, pair, field)
                            return max_leverage
                            
        except Exception as e:
            logger.warning("🔧 Failed to fetch leverage info for %s: %s", pair, e)
        
        # Fallback: Return reasonable defaults based on pair type
        if pair in self.markets:
            market = self.markets[pair]
            base_currency = market.get('base', '').upper()
            
            # Higher leverage for major pairs, lower for altcoins
            if base_currency in ['BTC', 'ETH', 'BNB']:
                max_leverage = 100.0
                logger.info("🔧 Using major pair default leverage %s for %s", max_leverage, pair)
            elif base_currency in ['ADA', 'SOL', 'AVAX', 'MATIC', 'DOT', 'LINK']:
                max_leverage = 75.0
                logger.info("🔧 Using popular altcoin default leverage %s for %s", max_leverage, pair)
            else:
                max_leverage = 50.0
                logger.info("🔧 Using conservative default leverage %s for %s", max_leverage, pair)
        else:
            max_leverage = 20.0
            logger.info("🔧 Using ultra-conservative default leverage %s for unknown pair %s", max_leverage, pair)
        
        return max_leverage

    def load_leverage_tiers(self) -> dict[str, list[dict]]:
        """
        Load leverage tiers from BloFin if supported.
        """
        if self.trading_mode != TradingMode.FUTURES:
            return {}
            
        logger.info("🔧 Loading leverage tiers from BloFin")
        
        try:
            # Try to use parent implementation first
            if self.exchange_has("fetchLeverageTiers") or self.exchange_has("fetchMarketLeverageTiers"):
                logger.info("🔧 BloFin supports leverage tiers, using parent implementation")
                return super().load_leverage_tiers()
            else:
                logger.info("🔧 BloFin doesn't support leverage tiers API, returning empty dict")
                return {}
                
        except Exception as e:
            logger.warning("🔧 Failed to load leverage tiers from BloFin: %s", e)
            return {}

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

    def fetch_funding_rates(self, symbols: list[str] | None = None) -> dict[str, dict[str, float]]:
        """
        Fetch funding rates for the given symbols.
        :param symbols: List of symbols to fetch funding rates for
        :return: Dict of funding rates for the given symbols
        """
        logger.info("🔧 fetch_funding_rates called for symbols: %s", symbols)
        
        try:
            if self.trading_mode != TradingMode.FUTURES:
                logger.info("🔧 Not futures mode, returning empty funding rates")
                return {}
            
            if symbols is None:
                # If no symbols specified, use all available pairs
                symbols = list(self.markets.keys())
                logger.info("🔧 Using all available symbols: %s pairs", len(symbols))
            
            # BloFin supports fetchFundingRate but not fetchFundingRates (plural)
            # So we need to fetch each symbol individually
            funding_rates = {}
            
            for symbol in symbols:
                try:
                    logger.info("🔧 Fetching funding rate for %s", symbol)
                    rate_data = self._api.fetch_funding_rate(symbol)
                    
                    if rate_data:
                        funding_rates[symbol] = {
                            'fundingRate': rate_data.get('fundingRate', 0.0),
                            'fundingTimestamp': rate_data.get('fundingTimestamp'),
                            'nextFundingTime': rate_data.get('nextFundingTime'),
                            'info': rate_data.get('info', {})
                        }
                        logger.info("🔧 Got funding rate for %s: %s", symbol, rate_data.get('fundingRate', 0.0))
                    else:
                        logger.warning("🔧 No funding rate data for %s", symbol)
                        
                except ccxt.BaseError as e:
                    logger.warning("🔧 Failed to fetch funding rate for %s: %s", symbol, e)
                    continue
            
            logger.info("🔧 Successfully fetched funding rates for %s symbols", len(funding_rates))
            return funding_rates
            
        except ccxt.DDoSProtection as e:
            logger.warning("🔧 Rate limit exceeded when fetching funding rates")
            raise DDosProtection(e) from e
        except (ccxt.OperationFailed, ccxt.ExchangeError) as e:
            logger.error("🔧 Exchange error fetching funding rates: %s", e)
            raise TemporaryError(
                f"Error fetching funding rates due to {e.__class__.__name__}. Message: {e}"
            ) from e
        except ccxt.BaseError as e:
            logger.error("🔧 Unexpected error fetching funding rates: %s", e)
            raise OperationalException(e) from e

    def fetchFundingHistory(self, symbol=None, since=None, limit=None, params={}):
        """
        Custom implementation of fetchFundingHistory for BloFin.
        
        BloFin's ccxt implementation reports fetchFundingHistory as supported but throws
        NotSupported error. This custom implementation uses the asset/bills endpoint
        to retrieve actual funding payments.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT:USDT')
            since: Timestamp in milliseconds to start from
            limit: Maximum number of entries to return
            params: Additional parameters
            
        Returns:
            List of funding history entries with standardized format:
            [
                {
                    'info': {...},           # Raw API response
                    'symbol': 'BTC/USDT:USDT',
                    'code': 'USDT',
                    'timestamp': 1234567890000,
                    'datetime': '2023-01-01T00:00:00.000Z',
                    'id': 'bill_id',
                    'amount': -0.001,        # Funding fee amount (negative = paid)
                    'type': 'funding'
                }
            ]
        """
        logger.info("🔧 fetchFundingHistory called for %s, since: %s, limit: %s", symbol, since, limit)
        
        try:
            # BloFin uses asset/bills to get funding payments
            # We need to filter for funding-related bill types
            request_params = {}
            if since is not None:
                request_params['after'] = str(since)
            if limit is not None:
                request_params['limit'] = str(limit)
            else:
                request_params['limit'] = '100'  # Default limit
                
            # Get bills from BloFin
            response = self._api.private_get_asset_bills(request_params)
            bills = response.get('data', [])
            
            logger.info("🔧 Retrieved %s bills from BloFin", len(bills))
            
            # Log first few bills to understand structure
            if bills:
                logger.info("🔧 Sample bill structure: %s", bills[0])
                
                # Log bill types for debugging
                bill_types = set()
                account_transfers = 0
                instrument_bills = 0
                
                for bill in bills[:10]:  # Check first 10 bills
                    if 'type' in bill:
                        bill_types.add(bill['type'])
                    if 'fromAccount' in bill or 'toAccount' in bill:
                        account_transfers += 1
                    if 'instId' in bill and bill['instId']:
                        instrument_bills += 1
                
                logger.info("🔧 Bill analysis - Types found: %s, Account transfers: %d, Instrument bills: %d", 
                           list(bill_types), account_transfers, instrument_bills)
            
            # Filter for funding-related bills and parse them
            funding_history = []
            for bill in bills:
                # BloFin bills might not have a 'type' field, so check for funding indicators
                # Look for bills that are funding-related based on available fields
                is_funding_related = False
                
                # Check various possible indicators of funding payments
                if 'type' in bill:
                    bill_type = bill.get('type', '').lower()
                    is_funding_related = any(keyword in bill_type for keyword in ['funding', 'fund'])
                else:
                    # If no type field, look for other indicators
                    # Funding payments usually have instId (instrument) and specific patterns
                    has_instrument = bool(bill.get('instId'))
                    has_transfer_accounts = 'fromAccount' in bill or 'toAccount' in bill
                    
                    # Skip account transfers (funding <-> trading)
                    if has_transfer_accounts:
                        from_account = bill.get('fromAccount', '')
                        to_account = bill.get('toAccount', '')
                        if from_account in ['funding', 'trading'] or to_account in ['funding', 'trading']:
                            continue  # Skip account transfers
                    
                    # Look for funding-specific patterns
                    if has_instrument and not has_transfer_accounts:
                        # This might be a position-related bill (could include funding)
                        is_funding_related = True
                
                if is_funding_related:
                    inst_id = bill.get('instId', '')
                    if symbol is None or self.safe_symbol(inst_id) == symbol:
                        parsed_entry = self._parse_funding_history_entry(bill)
                        if parsed_entry:
                            funding_history.append(parsed_entry)
            
            logger.info("🔧 Found %s funding history entries after filtering", len(funding_history))
            return funding_history
            
        except Exception as e:
            logger.error("🔧 Error in custom fetchFundingHistory: %s", e)
            # Return empty list instead of raising exception to allow fallback
            return []

    def _parse_funding_history_entry(self, bill):
        """Parse a bill entry into funding history format."""
        try:
            timestamp = self.safe_integer(bill, 'ts')
            
            # BloFin bills may use different fields for amount based on structure
            amount = (self.safe_float(bill, 'amount') or 
                     self.safe_float(bill, 'bal') or 
                     self.safe_float(bill, 'balChg') or 
                     self.safe_float(bill, 'size'))
            
            inst_id = bill.get('instId', '')
            symbol = self.safe_symbol(inst_id) if inst_id else None
            
            # Get currency from various possible fields
            currency = (bill.get('currency') or 
                       bill.get('ccy') or 
                       bill.get('settleCcy'))
            
            return {
                'info': bill,
                'symbol': symbol,
                'code': currency,
                'timestamp': timestamp,
                'datetime': self.iso8601(timestamp) if timestamp else None,
                'id': bill.get('transferId') or bill.get('billId') or bill.get('id'),
                'amount': amount,
                'type': bill.get('type', 'funding'),
            }
        except Exception as e:
            logger.warning("🔧 Error parsing funding history entry: %s", e)
            return None

    def _get_funding_fees_from_exchange(
        self, pair: str, since: int | None
    ) -> list[dict[str, Any]]:
        """
        Fetch funding fees from exchange using custom fetchFundingHistory.
        """
        logger.info("🔧 _get_funding_fees_from_exchange called for %s, since: %s", pair, since)
        
        try:
            # Use our custom fetchFundingHistory method directly
            funding_history = self.fetchFundingHistory(symbol=pair, since=since)
            
            if funding_history:
                logger.info("🔧 Found %s funding history entries for %s", len(funding_history), pair)
                return funding_history
            else:
                logger.info("🔧 No funding history found for %s", pair)
                return []
                
        except Exception as e:
            logger.warning("🔧 Error fetching funding history for %s: %s", pair, e)
            # Return empty list to fallback to calculation method
            return []
            
            if funding_history:
                logger.info("🔧 Found %s funding history entries for %s", len(funding_history), pair)
                return funding_history
            else:
                logger.info("🔧 No funding history found for %s", pair)
                return []
                
        except ccxt.BaseError as e:
            logger.warning("🔧 Error fetching funding history for %s: %s", pair, e)
            # Return empty list to fallback to calculation method
            return []

    def get_funding_fees(
        self, pair: str, amount: float, is_short: bool, open_date: datetime
    ) -> float:
        """
        Calculate funding fees for a position.
        Enhanced to use funding rate history when funding history is not available.
        """
        logger.info("🔧 get_funding_fees called for %s, amount: %s, is_short: %s", pair, amount, is_short)
        
        try:
            # Try to get funding fees from exchange first
            since_timestamp = int(open_date.timestamp() * 1000)  # Convert to milliseconds
            funding_history = self._get_funding_fees_from_exchange(pair, since_timestamp)
            
            if funding_history:
                # Calculate actual funding fees from exchange data
                total_funding = 0.0
                for entry in funding_history:
                    funding_amount = entry.get('amount', 0.0)
                    if funding_amount:
                        total_funding += funding_amount
                
                logger.info("🔧 Calculated funding fees from exchange: %s", total_funding)
                return total_funding
            else:
                # Fallback to calculation using funding rate history
                logger.info("🔧 Funding history not available, trying funding rate history...")
                try:
                    # Use fetchFundingRateHistory which BloFin supports
                    rate_history = self._api.fetch_funding_rate_history(pair, since=since_timestamp, limit=100)
                    
                    if rate_history:
                        logger.info("🔧 Found %s funding rate entries for calculation", len(rate_history))
                        
                        # Calculate funding fees from rate history
                        total_funding = 0.0
                        position_notional = amount  # Assuming amount is in quote currency (USDT)
                        
                        for rate_entry in rate_history:
                            funding_rate = rate_entry.get('fundingRate', 0.0)
                            if funding_rate:
                                # Funding fee = position_notional * funding_rate
                                # Long positions pay when funding rate is positive
                                # Short positions receive when funding rate is positive
                                fee = position_notional * funding_rate
                                if is_short:
                                    fee = -fee  # Short positions have opposite fee direction
                                total_funding += fee
                                
                        logger.info("🔧 Calculated funding fees from rate history: %s", total_funding)
                        return total_funding
                    else:
                        logger.info("🔧 No funding rate history available either")
                        return 0.0
                        
                except ccxt.BaseError as e:
                    logger.warning("🔧 Error fetching funding rate history: %s", e)
                    return 0.0
                
        except Exception as e:
            logger.warning("🔧 Error calculating funding fees for %s: %s", pair, e)
            # Fallback to 0.0 to avoid breaking trades
            return 0.0