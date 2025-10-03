# FreqTrade Adaptive RL Trading - Makefile
# Einfache Verwaltung der Docker Services

.PHONY: help start stop restart logs build clean status monitor dev

# Default target
help:
	@echo "FreqTrade Adaptive RL Trading - Docker Management"
	@echo "================================================="
	@echo ""
	@echo "Available targets:"
	@echo "  start         - Start FreqTrade with adaptive throttling (DRY RUN)"
	@echo "  start-monitor - Start with TensorBoard monitoring"
	@echo "  start-dev     - Start development environment (with Jupyter)"
	@echo "  start-full    - Start all services (FreqTrade + Monitoring)"
	@echo "  stop          - Stop all services"
	@echo "  restart       - Restart FreqTrade service"
	@echo "  logs          - Show FreqTrade logs"
	@echo "  logs-follow   - Follow FreqTrade logs"
	@echo "  logs-telegram - Show Telegram notification logs"
	@echo "  build         - Build custom Docker image"
	@echo "  clean         - Stop and remove containers + volumes"
	@echo "  status        - Show service status"
	@echo "  monitor       - Open monitoring dashboards"
	@echo "  shell         - Open shell in FreqTrade container"
	@echo "  telegram-test - Test Telegram bot connection"
	@echo ""
	@echo "Configuration:"
	@echo "  setup         - Create .env file from template"
	@echo "  validate      - Validate configuration"

# Configuration setup
setup:
	@echo "Setting up environment configuration..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ Created .env file from template"; \
		echo "⚠️  Please edit .env and add your Binance API keys"; \
		echo "   nano .env"; \
	else \
		echo "⚠️  .env file already exists"; \
	fi

# Docker compose file
COMPOSE_FILE := docker-compose.adaptive-rl.yml
DOCKER_COMPOSE := docker-compose -f $(COMPOSE_FILE)

# Start services
start: setup
	@echo "🚀 Starting FreqTrade with Adaptive RL Throttling (DRY RUN)..."
	$(DOCKER_COMPOSE) up -d freqtrade-adaptive-rl
	@echo "✅ FreqTrade started! API available at http://localhost:8090"
	@echo "📱 Telegram Bot enabled for notifications"
	@echo "💰 Using READ-ONLY Binance API keys (DRY RUN mode)"

start-monitor: setup
	@echo "🚀 Starting FreqTrade with TensorBoard monitoring..."
	$(DOCKER_COMPOSE) --profile monitoring up -d
	@echo "✅ Services started!"
	@echo "   FreqTrade API: http://localhost:8090"
	@echo "   TensorBoard:   http://localhost:6007"

start-dev: setup
	@echo "🚀 Starting development environment..."
	$(DOCKER_COMPOSE) --profile development --profile monitoring up -d
	@echo "✅ Development environment started!"
	@echo "   FreqTrade API: http://localhost:8090"
	@echo "   TensorBoard:   http://localhost:6007"
	@echo "   Jupyter Lab:   http://localhost:8888"

start-full: setup
	@echo "🚀 Starting full monitoring stack..."
	$(DOCKER_COMPOSE) --profile monitoring up -d
	@echo "✅ Full stack started!"
	@echo "   FreqTrade API: http://localhost:8090"
	@echo "   TensorBoard:   http://localhost:6007"
	@echo "   Grafana:       http://localhost:3000 (admin/admin)"
	@echo "   Prometheus:    http://localhost:9090"

# Stop services
stop:
	@echo "🛑 Stopping FreqTrade services..."
	$(DOCKER_COMPOSE) --profile monitoring --profile development down
	@echo "✅ Services stopped"

# Restart main service
restart:
	@echo "🔄 Restarting FreqTrade..."
	$(DOCKER_COMPOSE) restart freqtrade-adaptive-rl
	@echo "✅ FreqTrade restarted"

# Logs
logs:
	@echo "📋 FreqTrade logs (last 50 lines):"
	$(DOCKER_COMPOSE) logs --tail=50 freqtrade-adaptive-rl

logs-follow:
	@echo "📋 Following FreqTrade logs (Ctrl+C to exit):"
	$(DOCKER_COMPOSE) logs -f freqtrade-adaptive-rl

logs-adaptive:
	@echo "📋 Adaptive throttling performance:"
	@$(DOCKER_COMPOSE) logs freqtrade-adaptive-rl 2>&1 | grep -E "(Adaptive|throttle|execution.*factor)" | tail -20

logs-telegram:
	@echo "📱 Telegram Bot notifications:"
	@$(DOCKER_COMPOSE) logs freqtrade-adaptive-rl 2>&1 | grep -E "(Telegram|telegram|notification)" | tail -20

# Telegram testing
telegram-test:
	@echo "📱 Testing Telegram Bot connection..."
	@if $(DOCKER_COMPOSE) ps freqtrade-adaptive-rl | grep -q Up; then \
		$(DOCKER_COMPOSE) exec freqtrade-adaptive-rl python /freqtrade/test_telegram.py; \
	else \
		echo "⚠️  Container not running, testing directly..."; \
		python test_telegram.py; \
	fi

# Build
build:
	@echo "🔨 Building FreqTrade Adaptive RL image..."
	$(DOCKER_COMPOSE) build freqtrade-adaptive-rl
	@echo "✅ Build completed"

# Clean up
clean:
	@echo "🧹 Cleaning up containers and volumes..."
	$(DOCKER_COMPOSE) --profile monitoring --profile development down -v
	docker system prune -f
	@echo "✅ Cleanup completed"

# Status
status:
	@echo "📊 Service Status:"
	@$(DOCKER_COMPOSE) ps

# Health check
health:
	@echo "🏥 Health Check:"
	@echo "FreqTrade API:"
	@curl -s http://localhost:8090/api/v1/ping || echo "❌ FreqTrade API not responding"
	@echo ""
	@echo "TensorBoard:"
	@curl -s http://localhost:6007 > /dev/null && echo "✅ TensorBoard is running" || echo "❌ TensorBoard not running"

# Open monitoring dashboards
monitor:
	@echo "🖥️  Opening monitoring dashboards..."
	@command -v open >/dev/null 2>&1 && open http://localhost:8090 || echo "FreqTrade API: http://localhost:8090"
	@command -v open >/dev/null 2>&1 && open http://localhost:6007 || echo "TensorBoard: http://localhost:6007"

# Shell access
shell:
	@echo "🐚 Opening shell in FreqTrade container..."
	$(DOCKER_COMPOSE) exec freqtrade-adaptive-rl /bin/bash

# Configuration validation
validate:
	@echo "✅ Validating configuration..."
	@if [ ! -f .env ]; then \
		echo "❌ .env file missing! Run 'make setup' first"; \
		exit 1; \
	fi
	@if [ ! -f user_data/config_binance_spot_longonly_rl.json ]; then \
		echo "❌ FreqTrade config missing!"; \
		exit 1; \
	fi
	@echo "✅ Configuration files found"
	@echo "🔍 Checking configuration details..."
	@grep -q "adaptive_throttling" user_data/config_binance_spot_longonly_rl.json && echo "✅ Adaptive throttling configured" || echo "⚠️  Adaptive throttling not found in config"
	@grep -q '"dry_run": true' user_data/config_binance_spot_longonly_rl.json && echo "✅ Dry run mode enabled (safe for read-only API)" || echo "⚠️  Dry run disabled - check if this is intended"
	@grep -q '"enabled": true' user_data/config_binance_spot_longonly_rl.json && echo "✅ Telegram notifications enabled" || echo "ℹ️  Telegram notifications disabled"
	@if [ -f .env ]; then \
		grep -q "TELEGRAM_TOKEN=79" .env && echo "✅ Telegram token configured" || echo "⚠️  Telegram token missing in .env"; \
		grep -q "BINANCE_API_KEY=" .env && echo "✅ Binance API key configured" || echo "⚠️  Binance API key missing in .env"; \
	fi

# Performance monitoring
perf:
	@echo "📈 Performance Metrics:"
	@echo "API Response Times (last 10):"
	@$(DOCKER_COMPOSE) logs freqtrade-adaptive-rl 2>&1 | grep -E "response.*time" | tail -10
	@echo ""
	@echo "Throttling Adjustments (last 10):"
	@$(DOCKER_COMPOSE) logs freqtrade-adaptive-rl 2>&1 | grep -E "Adaptive throttle" | tail -10

# Update
update:
	@echo "🔄 Updating FreqTrade image..."
	docker pull freqtradeorg/freqtrade:stable_freqai
	$(DOCKER_COMPOSE) build --no-cache freqtrade-adaptive-rl
	@echo "✅ Update completed - restart services to use new image"