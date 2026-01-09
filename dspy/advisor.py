"""
DSPy Advisory Module - Read-Only Parameter Optimization Suggestions

This module observes trading metrics and provides parameter optimization suggestions
without influencing execution. All suggestions are logged only.

Key Principles:
- OBSERVE: Monitor exploit Sharpe, drawdown contribution, capital efficiency
- SUGGEST: Output parameter deltas based on observations
- NEVER APPLY: Suggestions are logged only, never executed

This is a read-only advisory layer that has zero impact on trading execution.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from dspy.guardrails import DSPyGuardrails

if TYPE_CHECKING:
    from freqtrade.metrics.attribution import TradeAttribution

logger = logging.getLogger(__name__)


# Constants for Sharpe ratio calculation
SHARPE_PERFECT_CONSISTENCY_PROFITABLE = 100.0  # Very high Sharpe for perfect consistency with profit
SHARPE_PERFECT_CONSISTENCY_LOSS = -100.0  # Very low Sharpe for consistent losses

# Constants for suggestion rules
DEFAULT_POSITION_SIZE = 1.0
POSITION_SIZE_REDUCTION = 0.2  # 20% reduction
POSITION_SIZE_INCREASE = 0.15  # 15% increase
DEFAULT_STOP_LOSS = 0.05  # 5% stop loss
STOP_LOSS_TIGHTENING = 0.01  # 1% tightening
DEFAULT_HOLD_HOURS = 24.0  # 24 hours
HOLD_TIME_REDUCTION = 6.0  # 6 hours reduction

# Thresholds for suggestion rules
SHARPE_LOW_THRESHOLD = 0.5
SHARPE_HIGH_THRESHOLD = 1.5
DRAWDOWN_HIGH_THRESHOLD = 0.3
CAPITAL_EFF_LOW_THRESHOLD = 0.1
CAPITAL_EFF_HIGH_THRESHOLD = 0.3
MIN_TRADES_FOR_CAPITAL_EFF = 30

# Confidence calculation constants
CONFIDENCE_BASE_LOW_SHARPE = 0.9
CONFIDENCE_MULTIPLIER_LOW_SHARPE = 2.0
CONFIDENCE_CAP_DRAWDOWN = 0.95
CONFIDENCE_MULTIPLIER_DRAWDOWN = 1.5
CONFIDENCE_CAPITAL_EFF = 0.7
CONFIDENCE_BASE_HIGH_PERF = 0.6
CONFIDENCE_MULTIPLIER_HIGH_PERF = 0.5
CONFIDENCE_CAP_HIGH_PERF = 0.85


@dataclass
class MetricsSnapshot:
    """
    Snapshot of metrics observed at a point in time.
    
    This captures the key performance indicators that DSPy uses
    to generate parameter suggestions.
    
    Attributes:
        timestamp: When this snapshot was taken
        exploit_id: ID of the exploit being observed
        sharpe_ratio: Sharpe ratio of the exploit
        drawdown_contribution: Contribution to overall drawdown (0.0 to 1.0)
        capital_efficiency: How efficiently capital is being used (profit / avg deployed capital)
        total_trades: Number of trades in the observation window
        win_rate: Percentage of winning trades
        avg_profit_per_trade: Average profit per trade
        max_drawdown: Maximum drawdown observed
        deployed_capital_avg: Average capital deployed
    """
    
    timestamp: datetime
    exploit_id: str
    sharpe_ratio: float
    drawdown_contribution: float
    capital_efficiency: float
    total_trades: int
    win_rate: float
    avg_profit_per_trade: float
    max_drawdown: float
    deployed_capital_avg: float


@dataclass
class ParameterSuggestion:
    """
    A suggested parameter adjustment from DSPy.
    
    This is purely advisory - the suggestion is logged but never applied.
    
    Attributes:
        timestamp: When this suggestion was generated
        exploit_id: ID of the exploit this suggestion applies to
        parameter_name: Name of the parameter to adjust
        current_value: Current value of the parameter
        suggested_value: Suggested new value
        delta: Change from current to suggested (suggested - current)
        rationale: Why this change is suggested
        confidence: Confidence score (0.0 to 1.0)
        metrics_snapshot: The metrics that led to this suggestion
    """
    
    timestamp: datetime
    exploit_id: str
    parameter_name: str
    current_value: float
    suggested_value: float
    delta: float
    rationale: str
    confidence: float
    metrics_snapshot: MetricsSnapshot


class DSPyAdvisor:
    """
    DSPy Read-Only Advisory Layer
    
    Observes trading metrics and generates parameter optimization suggestions
    without influencing execution.
    
    Usage:
        >>> advisor = DSPyAdvisor()
        >>> 
        >>> # Feed trade attributions to the advisor
        >>> for trade_attr in trade_attributions:
        ...     advisor.observe_trade(trade_attr)
        >>> 
        >>> # Generate suggestions (logged only, never applied)
        >>> suggestions = advisor.generate_suggestions()
        >>> for suggestion in suggestions:
        ...     print(suggestion)
    
    The advisor tracks metrics per exploit and generates suggestions when
    it detects opportunities for optimization.
    """
    
    def __init__(
        self,
        min_trades_for_suggestion: int = 20,
        suggestion_confidence_threshold: float = 0.6,
        enable_guardrails: bool = True,
    ):
        """
        Initialize the DSPy advisor.
        
        Args:
            min_trades_for_suggestion: Minimum number of trades before generating suggestions
            suggestion_confidence_threshold: Minimum confidence for a suggestion to be logged
            enable_guardrails: Whether to enable guardrail enforcement (default: True)
        """
        self.min_trades_for_suggestion = min_trades_for_suggestion
        self.suggestion_confidence_threshold = suggestion_confidence_threshold
        
        # Storage for observed trades, keyed by exploit_id
        self.trades_by_exploit: dict[str, list["TradeAttribution"]] = {}
        
        # History of generated suggestions
        self.suggestion_history: list[ParameterSuggestion] = []
        
        # Initialize guardrails for bounded control
        self.guardrails = DSPyGuardrails(enforce_bounds=enable_guardrails)
        
        logger.info("DSPy Advisory Layer initialized (READ-ONLY mode)")
        logger.info(f"  - Guardrails: {'ENABLED' if enable_guardrails else 'DISABLED'}")
    
    def observe_trade(self, trade_attribution: "TradeAttribution") -> None:
        """
        Observe a completed trade.
        
        This method is called to feed trade data to the advisor.
        The advisor will store this data and use it to generate suggestions.
        
        Args:
            trade_attribution: Attribution data for a completed trade
        """
        exploit_id = trade_attribution.exploit_id
        
        if exploit_id not in self.trades_by_exploit:
            self.trades_by_exploit[exploit_id] = []
        
        self.trades_by_exploit[exploit_id].append(trade_attribution)
        
        logger.debug(f"DSPy observed trade for exploit '{exploit_id}': {trade_attribution.trade_id}")
    
    def _calculate_sharpe_ratio(self, trades: list["TradeAttribution"]) -> float:
        """
        Calculate Sharpe ratio for a set of trades.
        
        Args:
            trades: List of trade attributions
            
        Returns:
            Sharpe ratio (annualized)
        """
        if not trades:
            return 0.0
        
        # Extract profit ratios
        profit_ratios = [t.profit_ratio for t in trades if t.profit_ratio is not None]
        
        if not profit_ratios:
            return 0.0
        
        # Calculate mean and std of returns
        mean_return = sum(profit_ratios) / len(profit_ratios)
        
        if len(profit_ratios) < 2:
            return 0.0
        
        variance = sum((r - mean_return) ** 2 for r in profit_ratios) / (len(profit_ratios) - 1)
        std_dev = variance ** 0.5
        
        if std_dev == 0:
            # Perfect consistency - return a high Sharpe if profitable, low if not
            # This happens when all trades have exactly the same return
            if mean_return > 0:
                return SHARPE_PERFECT_CONSISTENCY_PROFITABLE
            else:
                return SHARPE_PERFECT_CONSISTENCY_LOSS
        
        # Annualized Sharpe ratio (assuming ~252 trading days)
        sharpe = (mean_return / std_dev) * (252 ** 0.5)
        
        return sharpe
    
    def _calculate_drawdown_contribution(self, trades: list["TradeAttribution"]) -> float:
        """
        Calculate drawdown contribution for a set of trades.
        
        This estimates what fraction of the overall drawdown is attributable
        to this exploit.
        
        Args:
            trades: List of trade attributions
            
        Returns:
            Drawdown contribution (0.0 to 1.0, higher means more drawdown)
        """
        if not trades:
            return 0.0
        
        # Calculate cumulative P&L
        cumulative_pnl = []
        running_total = 0.0
        for trade in sorted(trades, key=lambda t: t.exit_date or t.entry_date):
            if trade.realized_profit is not None:
                running_total += trade.realized_profit
                cumulative_pnl.append(running_total)
        
        if not cumulative_pnl:
            return 0.0
        
        # Calculate max drawdown
        peak = cumulative_pnl[0]
        max_drawdown = 0.0
        
        for value in cumulative_pnl:
            if value > peak:
                peak = value
            drawdown = peak - value
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Normalize to 0-1 range (contribution relative to total P&L range)
        total_range = max(cumulative_pnl) - min(cumulative_pnl)
        if total_range == 0:
            return 0.0
        
        return min(max_drawdown / total_range, 1.0)
    
    def _calculate_capital_efficiency(self, trades: list["TradeAttribution"]) -> float:
        """
        Calculate capital efficiency for a set of trades.
        
        Capital efficiency = Total Profit / Average Deployed Capital
        
        Args:
            trades: List of trade attributions
            
        Returns:
            Capital efficiency ratio
        """
        if not trades:
            return 0.0
        
        total_profit = sum(t.realized_profit for t in trades if t.realized_profit is not None)
        total_stake = sum(t.entry_stake for t in trades)
        
        if total_stake == 0:
            return 0.0
        
        avg_deployed_capital = total_stake / len(trades)
        
        if avg_deployed_capital == 0:
            return 0.0
        
        return total_profit / avg_deployed_capital
    
    def _create_metrics_snapshot(
        self, exploit_id: str, trades: list["TradeAttribution"]
    ) -> MetricsSnapshot:
        """
        Create a metrics snapshot for an exploit.
        
        Args:
            exploit_id: ID of the exploit
            trades: List of trade attributions for this exploit
            
        Returns:
            Metrics snapshot
        """
        sharpe = self._calculate_sharpe_ratio(trades)
        drawdown_contrib = self._calculate_drawdown_contribution(trades)
        capital_eff = self._calculate_capital_efficiency(trades)
        
        # Calculate additional metrics
        winning_trades = [t for t in trades if t.realized_profit and t.realized_profit > 0]
        win_rate = len(winning_trades) / len(trades) if trades else 0.0
        
        avg_profit = (
            sum(t.realized_profit for t in trades if t.realized_profit is not None) / len(trades)
            if trades
            else 0.0
        )
        
        avg_stake = sum(t.entry_stake for t in trades) / len(trades) if trades else 0.0
        
        # Max drawdown from cumulative P&L
        cumulative_pnl = []
        running_total = 0.0
        for trade in sorted(trades, key=lambda t: t.exit_date or t.entry_date):
            if trade.realized_profit is not None:
                running_total += trade.realized_profit
                cumulative_pnl.append(running_total)
        
        peak = cumulative_pnl[0] if cumulative_pnl else 0.0
        max_dd = 0.0
        for value in cumulative_pnl:
            if value > peak:
                peak = value
            drawdown = peak - value
            if drawdown > max_dd:
                max_dd = drawdown
        
        return MetricsSnapshot(
            timestamp=datetime.now(),
            exploit_id=exploit_id,
            sharpe_ratio=sharpe,
            drawdown_contribution=drawdown_contrib,
            capital_efficiency=capital_eff,
            total_trades=len(trades),
            win_rate=win_rate,
            avg_profit_per_trade=avg_profit,
            max_drawdown=max_dd,
            deployed_capital_avg=avg_stake,
        )
    
    def _create_bounded_suggestion(
        self,
        exploit_id: str,
        parameter_name: str,
        current_value: float,
        suggested_value: float,
        rationale: str,
        confidence: float,
        metrics: MetricsSnapshot,
    ) -> Optional[ParameterSuggestion]:
        """
        Create a parameter suggestion with guardrail bounds applied.
        
        This method validates the suggestion against guardrails and applies
        bounds if necessary. If the parameter is forbidden or the suggestion
        violates guardrails, it may be rejected or adjusted.
        
        Args:
            exploit_id: ID of the exploit
            parameter_name: Name of the parameter to adjust
            current_value: Current value of the parameter
            suggested_value: Suggested new value (before bounds)
            rationale: Reason for the suggestion
            confidence: Confidence score (0.0 to 1.0)
            metrics: Metrics snapshot that led to this suggestion
            
        Returns:
            ParameterSuggestion with bounds applied, or None if rejected
        """
        # Validate against guardrails
        is_valid, violation = self.guardrails.validate_suggestion(
            parameter_name=parameter_name,
            current_value=current_value,
            suggested_value=suggested_value,
        )
        
        # Apply bounds to the suggested value
        bounded_value = self.guardrails.apply_bounds(
            parameter_name=parameter_name,
            current_value=current_value,
            suggested_value=suggested_value,
        )
        
        # Calculate actual delta after bounds
        delta = bounded_value - current_value
        
        # If the bounded value is the same as current, no suggestion needed
        if abs(delta) < 1e-10:
            logger.debug(
                f"Suggestion for '{parameter_name}' resulted in no change after bounds - skipping"
            )
            return None
        
        # Create the suggestion with bounded values
        return ParameterSuggestion(
            timestamp=datetime.now(),
            exploit_id=exploit_id,
            parameter_name=parameter_name,
            current_value=current_value,
            suggested_value=bounded_value,
            delta=delta,
            rationale=rationale,
            confidence=confidence,
            metrics_snapshot=metrics,
        )
    
    def _generate_suggestions_for_exploit(
        self, exploit_id: str, trades: list["TradeAttribution"]
    ) -> list[ParameterSuggestion]:
        """
        Generate parameter suggestions for a specific exploit.
        
        Args:
            exploit_id: ID of the exploit
            trades: List of trade attributions for this exploit
            
        Returns:
            List of parameter suggestions
        """
        if len(trades) < self.min_trades_for_suggestion:
            logger.debug(
                f"DSPy: Not enough trades for '{exploit_id}' "
                f"({len(trades)} < {self.min_trades_for_suggestion})"
            )
            return []
        
        metrics = self._create_metrics_snapshot(exploit_id, trades)
        suggestions = []
        
        # Rule 1: Low Sharpe ratio → Suggest reducing position size
        if metrics.sharpe_ratio < SHARPE_LOW_THRESHOLD:
            confidence = min(
                CONFIDENCE_BASE_LOW_SHARPE,
                (SHARPE_LOW_THRESHOLD - metrics.sharpe_ratio) * CONFIDENCE_MULTIPLIER_LOW_SHARPE,
            )
            suggested_size = DEFAULT_POSITION_SIZE * (1 - POSITION_SIZE_REDUCTION)
            
            suggestion = self._create_bounded_suggestion(
                exploit_id=exploit_id,
                parameter_name="position_size_multiplier",
                current_value=DEFAULT_POSITION_SIZE,
                suggested_value=suggested_size,
                rationale=f"Low Sharpe ratio ({metrics.sharpe_ratio:.2f}) suggests reducing exposure",
                confidence=confidence,
                metrics=metrics,
            )
            if suggestion:
                suggestions.append(suggestion)
        
        # Rule 2: High drawdown contribution → Suggest tighter stop loss
        if metrics.drawdown_contribution > DRAWDOWN_HIGH_THRESHOLD:
            confidence = min(
                CONFIDENCE_CAP_DRAWDOWN, metrics.drawdown_contribution * CONFIDENCE_MULTIPLIER_DRAWDOWN
            )
            suggested_stop = DEFAULT_STOP_LOSS - STOP_LOSS_TIGHTENING
            
            suggestion = self._create_bounded_suggestion(
                exploit_id=exploit_id,
                parameter_name="stop_loss_percent",
                current_value=DEFAULT_STOP_LOSS,
                suggested_value=suggested_stop,
                rationale=f"High drawdown contribution ({metrics.drawdown_contribution:.2%}) "
                         f"suggests tighter risk management",
                confidence=confidence,
                metrics=metrics,
            )
            if suggestion:
                suggestions.append(suggestion)
        
        # Rule 3: Low capital efficiency → Suggest reducing holding time
        if (
            metrics.capital_efficiency < CAPITAL_EFF_LOW_THRESHOLD
            and metrics.total_trades > MIN_TRADES_FOR_CAPITAL_EFF
        ):
            confidence = CONFIDENCE_CAPITAL_EFF
            suggested_hold = DEFAULT_HOLD_HOURS - HOLD_TIME_REDUCTION
            
            suggestion = self._create_bounded_suggestion(
                exploit_id=exploit_id,
                parameter_name="max_holding_hours",
                current_value=DEFAULT_HOLD_HOURS,
                suggested_value=suggested_hold,
                rationale=f"Low capital efficiency ({metrics.capital_efficiency:.2%}) "
                         f"suggests reducing holding time",
                confidence=confidence,
                metrics=metrics,
            )
            if suggestion:
                suggestions.append(suggestion)
        
        # Rule 4: High Sharpe + High capital efficiency → Suggest increasing size
        if (
            metrics.sharpe_ratio > SHARPE_HIGH_THRESHOLD
            and metrics.capital_efficiency > CAPITAL_EFF_HIGH_THRESHOLD
        ):
            confidence = min(
                CONFIDENCE_CAP_HIGH_PERF,
                (metrics.sharpe_ratio - SHARPE_HIGH_THRESHOLD) * CONFIDENCE_MULTIPLIER_HIGH_PERF
                + CONFIDENCE_BASE_HIGH_PERF,
            )
            suggested_size = DEFAULT_POSITION_SIZE * (1 + POSITION_SIZE_INCREASE)
            
            suggestion = self._create_bounded_suggestion(
                exploit_id=exploit_id,
                parameter_name="position_size_multiplier",
                current_value=DEFAULT_POSITION_SIZE,
                suggested_value=suggested_size,
                rationale=f"Strong Sharpe ratio ({metrics.sharpe_ratio:.2f}) and "
                         f"capital efficiency ({metrics.capital_efficiency:.2%}) "
                         f"suggest increasing exposure",
                confidence=confidence,
                metrics=metrics,
            )
            if suggestion:
                suggestions.append(suggestion)
        
        # Filter by confidence threshold
        filtered_suggestions = [
            s for s in suggestions if s.confidence >= self.suggestion_confidence_threshold
        ]
        
        return filtered_suggestions
    
    def generate_suggestions(self) -> list[ParameterSuggestion]:
        """
        Generate parameter optimization suggestions based on observed trades.
        
        This is the main entry point for getting suggestions from DSPy.
        All suggestions are logged but NEVER applied to execution.
        
        Returns:
            List of parameter suggestions (may be empty)
        """
        all_suggestions = []
        
        for exploit_id, trades in self.trades_by_exploit.items():
            suggestions = self._generate_suggestions_for_exploit(exploit_id, trades)
            all_suggestions.extend(suggestions)
        
        # Store suggestions in history
        self.suggestion_history.extend(all_suggestions)
        
        # Log suggestions (READ-ONLY - never applied)
        for suggestion in all_suggestions:
            logger.info(
                f"DSPy SUGGESTION (READ-ONLY): "
                f"Exploit={suggestion.exploit_id}, "
                f"Parameter={suggestion.parameter_name}, "
                f"Current={suggestion.current_value:.4f}, "
                f"Suggested={suggestion.suggested_value:.4f}, "
                f"Delta={suggestion.delta:+.4f}, "
                f"Confidence={suggestion.confidence:.2%}, "
                f"Rationale={suggestion.rationale}"
            )
        
        if all_suggestions:
            logger.info(
                f"DSPy generated {len(all_suggestions)} suggestion(s) - "
                f"LOGGED ONLY, NOT APPLIED TO EXECUTION"
            )
        
        return all_suggestions
    
    def get_metrics_snapshot(self, exploit_id: str) -> Optional[MetricsSnapshot]:
        """
        Get current metrics snapshot for an exploit.
        
        Args:
            exploit_id: ID of the exploit
            
        Returns:
            Metrics snapshot or None if exploit has no trades
        """
        trades = self.trades_by_exploit.get(exploit_id, [])
        
        if not trades:
            return None
        
        return self._create_metrics_snapshot(exploit_id, trades)
    
    def get_all_metrics(self) -> dict[str, MetricsSnapshot]:
        """
        Get metrics snapshots for all observed exploits.
        
        Returns:
            Dictionary mapping exploit_id to metrics snapshot
        """
        return {
            exploit_id: self._create_metrics_snapshot(exploit_id, trades)
            for exploit_id, trades in self.trades_by_exploit.items()
            if trades
        }
    
    def get_guardrail_stats(self) -> dict:
        """
        Get statistics about guardrail violations.
        
        Returns:
            Dictionary with violation statistics
        """
        return self.guardrails.get_violation_stats()
    
    def reset(self) -> None:
        """
        Reset the advisor state.
        
        This clears all observed trades and suggestion history.
        Useful for testing or starting fresh.
        """
        self.trades_by_exploit.clear()
        self.suggestion_history.clear()
        self.guardrails.reset()
        logger.info("DSPy Advisory Layer reset")
