#!/usr/bin/env python3
"""
Adaptive FreqTrade Startup Script for RL Trading

This script starts FreqTrade with adaptive throttling enabled for optimal
RL trading performance on Binance Spot markets.

Usage:
    python adaptive_freqtrade_start.py --config user_data/config_binance_spot_longonly_rl.json
"""

import logging
import sys
from pathlib import Path


# Add user_data to Python path
sys.path.append(str(Path(__file__).parent))

from user_data.adaptive_worker import enable_adaptive_throttling


logger = logging.getLogger(__name__)


def start_adaptive_freqtrade():
    """Start FreqTrade with adaptive throttling enabled"""
    try:
        # Import FreqTrade components
        # Parse command line arguments
        from freqtrade.commands import Arguments
        from freqtrade.configuration import Configuration
        from freqtrade.loggers import setup_logging_pre
        from freqtrade.worker import Worker

        args = Arguments(sys.argv[1:]).get_parsed_arg()

        # Setup logging
        setup_logging_pre()

        # Load configuration
        configuration = Configuration(args, None)
        config = configuration.get_config()

        # Enable adaptive throttling BEFORE creating worker
        enable_adaptive_throttling(config)
        logger.info("🚀 Starting FreqTrade with Adaptive Throttling for RL Trading")

        # Display adaptive throttling configuration
        adaptive_config = config.get("internals", {}).get("adaptive_throttling", {})
        if adaptive_config.get("enabled", False):
            logger.info("📊 Adaptive Throttling Configuration:")
            logger.info(f"   ├─ Min throttle: {adaptive_config.get('min_throttle', 1.2)}s")
            logger.info(f"   ├─ Max throttle: {adaptive_config.get('max_throttle', 8.0)}s")
            logger.info(f"   ├─ RL overhead: {adaptive_config.get('rl_model_overhead', 0.8)}s")
            logger.info(f"   ├─ API factor: {adaptive_config.get('api_rate_factor', 1.5)}x")
            logger.info(
                f"   ├─ Volatility adj: {adaptive_config.get('volatility_adjustment', True)}"
            )
            logger.info(f"   └─ Trade factor: {adaptive_config.get('open_trades_factor', 0.2)}x")
        else:
            logger.warning("⚠️  Adaptive throttling is DISABLED")

        # Start FreqTrade worker
        worker = Worker(args, config)
        worker.run()

    except KeyboardInterrupt:
        logger.info("🛑 FreqTrade stopped by user")
    except Exception as e:
        logger.error(f"💥 Error starting FreqTrade: {e}")
        raise


if __name__ == "__main__":
    start_adaptive_freqtrade()
