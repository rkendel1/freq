"""
Trade Analyzer - Generates structured text for knowledge graph generation.

This module converts trade data into narratives suitable for LLM-based knowledge extraction.
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from freqtrade.persistence import Trade

logger = logging.getLogger(__name__)


class TradeAnalyzer:
    """
    Analyzes trades and generates structured narratives for knowledge graph generation.
    """
    
    def __init__(self):
        """Initialize the trade analyzer."""
        pass
    
    def generate_session_narrative(
        self,
        trades: list["Trade"],
        session_metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Generate a narrative description of a trading session.
        
        Args:
            trades: List of trades from the session
            session_metadata: Optional metadata about the session (e.g., regime, market conditions)
            
        Returns:
            str: Narrative text describing the session
        """
        if not trades:
            return "No trades executed in this session."
        
        # Separate winning and losing trades
        winners = [t for t in trades if not t.is_open and t.close_profit and t.close_profit > 0]
        losers = [t for t in trades if not t.is_open and t.close_profit and t.close_profit < 0]
        open_trades = [t for t in trades if t.is_open]
        
        narrative_parts = []
        
        # Session overview
        metadata = session_metadata or {}
        regime = metadata.get("regime", "unknown")
        narrative_parts.append(f"Trading Session Analysis - Market Regime: {regime}")
        narrative_parts.append(f"Total Trades: {len(trades)}")
        narrative_parts.append(f"Winners: {len(winners)}, Losers: {len(losers)}, Open: {len(open_trades)}")
        
        # Analyze winners
        if winners:
            narrative_parts.append("\nSuccessful Trades:")
            for trade in winners[:5]:  # Limit to top 5
                narrative_parts.append(self._format_trade_narrative(trade, "winner"))
        
        # Analyze losers
        if losers:
            narrative_parts.append("\nFailed Trades:")
            for trade in losers[:5]:  # Limit to top 5
                narrative_parts.append(self._format_trade_narrative(trade, "loser"))
        
        # Analyze patterns
        narrative_parts.append("\nIdentified Patterns:")
        patterns = self._identify_patterns(trades, metadata)
        narrative_parts.extend(patterns)
        
        return "\n".join(narrative_parts)
    
    def _format_trade_narrative(self, trade: "Trade", outcome: str) -> str:
        """
        Format a single trade as a narrative.
        
        Args:
            trade: Trade to format
            outcome: "winner" or "loser"
            
        Returns:
            str: Narrative description of the trade
        """
        parts = []
        
        # Basic info
        direction = "short" if trade.is_short else "long"
        profit_pct = (trade.close_profit or 0) * 100
        
        parts.append(
            f"- {outcome.upper()}: {direction} {trade.pair} "
            f"(Entry: {trade.open_rate:.4f}, Exit: {trade.close_rate or 'N/A'}, "
            f"P&L: {profit_pct:.2f}%)"
        )
        
        # Exit reason if available
        if hasattr(trade, 'exit_reason') and trade.exit_reason:
            parts.append(f"  Exit Reason: {trade.exit_reason}")
        
        # Duration
        if trade.close_date:
            duration = (trade.close_date - trade.open_date).total_seconds() / 3600
            parts.append(f"  Duration: {duration:.1f} hours")
        
        return " ".join(parts)
    
    def _identify_patterns(
        self,
        trades: list["Trade"],
        metadata: dict[str, Any],
    ) -> list[str]:
        """
        Identify trading patterns from the session.
        
        Args:
            trades: List of trades
            metadata: Session metadata
            
        Returns:
            list: List of pattern descriptions
        """
        patterns = []
        
        # Check for overtrading
        if len(trades) > 10:
            patterns.append("- High trade frequency detected (potential overtrading)")
        
        # Check for concentration in single pair
        if trades:
            pair_counts: dict[str, int] = {}
            for trade in trades:
                pair_counts[trade.pair] = pair_counts.get(trade.pair, 0) + 1
            
            max_pair = max(pair_counts, key=pair_counts.get)
            if pair_counts[max_pair] > len(trades) * 0.5:
                patterns.append(
                    f"- High concentration in {max_pair} "
                    f"({pair_counts[max_pair]}/{len(trades)} trades)"
                )
        
        # Check win rate
        closed_trades = [t for t in trades if not t.is_open and t.close_profit is not None]
        if closed_trades:
            winners = sum(1 for t in closed_trades if t.close_profit > 0)
            win_rate = winners / len(closed_trades)
            
            if win_rate < 0.3:
                patterns.append(f"- Low win rate detected ({win_rate*100:.1f}%)")
            elif win_rate > 0.7:
                patterns.append(f"- High win rate ({win_rate*100:.1f}%)")
        
        # Add regime-specific insights
        regime = metadata.get("regime")
        if regime:
            patterns.append(f"- Market regime: {regime}")
        
        return patterns if patterns else ["- No significant patterns detected"]
    
    def generate_regret_analysis(
        self,
        actual_trades: list["Trade"],
        shadow_trades: list[dict[str, Any]] | None = None,
        missed_opportunities: list[dict[str, Any]] | None = None,
    ) -> str:
        """
        Generate regret analysis comparing actual vs hypothetical outcomes.
        
        Captures insights like:
        - "Should have held longer and made more on that trade"
        - "Exited too early, left 50% on the table"
        - "Should have taken that setup but missed it"
        - "Position was too small, could have made 3x more"
        
        Args:
            actual_trades: Actual trades executed
            shadow_trades: Hypothetical trades that could have been taken
            missed_opportunities: Identified missed opportunities
            
        Returns:
            str: Regret analysis narrative
        """
        narrative_parts = ["Regret Analysis - What We Learned and Left on the Table\n"]
        
        # Analyze actual trades for regrets
        if actual_trades:
            narrative_parts.append("=== Trades We Took - Could We Have Done Better? ===\n")
            
            for trade in actual_trades:
                if trade.is_open:
                    continue
                    
                regrets = self._analyze_trade_regrets(trade)
                if regrets:
                    narrative_parts.extend(regrets)
        
        # Shadow trades - trades we didn't take but should have
        if shadow_trades:
            narrative_parts.append(
                f"\n=== Trades We DIDN'T Take (Regret) - {len(shadow_trades)} Opportunities ===\n"
            )
            for shadow in shadow_trades[:10]:  # Increased limit to capture more
                narrative_parts.append(
                    f"- REGRET: Didn't take {shadow.get('pair', 'Unknown')} "
                    f"{shadow.get('direction', 'long')} - "
                    f"Could have made {shadow.get('potential_profit', 0)*100:.2f}% "
                    f"(Reason skipped: {shadow.get('skip_reason', 'Unknown')})"
                )
        
        # Missed opportunities - interesting setups we should have caught
        if missed_opportunities:
            narrative_parts.append(
                f"\n=== Interesting Setups We Missed - {len(missed_opportunities)} Cases ===\n"
            )
            for opp in missed_opportunities[:10]:
                reason = opp.get('reason', 'Unknown reason')
                potential = opp.get('potential_profit', 0) * 100
                narrative_parts.append(
                    f"- MISSED: {reason} (Could have made ~{potential:.1f}%)"
                )
        
        # Calculate aggregate regret
        narrative_parts.append("\n=== Aggregate Regret Summary ===\n")
        
        total_actual_profit = sum(
            (t.close_profit or 0) for t in actual_trades if not t.is_open
        )
        
        total_shadow_profit = sum(
            shadow.get('potential_profit', 0) for shadow in (shadow_trades or [])
        )
        
        total_missed_profit = sum(
            opp.get('potential_profit', 0) for opp in (missed_opportunities or [])
        )
        
        narrative_parts.append(f"- Actual Profit: {total_actual_profit*100:.2f}%")
        narrative_parts.append(
            f"- Left on Table (Shadow): {total_shadow_profit*100:.2f}%"
        )
        narrative_parts.append(
            f"- Missed Completely: {total_missed_profit*100:.2f}%"
        )
        
        total_potential = total_actual_profit + total_shadow_profit + total_missed_profit
        if total_actual_profit > 0:
            capture_rate = (total_actual_profit / total_potential) * 100
            narrative_parts.append(
                f"- Capture Rate: {capture_rate:.1f}% of total potential"
            )
        
        # Key regret patterns
        narrative_parts.append("\n=== Key Regret Patterns to Address ===\n")
        regret_patterns = self._identify_regret_patterns(
            actual_trades, shadow_trades, missed_opportunities
        )
        narrative_parts.extend(regret_patterns)
        
        return "\n".join(narrative_parts)
    
    def _analyze_trade_regrets(self, trade: "Trade") -> list[str]:
        """
        Analyze a single trade for regret points.
        
        Args:
            trade: Trade to analyze
            
        Returns:
            list: List of regret narratives
        """
        regrets = []
        
        if trade.is_open or not trade.close_profit:
            return regrets
        
        pair = trade.pair
        profit_pct = trade.close_profit * 100
        
        # Check if trade was profitable but exited early
        # (This would require peak price tracking, simulate for now)
        if profit_pct > 0:
            # Simulate: could we have made more?
            # In real implementation, compare close_rate with peak_rate
            if profit_pct < 5:  # Small win
                regrets.append(
                    f"- REGRET: {pair} - Made {profit_pct:.2f}% but could have held longer "
                    f"(exited too conservatively?)"
                )
        
        # Check if we cut losses too late
        elif profit_pct < -3:  # Significant loss
            regrets.append(
                f"- REGRET: {pair} - Lost {abs(profit_pct):.2f}%, should have cut earlier "
                f"(stop loss not tight enough?)"
            )
        
        # Check position sizing
        # If trade was very profitable, was position too small?
        if profit_pct > 10:
            regrets.append(
                f"- REGRET: {pair} - Great trade ({profit_pct:.2f}%) but position was only "
                f"{trade.stake_amount:.0f} - could have made 2-3x more with larger size"
            )
        
        return regrets
    
    def _identify_regret_patterns(
        self,
        actual_trades: list["Trade"],
        shadow_trades: list[dict[str, Any]] | None,
        missed_opportunities: list[dict[str, Any]] | None,
    ) -> list[str]:
        """
        Identify recurring regret patterns.
        
        Args:
            actual_trades: Actual trades
            shadow_trades: Shadow trades
            missed_opportunities: Missed opportunities
            
        Returns:
            list: List of pattern descriptions
        """
        patterns = []
        
        # Pattern: Too conservative on exits
        early_exits = sum(
            1 for t in actual_trades 
            if not t.is_open and t.close_profit and 0 < t.close_profit < 0.05
        )
        if early_exits > len(actual_trades) * 0.3:
            patterns.append(
                f"- PATTERN: Exiting too early on {early_exits} trades "
                f"({early_exits/len(actual_trades)*100:.0f}% of trades). "
                "Consider trailing stops to capture more upside."
            )
        
        # Pattern: Not taking enough winning setups
        if shadow_trades and len(shadow_trades) > len(actual_trades):
            winning_shadows = sum(
                1 for s in shadow_trades if s.get('potential_profit', 0) > 0
            )
            patterns.append(
                f"- PATTERN: Left {winning_shadows} potentially winning trades untaken. "
                "Risk limits too tight or entry criteria too strict?"
            )
        
        # Pattern: Cutting losses too late
        big_losses = sum(
            1 for t in actual_trades
            if not t.is_open and t.close_profit and t.close_profit < -0.05
        )
        if big_losses > 0:
            patterns.append(
                f"- PATTERN: {big_losses} trades lost >5%. "
                "Stop losses not working or being overridden?"
            )
        
        # Pattern: Position sizing mismatches
        # Winners with small positions = regret
        closed = [t for t in actual_trades if not t.is_open and t.close_profit]
        if closed:
            avg_stake = sum(t.stake_amount for t in closed) / len(closed)
            big_winners_small_pos = [
                t for t in closed 
                if t.close_profit > 0.1 and t.stake_amount < avg_stake * 0.8
            ]
            if big_winners_small_pos:
                patterns.append(
                    f"- PATTERN: {len(big_winners_small_pos)} big winners had below-average "
                    "position sizes. Missing conviction signals or risk allocation issues?"
                )
        
        # Add catch-all insights
        if not patterns:
            patterns.append("- No major regret patterns detected in this session")
        
        patterns.append(
            "- INSIGHT: Review these patterns when refining strategy parameters"
        )
        
        return patterns
