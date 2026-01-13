"""
LLM utilities for knowledge graph generation.
Adapted from https://github.com/rkendel1/graph
"""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def call_llm(
    model: str,
    user_prompt: str,
    api_key: str,
    system_prompt: str | None = None,
    max_tokens: int = 8192,
    temperature: float = 0.2,
    base_url: str = "http://localhost:11434/v1/chat/completions",
) -> str:
    """
    Call an OpenAI-compatible LLM API.
    
    Args:
        model: Model name (e.g., "llama3.2", "gpt-4")
        user_prompt: User prompt text
        api_key: API key
        system_prompt: System prompt (optional)
        max_tokens: Maximum tokens to generate
        temperature: Temperature for generation
        base_url: Base URL for the API
        
    Returns:
        str: LLM response text
        
    Raises:
        ImportError: If requests is not installed
        Exception: If API call fails
    """
    try:
        import requests
    except ImportError:
        raise ImportError(
            "requests library is required for LLM calls. "
            "Install with: pip install requests"
        )
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    
    try:
        response = requests.post(base_url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"LLM API call failed: {e}")
        raise


def extract_json_from_text(text: str) -> list[dict[str, Any]] | None:
    """
    Extract JSON from text that may contain markdown code blocks or other formatting.
    
    Args:
        text: Text potentially containing JSON
        
    Returns:
        list: Extracted JSON data or None if extraction failed
    """
    # Try to find JSON in markdown code blocks
    json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', text, re.DOTALL)
    
    if json_match:
        json_text = json_match.group(1)
    else:
        # Try to extract JSON directly
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if json_match:
            json_text = json_match.group(0)
        else:
            return None
    
    try:
        data = json.loads(json_text)
        if isinstance(data, list):
            return data
        return None
    except json.JSONDecodeError:
        logger.error("Failed to decode JSON from LLM response")
        return None


def chunk_text(text: str, chunk_size: int = 200, overlap: int = 20) -> list[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: Text to chunk
        chunk_size: Number of words per chunk
        overlap: Number of words to overlap between chunks
        
    Returns:
        list: List of text chunks
    """
    words = text.split()
    chunks = []
    
    i = 0
    while i < len(words):
        chunk = words[i:i + chunk_size]
        chunks.append(" ".join(chunk))
        i += chunk_size - overlap
    
    return chunks
