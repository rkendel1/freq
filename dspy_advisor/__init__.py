"""
DSPy Read-Only Advisory Layer

This module provides a read-only advisory layer that observes trading metrics
and suggests parameter adjustments without influencing execution.

All suggestions are logged only and never applied to the trading system.
"""

from dspy_advisor.advisor import DSPyAdvisor, MetricsSnapshot, ParameterSuggestion

__all__ = ["DSPyAdvisor", "MetricsSnapshot", "ParameterSuggestion"]
