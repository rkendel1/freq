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

if TYPE_CHECKING:
    from freqtrade.metrics.attribution import TradeAttribution

logger = logging.getLogger(__name__)


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
    ):
        """
        Initialize the DSPy advisor.
        
        Args:
            min_trades_for_suggestion: Minimum number of trades before generating suggestions
            suggestion_confidence_threshold: Minimum confidence for a suggestion to be logged
        """
        self.min_trades_for_suggestion = min_trades_for_suggestion
        self.suggestion_confidence_threshold = suggestion_confidence_threshold
        
        # Storage for observed trades, keyed by exploit_id
        self.trades_by_exploit: dict[str, list["TradeAttribution"]] = {}
        
        # History of generated suggestions
        self.suggestion_history: list[ParameterSuggestion] = []
        
        logger.info("DSPy Advisory Layer initialized (READ-ONLY mode)")
    
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
                return 100.0  # Very high Sharpe for perfect consistency with profit
            else:
                return -100.0  # Very low Sharpe for consistent losses
        
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
        if metrics.sharpe_ratio < 0.5:
            confidence = min(0.9, (0.5 - metrics.sharpe_ratio) * 2)
            current_size = 1.0  # Normalized position size
            reduction = 0.2  # Reduce by 20%
            suggested_size = current_size * (1 - reduction)
            
            suggestions.append(
                ParameterSuggestion(
                    timestamp=datetime.now(),
                    exploit_id=exploit_id,
                    parameter_name="position_size_multiplier",
                    current_value=current_size,
                    suggested_value=suggested_size,
                    delta=-reduction,
                    rationale=f"Low Sharpe ratio ({metrics.sharpe_ratio:.2f}) suggests reducing exposure",
                    confidence=confidence,
                    metrics_snapshot=metrics,
                )
            )
        
        # Rule 2: High drawdown contribution → Suggest tighter stop loss
        if metrics.drawdown_contribution > 0.3:
            confidence = min(0.95, metrics.drawdown_contribution * 1.5)
            current_stop = 0.05  # 5% stop loss
            reduction = 0.01  # Tighten by 1%
            suggested_stop = current_stop - reduction
            
            suggestions.append(
                ParameterSuggestion(
                    timestamp=datetime.now(),
                    exploit_id=exploit_id,
                    parameter_name="stop_loss_percent",
                    current_value=current_stop,
                    suggested_value=suggested_stop,
                    delta=-reduction,
                    rationale=f"High drawdown contribution ({metrics.drawdown_contribution:.2%}) "
                    f"suggests tighter risk management",
                    confidence=confidence,
                    metrics_snapshot=metrics,
                )
            )
        
        # Rule 3: Low capital efficiency → Suggest reducing holding time
        if metrics.capital_efficiency < 0.1 and metrics.total_trades > 30:
            confidence = 0.7
            current_hold_hours = 24.0  # Example current holding time
            reduction = 6.0  # Reduce by 6 hours
            suggested_hold = current_hold_hours - reduction
            
            suggestions.append(
                ParameterSuggestion(
                    timestamp=datetime.now(),
                    exploit_id=exploit_id,
                    parameter_name="max_holding_hours",
                    current_value=current_hold_hours,
                    suggested_value=suggested_hold,
                    delta=-reduction,
                    rationale=f"Low capital efficiency ({metrics.capital_efficiency:.2%}) "
                    f"suggests reducing holding time",
                    confidence=confidence,
                    metrics_snapshot=metrics,
                )
            )
        
        # Rule 4: High Sharpe + High capital efficiency → Suggest increasing size
        if metrics.sharpe_ratio > 1.5 and metrics.capital_efficiency > 0.3:
            confidence = min(0.85, (metrics.sharpe_ratio - 1.5) * 0.5 + 0.6)
            current_size = 1.0
            increase = 0.15  # Increase by 15%
            suggested_size = current_size * (1 + increase)
            
            suggestions.append(
                ParameterSuggestion(
                    timestamp=datetime.now(),
                    exploit_id=exploit_id,
                    parameter_name="position_size_multiplier",
                    current_value=current_size,
                    suggested_value=suggested_size,
                    delta=increase,
                    rationale=f"Strong Sharpe ratio ({metrics.sharpe_ratio:.2f}) and "
                    f"capital efficiency ({metrics.capital_efficiency:.2%}) "
                    f"suggest increasing exposure",
                    confidence=confidence,
                    metrics_snapshot=metrics,
                )
            )
        
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
    
    def reset(self) -> None:
        """
        Reset the advisor state.
        
        This clears all observed trades and suggestion history.
        Useful for testing or starting fresh.
        """
        self.trades_by_exploit.clear()
        self.suggestion_history.clear()
        logger.info("DSPy Advisory Layer reset")
