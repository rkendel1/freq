#!/bin/bash

# Adaptive FreqTrade RL Trading Startup Script
# Optimized for Binance Spot Long-Only RL Strategy with intelligent throttling

set -e

echo "🚀 Starting FreqTrade with Adaptive Throttling for RL Trading"
echo "=================================================="

# Configuration
CONFIG_FILE="user_data/config_binance_spot_longonly_rl.json"
STRATEGY_PATH="user_data/strategies"
LOG_LEVEL="info"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Configuration file not found: $CONFIG_FILE"
    exit 1
fi

# Display adaptive throttling info
echo "📊 Adaptive Throttling Configuration:"
echo "   ├─ Base throttle: 2.0s (adaptive from 1.2s to 8.0s)"
echo "   ├─ RL model overhead: 0.8s (for TensorFlow inference)"
echo "   ├─ Binance API rate factor: 1.5x (conservative)"
echo "   ├─ Volatility adjustment: ENABLED"
echo "   └─ Trade scaling factor: 0.2x per trade"
echo ""

# Check if we should use the adaptive starter
if [ -f "adaptive_freqtrade_start.py" ]; then
    echo "🎯 Using adaptive throttling startup script..."
    python adaptive_freqtrade_start.py \
        --config "$CONFIG_FILE" \
        --strategy-path "$STRATEGY_PATH" \
        --verbosity "$LOG_LEVEL" \
        "$@"
else
    echo "⚠️  Adaptive startup script not found, using standard FreqTrade..."
    echo "   (Throttling will be fixed at 2.0s instead of adaptive)"
    freqtrade trade \
        --config "$CONFIG_FILE" \
        --strategy-path "$STRATEGY_PATH" \
        --verbosity "$LOG_LEVEL" \
        "$@"
fi

echo ""
echo "✅ FreqTrade session ended"