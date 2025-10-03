#!/usr/bin/env python3
"""
Enhanced Adaptive FreqTrade Startup Script for RL Trading with Telegram

This script:
1. Configures API keys from environment variables
2. Enables Telegram notifications
3. Starts FreqTrade with adaptive throttling
4. Optimized for dry run with read-only Binance API keys

Usage:
    python adaptive_freqtrade_enhanced.py --config user_data/config_binance_spot_longonly_rl.json
"""

import json
import logging
import os
import sys
from pathlib import Path


# Add user_data to Python path
sys.path.append(str(Path(__file__).parent))

from user_data.adaptive_worker import enable_adaptive_throttling


logger = logging.getLogger(__name__)


def update_config_with_env_vars(config_path: str) -> dict:
    """Update FreqTrade config with environment variables"""

    with open(config_path) as f:
        config = json.load(f)

    # Update Binance API keys from environment
    binance_api_key = os.getenv("BINANCE_API_KEY")
    binance_secret_key = os.getenv("BINANCE_SECRET_KEY")

    if binance_api_key and binance_secret_key:
        config["exchange"]["key"] = binance_api_key
        config["exchange"]["secret"] = binance_secret_key
        logger.info("✅ Binance API keys loaded from environment (READ-ONLY for DRY RUN)")
    else:
        logger.warning("⚠️  Binance API keys not found in environment variables")

    # Update Telegram settings from environment
    telegram_enabled = os.getenv("TELEGRAM_ENABLED", "true").lower() == "true"
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if telegram_enabled and telegram_token and telegram_chat_id:
        config["telegram"]["enabled"] = True
        config["telegram"]["token"] = telegram_token
        config["telegram"]["chat_id"] = telegram_chat_id
        logger.info("✅ Telegram Bot configured and enabled")
    elif telegram_enabled:
        logger.warning("⚠️  Telegram enabled but token/chat_id missing")
    else:
        config["telegram"]["enabled"] = False
        logger.info("ℹ️  Telegram notifications disabled")

    # Ensure dry run is enabled for read-only API keys
    if config.get("dry_run", False):
        logger.info("✅ Dry run mode enabled - safe for read-only API keys")
    else:
        logger.warning("⚠️  Dry run disabled - this may not work with read-only API keys")

    return config


def start_adaptive_freqtrade():
    """Start FreqTrade with adaptive throttling and enhanced configuration"""
    try:
        # Import FreqTrade components
        from freqtrade.commands import Arguments
        from freqtrade.configuration import Configuration
        from freqtrade.loggers import setup_logging_pre
        from freqtrade.worker import Worker

        # Parse command line arguments
        args = Arguments(sys.argv[1:]).get_parsed_arg()

        # Setup logging
        setup_logging_pre()

        # Load and update configuration
        config_path = args.get("config")
        if isinstance(config_path, list):
            config_path = config_path[0]
        config_path = config_path or "user_data/config_binance_spot_longonly_rl.json"

        # Update config with environment variables
        updated_config = update_config_with_env_vars(config_path)

        # Create a temporary config file with updated values
        temp_config_path = "/tmp/freqtrade_config_temp.json"
        with open(temp_config_path, "w") as f:
            json.dump(updated_config, f, indent=2)

        # Update args to use temporary config
        args["config"] = [temp_config_path]

        # Load configuration through FreqTrade
        configuration = Configuration(args, None)
        config = configuration.get_config()

        # Enable adaptive throttling BEFORE creating worker
        enable_adaptive_throttling(config)

        logger.info("🚀 Starting FreqTrade with Adaptive Throttling for RL Trading")
        logger.info("📱 Dry Run Mode with Read-Only Binance API Keys")

        # Display configuration summary
        logger.info("📊 Configuration Summary:")
        logger.info(f"   ├─ Trading Mode: {'DRY RUN' if config.get('dry_run') else 'LIVE'}")
        logger.info(f"   ├─ Exchange: {config.get('exchange', {}).get('name', 'Unknown')}")
        logger.info(
            f"   ├─ Telegram: {'ENABLED' if config.get('telegram', {}).get('enabled') else 'DISABLED'}"
        )
        logger.info(
            f"   ├─ FreqAI: {'ENABLED' if config.get('freqai', {}).get('enabled') else 'DISABLED'}"
        )
        logger.info(f"   └─ Max Trades: {config.get('max_open_trades', 'Unknown')}")

        # Display adaptive throttling configuration
        adaptive_config = config.get("internals", {}).get("adaptive_throttling", {})
        if adaptive_config.get("enabled", False):
            logger.info("🎯 Adaptive Throttling Configuration:")
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

        # Send startup notification if Telegram is enabled
        if config.get("telegram", {}).get("enabled"):
            try:
                worker.freqtrade.rpc.send_msg(
                    {
                        "type": "startup",
                        "status": "🚀 FreqTrade Adaptive RL Bot Started!\n"
                        f"Mode: {'DRY RUN' if config.get('dry_run') else 'LIVE'}\n"
                        f"Adaptive Throttling: {'✅ ENABLED' if adaptive_config.get('enabled') else '❌ DISABLED'}\n"
                        f"RL Training: {'✅ ENABLED' if config.get('freqai', {}).get('enabled') else '❌ DISABLED'}",
                    }
                )
            except Exception as e:
                logger.warning(f"Could not send Telegram startup message: {e}")

        logger.info("✅ FreqTrade worker starting...")
        worker.run()

    except KeyboardInterrupt:
        logger.info("🛑 FreqTrade stopped by user")
        # Send shutdown notification if possible
        try:
            if "worker" in locals() and worker.freqtrade.rpc:
                worker.freqtrade.rpc.send_msg(
                    {"type": "status", "status": "🛑 FreqTrade Adaptive RL Bot Stopped by User"}
                )
        except:
            pass
    except Exception as e:
        logger.error(f"💥 Error starting FreqTrade: {e}")
        # Send error notification if possible
        try:
            if "worker" in locals() and worker.freqtrade.rpc:
                worker.freqtrade.rpc.send_msg(
                    {"type": "warning", "status": f"💥 FreqTrade Error: {str(e)}"}
                )
        except:
            pass
        raise


if __name__ == "__main__":
    start_adaptive_freqtrade()
