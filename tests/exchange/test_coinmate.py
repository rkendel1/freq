import pytest
from unittest.mock import MagicMock

from freqtrade.enums import MarginMode, TradingMode
from freqtrade.exceptions import OperationalException
from freqtrade.exchange import Coinmate
from tests.conftest import get_patched_exchange


def test_coinmate_exchange_initialization(default_conf, mocker):
    """Test that Coinmate exchange initializes correctly"""
    api_mock = MagicMock()
    exchange = get_patched_exchange(mocker, default_conf, api_mock=api_mock, id="coinmate")
    
    assert isinstance(exchange, Coinmate)
    assert exchange.name == "Coinmate"
    assert exchange.id == "coinmate"
    

def test_coinmate_supported_features(default_conf, mocker):
    """Test that Coinmate reports correct supported features"""
    api_mock = MagicMock()
    exchange = get_patched_exchange(mocker, default_conf, api_mock=api_mock, id="coinmate")
    
    # Features that should be supported per requirements
    assert exchange.exchange_has("fetchOrder")
    assert exchange.exchange_has("fetchOpenOrders")
    assert exchange.exchange_has("fetchMyTrades")
    assert exchange.exchange_has("cancelOrder")
    assert exchange.exchange_has("createOrder")
    assert exchange.exchange_has("fetchBalance")
    assert exchange.exchange_has("fetchTicker")
    assert exchange.exchange_has("fetchOrderBook")
    assert exchange.exchange_has("fetchTrades")
    assert exchange.exchange_has("fetchMarkets")
    
    # Features that are not supported
    assert not exchange.exchange_has("fetchOHLCV")
    assert not exchange._ft_has["stoploss_on_exchange"]


def test_coinmate_trading_mode_spot_only(default_conf, mocker):
    """Test that only spot trading is supported"""
    api_mock = MagicMock()
    exchange = get_patched_exchange(mocker, default_conf, api_mock=api_mock, id="coinmate")
    
    supported_modes = exchange._supported_trading_mode_margin_pairs
    assert len(supported_modes) == 1
    assert supported_modes[0] == (TradingMode.SPOT, MarginMode.NONE)


def test_coinmate_validate_trading_mode_spot_valid(default_conf, mocker):
    """Test that spot trading mode validation passes"""
    api_mock = MagicMock()
    exchange = get_patched_exchange(mocker, default_conf, api_mock=api_mock, id="coinmate")
    
    # Should not raise exception
    exchange.validate_trading_mode_and_margin_mode(TradingMode.SPOT, MarginMode.NONE)


def test_coinmate_validate_trading_mode_futures_invalid(default_conf, mocker):
    """Test that futures trading mode is rejected"""
    api_mock = MagicMock()
    exchange = get_patched_exchange(mocker, default_conf, api_mock=api_mock, id="coinmate")
    
    with pytest.raises(OperationalException, match="Trading mode 'futures' is not supported"):
        exchange.validate_trading_mode_and_margin_mode(TradingMode.FUTURES, MarginMode.ISOLATED)


def test_coinmate_validate_ordertypes_valid(default_conf, mocker):
    """Test that valid order types are accepted"""
    api_mock = MagicMock()
    exchange = get_patched_exchange(mocker, default_conf, api_mock=api_mock, id="coinmate")
    
    # Should not raise exception for market orders
    order_types = {"entry": "market", "exit": "market", "stoploss": "market", "stoploss_on_exchange": False}
    exchange.validate_ordertypes(order_types)
    
    # Should not raise exception for limit orders
    order_types = {"entry": "limit", "exit": "limit", "stoploss": "limit", "stoploss_on_exchange": False}
    exchange.validate_ordertypes(order_types)


def test_coinmate_validate_ordertypes_invalid(default_conf, mocker):
    """Test that invalid order types are rejected"""
    api_mock = MagicMock()
    exchange = get_patched_exchange(mocker, default_conf, api_mock=api_mock, id="coinmate")
    
    # Should reject unsupported order types
    order_types = {"entry": "stop", "exit": "market"}
    with pytest.raises(OperationalException, match="Coinmate only supports 'market' and 'limit' orders"):
        exchange.validate_ordertypes(order_types)


def test_coinmate_validate_stoploss_on_exchange_rejected(default_conf, mocker):
    """Test that stoploss on exchange is rejected"""
    api_mock = MagicMock()
    exchange = get_patched_exchange(mocker, default_conf, api_mock=api_mock, id="coinmate")
    
    order_types = {"entry": "market", "exit": "market", "stoploss_on_exchange": True}
    with pytest.raises(OperationalException, match="Coinmate does not support stoploss orders on exchange"):
        exchange.validate_ordertypes(order_types)


def test_coinmate_validate_config_uid_required(default_conf, mocker):
    """Test that UID is required in configuration"""
    api_mock = MagicMock()
    exchange = get_patched_exchange(mocker, default_conf, api_mock=api_mock, id="coinmate")
    
    # Should raise exception when UID is missing
    config_without_uid = {"exchange": {"name": "coinmate", "key": "test", "secret": "test"}}
    with pytest.raises(OperationalException, match="Coinmate requires 'uid' parameter"):
        exchange.validate_config(config_without_uid)
    
    # Should not raise exception when UID is present
    config_with_uid = {"exchange": {"name": "coinmate", "key": "test", "secret": "test", "uid": "123"}}
    exchange.validate_config(config_with_uid)  # Should not raise


def test_coinmate_rate_limiting_config(default_conf, mocker):
    """Test that rate limiting is properly configured"""
    api_mock = MagicMock()
    exchange = get_patched_exchange(mocker, default_conf, api_mock=api_mock, id="coinmate")
    
    ccxt_config = exchange._ccxt_config
    assert ccxt_config["rateLimit"] == 600  # 100 requests/minute = 600ms between requests
    assert ccxt_config["enableRateLimit"] is True


def test_coinmate_get_fee_fallback(default_conf, mocker):
    """Test that fee calculation falls back to default when API unavailable"""
    api_mock = MagicMock()
    exchange = get_patched_exchange(mocker, default_conf, api_mock=api_mock, id="coinmate")
    
    # Mock the parent get_fee to raise exception
    mocker.patch.object(exchange, 'get_fee', side_effect=Exception("API unavailable"))
    
    # Should fall back to default fee (0.35%)
    fee = exchange.get_fee("BTC/CZK", "limit", "buy", 1, 25000, "maker")
    assert fee == 0.0035


def test_coinmate_ccxt_config_uid(default_conf, mocker):
    """Test that UID is properly passed to CCXT config"""
    default_conf["exchange"]["uid"] = "test123"
    api_mock = MagicMock()
    exchange = get_patched_exchange(mocker, default_conf, api_mock=api_mock, id="coinmate")
    
    ccxt_config = exchange._ccxt_config
    assert ccxt_config["uid"] == "test123"


def test_coinmate_ft_has_configuration():
    """Test that _ft_has is properly configured for Coinmate requirements"""
    exchange = Coinmate(config={}, validate=False)
    
    # Test rate limiting configuration
    assert exchange._ft_has["l2_limit_range"] == [1, 10, 50, 100]
    assert exchange._ft_has["stoploss_on_exchange"] is False
    assert exchange._ft_has["order_time_in_force"] == ["GTC"]
    assert exchange._ft_has["trades_pagination"] == "id"
    assert exchange._ft_has["trades_pagination_arg"] == "fromId"
    assert exchange._ft_has["trades_has_history"] is True
    assert exchange._ft_has["ohlcv_candle_limit"] is None  # No OHLCV support
