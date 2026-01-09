"""
Metrics module for trade analytics and attribution.

This module provides tools for analyzing trade performance and attributing
profits/losses to various factors.
"""

from freqtrade.metrics.attribution import TradeAttribution, attribute_trade

__all__ = [
    "TradeAttribution",
    "attribute_trade",
]
