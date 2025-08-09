import logging
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
        "needs_trading_fees": False,
        "order_time_in_force": ["GTC", "IOC", "FOK"],
        "floor_leverage": True,  # Blofin requires integer leverage values
        "exchange_has_overrides": {
            "fetchOrder": True,  # We implement this method in our custom class
        },
    }

    _supported_trading_mode_margin_pairs: list[tuple[TradingMode, MarginMode]] = [
        (TradingMode.SPOT, MarginMode.NONE),
        (TradingMode.FUTURES, MarginMode.CROSS),
        # Note: Blofin does not support isolated futures trading
    ]

    def __init__(
        self,
        config: Config,
        *,
        exchange_config: ExchangeConfig | None = None,
        validate: bool = True,
        load_leverage_tiers: bool = False,
    ) -> None:
        super().__init__(
            config,
            exchange_config=exchange_config,
            validate=validate,
            load_leverage_tiers=load_leverage_tiers
        )

    @retrier
    def fetch_order(self, order_id: str, pair: str, params: dict | None = None) -> CcxtOrder:
        """
        Fetch a specific order by ID.
        Since blofin doesn't support fetchOrder directly, we emulate it using
        fetchOpenOrders and fetchClosedOrders.
        """
        if params is None:
            params = {}

        try:
            # First try to find in open orders
            open_orders = self._api.fetch_open_orders(pair, params=params)
            for order in open_orders:
                if str(order['id']) == str(order_id):
                    self._log_exchange_response("fetch_order", order)
                    return self._order_contracts_to_amount(order)

            # If not found in open orders, try closed orders
            closed_orders = self._api.fetch_closed_orders(pair, params=params)
            for order in closed_orders:
                if str(order['id']) == str(order_id):
                    self._log_exchange_response("fetch_order", order)
                    return self._order_contracts_to_amount(order)

            # If order not found in either list, raise OrderNotFound
            raise ccxt.OrderNotFound(f"Order {order_id} not found")

        except ccxt.OrderNotFound as e:
            from freqtrade.exceptions import RetryableOrderError
            raise RetryableOrderError(
                f"Order not found (pair: {pair} id: {order_id}). Message: {e}"
            ) from e
        except ccxt.InvalidOrder as e:
            from freqtrade.exceptions import InvalidOrderException
            raise InvalidOrderException(
                f"Tried to get an invalid order (pair: {pair} id: {order_id}). Message: {e}"
            ) from e
        except ccxt.DDoSProtection as e:
            raise DDosProtection(e) from e
        except (ccxt.OperationFailed, ccxt.ExchangeError) as e:
            raise TemporaryError(
                f"Could not get order due to {e.__class__.__name__}. Message: {e}"
            ) from e
        except ccxt.BaseError as e:
            raise OperationalException(e) from e

    def _set_leverage(
        self,
        leverage: float,
        pair: str | None = None,
        accept_fail: bool = False,
    ):
        """
        Set leverage for blofin exchange.
        Blofin might have specific leverage requirements.
        """
        if self._config["dry_run"] or not self.exchange_has("setLeverage"):
            return
            
        try:
            # Ensure leverage is an integer for blofin
            leverage_int = int(leverage)
            # Blofin might have leverage limits, so clamp to reasonable range
            leverage_int = max(1, min(leverage_int, 100))  # Assuming max 100x leverage
            
            res = self._api.set_leverage(symbol=pair, leverage=leverage_int)
            self._log_exchange_response("set_leverage", res)
        except ccxt.DDoSProtection as e:
            raise DDosProtection(e) from e
        except (ccxt.BadRequest, ccxt.OperationRejected, ccxt.InsufficientFunds) as e:
            if not accept_fail:
                raise TemporaryError(
                    f"Could not set leverage due to {e.__class__.__name__}. Message: {e}"
                ) from e
        except ccxt.BaseError as e:
            if not accept_fail:
                raise OperationalException(e) from e

    def _lev_prep(self, pair: str, leverage: float, side: str, accept_fail: bool = False):
        """
        Prepare leverage settings for blofin.
        """
        if self.trading_mode != TradingMode.SPOT:
            # Set margin mode first, then leverage
            try:
                self.set_margin_mode(pair, self.margin_mode, accept_fail=True)
                # Add a small delay to avoid rate limiting
                import time
                time.sleep(0.1)
                self._set_leverage(leverage, pair, accept_fail=True)
            except Exception as e:
                if not accept_fail:
                    logger.warning(f"Failed to set leverage for {pair}: {e}")

    def _get_funding_fees_from_exchange(
        self, pair: str, since: int | None
    ) -> list[dict[str, Any]]:
        """
        Fetch funding fees from exchange.
        """
        # Blofin might not support funding fee history
        # Return empty list for now, can be implemented later if needed
        return []

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
        Calculate liquidation price for dry run mode.
        TODO: Implement proper liquidation price calculation for blofin.
        For now, return None to suppress warnings.
        """
        # Return None for now - this will use the default calculation
        # or suppress liquidation price warnings
        return None

    @retrier
    def additional_exchange_init(self) -> None:
        """
        Additional exchange initialization logic.
        """
        try:
            # Add any blofin-specific initialization here
            pass
        except ccxt.BaseError as e:
            logger.warning(f"Unable to initialize exchange. Reason: {e}")
