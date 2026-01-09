"""
Risk management primitives.

This module provides exploit-agnostic risk management with hard bounds only.
Risk logic is extracted from strategy-awareness and enforced uniformly.

Risk is checked BEFORE execution, not during signal generation.
"""

import logging
from typing import Optional
from dataclasses import dataclass

from freqtrade.exploits.exploit_module import Action, ActionType


logger = logging.getLogger(__name__)


@dataclass
class RiskLimits:
    """
    Hard risk bounds enforced by the engine.
    
    These are config-driven and apply uniformly to all exploits.
    """
    # Capital limits
    max_position_size: float  # Max fraction of capital per position
    max_total_exposure: float  # Max fraction of capital deployed
    max_open_positions: int  # Max number of simultaneous positions
    
    # Stop loss limits
    max_loss_per_trade: float  # Max acceptable loss per trade (fraction)
    max_daily_loss: float  # Max acceptable daily loss (fraction)
    
    # Leverage limits (futures)
    max_leverage: float = 1.0  # Max leverage allowed
    
    # Cooldown periods (seconds)
    position_cooldown: int = 0  # Min time between positions on same symbol
    global_cooldown: int = 0  # Min time between any positions


class RiskManager:
    """
    Enforces risk limits before execution.
    
    This is called by the execution engine, NOT by exploits.
    Exploits propose actions, the engine checks risk, then executes.
    """
    
    def __init__(self, limits: RiskLimits):
        """
        Initialize risk manager.
        
        Args:
            limits: Risk limits to enforce
        """
        self.limits = limits
        self._daily_loss: float = 0.0
        self._last_action_time: dict[str, int] = {}  # symbol -> timestamp
        self._last_global_action_time: int = 0
    
    def check_action(
        self,
        action: Action,
        available: float,
        deployed: float,
        open_positions: int,
        current_timestamp: int,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if an action is allowed under current risk limits.
        
        Args:
            action: The proposed action
            available: Available capital
            deployed: Currently deployed capital
            open_positions: Number of open positions
            current_timestamp: Current timestamp
            
        Returns:
            (allowed: bool, reason: Optional[str])
            If not allowed, reason explains why.
        """
        # Check position limit
        if action.type in (ActionType.OPEN_LONG, ActionType.OPEN_SHORT):
            if open_positions >= self.limits.max_open_positions:
                return False, f"Max positions reached: {self.limits.max_open_positions}"
        
        # Check exposure limit
        if action.type in (ActionType.OPEN_LONG, ActionType.OPEN_SHORT):
            total_capital = available + deployed
            if total_capital == 0:
                return False, "No capital available"
            
            exposure = deployed / total_capital
            if exposure >= self.limits.max_total_exposure:
                return False, f"Max exposure reached: {exposure:.2%}"
        
        # Check position size limit
        if action.size is not None:
            if action.size > self.limits.max_position_size:
                return False, f"Position size {action.size:.2%} exceeds limit {self.limits.max_position_size:.2%}"
        
        # Check daily loss limit
        if self._daily_loss >= self.limits.max_daily_loss:
            return False, f"Daily loss limit reached: {self._daily_loss:.2%}"
        
        # Check cooldown periods
        if self.limits.position_cooldown > 0:
            last_action = self._last_action_time.get(action.symbol, 0)
            if current_timestamp - last_action < self.limits.position_cooldown:
                return False, f"Position cooldown active for {action.symbol}"
        
        if self.limits.global_cooldown > 0:
            if current_timestamp - self._last_global_action_time < self.limits.global_cooldown:
                return False, "Global cooldown active"
        
        # All checks passed
        return True, None
    
    def record_action(self, action: Action, timestamp: int) -> None:
        """
        Record an action for cooldown tracking.
        
        Args:
            action: The executed action
            timestamp: When it was executed
        """
        self._last_action_time[action.symbol] = timestamp
        self._last_global_action_time = timestamp
    
    def record_loss(self, loss: float) -> None:
        """
        Record a loss for daily loss tracking.
        
        Args:
            loss: Loss amount (positive number)
        """
        self._daily_loss += abs(loss)
    
    def reset_daily_loss(self) -> None:
        """Reset daily loss counter (call at start of new trading day)."""
        self._daily_loss = 0.0


def create_risk_manager_from_config(config: dict) -> RiskManager:
    """
    Create a RiskManager from freqtrade config.
    
    Args:
        config: Freqtrade configuration dict
        
    Returns:
        Configured RiskManager
    """
    limits = RiskLimits(
        max_position_size=config.get('max_position_size', 0.1),  # Default 10%
        max_total_exposure=config.get('max_total_exposure', 0.95),  # Default 95%
        max_open_positions=config.get('max_open_trades', 3),
        max_loss_per_trade=config.get('stoploss', 0.10),
        max_daily_loss=config.get('max_daily_loss', 0.20),  # Default 20%
        max_leverage=config.get('leverage', {}).get('max', 1.0),
        position_cooldown=config.get('position_cooldown', 0),
        global_cooldown=config.get('global_cooldown', 0),
    )
    
    return RiskManager(limits)
