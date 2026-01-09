"""
Core execution engine module.

This module contains the minimal infrastructure for:
- Order execution
- Position tracking
- PnL attribution
- Exchange abstraction
- Backtesting/simulation
- Risk management
- State isolation
- Action contract (immutable interface between exploits and execution)
"""

from freqtrade.core.actions import Action, ActionType, Side, validate_action
from freqtrade.core.risk import RiskManager, RiskLimits, create_risk_manager_from_config
from freqtrade.core.state import (
    CapitalState,
    ExecutionEngineState,
    create_initial_state,
)


__all__ = [
    'Action',
    'ActionType',
    'Side',
    'validate_action',
    'RiskManager',
    'RiskLimits',
    'create_risk_manager_from_config',
    'CapitalState',
    'ExecutionEngineState',
    'create_initial_state',
]

