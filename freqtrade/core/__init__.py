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
"""

from freqtrade.core.risk import RiskManager, RiskLimits, create_risk_manager_from_config
from freqtrade.core.state import (
    CapitalState,
    ExecutionEngineState,
    create_initial_state,
)


__all__ = [
    'RiskManager',
    'RiskLimits',
    'create_risk_manager_from_config',
    'CapitalState',
    'ExecutionEngineState',
    'create_initial_state',
]

