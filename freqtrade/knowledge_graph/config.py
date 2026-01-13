"""
Configuration management for knowledge graph generation.
"""

from pathlib import Path
from typing import Any


def get_default_kg_config() -> dict[str, Any]:
    """
    Get default configuration for knowledge graph generation.
    
    Returns:
        dict: Default configuration settings
    """
    return {
        "enabled": False,
        "llm": {
            "model": "llama3.2",  # Default Ollama model
            "api_key": "sk-1234",  # Dummy key for Ollama
            "base_url": "http://localhost:11434/v1/chat/completions",
            "max_tokens": 8192,
            "temperature": 0.2,
        },
        "chunking": {
            "chunk_size": 200,  # Number of words per chunk
            "overlap": 20,  # Number of words to overlap between chunks
        },
        "standardization": {
            "enabled": True,
            "use_llm_for_entities": True,
        },
        "inference": {
            "enabled": True,
            "use_llm_for_inference": True,
            "apply_transitive": True,
        },
        "output": {
            "directory": "exports/knowledge_graphs",
            "format": "html",  # html or json
        },
    }


def merge_kg_config(user_config: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Merge user configuration with defaults.
    
    Args:
        user_config: User-provided configuration (optional)
        
    Returns:
        dict: Merged configuration
    """
    config = get_default_kg_config()
    
    if user_config:
        # Deep merge user config
        for key, value in user_config.items():
            if isinstance(value, dict) and key in config:
                config[key].update(value)
            else:
                config[key] = value
    
    return config


def validate_kg_config(config: dict[str, Any]) -> bool:
    """
    Validate knowledge graph configuration.
    
    Args:
        config: Configuration to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    required_keys = ["llm", "output"]
    
    for key in required_keys:
        if key not in config:
            return False
    
    # Validate LLM config
    llm_required = ["model", "base_url"]
    for key in llm_required:
        if key not in config["llm"]:
            return False
    
    return True
