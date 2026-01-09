#!/usr/bin/env python3
"""
Run Automated Backtest with Real Data

This script demonstrates how to use the AutomatedStrategy with freqtrade's
backtesting infrastructure to test the automated exploit with real historical data.

Usage:
    python scripts/run_automated_backtest.py
"""

import json
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from freqtrade.configuration import Configuration
from freqtrade.data.history import download_data_main
from freqtrade.optimize.backtesting import Backtesting
from freqtrade.resolvers import StrategyResolver


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_test_config():
    """Create a minimal config for testing."""
    config = {
        "strategy": "AutomatedStrategy",
        "strategy_path": "freqtrade/ui",
        "max_open_trades": 3,
        "stake_currency": "USDT",
        "stake_amount": "unlimited",
        "tradable_balance_ratio": 0.99,
        "fiat_display_currency": "USD",
        "dry_run": True,
        "cancel_open_orders_on_exit": False,
        "trading_mode": "spot",
        "margin_mode": "",
        "unfilledtimeout": {
            "entry": 10,
            "exit": 10,
            "exit_timeout_count": 0,
            "unit": "minutes"
        },
        "entry_pricing": {
            "price_side": "same",
            "use_order_book": True,
            "order_book_top": 1,
            "price_last_balance": 0.0,
            "check_depth_of_market": {
                "enabled": False,
                "bids_to_ask_delta": 1
            }
        },
        "exit_pricing": {
            "price_side": "same",
            "use_order_book": True,
            "order_book_top": 1
        },
        "exchange": {
            "name": "binance",
            "key": "",
            "secret": "",
            "ccxt_config": {},
            "ccxt_async_config": {},
            "pair_whitelist": [
                "BTC/USDT",
                "ETH/USDT"
            ],
            "pair_blacklist": []
        },
        "pairlists": [
            {"method": "StaticPairList"}
        ],
        "timeframe": "5m",
        "datadir": "user_data/data/binance",
        "user_data_dir": "user_data",
        "db_url": "sqlite:///user_data/tradesv3_automated.sqlite",
    }
    
    return config


def download_test_data(config):
    """Download sample data for testing."""
    logger.info("Downloading test data...")
    
    # Download 7 days of data
    download_config = config.copy()
    download_config['timerange'] = '20240101-20240107'
    download_config['download_trades'] = False
    
    try:
        download_data_main(download_config)
        logger.info("✓ Test data downloaded successfully")
        return True
    except Exception as e:
        logger.warning(f"Could not download data: {e}")
        logger.info("You may need to provide your own historical data")
        return False


def run_backtest_with_real_data():
    """Run backtest with the automated strategy using real data."""
    logger.info("="*70)
    logger.info("AUTOMATED BACKTEST WITH REAL HISTORICAL DATA")
    logger.info("="*70)
    
    # Create configuration
    config = create_test_config()
    
    # Ensure user_data directory exists
    user_data_dir = Path(config['user_data_dir'])
    user_data_dir.mkdir(exist_ok=True)
    (user_data_dir / 'data' / 'binance').mkdir(parents=True, exist_ok=True)
    
    # Save config
    config_path = user_data_dir / 'config_automated_backtest.json'
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    logger.info(f"✓ Configuration saved to {config_path}")
    
    # Download data (optional - may fail without exchange API keys)
    data_available = download_test_data(config)
    
    if not data_available:
        logger.info("\n" + "="*70)
        logger.info("MANUAL DATA SETUP REQUIRED")
        logger.info("="*70)
        logger.info("\nTo run the backtest, you need historical data.")
        logger.info("\nOption 1: Download data with exchange credentials:")
        logger.info("  1. Add your exchange API keys to the config")
        logger.info("  2. Run: freqtrade download-data --config user_data/config_automated_backtest.json --timerange 20240101-20240107")
        logger.info("\nOption 2: Use existing data:")
        logger.info("  1. Copy your historical data to: user_data/data/binance/")
        logger.info("  2. Data should be in JSON format: BTC_USDT-5m.json, ETH_USDT-5m.json")
        logger.info("\nOption 3: Use the synthetic BacktestAdapter instead:")
        logger.info("  python examples/automated_backtest_example.py")
        logger.info("\n" + "="*70)
        return
    
    logger.info("\n" + "="*70)
    logger.info("RUNNING BACKTEST")
    logger.info("="*70)
    
    try:
        # Initialize configuration
        configuration = Configuration.from_files([str(config_path)])
        
        # Set backtest parameters
        configuration['timerange'] = '20240101-20240107'
        configuration['max_open_trades'] = 3
        configuration['stake_amount'] = 'unlimited'
        configuration['dry_run_wallet'] = 10000
        
        logger.info(f"\nStrategy: AutomatedStrategy")
        logger.info(f"Pairs: {configuration['exchange']['pair_whitelist']}")
        logger.info(f"Timeframe: {configuration['timeframe']}")
        logger.info(f"Timerange: {configuration['timerange']}")
        logger.info(f"Starting Capital: ${configuration['dry_run_wallet']:,.2f}")
        
        # Initialize backtesting
        backtesting = Backtesting(configuration)
        
        # Run backtest
        logger.info("\nStarting backtest with real historical data...")
        logger.info("-"*70)
        
        results = backtesting.start()
        
        logger.info("-"*70)
        logger.info("\n✓ Backtest completed!")
        
        # Results are displayed by freqtrade's backtesting module
        
    except FileNotFoundError as e:
        logger.error(f"\nData files not found: {e}")
        logger.info("\nPlease download historical data first:")
        logger.info("  freqtrade download-data --config user_data/config_automated_backtest.json --timerange 20240101-20240107")
        
    except Exception as e:
        logger.error(f"\nBacktest failed: {e}")
        logger.exception("Full error:")
    
    logger.info("\n" + "="*70)
    logger.info("For more options, see:")
    logger.info("  - AUTOMATED_DEMO_GUIDE.md")
    logger.info("  - examples/automated_backtest_example.py (synthetic data)")
    logger.info("="*70 + "\n")


if __name__ == "__main__":
    run_backtest_with_real_data()
