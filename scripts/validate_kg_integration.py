#!/usr/bin/env python3
"""
Validation script for knowledge graph integration.

This script verifies that all components are working correctly.
"""

import sys


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from freqtrade.knowledge_graph.config import get_default_kg_config
        from freqtrade.knowledge_graph.llm import chunk_text, extract_json_from_text
        from freqtrade.knowledge_graph.prompts import prompt_factory
        from freqtrade.knowledge_graph.trade_analyzer import TradeAnalyzer
        from freqtrade.knowledge_graph.generator import KnowledgeGraphGenerator
        print("✅ All core modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_config():
    """Test configuration module."""
    print("\nTesting configuration...")
    
    from freqtrade.knowledge_graph.config import (
        get_default_kg_config,
        merge_kg_config,
        validate_kg_config,
    )
    
    # Test default config
    config = get_default_kg_config()
    assert config["enabled"] is False, "Default should be disabled"
    assert "llm" in config, "Missing llm config"
    assert validate_kg_config(config), "Default config should be valid"
    
    # Test merge
    user_config = {"enabled": True, "llm": {"model": "gpt-4"}}
    merged = merge_kg_config(user_config)
    assert merged["enabled"] is True, "Merge failed"
    assert merged["llm"]["model"] == "gpt-4", "Merge failed"
    
    print("✅ Configuration module working")
    return True


def test_llm_utils():
    """Test LLM utilities."""
    print("\nTesting LLM utilities...")
    
    from freqtrade.knowledge_graph.llm import chunk_text, extract_json_from_text
    
    # Test chunking
    text = " ".join([f"word{i}" for i in range(100)])
    chunks = chunk_text(text, chunk_size=10, overlap=2)
    assert len(chunks) > 1, "Chunking failed"
    
    # Test JSON extraction
    json_text = '''```json
[{"subject": "A", "predicate": "test", "object": "B"}]
```'''
    result = extract_json_from_text(json_text)
    assert result is not None, "JSON extraction failed"
    assert len(result) == 1, "JSON extraction failed"
    
    print("✅ LLM utilities working")
    return True


def test_trade_analyzer():
    """Test trade analyzer."""
    print("\nTesting trade analyzer...")
    
    from freqtrade.knowledge_graph.trade_analyzer import TradeAnalyzer
    from unittest.mock import MagicMock
    from datetime import datetime, timedelta
    
    analyzer = TradeAnalyzer()
    
    # Create mock trade
    mock_trade = MagicMock()
    mock_trade.pair = "BTC/USDT"
    mock_trade.is_open = False
    mock_trade.is_short = False
    mock_trade.open_rate = 50000
    mock_trade.close_rate = 51000
    mock_trade.close_profit = 0.02
    mock_trade.stake_amount = 1000
    mock_trade.exit_reason = "roi"
    mock_trade.open_date = datetime.now() - timedelta(hours=1)
    mock_trade.close_date = datetime.now()
    
    # Test narrative generation
    narrative = analyzer.generate_session_narrative([mock_trade], {"regime": "test"})
    assert "BTC/USDT" in narrative, "Narrative generation failed"
    assert "test" in narrative, "Metadata not included"
    
    # Test regret analysis
    regret = analyzer.generate_regret_analysis([mock_trade], None, None)
    assert "Regret" in regret, "Regret analysis failed"
    
    print("✅ Trade analyzer working")
    return True


def test_generator():
    """Test knowledge graph generator initialization."""
    print("\nTesting generator...")
    
    from freqtrade.knowledge_graph.generator import KnowledgeGraphGenerator
    
    config = {
        "enabled": True,
        "llm": {
            "model": "llama3.2",
            "base_url": "http://localhost:11434/v1/chat/completions",
            "api_key": "sk-1234",
        },
        "output": {
            "directory": "exports/test",
        },
    }
    
    kg = KnowledgeGraphGenerator(config)
    assert kg is not None, "Generator initialization failed"
    assert kg.config["enabled"] is True, "Config not set"
    
    print("✅ Generator initialization working")
    return True


def test_visualization_import():
    """Test visualization module import (optional dependencies)."""
    print("\nTesting visualization module...")
    
    try:
        from freqtrade.knowledge_graph.visualization import save_triples_json
        print("✅ Visualization module imported (basic)")
        
        try:
            from freqtrade.knowledge_graph.visualization import visualize_knowledge_graph
            import networkx
            import pyvis
            print("✅ Visualization fully available (networkx, pyvis installed)")
        except ImportError as e:
            print(f"⚠️  Visualization partially available (missing: {e})")
            print("   Install: pip install networkx pyvis python-louvain")
        
        return True
    except ImportError as e:
        print(f"❌ Visualization module failed: {e}")
        return False


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("Knowledge Graph Integration Validation")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("LLM Utilities", test_llm_utils),
        ("Trade Analyzer", test_trade_analyzer),
        ("Generator", test_generator),
        ("Visualization", test_visualization_import),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} test failed with exception: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Knowledge graph integration is ready.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
