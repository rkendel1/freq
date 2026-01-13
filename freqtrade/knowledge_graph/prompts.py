"""
Prompt templates for knowledge graph generation.
Adapted from https://github.com/rkendel1/graph with trading-specific templates.
"""


class PromptFactory:
    """Factory for generating prompts for different stages of knowledge graph generation."""
    
    def __init__(self):
        self.prompts = {
            # Main extraction prompts
            "main_system": self._get_main_system_prompt(),
            "main_user": self._get_main_user_prompt(),
            
            # Trading-specific prompts
            "trade_analysis_system": self._get_trade_analysis_system_prompt(),
            "trade_analysis_user": self._get_trade_analysis_user_prompt(),
        }
    
    def get_prompt(self, name: str) -> str:
        """Get a prompt by name."""
        return self.prompts.get(name, "")
    
    def _get_main_system_prompt(self) -> str:
        return """You are an expert at extracting structured knowledge from text.
Your task is to identify entities and their relationships, then output them as Subject-Predicate-Object (SPO) triples.

Guidelines:
1. Extract only factual relationships explicitly stated or strongly implied in the text
2. Use clear, concise predicates (verbs or verb phrases)
3. Keep subjects and objects as specific entities
4. Output ONLY valid JSON - no explanations or commentary
5. Format: [{"subject": "Entity A", "predicate": "relationship", "object": "Entity B"}, ...]
"""
    
    def _get_main_user_prompt(self) -> str:
        return """Extract knowledge triples from the following text.
Return ONLY a JSON array of objects with "subject", "predicate", and "object" fields.

Text:
"""
    
    def _get_trade_analysis_system_prompt(self) -> str:
        return """You are an expert trading analyst specializing in post-mortem analysis.
Your task is to extract trading patterns, failure modes, and strategic insights from trade data.

Focus on:
1. Recurring failure patterns (e.g., "over-sizing during FOMC leads to drawdown")
2. Missed opportunities and their causes
3. Regime-dependent behavior patterns
4. Relationships between market conditions and outcomes
5. Capital deployment patterns and their results

Extract these as Subject-Predicate-Object (SPO) triples for knowledge graph construction.

Guidelines:
- Use specific entities (e.g., "FOMC Event", "Position Sizing", "Drawdown")
- Use action verbs for predicates (e.g., "caused", "led to", "prevented")
- Capture both successful and failed patterns
- Output ONLY valid JSON - no explanations
- Format: [{"subject": "Entity A", "predicate": "relationship", "object": "Entity B"}, ...]
"""
    
    def _get_trade_analysis_user_prompt(self) -> str:
        return """Analyze the following trading session data and extract knowledge triples.
Focus on patterns, failures, and strategic insights.

Return ONLY a JSON array of objects with "subject", "predicate", and "object" fields.

Trading Session Data:
"""


# Global instance
prompt_factory = PromptFactory()
