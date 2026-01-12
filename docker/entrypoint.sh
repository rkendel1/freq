#!/bin/bash
set -e

echo "🚀 Freqtrade Docker Development Environment"
echo "============================================="

# Directories to create
USER_DATA_DIR="/freqtrade/user_data"
LOGS_DIR="${USER_DATA_DIR}/logs"
DATA_DIR="${USER_DATA_DIR}/data"
STRATEGIES_DIR="${USER_DATA_DIR}/strategies"
EXPLOITS_DIR="${USER_DATA_DIR}/exploits"

# Configuration file paths
CONFIG_FILE="${USER_DATA_DIR}/config.prod.json"
DEFAULT_CONFIG_TEMPLATE="/freqtrade/config.prod.json.example"

echo "📁 Setting up user_data directory structure..."

# Create directory structure if it doesn't exist
mkdir -p "${LOGS_DIR}" "${DATA_DIR}" "${STRATEGIES_DIR}" "${EXPLOITS_DIR}"

# Fix permissions for mounted volumes
if [ -d "${USER_DATA_DIR}" ]; then
    # Only change ownership if needed (to avoid errors with read-only volumes)
    if [ "$(stat -c '%u' ${USER_DATA_DIR})" != "1000" ]; then
        echo "🔧 Fixing permissions for user_data directory..."
        sudo chown -R ftuser:ftuser "${USER_DATA_DIR}" 2>/dev/null || true
    fi
fi

# Initialize configuration if it doesn't exist
if [ ! -f "${CONFIG_FILE}" ]; then
    echo "📝 Creating default configuration file..."
    
    if [ -f "${DEFAULT_CONFIG_TEMPLATE}" ]; then
        cp "${DEFAULT_CONFIG_TEMPLATE}" "${CONFIG_FILE}"
    else
        # Create minimal config if template doesn't exist
        cat > "${CONFIG_FILE}" <<EOF
{
  "max_open_trades": 3,
  "stake_currency": "USDT",
  "stake_amount": "unlimited",
  "tradable_balance_ratio": 0.99,
  "fiat_display_currency": "USD",
  "dry_run": true,
  "initial_capital": ${INITIAL_CAPITAL:-10000.0},
  "exploit_modules": [],
  "exchange": {
    "name": "${EXCHANGE_NAME:-binance}",
    "key": "",
    "secret": "",
    "ccxt_config": {},
    "ccxt_async_config": {},
    "pair_whitelist": ["BTC/USDT", "ETH/USDT"],
    "pair_blacklist": []
  },
  "risk_limits": {
    "max_position_size": 0.2,
    "max_total_exposure": 0.8,
    "max_open_positions": 3,
    "max_loss_per_trade": 0.1,
    "max_daily_loss": 0.2,
    "position_cooldown": 0
  },
  "entry_pricing": {
    "price_side": "same",
    "use_order_book": true,
    "order_book_top": 1,
    "price_last_balance": 0.0,
    "check_depth_of_market": {
      "enabled": false,
      "bids_to_ask_delta": 1
    }
  },
  "exit_pricing": {
    "price_side": "same",
    "use_order_book": true,
    "order_book_top": 1
  },
  "pairlists": [{"method": "StaticPairList"}],
  "bot_name": "freqtrade_docker_dev",
  "initial_state": "running",
  "force_entry_enable": false,
  "internals": {
    "process_throttle_secs": 5
  }
}
EOF
    fi
    
    echo "✅ Configuration file created at: ${CONFIG_FILE}"
else
    echo "✅ Configuration file already exists: ${CONFIG_FILE}"
fi

# Initialize database if it doesn't exist
DB_FILE="${USER_DATA_DIR}/tradesv3.sqlite"
if [ ! -f "${DB_FILE}" ]; then
    echo "🗄️  Initializing SQLite database..."
    touch "${DB_FILE}"
    echo "✅ Database initialized at: ${DB_FILE}"
else
    echo "✅ Database already exists: ${DB_FILE}"
fi

# Create a README in user_data for first-time users
README_FILE="${USER_DATA_DIR}/README.md"
if [ ! -f "${README_FILE}" ]; then
    cat > "${README_FILE}" <<EOF
# Freqtrade User Data Directory

This directory contains your persistent configuration, data, and logs.

## Structure

- \`config.prod.json\` - Main configuration file
- \`logs/\` - Application and dashboard logs
- \`data/\` - Market data cache
- \`strategies/\` - Custom trading strategies (if using original Freqtrade strategies)
- \`exploits/\` - Custom ExploitModules for trading logic
- \`tradesv3.sqlite\` - SQLite database for trades and orders

## Accessing Services

- **Demo UI**: http://localhost:5000
- **Configuration Dashboard**: http://localhost:8501
- **Monitoring Dashboard**: http://localhost:8502

## Configuration Dashboard

The configuration dashboard (port 8501) allows you to:
- Select and configure ExploitModules
- Configure exchange settings (supports all CCXT exchanges)
- Set risk limits and capital management
- Manage API credentials securely

**Security Note**: Set the \`STREAMLIT_PASSWORD\` environment variable to enable password protection.

## Monitoring Dashboard

The monitoring dashboard (port 8502) provides real-time visibility into:
- Capital state (available, deployed, total)
- Open positions
- Recent orders
- Cumulative PnL chart
- Live logs

## Custom ExploitModules

To use custom ExploitModules:

1. Place your module files in \`./exploits/\`
2. They will be auto-discovered by the configuration dashboard
3. Or mount them via Docker: \`-v ./my_exploits:/freqtrade/custom_exploits\`

## Environment Variables

- \`STREAMLIT_PASSWORD\` - Password for configuration dashboard
- \`INITIAL_CAPITAL\` - Initial capital amount (default: 10000.0)
- \`EXCHANGE_NAME\` - Exchange to use (default: binance)
- \`DRY_RUN\` - Enable dry-run mode (default: true)
- \`LOG_LEVEL\` - Logging level (default: INFO)

## Documentation

For more information, see:
- Main README: /freqtrade/README.md
- Architecture: /freqtrade/ARCHITECTURE.md
- Local Development: /freqtrade/LOCAL_DEVELOPMENT.md
EOF
fi

# Display environment info
echo ""
echo "🌍 Environment Configuration:"
echo "   - Dry Run Mode: ${DRY_RUN:-true}"
echo "   - Initial Capital: \$${INITIAL_CAPITAL:-10000.0}"
echo "   - Exchange: ${EXCHANGE_NAME:-binance}"
echo "   - Log Level: ${LOG_LEVEL:-INFO}"
[ -n "$STREAMLIT_PASSWORD" ] && echo "   - Config Dashboard Password: ✅ Set" || echo "   - Config Dashboard Password: ⚠️  Not set (recommended)"

echo ""
echo "📊 Services will be available at:"
echo "   - Demo UI:              http://localhost:5000"
echo "   - Configuration Panel:  http://localhost:8501"
echo "   - Monitoring Dashboard: http://localhost:8502"
echo ""
echo "📁 Data directory: ${USER_DATA_DIR}"
echo ""

# Check if we should run database migrations
# (In future, this could call freqtrade migrations)
echo "🔄 Checking database schema..."
# Placeholder for future migration logic
# python -c "from freqtrade.persistence import init_db; init_db('sqlite:///${DB_FILE}')" || true

echo ""
echo "✅ Initialization complete!"
echo "🚀 Starting services with supervisord..."
echo ""

# Execute the main command (supervisord or whatever was passed)
exec "$@"
