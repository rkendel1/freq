"""
Capital and state isolation.

This module provides explicit capital pools and state management.
No global mutable capital - all state is explicit and trackable.

This enables MYCELIUM's micro-exploits to feed each other safely
without implicit state coupling.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from freqtrade.persistence import Trade


logger = logging.getLogger(__name__)


@dataclass
class CapitalState:
    """
    Explicit capital state tracking.
    
    All capital changes are tracked explicitly - no hidden mutations.
    """
    # Capital pools
    total_capital: float  # Total capital in the system
    available_capital: float  # Capital available for new positions
    deployed_capital: float  # Capital currently in positions
    reserved_capital: float  # Capital reserved (e.g., for fees, margin)
    
    # PnL tracking
    pnl_realized: float = 0.0  # Realized profit/loss
    pnl_unrealized: float = 0.0  # Unrealized profit/loss (updated periodically)
    
    # Fees
    total_fees: float = 0.0  # Total fees paid
    
    # Metadata
    last_updated: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate capital state invariants."""
        self._validate()
    
    def _validate(self) -> None:
        """Ensure capital accounting is consistent."""
        # available + deployed + reserved should equal total (approximately)
        accounted = self.available_capital + self.deployed_capital + self.reserved_capital
        if abs(accounted - self.total_capital) > 0.01:  # Allow small rounding errors
            logger.warning(
                f"Capital accounting mismatch: "
                f"total={self.total_capital}, "
                f"accounted={accounted}"
            )
    
    def allocate(self, amount: float) -> bool:
        """
        Allocate capital from available to deployed.
        
        Args:
            amount: Amount to allocate
            
        Returns:
            True if successful, False if insufficient capital
        """
        if amount > self.available_capital:
            return False
        
        self.available_capital -= amount
        self.deployed_capital += amount
        self.last_updated = datetime.now()
        self._validate()
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
        self.last_updated = datetime.now()
        self._validate()
    
    def reserve(self, amount: float) -> bool:
        """
        Reserve capital (e.g., for fees, margin requirements).
        
        Args:
            amount: Amount to reserve
            
        Returns:
            True if successful, False if insufficient capital
        """
        if amount > self.available_capital:
            return False
        
        self.available_capital -= amount
        self.reserved_capital += amount
        self.last_updated = datetime.now()
        self._validate()
        return True
    
    def unreserve(self, amount: float) -> None:
        """
        Release reserved capital back to available.
        
        Args:
            amount: Amount to unreserve
        """
        self.reserved_capital -= amount
        self.available_capital += amount
        self.last_updated = datetime.now()
        self._validate()
    
    def record_fee(self, fee: float) -> None:
        """
        Record a fee payment.
        
        Args:
            fee: Fee amount
        """
        self.total_fees += fee
        # Fees are already deducted from capital elsewhere
        self.last_updated = datetime.now()


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
    
    # Cooldowns (symbol -> timestamp)
    position_cooldowns: dict[str, int] = field(default_factory=dict)
    
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
        """Update cooldown for a symbol."""
        self.position_cooldowns[symbol] = timestamp
    
    def is_in_cooldown(self, symbol: str, current_time: int, cooldown_seconds: int) -> bool:
        """Check if a symbol is in cooldown."""
        last_action = self.position_cooldowns.get(symbol, 0)
        return (current_time - last_action) < cooldown_seconds


def create_initial_state(total_capital: float) -> ExecutionEngineState:
    """
    Create initial execution engine state.
    
    Args:
        total_capital: Starting capital
        
    Returns:
        Initial state with all capital available
    """
    capital = CapitalState(
        total_capital=total_capital,
        available_capital=total_capital,
        deployed_capital=0.0,
        reserved_capital=0.0,
        pnl_realized=0.0,
        pnl_unrealized=0.0,
        total_fees=0.0,
        last_updated=datetime.now(),
    )
    
    return ExecutionEngineState(capital=capital)
