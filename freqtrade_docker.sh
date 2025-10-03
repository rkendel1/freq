#!/bin/bash
#
# FreqTrade Docker Setup Script
# Provides easy commands for different FreqTrade configurations
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if docker and docker-compose are installed
check_dependencies() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
}

# Function to create required directories
setup_directories() {
    print_info "Creating required directories..."
    mkdir -p user_data/{config,data,logs,strategies,hyperopts,models,hyperopt_results}
    mkdir -p notebooks
    print_success "Directories created successfully"
}

# Function to show usage
show_usage() {
    echo "FreqTrade Docker Setup Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  standard         - Run standard FreqTrade"
    echo "  freqai          - Run FreqTrade with FreqAI"
    echo "  hyperopt        - Run Hyperopt optimization"
    echo "  freqai-hyperopt - Run FreqAI with Hyperopt optimization"
    echo "  jupyter         - Start Jupyter notebook for analysis"
    echo "  database        - Start PostgreSQL database"
    echo "  stop            - Stop all services"
    echo "  logs            - Show logs for a service"
    echo "  setup           - Setup directories and initial config"
    echo "  status          - Show status of all services"
    echo ""
    echo "Examples:"
    echo "  $0 setup           # Initial setup"
    echo "  $0 standard        # Run standard trading"
    echo "  $0 freqai          # Run with FreqAI"
    echo "  $0 hyperopt        # Run hyperopt optimization"
    echo "  $0 logs freqtrade  # Show logs for freqtrade service"
}

# Function to run standard FreqTrade
run_standard() {
    print_info "Starting standard FreqTrade..."
    docker-compose up -d freqtrade
    print_success "FreqTrade started. Access UI at http://localhost:8080"
}

# Function to run FreqAI
run_freqai() {
    print_info "Starting FreqTrade with FreqAI..."
    docker-compose --profile freqai up -d freqtrade-freqai
    print_success "FreqTrade with FreqAI started. Access UI at http://localhost:8081"
    print_warning "Make sure you have a proper FreqAI configuration in user_data/config_freqai.json"
}

# Function to run Hyperopt
run_hyperopt() {
    print_info "Starting Hyperopt optimization..."
    docker-compose --profile hyperopt up freqtrade-hyperopt
    print_success "Hyperopt optimization completed. Check results in user_data/hyperopt_results/"
}

# Function to run FreqAI + Hyperopt
run_freqai_hyperopt() {
    print_info "Starting FreqAI with Hyperopt optimization..."
    docker-compose --profile freqai-hyperopt up freqtrade-freqai-hyperopt
    print_success "FreqAI Hyperopt optimization completed. Check results in user_data/hyperopt_results/"
}

# Function to start Jupyter
run_jupyter() {
    print_info "Starting Jupyter notebook..."
    docker-compose --profile jupyter up -d jupyter
    print_success "Jupyter started. Access at http://localhost:8888"
}

# Function to start database
run_database() {
    print_info "Starting PostgreSQL database..."
    docker-compose --profile database up -d postgres
    print_success "PostgreSQL started. Connect at localhost:5432"
}

# Function to stop all services
stop_services() {
    print_info "Stopping all FreqTrade services..."
    docker-compose down
    print_success "All services stopped"
}

# Function to show logs
show_logs() {
    local service=${1:-freqtrade}
    print_info "Showing logs for $service..."
    docker-compose logs -f "$service"
}

# Function to show status
show_status() {
    print_info "Service status:"
    docker-compose ps
}

# Function to setup initial configuration
setup_config() {
    setup_directories

    if [ ! -f "user_data/config.json" ]; then
        print_info "Creating example configuration..."
        cat > user_data/config.json << 'EOF'
{
    "max_open_trades": 3,
    "stake_currency": "USDT",
    "stake_amount": 100,
    "tradable_balance_ratio": 0.99,
    "fiat_display_currency": "USD",
    "dry_run": true,
    "dry_run_wallet": 1000,
    "timeframe": "5m",
    "exchange": {
        "name": "binance",
        "key": "your_api_key_here",
        "secret": "your_api_secret_here",
        "ccxt_config": {
            "enableRateLimit": true
        },
        "pair_whitelist": [
            "BTC/USDT",
            "ETH/USDT"
        ]
    },
    "pairlist": {
        "method": "StaticPairList"
    },
    "api_server": {
        "enabled": true,
        "listen_ip_address": "0.0.0.0",
        "listen_port": 8080,
        "verbosity": "error",
        "enable_openapi": false,
        "jwt_secret_key": "something-secret",
        "CORS_origins": [],
        "username": "admin",
        "password": "password"
    },
    "bot_name": "freqtrade",
    "initial_state": "running",
    "force_entry_enable": false
}
EOF
        print_success "Example configuration created at user_data/config.json"
        print_warning "Please update the API keys and other settings before running!"
    fi

    if [ ! -f "user_data/config_freqai.json" ]; then
        print_info "Creating FreqAI configuration example..."
        cp user_data/config.json user_data/config_freqai.json
        # Add FreqAI configuration to the file
        python3 -c "
import json
with open('user_data/config_freqai.json', 'r') as f:
    config = json.load(f)

config['freqai'] = {
    'enabled': True,
    'purge_old_models': True,
    'train_period_days': 30,
    'backtest_period_days': 7,
    'identifier': 'example',
    'feature_parameters': {
        'include_timeframes': ['5m', '15m', '4h'],
        'include_corr_pairlist': ['ETH/USDT', 'LINK/USDT'],
        'label_period_candles': 24,
        'include_shifted_candles': 2,
        'DI_threshold': 0.9,
        'weight_factor': 0.9,
        'principal_component_analysis': False,
        'use_SVM_to_remove_outliers': True,
        'indicator_periods_candles': [10, 20, 50]
    },
    'data_split_parameters': {
        'test_size': 0.33,
        'shuffle': False
    },
    'model_training_parameters': {
        'n_estimators': 1000
    }
}

with open('user_data/config_freqai.json', 'w') as f:
    json.dump(config, f, indent=4)
" 2>/dev/null || print_warning "Could not create FreqAI config automatically. Please create manually."
        print_success "FreqAI configuration created at user_data/config_freqai.json"
    fi
}

# Main script logic
main() {
    check_dependencies

    case "${1:-}" in
        "standard")
            run_standard
            ;;
        "freqai")
            run_freqai
            ;;
        "hyperopt")
            run_hyperopt
            ;;
        "freqai-hyperopt")
            run_freqai_hyperopt
            ;;
        "jupyter")
            run_jupyter
            ;;
        "database")
            run_database
            ;;
        "stop")
            stop_services
            ;;
        "logs")
            show_logs "$2"
            ;;
        "status")
            show_status
            ;;
        "setup")
            setup_config
            ;;
        *)
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"