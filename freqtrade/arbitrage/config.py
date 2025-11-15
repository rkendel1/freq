"""Arbitrage configuration management"""

import logging
from typing import Any, Optional

from freqtrade.constants import Config


logger = logging.getLogger(__name__)


class ArbitrageConfig:
    """Manages arbitrage-specific configuration"""
    
    DEFAULT_CONFIG = {
        "enabled": False,
        "auto_trade": False,
        "min_spread_percent": 2.0,
        "max_spread_percent": 10.0,
        "min_trade_amount": 100.0,
        "max_trade_amount": 10000.0,
        "trading_pairs": ["BTC/USD", "ETH/USD"],
        "exchange_1": "kraken",
        "exchange_2": "coinbase",
        "update_interval_seconds": 5,
        "fee_buffer_percent": 0.5,
        "slippage_buffer_percent": 0.2,
        "max_open_trades": 3,
        "stop_loss_percent": 5.0,
        "take_profit_percent": 3.0,
        "notifications": {
            "browser": True,
            "email": False,
            "webhook": False,
        },
    }
    
    def __init__(self, config: Config):
        """Initialize arbitrage configuration
        
        Args:
            config: Main Freqtrade configuration dictionary
        """
        self.config = config
        self.arbitrage_config = self._load_arbitrage_config()
        
    def _load_arbitrage_config(self) -> dict[str, Any]:
        """Load arbitrage configuration from main config"""
        arb_config = self.config.get("arbitrage", {})
        
        # Merge with defaults
        merged_config = self.DEFAULT_CONFIG.copy()
        merged_config.update(arb_config)
        
        return merged_config
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        return self.arbitrage_config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        self.arbitrage_config[key] = value
        logger.info(f"Updated arbitrage config: {key} = {value}")
    
    def is_enabled(self) -> bool:
        """Check if arbitrage is enabled"""
        return self.arbitrage_config.get("enabled", False)
    
    def is_auto_trade_enabled(self) -> bool:
        """Check if auto-trading is enabled"""
        return self.arbitrage_config.get("auto_trade", False)
    
    def get_min_spread(self) -> float:
        """Get minimum spread threshold"""
        return self.arbitrage_config.get("min_spread_percent", 2.0)
    
    def get_max_spread(self) -> float:
        """Get maximum spread threshold"""
        return self.arbitrage_config.get("max_spread_percent", 10.0)
    
    def get_trading_pairs(self) -> list[str]:
        """Get list of trading pairs to monitor"""
        return self.arbitrage_config.get("trading_pairs", ["BTC/USD", "ETH/USD"])
    
    def get_exchanges(self) -> tuple[str, str]:
        """Get exchange pair for arbitrage
        
        Returns:
            Tuple of (exchange_1, exchange_2)
        """
        return (
            self.arbitrage_config.get("exchange_1", "kraken"),
            self.arbitrage_config.get("exchange_2", "coinbase"),
        )
    
    def get_trade_limits(self) -> tuple[float, float]:
        """Get trade amount limits
        
        Returns:
            Tuple of (min_amount, max_amount)
        """
        return (
            self.arbitrage_config.get("min_trade_amount", 100.0),
            self.arbitrage_config.get("max_trade_amount", 10000.0),
        )
    
    def get_fee_buffer(self) -> float:
        """Get fee buffer percentage"""
        return self.arbitrage_config.get("fee_buffer_percent", 0.5)
    
    def get_slippage_buffer(self) -> float:
        """Get slippage buffer percentage"""
        return self.arbitrage_config.get("slippage_buffer_percent", 0.2)
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate configuration
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        if not self.get_trading_pairs():
            return False, "No trading pairs configured"
        
        # Check spread thresholds
        min_spread = self.get_min_spread()
        max_spread = self.get_max_spread()
        if min_spread >= max_spread:
            return False, "min_spread_percent must be less than max_spread_percent"
        
        if min_spread < 0 or max_spread < 0:
            return False, "Spread percentages must be positive"
        
        # Check trade limits
        min_amount, max_amount = self.get_trade_limits()
        if min_amount >= max_amount:
            return False, "min_trade_amount must be less than max_trade_amount"
        
        if min_amount <= 0 or max_amount <= 0:
            return False, "Trade amounts must be positive"
        
        return True, None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary
        
        Returns:
            Configuration dictionary
        """
        return self.arbitrage_config.copy()
