#!/bin/bash
# =============================================================================
# FreqTrade Docker Entrypoint Script
# =============================================================================
# This script handles container initialization, environment setup,
# and graceful application startup/shutdown
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# Environment Setup
# =============================================================================
log_info "Starting FreqTrade container initialization..."

# Set default environment variables if not provided
export FREQTRADE_USER_DATA="${FREQTRADE_USER_DATA:-/freqtrade/user_data}"
export FREQTRADE_CONFIG="${FREQTRADE_CONFIG:-${FREQTRADE_USER_DATA}/config.json}"
export FREQTRADE_LOGFILE="${FREQTRADE_LOGFILE:-${FREQTRADE_USER_DATA}/logs/freqtrade.log}"
export FREQTRADE_DB_URL="${FREQTRADE_DB_URL:-sqlite:///${FREQTRADE_USER_DATA}/tradesv3.sqlite}"
export LOG_LEVEL="${LOG_LEVEL:-info}"

log_info "Environment configuration:"
log_info "  - User Data Dir: ${FREQTRADE_USER_DATA}"
log_info "  - Config File: ${FREQTRADE_CONFIG}"
log_info "  - Log File: ${FREQTRADE_LOGFILE}"
log_info "  - Database: ${FREQTRADE_DB_URL}"
log_info "  - Log Level: ${LOG_LEVEL}"

# =============================================================================
# Directory Setup
# =============================================================================
setup_directories() {
    log_info "Setting up directory structure..."
    
    # Create required directories if they don't exist
    mkdir -p "${FREQTRADE_USER_DATA}/data"
    mkdir -p "${FREQTRADE_USER_DATA}/logs"
    mkdir -p "${FREQTRADE_USER_DATA}/strategies"
    mkdir -p "${FREQTRADE_USER_DATA}/hyperopts"
    mkdir -p "${FREQTRADE_USER_DATA}/hyperopt_results"
    mkdir -p "${FREQTRADE_USER_DATA}/plot"
    mkdir -p "${FREQTRADE_USER_DATA}/notebooks"
    mkdir -p "${FREQTRADE_USER_DATA}/models"  # For FreqAI
    
    # Set proper permissions
    if [ "$(id -u)" = "0" ]; then
        # Running as root, set ownership to ftuser
        chown -R ftuser:ftuser "${FREQTRADE_USER_DATA}" 2>/dev/null || true
    fi
    
    log_success "Directory structure created"
}

# =============================================================================
# Configuration Validation
# =============================================================================
validate_config() {
    log_info "Validating configuration..."
    
    # Check if config file exists
    if [ ! -f "${FREQTRADE_CONFIG}" ]; then
        log_warning "Configuration file not found: ${FREQTRADE_CONFIG}"
        log_info "Creating default configuration structure..."
        
        # Create a basic config structure if it doesn't exist
        cat > "${FREQTRADE_CONFIG}" <<EOF
{
    "max_open_trades": 3,
    "stake_currency": "USDT",
    "stake_amount": "unlimited",
    "tradable_balance_ratio": 0.99,
    "fiat_display_currency": "USD",
    "dry_run": true,
    "cancel_open_orders_on_exit": false,
    "unfilledtimeout": {
        "entry": 10,
        "exit": 10,
        "exit_timeout_count": 0,
        "unit": "minutes"
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
    "exchange": {
        "name": "binance",
        "key": "",
        "secret": "",
        "ccxt_config": {},
        "ccxt_async_config": {},
        "pair_whitelist": [],
        "pair_blacklist": []
    },
    "pairlists": [
        {"method": "StaticPairList"}
    ],
    "telegram": {
        "enabled": false,
        "token": "",
        "chat_id": ""
    },
    "api_server": {
        "enabled": false,
        "listen_ip_address": "0.0.0.0",
        "listen_port": 8080,
        "verbosity": "error",
        "enable_openapi": false,
        "jwt_secret_key": "",
        "ws_token": "",
        "CORS_origins": []
    },
    "bot_name": "freqtrade",
    "initial_state": "running",
    "force_entry_enable": false,
    "internals": {
        "process_throttle_secs": 5
    }
}
EOF
        log_warning "Basic configuration created. Please customize it before trading!"
    fi
    
    # Validate config syntax with FreqTrade
    if ! freqtrade show-config --config "${FREQTRADE_CONFIG}" > /dev/null 2>&1; then
        log_error "Configuration validation failed!"
        log_error "Please check your configuration file: ${FREQTRADE_CONFIG}"
        exit 1
    fi
    
    log_success "Configuration validated successfully"
}

# =============================================================================
# Database Setup
# =============================================================================
setup_database() {
    log_info "Setting up database..."
    
    # Check if database exists and is accessible
    if [[ "${FREQTRADE_DB_URL}" == sqlite* ]]; then
        DB_PATH=$(echo "${FREQTRADE_DB_URL}" | sed 's|sqlite:///||')
        DB_DIR=$(dirname "${DB_PATH}")
        
        # Ensure database directory exists
        mkdir -p "${DB_DIR}"
        
        if [ -f "${DB_PATH}" ]; then
            log_info "Database found at: ${DB_PATH}"
            
            # Check database integrity
            if sqlite3 "${DB_PATH}" "PRAGMA integrity_check;" > /dev/null 2>&1; then
                log_success "Database integrity check passed"
            else
                log_warning "Database integrity check failed. Backup recommended!"
            fi
        else
            log_info "Database will be created at: ${DB_PATH}"
        fi
    elif [[ "${FREQTRADE_DB_URL}" == postgresql* ]]; then
        log_info "Using PostgreSQL database"
        # Database will be created by FreqTrade on first run
    fi
}

# =============================================================================
# Health Check Setup
# =============================================================================
setup_healthcheck() {
    log_info "Setting up health check endpoint..."
    
    # Create health check script
    cat > /tmp/health_check.sh <<'EOF'
#!/bin/bash
# Simple health check for FreqTrade
set -e

# Check if FreqTrade process is running
if ! pgrep -f "freqtrade" > /dev/null; then
    echo "FreqTrade process not running"
    exit 1
fi

# If API is enabled, check API endpoint
if [ -f "/freqtrade/user_data/config.json" ]; then
    API_ENABLED=$(grep -o '"enabled"[[:space:]]*:[[:space:]]*true' /freqtrade/user_data/config.json | head -1)
    if [ -n "$API_ENABLED" ]; then
        if ! curl -sf http://localhost:8080/api/v1/ping > /dev/null 2>&1; then
            echo "API not responding"
            exit 1
        fi
    fi
fi

echo "FreqTrade is healthy"
exit 0
EOF
    chmod +x /tmp/health_check.sh
    
    log_success "Health check script created"
}

# =============================================================================
# Signal Handling for Graceful Shutdown
# =============================================================================
graceful_shutdown() {
    log_warning "Received shutdown signal, stopping FreqTrade gracefully..."
    
    # Send SIGTERM to FreqTrade process
    if [ -n "${FREQTRADE_PID}" ]; then
        kill -TERM "${FREQTRADE_PID}" 2>/dev/null || true
        
        # Wait for process to terminate (max 30 seconds)
        for i in {1..30}; do
            if ! kill -0 "${FREQTRADE_PID}" 2>/dev/null; then
                log_success "FreqTrade stopped gracefully"
                exit 0
            fi
            sleep 1
        done
        
        # Force kill if still running
        log_warning "Force stopping FreqTrade..."
        kill -KILL "${FREQTRADE_PID}" 2>/dev/null || true
    fi
    
    exit 0
}

# Trap signals for graceful shutdown
trap graceful_shutdown SIGTERM SIGINT SIGQUIT

# =============================================================================
# Pre-flight Checks
# =============================================================================
preflight_checks() {
    log_info "Running pre-flight checks..."
    
    # Check FreqTrade installation
    if ! command -v freqtrade &> /dev/null; then
        log_error "FreqTrade not found in PATH"
        exit 1
    fi
    
    # Display FreqTrade version
    FREQTRADE_VERSION=$(freqtrade --version 2>&1 | head -1)
    log_info "FreqTrade version: ${FREQTRADE_VERSION}"
    
    # Check Python version
    PYTHON_VERSION=$(python --version 2>&1)
    log_info "Python version: ${PYTHON_VERSION}"
    
    # Check available disk space
    DISK_USAGE=$(df -h "${FREQTRADE_USER_DATA}" | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "${DISK_USAGE}" -gt 90 ]; then
        log_warning "Disk usage is at ${DISK_USAGE}%"
    fi
    
    log_success "Pre-flight checks completed"
}

# =============================================================================
# Initialization
# =============================================================================
initialize() {
    setup_directories
    validate_config
    setup_database
    setup_healthcheck
    preflight_checks
}

# =============================================================================
# Main Execution
# =============================================================================
main() {
    log_info "========================================"
    log_info "FreqTrade Docker Container"
    log_info "========================================"
    
    # Run initialization
    initialize
    
    log_success "Initialization complete!"
    log_info "========================================"
    
    # If no command provided, run freqtrade with default arguments
    if [ $# -eq 0 ]; then
        log_info "Starting FreqTrade with default configuration..."
        exec freqtrade trade \
            --config "${FREQTRADE_CONFIG}" \
            --logfile "${FREQTRADE_LOGFILE}" \
            --db-url "${FREQTRADE_DB_URL}" &
        FREQTRADE_PID=$!
        
        # Wait for FreqTrade process
        wait "${FREQTRADE_PID}"
    else
        # Execute provided command
        log_info "Executing command: $*"
        exec "$@"
    fi
}

# Run main function with all arguments
main "$@"
