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
        logger.info(
            f"🔧 _set_leverage called: leverage={leverage}, pair={pair}, "
            f"dry_run={self._config['dry_run']}"
        )
        
        if self._config["dry_run"] or not self.exchange_has("setLeverage"):
            logger.info(f"Skipping leverage setting: dry_run={self._config['dry_run']}, "
                       f"has_setLeverage={self.exchange_has('setLeverage')}")
            return

        try:
            # Ensure leverage is an integer for blofin (this is the key fix)
            leverage_int = round(leverage)
            # Blofin might have leverage limits, so clamp to reasonable range
            leverage_int = max(1, min(leverage_int, 100))  # Assuming max 100x leverage

            logger.info(f"🚀 Setting leverage for {pair} to {leverage_int}x (from {leverage})")
            res = self._api.set_leverage(symbol=pair, leverage=leverage_int)
            self._log_exchange_response("set_leverage", res)
            logger.info(f"✅ Successfully set leverage for {pair} to {leverage_int}x")
        except ccxt.DDoSProtection as e:
            logger.warning(f"Rate limit exceeded when setting leverage for {pair}")
            raise DDosProtection(e) from e
        except (ccxt.BadRequest, ccxt.OperationRejected, ccxt.InsufficientFunds) as e:
            logger.error(f"❌ Failed to set leverage for {pair}: {e}")
            if not accept_fail:
                raise TemporaryError(
                    f"Could not set leverage due to {e.__class__.__name__}. Message: {e}"
                ) from e
        except ccxt.BaseError as e:
            logger.error(f"❌ Unexpected error setting leverage for {pair}: {e}")
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
        pair: str,
        ordertype: str,
        side: str,
        amount: float,
        rate: float,
        leverage: float = 1.0,
        reduceOnly: bool = False,
        time_in_force: str = 'GTC',
        params: dict | None = None,
    ) -> dict:
        """
        Create an order on the exchange.
        Override to ensure leverage is set before creating the order.
        """
        logger.info(
            f"🛒 create_order called: pair={pair}, side={side}, amount={amount}, "
            f"rate={rate}, leverage={leverage}"
        )

        # Set leverage before creating the order if leverage is specified
        if leverage and leverage > 1.0:
            logger.info(f"🔧 Setting leverage {leverage}x for {pair} before creating order")
            self._set_leverage(leverage=leverage, pair=pair, accept_fail=True)

        # Call the parent create_order method
        return super().create_order(
            pair=pair,
            ordertype=ordertype,
            side=side,
            amount=amount,
            rate=rate,
            leverage=leverage,
            reduceOnly=reduceOnly,
            time_in_force=time_in_force,
            params=params,
        )

    def dry_run_liquidation_price(
        self,
        pair: str,
        open_rate: float,
        is_short: bool,
        amount: float,
        stake_amount: float,
        leverage: float,
        wallet_balance: float,
    ) -> float | None:
        """
        Important: Must be implemented to prevent errors in the margin mode

        Calculate the liquidation price for dry-run mode.
        In dry-run, we can return a reasonable estimate or None.
        """
        return None

    def _get_funding_fees_from_exchange(
        self, pair: str, since: int | None
    ) -> list[dict[str, Any]]:
        """
        Fetch funding fees from exchange.
        Blofin might not support funding fee history - return empty list for now.
        """
        # Return empty list - freqtrade will handle this gracefully
        # This prevents the TypeError when trying to add int + list
        return []

    def get_funding_fees(
        self, pair: str, amount: float, is_short: bool, open_date: datetime
    ) -> float:
        """
        Calculate funding fees for a position.
        Override this to provide proper funding fee calculation or return 0.0 if not supported.
        """
        # For now, return 0.0 to avoid funding fee calculation errors
        # This can be implemented later with proper blofin funding fee logic
        return 0.0
