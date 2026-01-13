#!/usr/bin/env python3
"""
Example script demonstrating knowledge graph generation from trades.

This example shows how to use the knowledge graph module to generate
post-mortem analysis from trading sessions.

Requirements:
    pip install networkx pyvis python-louvain

Usage:
    python examples/knowledge_graph_example.py
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

from freqtrade.knowledge_graph import KnowledgeGraphGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def create_mock_trades():
    """
    Create mock trades for demonstration.
    
    In real usage, you would get trades from the database:
        from freqtrade.persistence import Trade
        trades = Trade.get_trades().filter(Trade.is_open == False).all()
    """
    trades = []
    
    # Create a mix of winning and losing trades
    trade_scenarios = [
        # Winners
        ("BTC/USDT", False, 50000, 52000, 0.04, "roi", 2),
        ("ETH/USDT", False, 3000, 3150, 0.05, "roi", 1.5),
        ("SOL/USDT", False, 100, 112, 0.12, "roi", 3),
        
        # Losers
        ("ADA/USDT", False, 0.5, 0.47, -0.06, "stop_loss", 0.5),
        ("DOT/USDT", False, 7.0, 6.8, -0.03, "stop_loss", 1),
        
        # Small winners (early exit regrets)
        ("LINK/USDT", False, 15, 15.3, 0.02, "roi", 0.25),
        ("AVAX/USDT", False, 35, 35.7, 0.02, "roi", 0.3),
    ]
    
    base_time = datetime.now() - timedelta(hours=12)
    
    for i, (pair, is_short, entry, exit, profit, reason, duration) in enumerate(trade_scenarios):
        trade = MagicMock()
        trade.pair = pair
        trade.is_short = is_short
        trade.is_open = False
        trade.open_rate = entry
        trade.close_rate = exit
        trade.close_profit = profit
        trade.exit_reason = reason
        trade.stake_amount = 1000
        trade.open_date = base_time + timedelta(hours=i)
        trade.close_date = base_time + timedelta(hours=i + duration)
        
        trades.append(trade)
    
    return trades


def example_basic_session_analysis():
    """Example: Basic session analysis."""
    logger.info("=" * 60)
    logger.info("Example 1: Basic Session Analysis")
    logger.info("=" * 60)
    
    # Configuration
    config = {
        "enabled": True,
        "llm": {
            "model": "llama3.2",
            "api_key": "sk-1234",
            "base_url": "http://localhost:11434/v1/chat/completions",
            "max_tokens": 8192,
            "temperature": 0.2,
        },
        "output": {
            "directory": "exports/knowledge_graphs",
            "format": "html",
        },
    }
    
    # Note: This example won't actually call the LLM since we're just demonstrating
    # In real usage, you would need Ollama or another LLM API running
    
    # Create generator
    kg = KnowledgeGraphGenerator(config)
    
    # Get mock trades
    trades = create_mock_trades()
    
    logger.info(f"Analyzing {len(trades)} trades...")
    
    # Generate knowledge graph (will fail without LLM, but shows the interface)
    try:
        results = kg.generate_from_trades(
            trades,
            session_metadata={"regime": "high_volatility"},
            output_name=f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        )
        
        if results.get("success"):
            logger.info("Knowledge graph generated successfully!")
            logger.info(f"  - HTML: {results.get('html_path')}")
            logger.info(f"  - JSON: {results.get('json_path')}")
            logger.info(f"  - Stats: {results.get('stats')}")
    except Exception as e:
        logger.warning(f"LLM call failed (expected without Ollama): {e}")
        logger.info("This is expected if you don't have Ollama or an LLM API running")


def example_regret_analysis():
    """Example: Regret analysis with shadow trades."""
    logger.info("\n" + "=" * 60)
    logger.info("Example 2: Regret Analysis")
    logger.info("=" * 60)
    
    config = {
        "enabled": True,
        "llm": {
            "model": "llama3.2",
            "api_key": "sk-1234",
            "base_url": "http://localhost:11434/v1/chat/completions",
        },
        "output": {
            "directory": "exports/knowledge_graphs",
            "format": "html",
        },
    }
    
    kg = KnowledgeGraphGenerator(config)
    
    # Actual trades
    actual_trades = create_mock_trades()[:3]  # Just winners for this example
    
    # Shadow trades - opportunities we didn't take
    shadow_trades = [
        {
            "pair": "MATIC/USDT",
            "direction": "long",
            "potential_profit": 0.15,
            "skip_reason": "Risk limit reached",
        },
        {
            "pair": "UNI/USDT",
            "direction": "long",
            "potential_profit": 0.08,
            "skip_reason": "Signal confidence too low",
        },
    ]
    
    # Missed opportunities - setups we should have caught
    missed_opportunities = [
        {
            "reason": "Breakout signal fired but we were in cooldown",
            "potential_profit": 0.12,
        },
        {
            "reason": "Entry criteria too strict, missed the move",
            "potential_profit": 0.07,
        },
    ]
    
    logger.info("Generating regret analysis...")
    logger.info(f"  - Actual trades: {len(actual_trades)}")
    logger.info(f"  - Shadow trades: {len(shadow_trades)}")
    logger.info(f"  - Missed opportunities: {len(missed_opportunities)}")
    
    try:
        results = kg.generate_regret_analysis(
            actual_trades,
            shadow_trades,
            missed_opportunities,
            output_name=f"regret_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        )
        
        if results.get("success"):
            logger.info("Regret analysis generated successfully!")
            logger.info(f"  - Stats: {results.get('stats')}")
    except Exception as e:
        logger.warning(f"LLM call failed (expected without Ollama): {e}")


def example_narrative_only():
    """Example: Generate narrative without LLM."""
    logger.info("\n" + "=" * 60)
    logger.info("Example 3: Narrative Generation (No LLM needed)")
    logger.info("=" * 60)
    
    from freqtrade.knowledge_graph.trade_analyzer import TradeAnalyzer
    
    analyzer = TradeAnalyzer()
    trades = create_mock_trades()
    
    # Generate session narrative
    narrative = analyzer.generate_session_narrative(
        trades,
        session_metadata={
            "regime": "high_volatility",
            "market": "crypto",
        }
    )
    
    logger.info("\nGenerated Narrative:")
    logger.info("-" * 60)
    print(narrative)
    logger.info("-" * 60)
    
    # Generate regret analysis narrative
    shadow_trades = [
        {
            "pair": "MATIC/USDT",
            "direction": "long",
            "potential_profit": 0.15,
            "skip_reason": "Risk limit reached",
        },
    ]
    
    regret_narrative = analyzer.generate_regret_analysis(
        trades,
        shadow_trades=shadow_trades,
        missed_opportunities=[],
    )
    
    logger.info("\nRegret Analysis Narrative:")
    logger.info("-" * 60)
    print(regret_narrative)
    logger.info("-" * 60)


if __name__ == "__main__":
    logger.info("Knowledge Graph Examples\n")
    
    # Example 1: Basic session analysis (requires LLM)
    example_basic_session_analysis()
    
    # Example 2: Regret analysis (requires LLM)
    example_regret_analysis()
    
    # Example 3: Narrative generation only (no LLM required)
    example_narrative_only()
    
    logger.info("\n" + "=" * 60)
    logger.info("Examples completed!")
    logger.info("=" * 60)
    logger.info("\nTo use with a real LLM:")
    logger.info("  1. Install Ollama: https://ollama.ai")
    logger.info("  2. Run: ollama run llama3.2")
    logger.info("  3. Re-run this script")
