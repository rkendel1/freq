"""
Action Contract - Immutable interface between exploits and execution.

This defines the hard interface for trading actions. It is:
- Minimal: Only essential fields
- Immutable: Actions cannot be modified after creation
- Validated: Invalid actions are rejected at creation time
- Stable: This contract must remain backwards compatible

The execution engine accepts ONLY Action objects.
"""

from dataclasses import dataclass
from enum import Enum


class ActionType(Enum):
    """Types of trading actions."""

    OPEN = "OPEN"
    CLOSE = "CLOSE"
    ADJUST = "ADJUST"


class Side(Enum):
    """Position side."""

    LONG = "LONG"
    SHORT = "SHORT"


@dataclass(frozen=True)
class Action:
    """
    Immutable trading action sent from exploits to execution engine.

    This is the hard interface contract. All fields are required except ttl.
    Actions are validated at creation time - invalid actions raise ValueError.

    Attributes:
        type: Action type (OPEN, CLOSE, ADJUST)
        symbol: Trading pair symbol (e.g., "BTC/USDT")
        side: Position side (LONG or SHORT)
        size: Position size (positive float, interpretation depends on config)
        reason: Human-readable reason for this action (for logging/telemetry)
        ttl: Optional time-to-live in seconds (if not executed within ttl, action expires)
    """

    type: ActionType
    symbol: str
    side: Side
    size: float
    reason: str
    ttl: int | None = None

    def __post_init__(self) -> None:
        """Validate action fields after initialization."""
        # Validate type
        if not isinstance(self.type, ActionType):
            raise ValueError(f"type must be ActionType enum, got {type(self.type)}")

        # Validate symbol
        if not isinstance(self.symbol, str):
            raise ValueError(f"symbol must be str, got {type(self.symbol)}")
        if not self.symbol or not self.symbol.strip():
            raise ValueError("symbol cannot be empty")

        # Validate side
        if not isinstance(self.side, Side):
            raise ValueError(f"side must be Side enum, got {type(self.side)}")

        # Validate size
        if not isinstance(self.size, (int, float)):
            raise ValueError(f"size must be numeric, got {type(self.size)}")
        if self.size <= 0:
            raise ValueError(f"size must be positive, got {self.size}")

        # Validate reason
        if not isinstance(self.reason, str):
            raise ValueError(f"reason must be str, got {type(self.reason)}")
        if not self.reason or not self.reason.strip():
            raise ValueError("reason cannot be empty")

        # Validate ttl
        if self.ttl is not None:
            if not isinstance(self.ttl, int):
                raise ValueError(f"ttl must be int or None, got {type(self.ttl)}")
            if self.ttl <= 0:
                raise ValueError(f"ttl must be positive, got {self.ttl}")


def validate_action(action: Action) -> None:
    """
    Validate that an action is a valid Action object.

    This is called by the execution engine before processing actions.
    Invalid actions are rejected before execution.

    Args:
        action: Action to validate

    Raises:
        TypeError: If action is not an Action object
        ValueError: If action has invalid field values (caught during Action creation)
    """
    if not isinstance(action, Action):
        raise TypeError(f"Expected Action object, got {type(action)}")

    # Note: Field validation happens in Action.__post_init__
    # This function primarily ensures type safety at the engine boundary
