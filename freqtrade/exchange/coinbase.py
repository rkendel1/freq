"""Coinbase exchange subclass"""

import logging
from typing import Any

import ccxt

from freqtrade.enums import MarginMode, TradingMode
from freqtrade.exchange import Exchange
from freqtrade.exchange.exchange_types import FtHas


logger = logging.getLogger(__name__)


class Coinbase(Exchange):
    """Coinbase exchange class.
    Contains adjustments needed for Freqtrade to work with this exchange.
    
    Note: This implementation supports Coinbase Advanced Trade API (formerly Coinbase Pro).
    """

    _ft_has: FtHas = {
        "stoploss_on_exchange": True,
        "stop_price_param": "stopPrice",
        "stop_price_prop": "stopPrice",
        "stoploss_order_types": {"limit": "limit", "market": "market"},
        "order_time_in_force": ["GTC", "IOC", "FOK", "PO"],
        "ohlcv_has_history": True,
        "trades_pagination": "id",
        "trades_pagination_arg": "after",
        "trades_pagination_overlap": False,
        "trades_has_history": True,
    }

    _supported_trading_mode_margin_pairs: list[tuple[TradingMode, MarginMode]] = [
        (TradingMode.SPOT, MarginMode.NONE),
    ]

    def market_is_tradable(self, market: dict[str, Any]) -> bool:
        """
        Check if the market symbol is tradable by Freqtrade.
        Default checks + check if pair is active.
        """
        parent_check = super().market_is_tradable(market)
        
        # Coinbase specific checks
        return (
            parent_check 
            and market.get("active", False) is True
            and market.get("type") == "spot"
        )

    def _get_params(
        self,
        side: str,
        ordertype: str,
        leverage: float,
        reduceOnly: bool,
        time_in_force: str = "GTC",
    ) -> dict:
        """
        Get exchange-specific parameters for order placement.
        """
        params = super()._get_params(
            side=side,
            ordertype=ordertype,
            leverage=leverage,
            reduceOnly=reduceOnly,
            time_in_force=time_in_force,
        )
        
        # Coinbase uses 'timeInForce' parameter
        if time_in_force != "GTC":
            params["timeInForce"] = time_in_force
            
        return params
