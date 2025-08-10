import logging
import time
from datetime import datetime
from typing import Any

import ccxt

from freqtrade.constants import Config, ExchangeConfig
from freqtrade.enums import MarginMode, TradingMode
from freqtrade.exceptions import DDosProtection, OperationalException, TemporaryError
from freqtrade.exchange import Exchange
from freqtrade.exchange.common import retrier
from freqtrade.exchange.exchange_types import CcxtOrder


logger = logging.getLogger(__name__)


class Blofin(Exchange):
    """
    Blofin exchange class. Contains adjustments needed for Freqtrade to work
    with this exchange.
    """

    _ft_has: dict = {
        "stoploss_on_exchange": False,  # Blofin may not support stop-loss orders on exchange
        "ohlcv_candle_limit": 5000,
        "trades_pagination": "id",
        "trades_pagination_arg": "fromId",
        "l2_limit_range": [1, 200],
        "l2_limit_range_required": False,
    }

    _supported_trading_mode_margin_pairs = [
        (TradingMode.FUTURES, MarginMode.CROSS),
    ]

    def __init__(self, config: Config, *, exchange_config: ExchangeConfig | None = None, **kwargs):
        """
        Initialize the Blofin exchange.
        """
        logger.info("Initializing Blofin exchange")
        super().__init__(config, exchange_config=exchange_config, **kwargs)

    @retrier
    def fetch_order(self, order_id: str, pair: str, params: dict | None = None) -> CcxtOrder:
        """
        Fetch order from exchange.
        Blofin doesn't have a direct fetchOrder method, so we emulate it
        using fetchOpenOrders and fetchClosedOrders.
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

            # If still not found, raise an error
            raise ccxt.OrderNotFound(f"Order {order_id} not found for {pair}")

        except ccxt.BaseError as e:
            logger.error(f"Error fetching order {order_id} for {pair}: {e}")
            raise

    def _set_leverage(
        self,
        leverage: float,
        pair: str | None = None,
        accept_fail: bool = False,
    ):
        """
        Set leverage for blofin exchange.
        Blofin requires integer leverage values.
        """
        logger.info(f"🔧 _set_leverage called with leverage={leverage} (type: {type(leverage)}) for pair={pair}")
        
        if self._config["dry_run"] or not self.exchange_has("setLeverage"):
            logger.info(f"🔧 Skipping leverage setting: dry_run={self._config['dry_run']}, "
                       f"has_setLeverage={self.exchange_has('setLeverage')}")
            return

        try:
            # Ensure leverage is an integer for blofin (this is the key fix)
            leverage_int = int(round(leverage))
            logger.info(f"🔧 Converting leverage {leverage} -> {leverage_int} (integer)")
            
            # Blofin might have leverage limits, so clamp to reasonable range
            leverage_int = max(1, min(leverage_int, 100))  # Assuming max 100x leverage
            logger.info(f"🔧 Final leverage value after clamping: {leverage_int}")

            logger.info(f"� Setting leverage for {pair} to {leverage_int}x (from {leverage})")
            res = self._api.set_leverage(symbol=pair, leverage=leverage_int)
            self._log_exchange_response("set_leverage", res)
            logger.info(f"🔧 Successfully set leverage for {pair} to {leverage_int}x")
        except ccxt.DDoSProtection as e:
            logger.warning(f"🔧 Rate limit exceeded when setting leverage for {pair}")
            raise DDosProtection(e) from e
        except (ccxt.BadRequest, ccxt.OperationRejected, ccxt.InsufficientFunds) as e:
            logger.error(f"🔧 Failed to set leverage for {pair}: {e}")
            if not accept_fail:
                raise TemporaryError(
                    f"Could not set leverage due to {e.__class__.__name__}. Message: {e}"
                ) from e
        except ccxt.BaseError as e:
            logger.error(f"🔧 Unexpected error setting leverage for {pair}: {e}")
            if not accept_fail:
                raise OperationalException(e) from e

    def _lev_prep(self, pair: str, leverage: float, side: str):
        """
        Leverage preparation for blofin.
        Ensures leverage is set before trades.
        """
        if self._config["dry_run"]:
            return

        logger.info(f"Preparing leverage for {pair}: {leverage}x, side: {side}")

        # Add delay to avoid rate limits
        time.sleep(0.5)

        try:
            # Ensure leverage is properly set for this pair
            self._set_leverage(leverage=leverage, pair=pair, accept_fail=False)

            # Add another small delay to ensure the leverage setting is processed
            time.sleep(0.2)

        except Exception as e:
            logger.error(f"Failed to prepare leverage for {pair}: {e}")
            # Don't fail the trade, but log the issue
            pass

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
        """
        logger.info(
            f"🛒 create_order called: pair={pair}, side={side}, "
            f"amount={amount}, rate={rate}, leverage={leverage} (type: {type(leverage)})"
        )
        
        # Ensure leverage is set before creating order
        if leverage and leverage > 1:
            logger.info(f"� Setting leverage {leverage}x for {pair} before creating order")
            self._set_leverage(leverage=leverage, pair=pair, accept_fail=True)
        else:
            logger.info(f"🛒 No leverage setting needed (leverage={leverage})")

        # Call parent create_order method with exact signature
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
        
        logger.info(f"🛒 Order created successfully: {result.get('id', 'unknown_id')}")
        return result

    def get_max_leverage(self, pair: str, stake_amount: float | None) -> float:
        """
        Override get_max_leverage to return reasonable blofin limits.
        Blofin typically supports up to 100x leverage for most pairs.
        """
        logger.info(f"🔧 get_max_leverage called for pair={pair}, stake_amount={stake_amount}")
        
        if self.trading_mode != TradingMode.FUTURES:
            logger.info(f"🔧 Not futures mode, returning 1.0")
            return 1.0
        
        # For blofin, return a reasonable max leverage
        # Most exchanges support different max leverage per pair, but for simplicity
        # we'll return a conservative 50x max leverage for all pairs
        max_leverage = 50.0
        logger.info(f"🔧 Returning max_leverage={max_leverage} for {pair}")
        return max_leverage

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
        logger.info(f"🔧 fetch_funding_rates called for symbols: {symbols}")
        
        try:
            if self.trading_mode != TradingMode.FUTURES:
                logger.info("🔧 Not futures mode, returning empty funding rates")
                return {}
            
            if symbols is None:
                # If no symbols specified, use all available pairs
                symbols = list(self.markets.keys())
                logger.info(f"🔧 Using all available symbols: {len(symbols)} pairs")
            
            # Blofin supports fetchFundingRate but not fetchFundingRates (plural)
            # So we need to fetch each symbol individually
            funding_rates = {}
            
            for symbol in symbols:
                try:
                    logger.info(f"🔧 Fetching funding rate for {symbol}")
                    rate_data = self._api.fetch_funding_rate(symbol)
                    
                    if rate_data:
                        funding_rates[symbol] = {
                            'fundingRate': rate_data.get('fundingRate', 0.0),
                            'fundingTimestamp': rate_data.get('fundingTimestamp'),
                            'nextFundingTime': rate_data.get('nextFundingTime'),
                            'info': rate_data.get('info', {})
                        }
                        logger.info(f"🔧 Got funding rate for {symbol}: {rate_data.get('fundingRate', 0.0)}")
                    else:
                        logger.warning(f"🔧 No funding rate data for {symbol}")
                        
                except ccxt.BaseError as e:
                    logger.warning(f"🔧 Failed to fetch funding rate for {symbol}: {e}")
                    continue
            
            logger.info(f"🔧 Successfully fetched funding rates for {len(funding_rates)} symbols")
            return funding_rates
            
        except ccxt.DDoSProtection as e:
            logger.warning("🔧 Rate limit exceeded when fetching funding rates")
            raise DDosProtection(e) from e
        except (ccxt.OperationFailed, ccxt.ExchangeError) as e:
            logger.error(f"🔧 Exchange error fetching funding rates: {e}")
            raise TemporaryError(
                f"Error fetching funding rates due to {e.__class__.__name__}. Message: {e}"
            ) from e
        except ccxt.BaseError as e:
            logger.error(f"🔧 Unexpected error fetching funding rates: {e}")
            raise OperationalException(e) from e

    def _get_funding_fees_from_exchange(
        self, pair: str, since: int | None
    ) -> list[dict[str, Any]]:
        """
        Fetch funding fees from exchange using fetchFundingHistory.
        Blofin supports fetchFundingHistory so we can use it directly.
        """
        logger.info(f"🔧 _get_funding_fees_from_exchange called for {pair}, since: {since}")
        
        try:
            if not self.exchange_has("fetchFundingHistory"):
                logger.warning("🔧 Exchange doesn't support fetchFundingHistory")
                return []
            
            # Use CCXT's fetchFundingHistory method
            funding_history = self._api.fetch_funding_history(symbol=pair, since=since)
            
            if funding_history:
                logger.info(f"🔧 Found {len(funding_history)} funding history entries for {pair}")
                return funding_history
            else:
                logger.info(f"🔧 No funding history found for {pair}")
                return []
                
        except ccxt.BaseError as e:
            logger.warning(f"🔧 Error fetching funding history for {pair}: {e}")
            # Return empty list to fallback to calculation method
            return []

    def get_funding_fees(
        self, pair: str, amount: float, is_short: bool, open_date: datetime
    ) -> float:
        """
        Calculate funding fees for a position.
        Enhanced to use funding rate history when funding history is not available.
        """
        logger.info(f"🔧 get_funding_fees called for {pair}, amount: {amount}, is_short: {is_short}")
        
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
                
                logger.info(f"🔧 Calculated funding fees from exchange: {total_funding}")
                return total_funding
            else:
                # Fallback to calculation using funding rate history
                logger.info(f"🔧 Funding history not available, trying funding rate history...")
                try:
                    # Use fetchFundingRateHistory which blofin supports
                    rate_history = self._api.fetch_funding_rate_history(pair, since=since_timestamp, limit=100)
                    
                    if rate_history:
                        logger.info(f"🔧 Found {len(rate_history)} funding rate entries for calculation")
                        
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
                                
                        logger.info(f"🔧 Calculated funding fees from rate history: {total_funding}")
                        return total_funding
                    else:
                        logger.info(f"🔧 No funding rate history available either")
                        return 0.0
                        
                except ccxt.BaseError as e:
                    logger.warning(f"🔧 Error fetching funding rate history: {e}")
                    return 0.0
                
        except Exception as e:
            logger.warning(f"🔧 Error calculating funding fees for {pair}: {e}")
            # Fallback to 0.0 to avoid breaking trades
            return 0.0
