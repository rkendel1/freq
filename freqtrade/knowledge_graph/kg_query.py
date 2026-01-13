"""
Knowledge Graph Query Utility - Query regret patterns from stored knowledge graph data.

This module provides lightweight utilities to query historical regret patterns
from the knowledge graph database for use in DSPy-powered ExploitModules.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class KGQueryError(Exception):
    """Exception raised for errors during KG query operations."""
    pass


def query_recent_regrets(
    symbol: str,
    pattern_types: list[str],
    limit: int = 5,
    db_path: str | None = None,
) -> str:
    """
    Query recent regret patterns for a given symbol from the knowledge graph.
    
    This function searches stored regret narratives and patterns from past trades
    to help DSPy make more informed decisions about conviction, sizing, and timing.
    
    Args:
        symbol: Trading pair symbol (e.g., "BTC/USDT")
        pattern_types: List of regret pattern types to search for
                      Examples: ["early exit", "missed breakout", "over-sizing",
                                "stop loss failure", "tight stop"]
        limit: Maximum number of regret patterns to return (default: 5)
        db_path: Path to the knowledge graph database. If None, uses default location.
    
    Returns:
        str: Formatted text block of relevant regrets/patterns as bullet points.
             Returns empty string if no regrets found or on error.
    
    Examples:
        >>> regrets = query_recent_regrets(
        ...     symbol="BTC/USDT",
        ...     pattern_types=["early exit", "missed breakout"],
        ...     limit=3
        ... )
        >>> print(regrets)
        Historical Regret Patterns for BTC/USDT:
        - Early exit on BTC/USDT: Closed at 2% gain but price reached 8% shortly after
        - Missed breakout: Signal appeared but was filtered due to cooldown period
    """
    # Default database path
    if db_path is None:
        db_path = "user_data/knowledge_graph/regrets.db"
    
    db_file = Path(db_path)
    
    # If database doesn't exist, return empty (no regrets stored yet)
    if not db_file.exists():
        logger.debug(f"KG database not found at {db_path}, no regrets available")
        return ""
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(str(db_file))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Build search query for regret patterns
        # Use LIKE for flexible pattern matching
        pattern_conditions = " OR ".join(
            ["LOWER(pattern_type) LIKE ?"] * len(pattern_types)
        )
        
        # Prepare pattern search terms (add wildcards for partial matching)
        pattern_params = [f"%{pt.lower()}%" for pt in pattern_types]
        
        # Query for regret patterns matching the symbol and pattern types
        query = f"""
            SELECT 
                pattern_type,
                description,
                timestamp,
                metadata
            FROM regret_patterns
            WHERE symbol = ?
              AND ({pattern_conditions})
            ORDER BY timestamp DESC
            LIMIT ?
        """
        
        params = [symbol] + pattern_params + [limit]
        cursor.execute(query, params)
        
        results = cursor.fetchall()
        conn.close()
        
        # Format results as readable text
        if not results:
            logger.debug(f"No regret patterns found for {symbol} with types {pattern_types}")
            return ""
        
        # Build formatted output
        lines = [f"Historical Regret Patterns for {symbol}:"]
        
        for row in results:
            pattern_type = row['pattern_type']
            description = row['description']
            # Format: "- Pattern Type: Description"
            lines.append(f"- {pattern_type}: {description}")
        
        formatted_output = "\n".join(lines)
        logger.debug(f"Found {len(results)} regret patterns for {symbol}")
        
        return formatted_output
        
    except sqlite3.Error as e:
        logger.error(f"Database error querying regrets: {e}", exc_info=True)
        return ""
    except Exception as e:
        logger.error(f"Unexpected error querying regrets: {e}", exc_info=True)
        return ""


def store_regret_pattern(
    symbol: str,
    pattern_type: str,
    description: str,
    metadata: dict[str, Any] | None = None,
    db_path: str | None = None,
) -> bool:
    """
    Store a new regret pattern in the knowledge graph database.
    
    This function is called during post-trade analysis to record regret patterns
    that can later be queried by DSPy modules.
    
    Args:
        symbol: Trading pair symbol (e.g., "BTC/USDT")
        pattern_type: Type of regret pattern (e.g., "early exit", "missed breakout")
        description: Human-readable description of the regret
        metadata: Optional additional metadata (dict will be stored as JSON)
        db_path: Path to the knowledge graph database. If None, uses default location.
    
    Returns:
        bool: True if stored successfully, False otherwise
    
    Examples:
        >>> success = store_regret_pattern(
        ...     symbol="BTC/USDT",
        ...     pattern_type="early exit",
        ...     description="Closed at 2% gain but price reached 8% within 2 hours",
        ...     metadata={"actual_profit": 0.02, "potential_profit": 0.08}
        ... )
    """
    # Default database path
    if db_path is None:
        db_path = "user_data/knowledge_graph/regrets.db"
    
    db_file = Path(db_path)
    
    # Create directory if it doesn't exist
    db_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS regret_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                description TEXT NOT NULL,
                metadata TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index separately
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_symbol_pattern 
            ON regret_patterns (symbol, pattern_type)
        """)
        
        # Create full-text search virtual table for better search performance
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS regret_patterns_fts 
            USING fts5(
                symbol,
                pattern_type,
                description,
                content=regret_patterns,
                content_rowid=id
            )
        """)
        
        # Convert metadata dict to JSON string if provided
        import json
        metadata_json = json.dumps(metadata) if metadata else None
        
        # Insert the regret pattern
        cursor.execute("""
            INSERT INTO regret_patterns (symbol, pattern_type, description, metadata)
            VALUES (?, ?, ?, ?)
        """, (symbol, pattern_type, description, metadata_json))
        
        # Update FTS index
        cursor.execute("""
            INSERT INTO regret_patterns_fts (rowid, symbol, pattern_type, description)
            VALUES (?, ?, ?, ?)
        """, (cursor.lastrowid, symbol, pattern_type, description))
        
        conn.commit()
        conn.close()
        
        logger.debug(f"Stored regret pattern: {pattern_type} for {symbol}")
        return True
        
    except sqlite3.Error as e:
        logger.error(f"Database error storing regret pattern: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Unexpected error storing regret pattern: {e}", exc_info=True)
        return False


# Stub for future vector search implementation
def query_regrets_vector_search(
    symbol: str,
    query_text: str,
    limit: int = 5,
    db_path: str | None = None,
) -> str:
    """
    Query regret patterns using vector similarity search (FUTURE).
    
    This is a placeholder for future enhancement using embeddings
    to find semantically similar regret patterns.
    
    Args:
        symbol: Trading pair symbol
        query_text: Natural language query describing the current situation
        limit: Maximum number of results to return
        db_path: Path to the knowledge graph database
    
    Returns:
        str: Formatted text block of relevant regrets (currently returns empty string)
    
    Note:
        This feature requires vector embeddings and is not yet implemented.
        Use query_recent_regrets() for now.
    """
    logger.warning(
        "Vector search not yet implemented. Use query_recent_regrets() instead."
    )
    return ""
