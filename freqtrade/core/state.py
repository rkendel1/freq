"""
Capital and state isolation.

This module provides explicit capital pools and state management.
No global mutable capital - all state is explicit and trackable.

This enables MYCELIUM's micro-exploits to feed each other safely
without implicit state coupling.

## Capital Request/Allocation Pattern

The CapitalState class enforces a strict request/allocation pattern:

1. **Exploits request capital** via `allocate(amount)` method
2. **Receive allocation or rejection** - returns True/False
3. **No direct balance access** - fields are public but should only be read

Example usage in an exploit:

```python
def evaluate(self, state: ExecutionState) -> list[Action]:
    # Check available capital (read-only)
    if state.available_capital < 100:
        return []  # Not enough capital

    # Exploit decides to trade
    # Engine will call capital.allocate() on behalf of exploit
    return [Action(
        type=ActionType.OPEN_LONG,
        symbol="BTC/USDT",
        size=0.1,  # Request 10% of capital
        reason="signal detected"
    )]
```

In the execution engine:

```python
# Engine receives action from exploit
action = exploit.evaluate(state)

# Engine requests capital allocation
if capital_state.allocate(capital_amount):
    # Allocation granted - execute trade
    execute_trade(action)
else:
    # Allocation rejected - insufficient capital
    logger.warning("Capital allocation rejected")
```

This pattern ensures:
- Capital flows are explicit and inspectable
- No exploit can overdraw capital
- All allocations are logged and traceable
- Rejections prevent invalid trades
"""

import logging
from dataclasses import dataclass, field

from freqtrade.persistence import Trade


logger = logging.getLogger(__name__)


@dataclass
class CapitalState:
    """
    Explicit capital state tracking.

    All capital changes are tracked explicitly - no hidden mutations.
    Exploits must request capital and receive allocation or rejection.
    """

    # Capital pools
    available_capital: float  # Capital available for new positions
    deployed_capital: float  # Capital currently in positions

    # PnL tracking
    pnl_realized: float = 0.0  # Realized profit/loss
    pnl_unrealized: float = 0.0  # Unrealized profit/loss (updated periodically)

    # Cooldowns (symbol -> timestamp)
    cooldowns: dict = field(default_factory=dict)

    def allocate(self, amount: float) -> bool:
        """
        Allocate capital from available to deployed.

        Exploits must request capital through this method.
        Returns allocation or rejection - no direct balance access.

        Args:
            amount: Amount to allocate

        Returns:
            True if allocation successful, False if rejected (insufficient capital)
        """
        if amount > self.available_capital:
            logger.warning(
                f"Capital allocation rejected: requested={amount}, available={self.available_capital}"
            )
            return False

        self.available_capital -= amount
        self.deployed_capital += amount
        logger.debug(
            f"Capital allocated: {amount} (available={self.available_capital}, deployed={self.deployed_capital})"
        )
        return True

    def release(self, amount: float, profit: float = 0.0) -> None:
        """
        Release capital from deployed back to available.

        Args:
            amount: Amount of original capital to release
            profit: Profit/loss on this capital (negative for loss)
        """
        self.deployed_capital -= amount
        self.available_capital += amount + profit
        self.pnl_realized += profit
        logger.debug(
            f"Capital released: {amount} with profit={profit} "
            f"(available={self.available_capital}, deployed={self.deployed_capital}, pnl_realized={self.pnl_realized})"
        )

    def update_unrealized_pnl(self, pnl: float) -> None:
        """
        Update unrealized PnL (for open positions).

        Args:
            pnl: Current unrealized profit/loss
        """
        self.pnl_unrealized = pnl

    def update_cooldown(self, symbol: str, timestamp: int) -> None:
        """
        Update cooldown for a symbol.

        Args:
            symbol: Trading pair symbol
            timestamp: Timestamp when cooldown started
        """
        self.cooldowns[symbol] = timestamp

    def is_in_cooldown(self, symbol: str, current_time: int, cooldown_seconds: int) -> bool:
        """
        Check if a symbol is in cooldown.

        Args:
            symbol: Trading pair symbol
            current_time: Current timestamp
            cooldown_seconds: Cooldown duration in seconds

        Returns:
            True if symbol is in cooldown, False otherwise
        """
        last_action = self.cooldowns.get(symbol, 0)
        return (current_time - last_action) < cooldown_seconds


@dataclass
class ExecutionEngineState:
    """
    Complete state of the execution engine.

    This is the single source of truth for system state.
    No hidden state - everything is explicit.
    """

    # Capital management
    capital: CapitalState

    # Position tracking
    open_trades: list[Trade] = field(default_factory=list)
    closed_trades: list[Trade] = field(default_factory=list)

    # Execution history (for telemetry/debugging)
    last_action_timestamp: int = 0
    total_actions: int = 0
    successful_actions: int = 0
    failed_actions: int = 0

    def add_open_trade(self, trade: Trade) -> None:
        """Add a new open trade."""
        self.open_trades.append(trade)

    def close_trade(self, trade: Trade) -> None:
        """Move a trade from open to closed."""
        if trade in self.open_trades:
            self.open_trades.remove(trade)
        self.closed_trades.append(trade)

    def get_open_trades_for_symbol(self, symbol: str) -> list[Trade]:
        """Get all open trades for a specific symbol."""
        return [t for t in self.open_trades if t.pair == symbol]

    def update_cooldown(self, symbol: str, timestamp: int) -> None:
        """
        Update cooldown for a symbol.
        Delegates to CapitalState.
        """
        self.capital.update_cooldown(symbol, timestamp)

    def is_in_cooldown(self, symbol: str, current_time: int, cooldown_seconds: int) -> bool:
        """
        Check if a symbol is in cooldown.
        Delegates to CapitalState.
        """
        return self.capital.is_in_cooldown(symbol, current_time, cooldown_seconds)


def create_initial_state(total_capital: float) -> ExecutionEngineState:
    """
    Create initial execution engine state.

    Args:
        total_capital: Starting capital

    Returns:
        Initial state with all capital available
    """
    capital = CapitalState(
        available_capital=total_capital,
        deployed_capital=0.0,
        pnl_realized=0.0,
        pnl_unrealized=0.0,
    )

    return ExecutionEngineState(capital=capital)
