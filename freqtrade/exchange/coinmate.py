"""Coinmate exchange subclass"""

import logging
from typing import Dict

from freqtrade.enums import MarginMode, TradingMode
from freqtrade.exceptions import OperationalException
from freqtrade.exchange import Exchange
from freqtrade.exchange.exchange_types import FtHas

logger = logging.getLogger(__name__)


class Coinmate(Exchange):
    """
    Coinmate exchange class. Contains adjustments needed for Freqtrade to work
    with this exchange.
    
    Coinmate is a Czech cryptocurrency exchange supporting spot trading only.
    Rate limit: 100 requests/minute.
    """

    _ft_has: FtHas = {
        # Core trading features
        "stoploss_on_exchange": False,  # No stop-loss support on exchange
        "order_time_in_force": ["GTC"],  # Good Till Cancelled only
        "trades_pagination": "id",
        "trades_pagination_arg": "fromId",
        "trades_has_history": True,
        
        # Order book features  
        "l2_limit_range": [1, 10, 50, 100],  # Supported order book depths
        "l2_limit_range_required": False,
        
        # Market data features
        "ohlcv_candle_limit": None,  # No OHLCV support
        "ohlcv_has_history": False,
        
        # Rate limiting
        "ccxt_futures_name": "swap",  # Required by base class
    }

    _supported_trading_mode_margin_pairs: list[tuple[TradingMode, MarginMode]] = [
        # Coinmate only supports spot trading
        (TradingMode.SPOT, MarginMode.NONE),
    ]

    @property
    def _ccxt_config(self) -> Dict:
        """Configure CCXT parameters for Coinmate"""
        config = super()._ccxt_config
        config.update({
            "uid": self._api_key_headers.get("uid", ""),
            "rateLimit": 600,  # 100 requests/minute
            "enableRateLimit": True,
            "options": {
                "adjustForTimeDifference": True,
                "recvWindow": 10000,
            }
        })
        return config

    def validate_ordertypes(self, order_types: Dict) -> None:
        """Validate order types for Coinmate. Supports market and limit orders."""
        super().validate_ordertypes(order_types)
        
        # Coinmate supports both market and limit orders
        valid_order_types = ['market', 'limit']
        
        for order_type in ['entry', 'exit']:
            if order_types.get(order_type) not in valid_order_types:
                raise OperationalException(
                    f"Coinmate only supports 'market' and 'limit' orders for {order_type}. "
                    f"Got: {order_types.get(order_type)}"
                )
        
        # Stoploss orders are not supported on exchange
        if order_types.get("stoploss_on_exchange"):
            raise OperationalException(
                "Coinmate does not support stoploss orders on exchange. "
                "Please set 'stoploss_on_exchange': false in your configuration."
            )

    def validate_trading_mode_and_margin_mode(
        self, 
        trading_mode: TradingMode, 
        margin_mode: MarginMode
    ) -> None:
        """Validate trading mode and margin mode. Only spot trading supported."""
        if trading_mode != TradingMode.SPOT:
            raise OperationalException(
                f"Trading mode '{trading_mode.value}' is not supported by Coinmate. "
                "Only spot trading is available."
            )
        
        if margin_mode != MarginMode.NONE:
            raise OperationalException(
                f"Margin mode '{margin_mode.value}' is not supported by Coinmate. "
                "Only 'none' margin mode is available for spot trading."
            )

    def validate_config(self, config) -> None:
        """Validate Coinmate configuration. UID is required."""
        super().validate_config(config)
        
        # Coinmate requires UID for authentication
        exchange_config = config.get('exchange', {})
        if not exchange_config.get('uid'):
            raise OperationalException(
                "Coinmate requires 'uid' parameter in exchange configuration."
            )

    def get_fee(self, symbol: str, type: str = '', side: str = '', amount: float = 1,
                price: float = 1, taker_or_maker: str = 'maker') -> float:
        """Get trading fee for Coinmate. Falls back to 0.35% if API unavailable."""
        try:
            return super().get_fee(symbol, type, side, amount, price, taker_or_maker)
        except Exception:
            # Fallback to default Coinmate fees if not available from API
            # Coinmate standard fees: 0.35% maker, 0.35% taker
            return 0.0035