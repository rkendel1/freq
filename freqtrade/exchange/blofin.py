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
    BloFin exchange class. Contains adjustments needed for Freqtrade to work
    with this exchange.
    """

    _ft_has: dict = {
        "stoploss_on_exchange": False,  # BloFin may not support stop-loss orders on exchange
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

    def __init__(self, config: Config, *, exchange_config: ExchangeConfig | None = None, **kwargs):
        """
        Initialize the BloFin exchange.
        """
        logger.info("Initializing BloFin exchange")
        super().__init__(config, exchange_config=exchange_config, **kwargs)

    @retrier
    def fetch_order(self, order_id: str, pair: str, params: dict | None = None) -> CcxtOrder:
        """
        Fetch order from exchange.
        BloFin doesn't have a direct fetchOrder method, so we emulate it
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
            
            # BloFin might have leverage limits, so clamp to reasonable range
            leverage_int = max(1, min(leverage_int, 100))  # Assuming max 100x leverage
            logger.info("🔧 Final leverage value after clamping: %s", leverage_int)

            logger.info("⚖️ Setting leverage for %s to %sx (from %s)", pair, leverage_int, leverage)
            res = self._api.set_leverage(symbol=pair, leverage=leverage_int)
            self._log_exchange_response("set_leverage", res)
            logger.info("🔧 Successfully set leverage for %s to %sx", pair, leverage_int)
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

    def _lev_prep(self, pair: str, leverage: float, side: str):
        """
        Leverage preparation for BloFin.
        Ensures leverage is set before trades.
        """
        if self._config["dry_run"]:
            return

        logger.info("Preparing leverage for %s: %sx, side: %s", pair, leverage, side)

        # Add delay to avoid rate limits
        time.sleep(0.5)

        try:
            # Ensure leverage is properly set for this pair
            self._set_leverage(leverage=leverage, pair=pair, accept_fail=False)

            # Add another small delay to ensure the leverage setting is processed
            time.sleep(0.2)

        except Exception as e:
            logger.error("Failed to prepare leverage for %s: %s", pair, e)
            # Don't fail the trade, but log the issue
            pass

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
        Override create_order to ensure leverage and margin mode are set before creating the order.
        """
        logger.info(
            f"🛒 create_order called: pair={pair}, side={side}, "
            f"amount={amount}, rate={rate}, leverage={leverage} (type: {type(leverage)})"
        )
        
        # Set margin mode if configured
        if self.trading_mode == TradingMode.FUTURES:
            configured_margin_mode = self._config.get("margin_mode", "cross")
            if configured_margin_mode == "isolated":
                margin_mode = MarginMode.ISOLATED
            else:
                margin_mode = MarginMode.CROSS
            
            logger.info("🔧 Setting margin mode to %s for %s", margin_mode, pair)
            self.set_margin_mode(pair=pair, margin_mode=margin_mode, accept_fail=True)
        
        # Ensure leverage is set before creating order
        if leverage and leverage > 1:
            logger.info("⚖️ Setting leverage %sx for %s before creating order", leverage, pair)
            self._set_leverage(leverage=leverage, pair=pair, accept_fail=True)
        else:
            logger.info("🛒 No leverage setting needed (leverage=%s)", leverage)

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
        
        logger.info("🛒 Order created successfully: %s", result.get('id', 'unknown_id'))
        return result

    def get_max_leverage(self, pair: str, stake_amount: float | None) -> float:
        """
        Override get_max_leverage to return reasonable BloFin limits.
        BloFin typically supports up to 100x leverage for most pairs.
        """
        logger.info("🔧 get_max_leverage called for pair=%s, stake_amount=%s", pair, stake_amount)
        
        if self.trading_mode != TradingMode.FUTURES:
            logger.info("🔧 Not futures mode, returning 1.0")
            return 1.0
        
        # For BloFin, return a reasonable max leverage
        # Most exchanges support different max leverage per pair, but for simplicity
        # we'll return a conservative 50x max leverage for all pairs
        max_leverage = 50.0
        logger.info("🔧 Returning max_leverage=%s for %s", max_leverage, pair)
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

    def _get_funding_fees_from_exchange(
        self, pair: str, since: int | None
    ) -> list[dict[str, Any]]:
        """
        Fetch funding fees from exchange using fetchFundingHistory.
        BloFin supports fetchFundingHistory so we can use it directly.
        """
        logger.info("🔧 _get_funding_fees_from_exchange called for %s, since: %s", pair, since)
        
        try:
            if not self.exchange_has("fetchFundingHistory"):
                logger.warning("🔧 Exchange doesn't support fetchFundingHistory")
                return []
            
            # Use CCXT's fetchFundingHistory method
            funding_history = self._api.fetch_funding_history(symbol=pair, since=since)
            
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