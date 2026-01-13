"""
Tests for knowledge graph configuration.
"""

from freqtrade.knowledge_graph.config import (
    get_default_kg_config,
    merge_kg_config,
    validate_kg_config,
)


def test_get_default_kg_config():
    """Test that default config is returned correctly."""
    config = get_default_kg_config()
    
    assert config is not None
    assert "enabled" in config
    assert "llm" in config
    assert "output" in config
    assert config["enabled"] is False


def test_merge_kg_config_with_none():
    """Test merging with None returns defaults."""
    config = merge_kg_config(None)
    
    assert config is not None
    assert "llm" in config
    assert config["llm"]["model"] == "llama3.2"


def test_merge_kg_config_with_override():
    """Test that user config overrides defaults."""
    user_config = {
        "enabled": True,
        "llm": {
            "model": "gpt-4",
        },
    }
    
    config = merge_kg_config(user_config)
    
    assert config["enabled"] is True
    assert config["llm"]["model"] == "gpt-4"
    # Other defaults should still be present
    assert "base_url" in config["llm"]


def test_validate_kg_config_valid():
    """Test validation of valid config."""
    config = get_default_kg_config()
    
    assert validate_kg_config(config) is True


def test_validate_kg_config_missing_llm():
    """Test validation fails with missing llm config."""
    config = {
        "output": {
            "directory": "exports",
        },
    }
    
    assert validate_kg_config(config) is False


def test_validate_kg_config_missing_output():
    """Test validation fails with missing output config."""
    config = {
        "llm": {
            "model": "llama3.2",
            "base_url": "http://localhost:11434",
        },
    }
    
    assert validate_kg_config(config) is False


def test_validate_kg_config_incomplete_llm():
    """Test validation fails with incomplete llm config."""
    config = {
        "llm": {
            "model": "llama3.2",
            # Missing base_url
        },
        "output": {
            "directory": "exports",
        },
    }
    
    assert validate_kg_config(config) is False
