"""
Tests for PnL attribution module.

Tests that attribution correctly extracts and calculates trade metrics.
"""

from datetime import datetime, timezone, timedelta
import pytest

from freqtrade.persistence import LocalTrade
from freqtrade.metrics.attribution import TradeAttribution, attribute_trade


def test_trade_attribution_dataclass():
    """Test that TradeAttribution can be created with all required fields."""
    now = datetime.now(timezone.utc)
    
    attribution = TradeAttribution(
        trade_id=1,
        exploit_id="test_exploit",
        capital_source="initial",
        pair="BTC/USDT",
        is_short=False,
        entry_price=50000.0,
        entry_amount=0.1,
        entry_stake=5000.0,
        entry_date=now,
        exit_price=55000.0,
        exit_date=now + timedelta(hours=24),
        fee_open=0.001,
        fee_close=0.001,
        fee_open_cost=5.0,
        fee_close_cost=5.5,
        total_fees=10.5,
        funding_fees=2.0,
        holding_duration_seconds=86400.0,
        holding_duration_hours=24.0,
        realized_profit=490.0,
        profit_ratio=0.098,
        is_open=False,
        exit_reason="roi",
    )
    
    assert attribution.trade_id == 1
    assert attribution.exploit_id == "test_exploit"
    assert attribution.capital_source == "initial"
    assert attribution.pair == "BTC/USDT"
    assert attribution.is_short is False
    assert attribution.total_fees == 10.5
    assert attribution.funding_fees == 2.0
    assert attribution.holding_duration_hours == 24.0
    assert attribution.realized_profit == 490.0


def test_trade_attribution_to_dict():
    """Test that attribution can be converted to a dictionary."""
    now = datetime.now(timezone.utc)
    
    attribution = TradeAttribution(
        trade_id=1,
        exploit_id="test_exploit",
        capital_source="initial",
        pair="BTC/USDT",
        is_short=False,
        entry_price=50000.0,
        entry_amount=0.1,
        entry_stake=5000.0,
        entry_date=now,
        exit_price=55000.0,
        exit_date=now + timedelta(hours=24),
        fee_open=0.001,
        fee_close=0.001,
        fee_open_cost=5.0,
        fee_close_cost=5.5,
        total_fees=10.5,
        funding_fees=2.0,
        holding_duration_seconds=86400.0,
        holding_duration_hours=24.0,
        realized_profit=490.0,
        profit_ratio=0.098,
        is_open=False,
        exit_reason="roi",
    )
    
    attr_dict = attribution.to_dict()
    
    assert attr_dict["trade_id"] == 1
    assert attr_dict["exploit_id"] == "test_exploit"
    assert attr_dict["capital_source"] == "initial"
    assert attr_dict["pair"] == "BTC/USDT"
    assert attr_dict["total_fees"] == 10.5
    assert attr_dict["entry_date"] == now.isoformat()
    assert attr_dict["is_open"] is False


def test_attribute_trade_closed():
    """Test attributing a closed trade."""
    open_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    close_date = datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
    
    # Create a mock closed trade
    trade = LocalTrade(
        id=1,
        pair="BTC/USDT",
        is_short=False,
        open_rate=50000.0,
        amount=0.1,
        stake_amount=5000.0,
        open_date=open_date,
        close_rate=55000.0,
        close_date=close_date,
        fee_open=0.001,
        fee_close=0.001,
        fee_open_cost=5.0,
        fee_close_cost=5.5,
        funding_fees=2.0,
        close_profit_abs=489.5,
        close_profit=0.0979,
        is_open=False,
        exit_reason="roi",
        strategy="TestStrategy",
        enter_tag="test_entry",
    )
    
    attribution = attribute_trade(trade, capital_source="initial")
    
    assert attribution.trade_id == 1
    assert attribution.exploit_id == "TestStrategy"
    assert attribution.capital_source == "initial"
    assert attribution.pair == "BTC/USDT"
    assert attribution.is_short is False
    
    # Entry
    assert attribution.entry_price == 50000.0
    assert attribution.entry_amount == 0.1
    assert attribution.entry_stake == 5000.0
    assert attribution.entry_date == open_date
    
    # Exit
    assert attribution.exit_price == 55000.0
    assert attribution.exit_date == close_date
    
    # Fees
    assert attribution.fee_open == 0.001
    assert attribution.fee_close == 0.001
    assert attribution.fee_open_cost == 5.0
    assert attribution.fee_close_cost == 5.5
    assert attribution.total_fees == 10.5
    
    # Funding
    assert attribution.funding_fees == 2.0
    
    # Duration (36 hours)
    assert attribution.holding_duration_seconds == 129600.0
    assert attribution.holding_duration_hours == 36.0
    
    # PnL
    assert attribution.realized_profit == 489.5
    assert attribution.profit_ratio == 0.0979
    
    # Metadata
    assert attribution.is_open is False
    assert attribution.exit_reason == "roi"


def test_attribute_trade_open():
    """Test attributing an open trade."""
    open_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    
    # Create a mock open trade
    trade = LocalTrade(
        id=2,
        pair="ETH/USDT",
        is_short=True,
        open_rate=3000.0,
        amount=1.0,
        stake_amount=3000.0,
        open_date=open_date,
        close_rate=None,
        close_date=None,
        fee_open=0.001,
        fee_close=None,
        fee_open_cost=3.0,
        fee_close_cost=None,
        funding_fees=-1.5,
        close_profit_abs=None,
        close_profit=None,
        is_open=True,
        exit_reason=None,
        strategy="ShortStrategy",
    )
    
    attribution = attribute_trade(trade)
    
    assert attribution.trade_id == 2
    assert attribution.exploit_id == "ShortStrategy"
    assert attribution.capital_source == "initial"  # Default
    assert attribution.pair == "ETH/USDT"
    assert attribution.is_short is True
    
    # Entry
    assert attribution.entry_price == 3000.0
    assert attribution.entry_amount == 1.0
    assert attribution.entry_stake == 3000.0
    
    # Exit (should be None for open trade)
    assert attribution.exit_price is None
    assert attribution.exit_date is None
    
    # Fees
    assert attribution.fee_open == 0.001
    assert attribution.fee_close is None
    assert attribution.fee_open_cost == 3.0
    assert attribution.fee_close_cost is None
    assert attribution.total_fees == 3.0
    
    # Funding (negative means paid)
    assert attribution.funding_fees == -1.5
    
    # Duration (calculated from open_date to now)
    assert attribution.holding_duration_seconds > 0
    assert attribution.holding_duration_hours > 0
    
    # PnL (should be None for open trade)
    assert attribution.realized_profit is None
    assert attribution.profit_ratio is None
    
    # Metadata
    assert attribution.is_open is True
    assert attribution.exit_reason is None


def test_attribute_trade_no_strategy():
    """Test attributing a trade with no strategy (uses enter_tag or 'unknown')."""
    open_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    close_date = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # Trade with enter_tag but no strategy
    trade = LocalTrade(
        id=3,
        pair="ADA/USDT",
        is_short=False,
        open_rate=0.5,
        amount=1000.0,
        stake_amount=500.0,
        open_date=open_date,
        close_rate=0.55,
        close_date=close_date,
        fee_open=0.001,
        fee_close=0.001,
        fee_open_cost=0.5,
        fee_close_cost=0.55,
        close_profit_abs=48.95,
        close_profit=0.0979,
        is_open=False,
        strategy=None,
        enter_tag="manual_entry",
    )
    
    attribution = attribute_trade(trade)
    assert attribution.exploit_id == "manual_entry"
    
    # Trade with neither strategy nor enter_tag
    trade.enter_tag = None
    attribution = attribute_trade(trade)
    assert attribution.exploit_id == "unknown"


def test_attribute_trade_no_funding_fees():
    """Test attributing a spot trade with no funding fees."""
    open_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    close_date = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    trade = LocalTrade(
        id=4,
        pair="BTC/USDT",
        is_short=False,
        open_rate=50000.0,
        amount=0.1,
        stake_amount=5000.0,
        open_date=open_date,
        close_rate=51000.0,
        close_date=close_date,
        fee_open=0.001,
        fee_close=0.001,
        fee_open_cost=5.0,
        fee_close_cost=5.1,
        funding_fees=None,  # No funding fees for spot
        close_profit_abs=89.9,
        close_profit=0.01798,
        is_open=False,
        strategy="SpotStrategy",
    )
    
    attribution = attribute_trade(trade)
    assert attribution.funding_fees == 0.0  # Should default to 0


def test_attribute_trade_custom_capital_source():
    """Test attributing a trade with custom capital source."""
    open_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    close_date = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    trade = LocalTrade(
        id=5,
        pair="BTC/USDT",
        is_short=False,
        open_rate=50000.0,
        amount=0.1,
        stake_amount=5000.0,
        open_date=open_date,
        close_rate=51000.0,
        close_date=close_date,
        fee_open=0.001,
        fee_close=0.001,
        fee_open_cost=5.0,
        fee_close_cost=5.1,
        close_profit_abs=89.9,
        close_profit=0.01798,
        is_open=False,
        strategy="ReinvestStrategy",
    )
    
    attribution = attribute_trade(trade, capital_source="reinvested")
    assert attribution.capital_source == "reinvested"
    
    attribution = attribute_trade(trade, capital_source="borrowed")
    assert attribution.capital_source == "borrowed"
