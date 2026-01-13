"""
Tests for LLM utilities.
"""

import json

from freqtrade.knowledge_graph.llm import chunk_text, extract_json_from_text


def test_chunk_text_basic():
    """Test basic text chunking."""
    text = " ".join([f"word{i}" for i in range(100)])
    chunks = chunk_text(text, chunk_size=10, overlap=2)
    
    assert len(chunks) > 0
    assert len(chunks) > 1  # Should create multiple chunks


def test_chunk_text_no_overlap():
    """Test chunking with no overlap."""
    text = " ".join([f"word{i}" for i in range(50)])
    chunks = chunk_text(text, chunk_size=10, overlap=0)
    
    assert len(chunks) == 5  # 50 words / 10 words per chunk


def test_chunk_text_with_overlap():
    """Test chunking with overlap."""
    text = " ".join([f"word{i}" for i in range(30)])
    chunks = chunk_text(text, chunk_size=10, overlap=2)
    
    assert len(chunks) > 0
    # With overlap, should create more chunks than without
    assert len(chunks) > 3


def test_extract_json_from_markdown():
    """Test extracting JSON from markdown code block."""
    text = """Here is the result:
```json
[
  {"subject": "A", "predicate": "relates to", "object": "B"},
  {"subject": "C", "predicate": "causes", "object": "D"}
]
```
"""
    
    result = extract_json_from_text(text)
    
    assert result is not None
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["subject"] == "A"
    assert result[1]["predicate"] == "causes"


def test_extract_json_from_plain_text():
    """Test extracting JSON from plain text."""
    text = """[
  {"subject": "X", "predicate": "leads to", "object": "Y"}
]"""
    
    result = extract_json_from_text(text)
    
    assert result is not None
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["subject"] == "X"


def test_extract_json_no_json():
    """Test extraction when no JSON is present."""
    text = "This is just plain text with no JSON."
    
    result = extract_json_from_text(text)
    
    assert result is None


def test_extract_json_invalid_json():
    """Test extraction with invalid JSON."""
    text = """```json
[
  {"subject": "A", "predicate": "broken
]
```"""
    
    result = extract_json_from_text(text)
    
    assert result is None


def test_extract_json_from_markdown_without_lang():
    """Test extracting JSON from markdown without language specifier."""
    text = """```
[
  {"subject": "A", "predicate": "test", "object": "B"}
]
```"""
    
    result = extract_json_from_text(text)
    
    assert result is not None
    assert isinstance(result, list)
    assert len(result) == 1
