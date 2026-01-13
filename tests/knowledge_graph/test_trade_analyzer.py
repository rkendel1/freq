"""
Tests for trade analyzer.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

from freqtrade.knowledge_graph.trade_analyzer import TradeAnalyzer


def test_trade_analyzer_init():
    """Test that trade analyzer initializes."""
    analyzer = TradeAnalyzer()
    assert analyzer is not None


def test_generate_session_narrative_empty():
    """Test narrative generation with no trades."""
    analyzer = TradeAnalyzer()
    narrative = analyzer.generate_session_narrative([])
    
    assert narrative is not None
    assert "No trades" in narrative


def test_generate_session_narrative_with_trades():
    """Test narrative generation with mock trades."""
    analyzer = TradeAnalyzer()
    
    # Create mock trades
    mock_trade = MagicMock()
    mock_trade.pair = "BTC/USDT"
    mock_trade.is_open = False
    mock_trade.is_short = False
    mock_trade.open_rate = 50000.0
    mock_trade.close_rate = 51000.0
    mock_trade.close_profit = 0.02  # 2%
    mock_trade.open_date = datetime.now() - timedelta(hours=2)
    mock_trade.close_date = datetime.now()
    mock_trade.exit_reason = "roi"
    
    trades = [mock_trade]
    metadata = {"regime": "trending_up"}
    
    narrative = analyzer.generate_session_narrative(trades, metadata)
    
    assert narrative is not None
    assert "BTC/USDT" in narrative
    assert "trending_up" in narrative
    assert "Total Trades: 1" in narrative


def test_format_trade_narrative_winner():
    """Test formatting a winning trade."""
    analyzer = TradeAnalyzer()
    
    mock_trade = MagicMock()
    mock_trade.pair = "ETH/USDT"
    mock_trade.is_short = False
    mock_trade.is_open = False
    mock_trade.open_rate = 3000.0
    mock_trade.close_rate = 3150.0
    mock_trade.close_profit = 0.05  # 5%
    mock_trade.exit_reason = "roi"
    mock_trade.open_date = datetime.now() - timedelta(hours=1)
    mock_trade.close_date = datetime.now()
    
    narrative = analyzer._format_trade_narrative(mock_trade, "winner")
    
    assert "WINNER" in narrative
    assert "ETH/USDT" in narrative
    assert "5.00%" in narrative


def test_identify_patterns_overtrading():
    """Test pattern identification for overtrading."""
    analyzer = TradeAnalyzer()
    
    # Create 15 mock trades (should trigger overtrading pattern)
    trades = []
    for i in range(15):
        mock_trade = MagicMock()
        mock_trade.pair = f"PAIR{i}/USDT"
        mock_trade.is_open = False
        mock_trade.close_profit = 0.01
        trades.append(mock_trade)
    
    patterns = analyzer._identify_patterns(trades, {})
    
    assert any("overtrading" in p.lower() for p in patterns)


def test_generate_regret_analysis():
    """Test regret analysis generation."""
    analyzer = TradeAnalyzer()
    
    # Create actual trades
    actual_trade = MagicMock()
    actual_trade.pair = "BTC/USDT"
    actual_trade.is_open = False
    actual_trade.close_profit = 0.03  # 3%
    actual_trade.stake_amount = 1000
    
    # Create shadow trades
    shadow_trades = [
        {
            "pair": "ETH/USDT",
            "direction": "long",
            "potential_profit": 0.08,
            "skip_reason": "risk_limit",
        }
    ]
    
    # Create missed opportunities
    missed_opportunities = [
        {
            "reason": "Signal too weak",
            "potential_profit": 0.05,
        }
    ]
    
    narrative = analyzer.generate_regret_analysis(
        [actual_trade], shadow_trades, missed_opportunities
    )
    
    assert narrative is not None
    assert "Regret Analysis" in narrative
    assert "REGRET" in narrative or "MISSED" in narrative
    assert "ETH/USDT" in narrative


def test_analyze_trade_regrets_small_winner():
    """Test regret analysis for small winning trade."""
    analyzer = TradeAnalyzer()
    
    mock_trade = MagicMock()
    mock_trade.pair = "BTC/USDT"
    mock_trade.is_open = False
    mock_trade.close_profit = 0.02  # 2% - small win
    mock_trade.stake_amount = 1000
    
    regrets = analyzer._analyze_trade_regrets(mock_trade)
    
    # Should identify that we could have held longer
    assert len(regrets) > 0
    assert any("held longer" in r.lower() for r in regrets)


def test_analyze_trade_regrets_big_winner_small_position():
    """Test regret analysis for big winner with small position."""
    analyzer = TradeAnalyzer()
    
    mock_trade = MagicMock()
    mock_trade.pair = "BTC/USDT"
    mock_trade.is_open = False
    mock_trade.close_profit = 0.15  # 15% - big win
    mock_trade.stake_amount = 500
    
    regrets = analyzer._analyze_trade_regrets(mock_trade)
    
    # Should identify position sizing regret
    assert len(regrets) > 0
    assert any("position" in r.lower() or "size" in r.lower() for r in regrets)


def test_identify_regret_patterns_early_exits():
    """Test identification of early exit pattern."""
    analyzer = TradeAnalyzer()
    
    # Create many small winners (early exit pattern)
    trades = []
    for i in range(10):
        mock_trade = MagicMock()
        mock_trade.pair = f"PAIR{i}/USDT"
        mock_trade.is_open = False
        mock_trade.close_profit = 0.03  # 3% - small win
        mock_trade.stake_amount = 1000
        trades.append(mock_trade)
    
    patterns = analyzer._identify_regret_patterns(trades, None, None)
    
    assert any("early" in p.lower() for p in patterns)
