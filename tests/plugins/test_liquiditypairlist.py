# pragma pylint: disable=missing-docstring,protected-access
import logging
from unittest.mock import MagicMock, PropertyMock

import pytest

from freqtrade.exceptions import DDosProtection, ExchangeError, OperationalException, TemporaryError
from freqtrade.plugins.pairlist.LiquidityPairList import LiquidityPairList
from freqtrade.plugins.pairlistmanager import PairListManager
from tests.conftest import (
    EXMS,
    get_patched_exchange,
    get_patched_freqtradebot,
    log_has,
    log_has_re,
)


@pytest.fixture(scope="function")
def liquidity_config(default_conf):
    """Configuration for LiquidityPairList tests."""
    default_conf["runmode"] = "dry_run"
    default_conf["stake_currency"] = "USDT"
    default_conf["exchange"]["pair_whitelist"] = [
        "ETH/USDT",
        "BTC/USDT",
        "XRP/USDT",
        "LTC/USDT",
        "ADA/USDT",
    ]
    default_conf["exchange"]["pair_blacklist"] = ["BLK/USDT"]
    default_conf["pairlists"] = [
        {
            "method": "LiquidityPairList",
            "min_liquidity": 100000,
            "spread_pct_threshold": 0.5,
            "min_top_level": 5000,
        }
    ]
    return default_conf


@pytest.fixture(scope="function")
def mock_orderbook_data():
    """Mock orderbook data for testing."""
    return {
        "bids": [
            [50000.0, 1.0],  # $50,000 liquidity
            [49950.0, 2.0],  # $99,900 liquidity
            [49900.0, 1.0],  # $49,900 liquidity
            [49800.0, 1.0],  # $49,800 liquidity
        ],
        "asks": [
            [50100.0, 1.0],  # $50,100 liquidity
            [50150.0, 2.0],  # $100,300 liquidity
            [50200.0, 1.0],  # $50,200 liquidity
            [50300.0, 1.0],  # $50,300 liquidity
        ]
    }


class TestLiquidityPairListInit:
    """Test LiquidityPairList initialization and configuration validation."""

    def test_init_default_config(self, liquidity_config, mocker):
        """Test initialization with default configuration."""
        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )

        freqtrade = get_patched_freqtradebot(mocker, liquidity_config)
        pairlist = freqtrade.pairlists._pairlist_handlers[0]

        assert pairlist.__class__.__name__ == "LiquidityPairList"
        assert pairlist._min_liquidity == 100000
        assert pairlist._spread_pct_threshold == 0.5
        assert pairlist._min_top_level == 5000

    def test_init_custom_config(self, default_conf, mocker):
        """Test initialization with custom configuration."""
        default_conf["pairlists"] = [
            {
                "method": "LiquidityPairList",
                "min_liquidity": 200000,
                "spread_pct_threshold": 1.0,
                "min_top_level": 10000,
            }
        ]

        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )

        freqtrade = get_patched_freqtradebot(mocker, default_conf)
        pairlist = freqtrade.pairlists._pairlist_handlers[0]

        assert pairlist._min_liquidity == 200000
        assert pairlist._spread_pct_threshold == 1.0
        assert pairlist._min_top_level == 10000

    def test_init_validation_negative_liquidity(self, default_conf, mocker):
        """Test validation rejects negative min_liquidity."""
        default_conf["pairlists"] = [
            {
                "method": "LiquidityPairList",
                "min_liquidity": -1000,
            }
        ]

        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )

        with pytest.raises(ValueError, match="min_liquidity must be positive"):
            get_patched_freqtradebot(mocker, default_conf)

    def test_init_validation_invalid_spread_threshold(self, default_conf, mocker):
        """Test validation rejects invalid spread_pct_threshold."""
        test_cases = [
            (0, "spread_pct_threshold must be between 0 and 25"),
            (-1, "spread_pct_threshold must be between 0 and 25"),
            (30, "spread_pct_threshold must be between 0 and 25"),
        ]

        for threshold, expected_error in test_cases:
            default_conf["pairlists"] = [
                {
                    "method": "LiquidityPairList",
                    "spread_pct_threshold": threshold,
                }
            ]

            mocker.patch.multiple(
                EXMS,
                exchange_has=MagicMock(return_value=True),
                markets=PropertyMock(return_value={}),
            )

            with pytest.raises(ValueError, match=expected_error):
                get_patched_freqtradebot(mocker, default_conf)

    def test_init_validation_negative_top_level(self, default_conf, mocker):
        """Test validation rejects negative min_top_level."""
        default_conf["pairlists"] = [
            {
                "method": "LiquidityPairList",
                "min_top_level": -5000,
            }
        ]

        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )

        with pytest.raises(ValueError, match="min_top_level must be positive"):
            get_patched_freqtradebot(mocker, default_conf)

    def test_init_exchange_capability_validation(self, default_conf, mocker):
        """Test validation rejects exchanges without orderbook support."""
        default_conf["pairlists"] = [
            {
                "method": "LiquidityPairList",
                "min_liquidity": 100000,
            }
        ]

        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=False),  # Exchange doesn't support orderbook
            markets=PropertyMock(return_value={}),
        )

        with pytest.raises(OperationalException, match="requires exchange to support L2 orderbook data"):
            get_patched_freqtradebot(mocker, default_conf)

    def test_init_custom_cache_config(self, default_conf, mocker):
        """Test initialization with custom cache configuration."""
        default_conf["pairlists"] = [
            {
                "method": "LiquidityPairList",
                "cache_ttl": 600,
            }
        ]

        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )

        freqtrade = get_patched_freqtradebot(mocker, default_conf)
        pairlist = freqtrade.pairlists._pairlist_handlers[0]

        assert pairlist._cache_ttl == 600


class TestLiquidityPairListMethods:
    """Test LiquidityPairList core methods."""

    def test_short_desc(self, liquidity_config, mocker):
        """Test short_desc method."""
        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )

        freqtrade = get_patched_freqtradebot(mocker, liquidity_config)
        pairlist = freqtrade.pairlists._pairlist_handlers[0]

        desc = pairlist.short_desc()
        assert "Liquidity filter" in desc
        assert "100,000" in desc
        assert "0.5%" in desc

    def test_available_parameters(self):
        """Test available_parameters static method."""
        params = LiquidityPairList.available_parameters()

        assert isinstance(params, dict)
        assert "min_liquidity" in params
        assert "spread_pct_threshold" in params
        assert "min_top_level" in params

        # Check parameter structure
        for param_name, param_config in params.items():
            assert "type" in param_config
            assert "default" in param_config
            assert "description" in param_config
            assert "help" in param_config
            assert param_config["type"] == "number"

    def test_available_parameters_values(self):
        """Test available_parameters return correct default values."""
        params = LiquidityPairList.available_parameters()

        assert params["min_liquidity"]["default"] == 100000
        assert params["spread_pct_threshold"]["default"] == 0.5
        assert params["min_top_level"]["default"] == 5000
        assert params["cache_ttl"]["default"] == 300

    def test_available_parameters_new_parameters(self):
        """Test that new parameters are included in available_parameters."""
        params = LiquidityPairList.available_parameters()

        # Check new parameters exist
        assert "cache_ttl" in params
        assert "refresh_period" in params

        # Check parameter types
        assert params["cache_ttl"]["type"] == "number"
        assert params["refresh_period"]["type"] == "number"

    def test_supports_backtesting_attribute(self):
        """Test that supports_backtesting is set correctly."""
        from freqtrade.plugins.pairlist.IPairList import SupportsBacktesting

        assert LiquidityPairList.supports_backtesting == SupportsBacktesting.NO


class TestLiquidityPairListOrderbookCalculation:
    """Test orderbook liquidity calculation logic."""

    def test_calculate_orderbook_liquidity_success(self, liquidity_config, mocker, mock_orderbook_data):
        """Test successful liquidity calculation."""
        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )
        mocker.patch(f"{EXMS}.fetch_l2_order_book", MagicMock(return_value=mock_orderbook_data))

        freqtrade = get_patched_freqtradebot(mocker, liquidity_config)
        pairlist = freqtrade.pairlists._pairlist_handlers[0]

        passed, reason, metrics = pairlist._calculate_orderbook_liquidity("ETH/USDT")

        assert passed is True
        assert reason == "Passed (high liquidity)"  # Mock data has high liquidity
        assert "total_liquidity" in metrics
        assert "bid_liquidity" in metrics
        assert "ask_liquidity" in metrics
        assert "mid_price" in metrics
        assert metrics["total_liquidity"] > 100000  # Should exceed minimum
        assert metrics["skipped_top_level_check"] is True

    def test_calculate_orderbook_liquidity_insufficient_total(self, liquidity_config, mocker):
        """Test rejection due to insufficient total liquidity."""
        # Create orderbook with low liquidity
        low_liquidity_orderbook = {
            "bids": [[50000.0, 0.1]],  # Only $5,000 liquidity
            "asks": [[50100.0, 0.1]],  # Only $5,010 liquidity
        }

        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )
        mocker.patch(f"{EXMS}.fetch_l2_order_book", MagicMock(return_value=low_liquidity_orderbook))

        freqtrade = get_patched_freqtradebot(mocker, liquidity_config)
        pairlist = freqtrade.pairlists._pairlist_handlers[0]

        passed, reason, metrics = pairlist._calculate_orderbook_liquidity("ETH/USDT")

        assert passed is False
        assert "Total liquidity" in reason
        assert "100,000" in reason
        assert "total_liquidity" in metrics
        assert metrics["total_liquidity"] < 100000

    def test_calculate_orderbook_liquidity_insufficient_top_level(self, liquidity_config, mocker):
        """Test rejection due to insufficient top-level size."""
        # Create orderbook with sufficient total but low top-level
        # Use lower total liquidity to avoid early exit optimization
        orderbook = {
            "bids": [
                [50000.0, 0.01],  # Only $500 at best bid
                [49900.0, 1.0],  # Moderate liquidity deeper
            ],
            "asks": [
                [50100.0, 0.01],  # Only $501 at best ask
                [50200.0, 1.0],  # Moderate liquidity deeper
            ]
        }

        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )
        mocker.patch(f"{EXMS}.fetch_l2_order_book", MagicMock(return_value=orderbook))

        freqtrade = get_patched_freqtradebot(mocker, liquidity_config)
        pairlist = freqtrade.pairlists._pairlist_handlers[0]

        passed, reason, metrics = pairlist._calculate_orderbook_liquidity("ETH/USDT")

        assert passed is False
        assert "Top level size" in reason
        assert "5,000" in reason
        assert "min_top_level" in metrics
        assert metrics["min_top_level"] < 5000

    def test_calculate_orderbook_liquidity_high_liquidity_early_exit(self, liquidity_config, mocker):
        """Test early exit for high-liquidity pairs."""
        # Create orderbook with very high liquidity (2x minimum)
        high_liquidity_orderbook = {
            "bids": [[50000.0, 10.0]],  # $500,000 liquidity
            "asks": [[50100.0, 10.0]],  # $501,000 liquidity
        }

        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )
        mocker.patch(f"{EXMS}.fetch_l2_order_book", MagicMock(return_value=high_liquidity_orderbook))

        freqtrade = get_patched_freqtradebot(mocker, liquidity_config)
        pairlist = freqtrade.pairlists._pairlist_handlers[0]

        passed, reason, metrics = pairlist._calculate_orderbook_liquidity("ETH/USDT")

        assert passed is True
        assert reason == "Passed (high liquidity)"
        assert metrics["skipped_top_level_check"] is True
        assert metrics["total_liquidity"] >= 200000  # 2x minimum

    def test_calculate_orderbook_liquidity_exchange_not_supported(self, liquidity_config, mocker):
        """Test handling of exchange without orderbook support."""
        # Create a mock exchange that doesn't have the fetch_l2_order_book method
        exchange_mock = MagicMock()
        del exchange_mock.fetch_l2_order_book  # Remove the method entirely

        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )

        freqtrade = get_patched_freqtradebot(mocker, liquidity_config)
        pairlist = freqtrade.pairlists._pairlist_handlers[0]
        pairlist._exchange = exchange_mock  # Use _exchange instead of exchange

        passed, reason, metrics = pairlist._calculate_orderbook_liquidity("ETH/USDT")

        assert passed is False
        assert reason == "Unexpected error: fetch_l2_order_book"
        assert metrics == {}

    def test_calculate_orderbook_liquidity_rate_limited(self, liquidity_config, mocker):
        """Test handling of rate limiting."""
        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )
        mocker.patch(f"{EXMS}.fetch_l2_order_book", MagicMock(side_effect=Exception("rate limit exceeded")))

        freqtrade = get_patched_freqtradebot(mocker, liquidity_config)
        pairlist = freqtrade.pairlists._pairlist_handlers[0]

        passed, reason, metrics = pairlist._calculate_orderbook_liquidity("ETH/USDT")

        assert passed is False
        assert reason == "Unexpected error: rate limit exceeded"
        assert metrics == {}

    def test_calculate_orderbook_liquidity_no_data(self, liquidity_config, mocker):
        """Test handling of missing orderbook data."""
        test_cases = [
            None,  # No orderbook
            {},  # Empty orderbook
            {"bids": [], "asks": []},  # Empty bids/asks
            {"bids": [[50000.0, 1.0]]},  # Missing asks
            {"asks": [[50100.0, 1.0]]},  # Missing bids
        ]

        for orderbook_data in test_cases:
            mocker.patch.multiple(
                EXMS,
                exchange_has=MagicMock(return_value=True),
                markets=PropertyMock(return_value={}),
            )
            mocker.patch(f"{EXMS}.fetch_l2_order_book", MagicMock(return_value=orderbook_data))

            freqtrade = get_patched_freqtradebot(mocker, liquidity_config)
            pairlist = freqtrade.pairlists._pairlist_handlers[0]

            passed, reason, metrics = pairlist._calculate_orderbook_liquidity("ETH/USDT")

            assert passed is False
            assert "Invalid orderbook structure" in reason
            assert metrics == {}

    def test_calculate_orderbook_liquidity_exception_handling(self, liquidity_config, mocker):
        """Test exception handling in liquidity calculation."""
        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )
        mocker.patch(f"{EXMS}.fetch_l2_order_book", MagicMock(side_effect=Exception("Network error")))

        freqtrade = get_patched_freqtradebot(mocker, liquidity_config)
        pairlist = freqtrade.pairlists._pairlist_handlers[0]

        passed, reason, metrics = pairlist._calculate_orderbook_liquidity("ETH/USDT")

        assert passed is False
        assert reason == "Unexpected error: Network error"
        assert metrics == {}

    def test_calculate_orderbook_liquidity_ddos_protection(self, liquidity_config, mocker):
        """Test handling of DDoS protection errors."""
        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )
        mocker.patch(f"{EXMS}.fetch_l2_order_book", MagicMock(side_effect=DDosProtection("Rate limited")))

        freqtrade = get_patched_freqtradebot(mocker, liquidity_config)
        pairlist = freqtrade.pairlists._pairlist_handlers[0]

        passed, reason, metrics = pairlist._calculate_orderbook_liquidity("ETH/USDT")

        assert passed is False
        assert reason == "Rate limited"
        assert metrics == {}

    def test_calculate_orderbook_liquidity_temporary_error(self, liquidity_config, mocker):
        """Test handling of temporary network errors."""
        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )
        mocker.patch(f"{EXMS}.fetch_l2_order_book", MagicMock(side_effect=TemporaryError("Network timeout")))

        freqtrade = get_patched_freqtradebot(mocker, liquidity_config)
        pairlist = freqtrade.pairlists._pairlist_handlers[0]

        passed, reason, metrics = pairlist._calculate_orderbook_liquidity("ETH/USDT")

        assert passed is False
        assert reason == "Network error"
        assert metrics == {}

    def test_calculate_orderbook_liquidity_exchange_error(self, liquidity_config, mocker):
        """Test handling of exchange-specific errors."""
        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )
        mocker.patch(f"{EXMS}.fetch_l2_order_book", MagicMock(side_effect=ExchangeError("Invalid pair")))

        freqtrade = get_patched_freqtradebot(mocker, liquidity_config)
        pairlist = freqtrade.pairlists._pairlist_handlers[0]

        passed, reason, metrics = pairlist._calculate_orderbook_liquidity("ETH/USDT")

        assert passed is False
        assert reason == "Exchange error: Invalid pair"
        assert metrics == {}

    def test_calculate_orderbook_liquidity_caching(self, liquidity_config, mocker, mock_orderbook_data):
        """Test that caching works correctly."""
        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )
        fetch_mock = mocker.patch(f"{EXMS}.fetch_l2_order_book", MagicMock(return_value=mock_orderbook_data))

        freqtrade = get_patched_freqtradebot(mocker, liquidity_config)
        pairlist = freqtrade.pairlists._pairlist_handlers[0]

        # First call should fetch from exchange
        passed1, reason1, metrics1 = pairlist._calculate_orderbook_liquidity("ETH/USDT")
        assert passed1 is True
        assert fetch_mock.call_count == 1

        # Second call should use cache
        passed2, reason2, metrics2 = pairlist._calculate_orderbook_liquidity("ETH/USDT")
        assert passed2 is True
        assert fetch_mock.call_count == 1  # Should not have increased

        # Results should be identical
        assert reason1 == reason2
        assert metrics1 == metrics2

    def test_validate_orderbook_structure(self, liquidity_config, mocker):
        """Test orderbook structure validation."""
        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )

        freqtrade = get_patched_freqtradebot(mocker, liquidity_config)
        pairlist = freqtrade.pairlists._pairlist_handlers[0]

        # Test valid orderbook
        valid_orderbook = {
            "bids": [[50000.0, 1.0]],
            "asks": [[50100.0, 1.0]]
        }
        assert pairlist._validate_orderbook_structure(valid_orderbook, "ETH/USDT") is True

        # Test invalid orderbooks
        invalid_cases = [
            None,  # Empty orderbook
            {},  # Missing bids/asks
            {"bids": [], "asks": []},  # Empty bids/asks
            {"bids": [[50000.0, 1.0]]},  # Missing asks
            {"asks": [[50100.0, 1.0]]},  # Missing bids
            {"bids": "invalid", "asks": []},  # Wrong type
        ]

        for invalid_orderbook in invalid_cases:
            assert pairlist._validate_orderbook_structure(invalid_orderbook, "ETH/USDT") is False


class TestLiquidityPairListFiltering:
    """Test pairlist filtering functionality."""

    def test_filter_pairlist_empty_input(self, liquidity_config, mocker):
        """Test filtering with empty pairlist."""
        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )

        freqtrade = get_patched_freqtradebot(mocker, liquidity_config)
        pairlist = freqtrade.pairlists._pairlist_handlers[0]

        result = pairlist.filter_pairlist([], {})
        assert result == []

    def test_filter_pairlist_success(self, liquidity_config, mocker, mock_orderbook_data):
        """Test successful pairlist filtering."""
        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )
        mocker.patch(f"{EXMS}.fetch_l2_order_book", MagicMock(return_value=mock_orderbook_data))

        freqtrade = get_patched_freqtradebot(mocker, liquidity_config)
        pairlist = freqtrade.pairlists._pairlist_handlers[0]

        input_pairs = ["ETH/USDT", "BTC/USDT", "XRP/USDT"]
        result = pairlist.filter_pairlist(input_pairs, {})

        assert isinstance(result, list)
        assert len(result) == 3  # All pairs should pass with mock data

    def test_filter_pairlist_mixed_results(self, liquidity_config, mocker):
        """Test filtering with mixed pass/fail results."""
        def mock_fetch_order_book(pair, limit=100):
            if pair == "ETH/USDT":
                return {
                    "bids": [[50000.0, 10.0]],  # High liquidity - should pass
                    "asks": [[50100.0, 10.0]],
                }
            elif pair == "BTC/USDT":
                return {
                    "bids": [[50000.0, 0.1]],  # Low liquidity - should fail
                    "asks": [[50100.0, 0.1]],
                }
            else:  # XRP/USDT
                return None  # No data - should fail

        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )
        mocker.patch(f"{EXMS}.fetch_l2_order_book", MagicMock(side_effect=mock_fetch_order_book))

        freqtrade = get_patched_freqtradebot(mocker, liquidity_config)
        pairlist = freqtrade.pairlists._pairlist_handlers[0]

        input_pairs = ["ETH/USDT", "BTC/USDT", "XRP/USDT"]
        result = pairlist.filter_pairlist(input_pairs, {})

        assert len(result) == 1
        assert "ETH/USDT" in result

    def test_filter_pairlist_logging(self, liquidity_config, mocker, caplog):
        """Test that filtering produces appropriate log messages."""
        def mock_fetch_order_book(pair, limit=100):
            if pair == "ETH/USDT":
                return {
                    "bids": [[50000.0, 10.0]],  # High liquidity - should pass
                    "asks": [[50100.0, 10.0]],
                }
            else:  # BTC/USDT
                return {
                    "bids": [[50000.0, 0.1]],  # Low liquidity - should fail
                    "asks": [[50100.0, 0.1]],
                }

        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )
        mocker.patch(f"{EXMS}.fetch_l2_order_book", MagicMock(side_effect=mock_fetch_order_book))

        freqtrade = get_patched_freqtradebot(mocker, liquidity_config)
        pairlist = freqtrade.pairlists._pairlist_handlers[0]

        input_pairs = ["ETH/USDT", "BTC/USDT"]
        with caplog.at_level(logging.INFO):
            result = pairlist.filter_pairlist(input_pairs, {})

        assert len(result) == 1
        assert log_has("LiquidityPairList: Filtering 2 pairs", caplog)
        assert log_has("LiquidityPairList: 1/2 pairs passed final filter", caplog)
        assert log_has("Order book filter rejected 1 pairs", caplog)


class TestLiquidityPairListIntegration:
    """Test LiquidityPairList integration with PairListManager."""

    def test_pairlist_manager_integration(self, default_conf, mocker, mock_orderbook_data):
        """Test integration with PairListManager."""
        # Use LiquidityPairList as a filter after StaticPairList
        default_conf["stake_currency"] = "USDT"  # Set correct stake currency
        default_conf["pairlists"] = [
            {"method": "StaticPairList"},
            {
                "method": "LiquidityPairList",
                "min_liquidity": 100000,
                "spread_pct_threshold": 0.5,
                "min_top_level": 5000,
            }
        ]
        default_conf["exchange"]["pair_whitelist"] = ["ETH/USDT", "BTC/USDT", "XRP/USDT", "LTC/USDT", "ADA/USDT"]

        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )
        mocker.patch(f"{EXMS}.fetch_l2_order_book", MagicMock(return_value=mock_orderbook_data))

        freqtrade = get_patched_freqtradebot(mocker, default_conf)

        # Test that the pairlist is properly integrated
        assert len(freqtrade.pairlists._pairlist_handlers) == 2
        assert freqtrade.pairlists._pairlist_handlers[0].__class__.__name__ == "StaticPairList"
        assert freqtrade.pairlists._pairlist_handlers[1].__class__.__name__ == "LiquidityPairList"

        # Test refresh_pairlist
        freqtrade.pairlists.refresh_pairlist()
        whitelist = freqtrade.pairlists.whitelist

        assert isinstance(whitelist, list)
        assert len(whitelist) == 3  # ETH/USDT, BTC/USDT, XRP/USDT (LTC/USDT inactive, ADA/USDT not compatible)

    def test_pairlist_manager_with_static_pairlist(self, default_conf, mocker, mock_orderbook_data):
        """Test LiquidityPairList as filter after StaticPairList."""
        default_conf["stake_currency"] = "USDT"  # Set correct stake currency
        default_conf["pairlists"] = [
            {"method": "StaticPairList"},
            {
                "method": "LiquidityPairList",
                "min_liquidity": 100000,
                "spread_pct_threshold": 0.5,
                "min_top_level": 5000,
            }
        ]
        default_conf["exchange"]["pair_whitelist"] = ["ETH/USDT", "BTC/USDT", "XRP/USDT"]

        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )
        mocker.patch(f"{EXMS}.fetch_l2_order_book", MagicMock(return_value=mock_orderbook_data))

        freqtrade = get_patched_freqtradebot(mocker, default_conf)
        freqtrade.pairlists.refresh_pairlist()

        whitelist = freqtrade.pairlists.whitelist
        assert isinstance(whitelist, list)
        assert len(whitelist) == 3  # All pairs should pass with mock data


class TestLiquidityPairListEdgeCases:
    """Test edge cases and error conditions."""

    def test_very_small_spread_threshold(self, default_conf, mocker):
        """Test with very small spread threshold."""
        default_conf["pairlists"] = [
            {
                "method": "LiquidityPairList",
                "spread_pct_threshold": 0.01,  # 0.01%
                "min_liquidity": 1000,
                "min_top_level": 100,
            }
        ]

        # Create orderbook with very tight spread
        tight_spread_orderbook = {
            "bids": [[50000.0, 1.0]],
            "asks": [[50005.0, 1.0]],  # 0.01% spread
        }

        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )
        mocker.patch(f"{EXMS}.fetch_l2_order_book", MagicMock(return_value=tight_spread_orderbook))

        freqtrade = get_patched_freqtradebot(mocker, default_conf)
        pairlist = freqtrade.pairlists._pairlist_handlers[0]

        passed, reason, metrics = pairlist._calculate_orderbook_liquidity("ETH/USDT")

        # Should pass as liquidity is within the tight range
        assert passed is True
        assert "total_liquidity" in metrics

    def test_large_spread_threshold(self, default_conf, mocker):
        """Test with large spread threshold."""
        default_conf["pairlists"] = [
            {
                "method": "LiquidityPairList",
                "spread_pct_threshold": 5.0,  # 5%
                "min_liquidity": 1000,
                "min_top_level": 100,
            }
        ]

        # Create orderbook with wide spread
        wide_spread_orderbook = {
            "bids": [[47500.0, 1.0]],  # 5% below mid
            "asks": [[52500.0, 1.0]],  # 5% above mid
        }

        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )
        mocker.patch(f"{EXMS}.fetch_l2_order_book", MagicMock(return_value=wide_spread_orderbook))

        freqtrade = get_patched_freqtradebot(mocker, default_conf)
        pairlist = freqtrade.pairlists._pairlist_handlers[0]

        passed, reason, metrics = pairlist._calculate_orderbook_liquidity("ETH/USDT")

        # Should pass as liquidity is within the wide range
        assert passed is True
        assert "total_liquidity" in metrics

    def test_zero_volume_orderbook(self, liquidity_config, mocker):
        """Test handling of orderbook with zero volume."""
        zero_volume_orderbook = {
            "bids": [[50000.0, 0.0]],  # Zero volume
            "asks": [[50100.0, 0.0]],  # Zero volume
        }

        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )
        mocker.patch(f"{EXMS}.fetch_l2_order_book", MagicMock(return_value=zero_volume_orderbook))

        freqtrade = get_patched_freqtradebot(mocker, liquidity_config)
        pairlist = freqtrade.pairlists._pairlist_handlers[0]

        passed, reason, metrics = pairlist._calculate_orderbook_liquidity("ETH/USDT")

        assert passed is False
        assert "Total liquidity" in reason
        assert metrics["total_liquidity"] == 0.0

    def test_negative_prices_orderbook(self, liquidity_config, mocker):
        """Test handling of orderbook with negative prices."""
        negative_price_orderbook = {
            "bids": [[-50000.0, 1.0]],  # Negative price
            "asks": [[50100.0, 1.0]],
        }

        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )
        mocker.patch(f"{EXMS}.fetch_l2_order_book", MagicMock(return_value=negative_price_orderbook))

        freqtrade = get_patched_freqtradebot(mocker, liquidity_config)
        pairlist = freqtrade.pairlists._pairlist_handlers[0]

        passed, reason, metrics = pairlist._calculate_orderbook_liquidity("ETH/USDT")

        # Should handle gracefully - likely fail due to insufficient liquidity
        assert passed is False
        assert "total_liquidity" in metrics


class TestLiquidityPairListPerformance:
    """Test performance optimizations."""

    def test_early_exit_bid_processing(self, liquidity_config, mocker):
        """Test early exit optimization in bid processing."""
        # Create orderbook where early exit should trigger
        large_orderbook = {
            "bids": [
                [50000.0, 5.0],  # $250,000 - should trigger early exit
                [49900.0, 100.0],  # More liquidity that shouldn't be processed
                [49800.0, 100.0],
            ],
            "asks": [[50100.0, 1.0]],
        }

        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )
        mocker.patch(f"{EXMS}.fetch_l2_order_book", MagicMock(return_value=large_orderbook))

        freqtrade = get_patched_freqtradebot(mocker, liquidity_config)
        pairlist = freqtrade.pairlists._pairlist_handlers[0]

        passed, reason, metrics = pairlist._calculate_orderbook_liquidity("ETH/USDT")

        # Should pass due to early exit optimization
        assert passed is True
        assert "total_liquidity" in metrics
        # The total should be less than if all levels were processed
        assert metrics["total_liquidity"] < 500000  # Less than full calculation

    def test_high_liquidity_skip_top_level_check(self, liquidity_config, mocker):
        """Test that high-liquidity pairs skip top-level check."""
        # Create orderbook with 2x minimum liquidity but low top-level
        high_liquidity_low_top_orderbook = {
            "bids": [
                [50000.0, 0.01],  # Low top-level ($500)
                [49900.0, 200.0],  # High liquidity deeper
            ],
            "asks": [
                [50100.0, 0.01],  # Low top-level ($501)
                [50200.0, 200.0],  # High liquidity deeper
            ]
        }

        mocker.patch.multiple(
            EXMS,
            exchange_has=MagicMock(return_value=True),
            markets=PropertyMock(return_value={}),
        )
        mocker.patch(f"{EXMS}.fetch_l2_order_book", MagicMock(return_value=high_liquidity_low_top_orderbook))

        freqtrade = get_patched_freqtradebot(mocker, liquidity_config)
        pairlist = freqtrade.pairlists._pairlist_handlers[0]

        passed, reason, metrics = pairlist._calculate_orderbook_liquidity("ETH/USDT")

        # Should pass due to high liquidity optimization
        assert passed is True
        assert reason == "Passed (high liquidity)"
        assert metrics["skipped_top_level_check"] is True
        assert metrics["total_liquidity"] >= 200000  # 2x minimum