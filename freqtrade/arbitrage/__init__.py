"""Arbitrage trading module for Freqtrade"""

from freqtrade.arbitrage.engine import ArbitrageEngine
from freqtrade.arbitrage.detector import OpportunityDetector
from freqtrade.arbitrage.executor import TradeExecutor


__all__ = [
    "ArbitrageEngine",
    "OpportunityDetector",
    "TradeExecutor",
]
