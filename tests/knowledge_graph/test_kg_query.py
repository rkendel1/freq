"""
Tests for kg_query module.
"""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from freqtrade.knowledge_graph.kg_query import (
    query_recent_regrets,
    store_regret_pattern,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_regrets.db"
        yield str(db_path)


def test_query_regrets_no_db():
    """Test querying regrets when database doesn't exist."""
    result = query_recent_regrets(
        symbol="BTC/USDT",
        pattern_types=["early exit"],
        db_path="/nonexistent/path/regrets.db"
    )
    
    assert result == ""


def test_store_and_query_regret_pattern(temp_db):
    """Test storing and querying a regret pattern."""
    # Store a regret pattern
    success = store_regret_pattern(
        symbol="BTC/USDT",
        pattern_type="early exit",
        description="Closed at 2% gain but price reached 8% shortly after",
        metadata={"actual_profit": 0.02, "potential_profit": 0.08},
        db_path=temp_db
    )
    
    assert success is True
    
    # Query it back
    result = query_recent_regrets(
        symbol="BTC/USDT",
        pattern_types=["early exit"],
        limit=5,
        db_path=temp_db
    )
    
    assert result != ""
    assert "BTC/USDT" in result
    assert "early exit" in result.lower()
    assert "Closed at 2% gain" in result


def test_store_multiple_patterns(temp_db):
    """Test storing multiple regret patterns."""
    patterns = [
        {
            "symbol": "BTC/USDT",
            "pattern_type": "early exit",
            "description": "Exited too early on uptrend"
        },
        {
            "symbol": "BTC/USDT",
            "pattern_type": "missed breakout",
            "description": "Didn't take breakout signal due to cooldown"
        },
        {
            "symbol": "ETH/USDT",
            "pattern_type": "over-sizing",
            "description": "Position too large, increased risk"
        }
    ]
    
    for pattern in patterns:
        success = store_regret_pattern(db_path=temp_db, **pattern)
        assert success is True
    
    # Query BTC/USDT patterns
    result = query_recent_regrets(
        symbol="BTC/USDT",
        pattern_types=["early exit", "missed breakout"],
        limit=5,
        db_path=temp_db
    )
    
    assert result != ""
    assert "early exit" in result.lower() or "missed breakout" in result.lower()
    assert "BTC/USDT" in result
    
    # Query ETH/USDT patterns
    result_eth = query_recent_regrets(
        symbol="ETH/USDT",
        pattern_types=["over-sizing"],
        limit=5,
        db_path=temp_db
    )
    
    assert result_eth != ""
    assert "ETH/USDT" in result_eth
    assert "over-sizing" in result_eth.lower()


def test_query_with_limit(temp_db):
    """Test that query respects the limit parameter."""
    # Store 10 patterns
    for i in range(10):
        store_regret_pattern(
            symbol="BTC/USDT",
            pattern_type="early exit",
            description=f"Early exit pattern {i}",
            db_path=temp_db
        )
    
    # Query with limit=3
    result = query_recent_regrets(
        symbol="BTC/USDT",
        pattern_types=["early exit"],
        limit=3,
        db_path=temp_db
    )
    
    assert result != ""
    # Count the number of bullet points (lines starting with '- ')
    lines = [line for line in result.split('\n') if line.strip().startswith('- ')]
    assert len(lines) <= 3


def test_query_no_matching_patterns(temp_db):
    """Test querying when no patterns match."""
    # Store a pattern for BTC/USDT
    store_regret_pattern(
        symbol="BTC/USDT",
        pattern_type="early exit",
        description="Some pattern",
        db_path=temp_db
    )
    
    # Query for different symbol
    result = query_recent_regrets(
        symbol="ETH/USDT",
        pattern_types=["early exit"],
        db_path=temp_db
    )
    
    assert result == ""


def test_query_partial_pattern_match(temp_db):
    """Test that pattern matching is flexible (LIKE query)."""
    # Store pattern with "exit" in type
    store_regret_pattern(
        symbol="BTC/USDT",
        pattern_type="early exit from position",
        description="Exited too early",
        db_path=temp_db
    )
    
    # Query with just "exit" - should match
    result = query_recent_regrets(
        symbol="BTC/USDT",
        pattern_types=["exit"],
        db_path=temp_db
    )
    
    assert result != ""
    assert "BTC/USDT" in result


def test_store_pattern_with_metadata(temp_db):
    """Test storing pattern with complex metadata."""
    metadata = {
        "actual_profit": 0.02,
        "potential_profit": 0.08,
        "exit_reason": "roi",
        "duration_hours": 2.5
    }
    
    success = store_regret_pattern(
        symbol="BTC/USDT",
        pattern_type="early exit",
        description="Test pattern",
        metadata=metadata,
        db_path=temp_db
    )
    
    assert success is True
    
    # Verify it was stored by querying
    result = query_recent_regrets(
        symbol="BTC/USDT",
        pattern_types=["early exit"],
        db_path=temp_db
    )
    
    assert result != ""


def test_database_creation_on_first_store(temp_db):
    """Test that database and tables are created on first store."""
    # Verify database doesn't exist
    assert not Path(temp_db).exists()
    
    # Store pattern - should create database
    success = store_regret_pattern(
        symbol="BTC/USDT",
        pattern_type="test",
        description="Test pattern",
        db_path=temp_db
    )
    
    assert success is True
    assert Path(temp_db).exists()
    
    # Verify table structure
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    # Check that regret_patterns table exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='regret_patterns'
    """)
    result = cursor.fetchone()
    assert result is not None
    
    conn.close()


def test_query_empty_database(temp_db):
    """Test querying an empty database."""
    # Create empty database
    store_regret_pattern(
        symbol="BTC/USDT",
        pattern_type="test",
        description="Test",
        db_path=temp_db
    )
    
    # Clear all data
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM regret_patterns")
    conn.commit()
    conn.close()
    
    # Query should return empty
    result = query_recent_regrets(
        symbol="BTC/USDT",
        pattern_types=["early exit"],
        db_path=temp_db
    )
    
    assert result == ""
