"""
Knowledge Graph Module for Trade Analysis

This module provides knowledge graph generation for post-mortem analysis of trades,
integrating the graph generation capabilities from https://github.com/rkendel1/graph

Features:
- Post-backtest/replay analysis
- LLM-generated "lessons learned" from trades
- Visual knowledge graphs of trading patterns
- Relationship inference between failed trades and market conditions

Usage:
    from freqtrade.knowledge_graph import KnowledgeGraphGenerator
    
    # Initialize with config
    kg = KnowledgeGraphGenerator(config)
    
    # Generate from trades
    results = kg.generate_from_trades(trades, session_metadata)
"""

try:
    from freqtrade.knowledge_graph.generator import KnowledgeGraphGenerator
    from freqtrade.knowledge_graph.trade_analyzer import TradeAnalyzer
    
    __all__ = ['KnowledgeGraphGenerator', 'TradeAnalyzer']
except ImportError:
    # If optional dependencies are not installed, module is unavailable
    __all__ = []
