"""
Example: Integration with backtesting workflow.

This shows how to generate knowledge graphs after a backtest completes.
"""

import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def post_backtest_kg_analysis(config: dict, backtest_results: dict):
    """
    Generate knowledge graph analysis after backtest completes.
    
    Args:
        config: Bot configuration including knowledge_graph settings
        backtest_results: Results from backtesting
    """
    # Check if knowledge graph is enabled
    kg_config = config.get("knowledge_graph", {})
    if not kg_config.get("enabled", False):
        logger.info("Knowledge graph generation disabled")
        return
    
    try:
        from freqtrade.knowledge_graph import KnowledgeGraphGenerator
        from freqtrade.persistence import Trade
    except ImportError as e:
        logger.warning(f"Knowledge graph dependencies not available: {e}")
        return
    
    logger.info("Generating post-backtest knowledge graph...")
    
    # Initialize generator
    kg = KnowledgeGraphGenerator(kg_config)
    
    # Get trades from backtest
    trades = Trade.get_trades().filter(Trade.is_open == False).all()
    
    if not trades:
        logger.warning("No closed trades found for analysis")
        return
    
    # Extract metadata from backtest results
    session_metadata = {
        "type": "backtest",
        "timeframe": backtest_results.get("timeframe", "unknown"),
        "start_date": backtest_results.get("backtest_start", ""),
        "end_date": backtest_results.get("backtest_end", ""),
        "pairs": backtest_results.get("pairs", []),
    }
    
    # Generate knowledge graph
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_name = f"backtest_{timestamp}"
    
    results = kg.generate_from_trades(
        trades,
        session_metadata=session_metadata,
        output_name=output_name,
    )
    
    if results.get("success"):
        logger.info("=" * 60)
        logger.info("Knowledge Graph Generated Successfully!")
        logger.info("=" * 60)
        
        if results.get("html_path"):
            logger.info(f"📊 Visualization: {results['html_path']}")
        if results.get("json_path"):
            logger.info(f"📄 Data: {results['json_path']}")
        if results.get("narrative_path"):
            logger.info(f"📝 Narrative: {results['narrative_path']}")
        
        stats = results.get("stats", {})
        logger.info(f"📈 Stats: {stats.get('nodes', 0)} nodes, "
                   f"{stats.get('edges', 0)} edges, "
                   f"{stats.get('communities', 0)} communities")
        logger.info("=" * 60)
    else:
        logger.error("Knowledge graph generation failed")


def post_backtest_regret_analysis(
    config: dict,
    actual_trades: list,
    shadow_trades: list | None = None,
    missed_opportunities: list | None = None,
):
    """
    Generate regret analysis after backtest with shadow trading.
    
    Args:
        config: Bot configuration
        actual_trades: Actual trades executed
        shadow_trades: Hypothetical trades (from what-if scenarios)
        missed_opportunities: Identified missed setups
    """
    kg_config = config.get("knowledge_graph", {})
    if not kg_config.get("enabled", False):
        return
    
    try:
        from freqtrade.knowledge_graph import KnowledgeGraphGenerator
    except ImportError as e:
        logger.warning(f"Knowledge graph not available: {e}")
        return
    
    logger.info("Generating regret analysis...")
    
    kg = KnowledgeGraphGenerator(kg_config)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = kg.generate_regret_analysis(
        actual_trades,
        shadow_trades,
        missed_opportunities,
        output_name=f"regret_{timestamp}",
    )
    
    if results.get("success"):
        logger.info("Regret analysis complete!")
        logger.info(f"Capture rate: {results['stats'].get('capture_rate', 'N/A')}")


# Example: Add to backtesting.py
def integrate_with_backtesting():
    """
    Example of how to integrate with the Backtesting class.
    
    In freqtrade/optimize/backtesting.py, add:
    """
    
    example_integration = """
    # In Backtesting.start() method, after backtest completes:
    
    def start(self) -> Dict[str, Any]:
        # ... existing backtest code ...
        
        # Generate backtest results
        results = self._generate_backtest_results(...)
        
        # Generate knowledge graph if enabled
        if self.config.get("knowledge_graph", {}).get("enabled", False):
            from examples.backtest_kg_integration import post_backtest_kg_analysis
            post_backtest_kg_analysis(self.config, results)
        
        return results
    """
    
    return example_integration


# Example: Configuration
example_config = {
    "max_open_trades": 3,
    "stake_currency": "USDT",
    # ... other config ...
    
    "knowledge_graph": {
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
    },
}


if __name__ == "__main__":
    logger.info("Backtest Knowledge Graph Integration Example")
    logger.info("")
    logger.info("To use this:")
    logger.info("1. Add knowledge_graph config to your config.json")
    logger.info("2. Run backtest normally")
    logger.info("3. Knowledge graph will be generated automatically")
    logger.info("")
    logger.info("Output will be in: exports/knowledge_graphs/")
    logger.info("")
    logger.info("Example integration code:")
    print(integrate_with_backtesting())
