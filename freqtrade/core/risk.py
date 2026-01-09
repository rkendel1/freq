"""
Risk management primitives.

This module provides exploit-agnostic risk management with hard bounds only.
Risk logic is extracted from strategy-awareness and enforced uniformly.

Risk is checked BEFORE execution, not during signal generation.
"""

import logging
from dataclasses import dataclass

from freqtrade.core.actions import Action, ActionType


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

    # Funding anomaly detection
    max_funding_rate: float = 0.01  # Max acceptable funding rate (1% default)
    funding_rate_change_threshold: float = 0.005  # Max sudden change in funding rate

    # Exchange health monitoring
    max_exchange_disconnect_time: int = 30  # Max seconds exchange can be disconnected


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
        self._emergency_stop: bool = False  # Manual kill switch
        self._exchange_connected: bool = True  # Exchange connection status
        self._exchange_disconnect_time: int | None = None  # When exchange disconnected
        self._last_funding_rate: dict[str, float] = {}  # symbol -> last funding rate

    def check_action(
        self,
        action: Action,
        available: float,
        deployed: float,
        open_positions: int,
        current_timestamp: int,
    ) -> tuple[bool, str | None]:
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
        # CRITICAL: Check emergency stop first - this cannot be bypassed
        if self._emergency_stop:
            return False, "EMERGENCY STOP ACTIVE - All trading halted"

        # CRITICAL: Check exchange connectivity - cannot trade if disconnected
        if not self._exchange_connected:
            return False, "Exchange disconnected - Trading halted"

        # CRITICAL: Check if exchange has been disconnected too long
        if (
            self._exchange_disconnect_time is not None
            and current_timestamp - self._exchange_disconnect_time
            > self.limits.max_exchange_disconnect_time
        ):
            return False, "Exchange disconnect timeout exceeded - Trading halted"

        # CRITICAL: Check daily loss limit - this is non-bypassable
        if self._daily_loss >= self.limits.max_daily_loss:
            return False, f"Daily loss limit reached: {self._daily_loss:.2%}"

        # Check position limit
        if action.type == ActionType.OPEN:
            if open_positions >= self.limits.max_open_positions:
                return False, f"Max positions reached: {self.limits.max_open_positions}"

        # Check exposure limit
        if action.type == ActionType.OPEN:
            total_capital = available + deployed
            if total_capital == 0:
                return False, "No capital available"

            exposure = deployed / total_capital
            if exposure >= self.limits.max_total_exposure:
                return False, f"Max exposure reached: {exposure:.2%}"

        # Check position size limit
        if action.size > self.limits.max_position_size:
            return (
                False,
                f"Position size {action.size:.2%} exceeds limit {self.limits.max_position_size:.2%}",
            )

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

    def activate_emergency_stop(self) -> None:
        """
        Activate emergency stop - halts all trading immediately.

        This is a manual kill switch that cannot be bypassed.
        Once activated, no trades will be allowed until deactivated.
        """
        logger.critical("EMERGENCY STOP ACTIVATED - All trading halted")
        self._emergency_stop = True

    def deactivate_emergency_stop(self) -> None:
        """
        Deactivate emergency stop - resumes trading.

        Use with extreme caution. Ensure all issues are resolved before resuming.
        """
        logger.warning("Emergency stop deactivated - Trading resumed")
        self._emergency_stop = False

    def is_emergency_stop_active(self) -> bool:
        """Check if emergency stop is active."""
        return self._emergency_stop

    def set_exchange_connected(self, connected: bool, current_timestamp: int) -> None:
        """
        Update exchange connection status.

        Args:
            connected: True if exchange is connected, False otherwise
            current_timestamp: Current timestamp
        """
        if connected and not self._exchange_connected:
            logger.info("Exchange reconnected")
            self._exchange_connected = True
            self._exchange_disconnect_time = None
        elif not connected and self._exchange_connected:
            logger.error("Exchange disconnected - Trading halted")
            self._exchange_connected = False
            self._exchange_disconnect_time = current_timestamp

    def is_exchange_connected(self) -> bool:
        """Check if exchange is currently connected."""
        return self._exchange_connected

    def check_funding_rate(
        self, symbol: str, funding_rate: float
    ) -> tuple[bool, str | None]:
        """
        Check if funding rate is within acceptable limits.

        Args:
            symbol: Trading pair symbol
            funding_rate: Current funding rate

        Returns:
            (safe: bool, reason: Optional[str])
            If not safe, reason explains the anomaly.
        """
        # Check absolute funding rate limit
        if abs(funding_rate) > self.limits.max_funding_rate:
            logger.error(
                f"Funding rate anomaly detected for {symbol}: "
                f"{funding_rate:.4%} exceeds limit {self.limits.max_funding_rate:.4%}"
            )
            return (
                False,
                f"Funding rate {funding_rate:.4%} exceeds limit {self.limits.max_funding_rate:.4%}",
            )

        # Check sudden funding rate changes
        if symbol in self._last_funding_rate:
            last_rate = self._last_funding_rate[symbol]
            rate_change = abs(funding_rate - last_rate)
            if rate_change > self.limits.funding_rate_change_threshold:
                logger.error(
                    f"Sudden funding rate change detected for {symbol}: "
                    f"{rate_change:.4%} exceeds threshold {self.limits.funding_rate_change_threshold:.4%}"
                )
                return (
                    False,
                    f"Funding rate change {rate_change:.4%} exceeds threshold",
                )

        # Update last known funding rate
        self._last_funding_rate[symbol] = funding_rate
        return True, None


def create_risk_manager_from_config(config: dict) -> RiskManager:
    """
    Create a RiskManager from freqtrade config.

    Args:
        config: Freqtrade configuration dict

    Returns:
        Configured RiskManager
    """
    limits = RiskLimits(
        max_position_size=config.get("max_position_size", 0.1),  # Default 10%
        max_total_exposure=config.get("max_total_exposure", 0.95),  # Default 95%
        max_open_positions=config.get("max_open_trades", 3),
        max_loss_per_trade=config.get("stoploss", 0.10),
        max_daily_loss=config.get("max_daily_loss", 0.20),  # Default 20%
        max_leverage=config.get("leverage", {}).get("max", 1.0),
        position_cooldown=config.get("position_cooldown", 0),
        global_cooldown=config.get("global_cooldown", 0),
        max_funding_rate=config.get("max_funding_rate", 0.01),  # Default 1%
        funding_rate_change_threshold=config.get("funding_rate_change_threshold", 0.005),  # Default 0.5%
        max_exchange_disconnect_time=config.get("max_exchange_disconnect_time", 30),  # Default 30s
    )

    return RiskManager(limits)
