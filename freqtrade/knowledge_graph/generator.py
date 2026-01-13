"""
Knowledge Graph Generator - Main orchestrator for KG creation from trade data.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from freqtrade.knowledge_graph.config import merge_kg_config, validate_kg_config
from freqtrade.knowledge_graph.llm import call_llm, chunk_text, extract_json_from_text
from freqtrade.knowledge_graph.prompts import prompt_factory
from freqtrade.knowledge_graph.trade_analyzer import TradeAnalyzer
from freqtrade.knowledge_graph.visualization import (
    save_triples_json,
    visualize_knowledge_graph,
)

if TYPE_CHECKING:
    from freqtrade.persistence import Trade

logger = logging.getLogger(__name__)


class KnowledgeGraphGenerator:
    """
    Main class for generating knowledge graphs from trading data.
    
    This integrates the graph generation pipeline from https://github.com/rkendel1/graph
    with trading-specific analysis.
    """
    
    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize the knowledge graph generator.
        
        Args:
            config: Configuration dictionary (optional)
        """
        self.config = merge_kg_config(config)
        
        if not validate_kg_config(self.config):
            raise ValueError("Invalid knowledge graph configuration")
        
        self.trade_analyzer = TradeAnalyzer()
    
    def generate_from_trades(
        self,
        trades: list["Trade"],
        session_metadata: dict[str, Any] | None = None,
        output_name: str = "trade_session",
    ) -> dict[str, Any]:
        """
        Generate a knowledge graph from trading session data.
        
        Args:
            trades: List of trades from the session
            session_metadata: Optional metadata (regime, market conditions, etc.)
            output_name: Base name for output files
            
        Returns:
            dict: Results including stats and output paths
        """
        if not self.config.get("enabled", False):
            logger.info("Knowledge graph generation is disabled")
            return {"enabled": False}
        
        logger.info(f"Generating knowledge graph from {len(trades)} trades")
        
        # Step 1: Generate narrative from trades
        narrative = self.trade_analyzer.generate_session_narrative(
            trades, session_metadata
        )
        
        logger.info("Generated trade narrative")
        
        # Step 2: Extract triples from narrative
        triples = self._extract_triples_from_text(narrative)
        
        if not triples:
            logger.warning("No triples extracted from trade narrative")
            return {
                "enabled": True,
                "success": False,
                "error": "No triples extracted",
            }
        
        logger.info(f"Extracted {len(triples)} triples")
        
        # Step 3: Generate outputs
        output_dir = Path(self.config["output"]["directory"])
        output_format = self.config["output"]["format"]
        
        results = {
            "enabled": True,
            "success": True,
            "stats": {
                "trades": len(trades),
                "triples": len(triples),
            },
        }
        
        # Save JSON
        json_path = output_dir / f"{output_name}_triples.json"
        save_triples_json(triples, json_path)
        results["json_path"] = str(json_path)
        
        # Save narrative
        narrative_path = output_dir / f"{output_name}_narrative.txt"
        narrative_path.parent.mkdir(parents=True, exist_ok=True)
        with open(narrative_path, 'w') as f:
            f.write(narrative)
        results["narrative_path"] = str(narrative_path)
        
        # Generate visualization if format is HTML
        if output_format == "html":
            try:
                html_path = output_dir / f"{output_name}_graph.html"
                stats = visualize_knowledge_graph(
                    triples,
                    html_path,
                    title=f"Trading Session - {output_name}",
                )
                results["html_path"] = str(html_path)
                results["stats"].update(stats)
                
                logger.info(
                    f"Knowledge graph created: {stats['nodes']} nodes, "
                    f"{stats['edges']} edges, {stats['communities']} communities"
                )
            except ImportError as e:
                logger.warning(f"Could not create visualization: {e}")
                results["visualization_error"] = str(e)
        
        return results
    
    def generate_regret_analysis(
        self,
        actual_trades: list["Trade"],
        shadow_trades: list[dict[str, Any]] | None = None,
        missed_opportunities: list[dict[str, Any]] | None = None,
        output_name: str = "regret_analysis",
    ) -> dict[str, Any]:
        """
        Generate knowledge graph from regret analysis.
        
        Args:
            actual_trades: Actual trades executed
            shadow_trades: Hypothetical trades not taken
            missed_opportunities: Missed opportunities
            output_name: Base name for output files
            
        Returns:
            dict: Results including stats and output paths
        """
        if not self.config.get("enabled", False):
            return {"enabled": False}
        
        logger.info("Generating regret analysis knowledge graph")
        
        # Generate regret narrative
        narrative = self.trade_analyzer.generate_regret_analysis(
            actual_trades, shadow_trades, missed_opportunities
        )
        
        # Extract triples
        triples = self._extract_triples_from_text(narrative, use_trade_prompts=True)
        
        if not triples:
            return {
                "enabled": True,
                "success": False,
                "error": "No triples extracted",
            }
        
        # Generate outputs
        output_dir = Path(self.config["output"]["directory"])
        
        results = {
            "enabled": True,
            "success": True,
            "stats": {
                "actual_trades": len(actual_trades),
                "shadow_trades": len(shadow_trades) if shadow_trades else 0,
                "missed_opportunities": len(missed_opportunities) if missed_opportunities else 0,
                "triples": len(triples),
            },
        }
        
        # Save outputs
        json_path = output_dir / f"{output_name}_triples.json"
        save_triples_json(triples, json_path)
        results["json_path"] = str(json_path)
        
        if self.config["output"]["format"] == "html":
            try:
                html_path = output_dir / f"{output_name}_graph.html"
                stats = visualize_knowledge_graph(
                    triples, html_path, title=f"Regret Analysis - {output_name}"
                )
                results["html_path"] = str(html_path)
                results["stats"].update(stats)
            except ImportError as e:
                logger.warning(f"Could not create visualization: {e}")
        
        return results
    
    def _extract_triples_from_text(
        self,
        text: str,
        use_trade_prompts: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Extract SPO triples from text using LLM.
        
        Args:
            text: Text to analyze
            use_trade_prompts: Whether to use trading-specific prompts
            
        Returns:
            list: Extracted triples
        """
        # Get prompts
        if use_trade_prompts:
            system_prompt = prompt_factory.get_prompt("trade_analysis_system")
            user_prompt = prompt_factory.get_prompt("trade_analysis_user")
        else:
            system_prompt = prompt_factory.get_prompt("main_system")
            user_prompt = prompt_factory.get_prompt("main_user")
        
        # Chunk text if needed
        chunk_size = self.config["chunking"]["chunk_size"]
        overlap = self.config["chunking"]["overlap"]
        
        chunks = chunk_text(text, chunk_size, overlap)
        logger.info(f"Processing {len(chunks)} text chunks")
        
        all_triples = []
        
        # Process each chunk
        for i, chunk in enumerate(chunks):
            logger.debug(f"Processing chunk {i+1}/{len(chunks)}")
            
            prompt = user_prompt + f"\n```\n{chunk}\n```"
            
            try:
                response = call_llm(
                    model=self.config["llm"]["model"],
                    user_prompt=prompt,
                    api_key=self.config["llm"]["api_key"],
                    system_prompt=system_prompt,
                    max_tokens=self.config["llm"]["max_tokens"],
                    temperature=self.config["llm"]["temperature"],
                    base_url=self.config["llm"]["base_url"],
                )
                
                triples = extract_json_from_text(response)
                
                if triples:
                    all_triples.extend(triples)
                    logger.debug(f"Extracted {len(triples)} triples from chunk {i+1}")
            except Exception as e:
                logger.error(f"Error processing chunk {i+1}: {e}")
                continue
        
        return all_triples
