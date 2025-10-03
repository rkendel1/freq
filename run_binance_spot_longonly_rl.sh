#!/bin/bash

# ================================================================
# 🚀 BINANCE SPOT LONG-ONLY TENSORFLOW RL SYSTEM
# Automatisierter Workflow für präzise Long-Entscheidungen
# ================================================================

set -e  # Stoppe bei Fehlern

# Farben für bessere Ausgabe
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Funktionen
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

print_header() {
    echo ""
    echo "================================================================"
    echo -e "${PURPLE}🎯 $1${NC}"
    echo "================================================================"
}

print_subheader() {
    echo ""
    echo -e "${CYAN}📋 $1${NC}"
    echo "----------------------------------------"
}

# ================================================================
# HAUPTFUNKTIONEN
# ================================================================

check_system() {
    print_header "SYSTEM-ÜBERPRÜFUNG"

    log_info "Überprüfe Python-Umgebung..."
    python --version || { log_error "Python nicht verfügbar!"; exit 1; }

    log_info "Überprüfe FreqTrade Installation..."
    freqtrade --version || { log_error "FreqTrade nicht verfügbar!"; exit 1; }

    log_info "Überprüfe TensorFlow..."
    python -c "import tensorflow as tf; print(f'TensorFlow {tf.__version__} verfügbar')" || {
        log_warning "TensorFlow nicht verfügbar - installiere FreqAI Dependencies"
        pip install -r requirements-freqai.txt
    }

    log_info "Überprüfe Konfigurationsdateien..."

    REQUIRED_FILES=(
        "user_data/config_binance_spot_longonly_rl.json"
        "user_data/strategies/BinanceSpotLongOnlyRLStrategy.py"
        "user_data/freqaimodels/BinanceSpotLongOnlyRLModel.py"
    )

    for file in "${REQUIRED_FILES[@]}"; do
        if [[ -f "$file" ]]; then
            log_success "✓ $file vorhanden"
        else
            log_error "✗ $file fehlt!"
            exit 1
        fi
    done

    log_success "System-Check abgeschlossen!"
}

download_data() {
    print_header "DATEN-DOWNLOAD FÜR BINANCE SPOT"

    # Hauptpaare für Spot Trading
    PAIRS="BTC/USDT ETH/USDT"

    print_subheader "5m Daten (Haupt-Zeitrahmen)"
    freqtrade download-data \
        --config user_data/config_binance_spot_longonly_rl.json \
        --timeframe 5m \
        --pairs $PAIRS \
        --days 180 \
        --exchange binance \
        --trading-mode spot || log_warning "5m Download mit Problemen"

    print_subheader "15m Daten (Informativ)"
    freqtrade download-data \
        --config user_data/config_binance_spot_longonly_rl.json \
        --timeframe 15m \
        --pairs $PAIRS \
        --days 180 \
        --exchange binance \
        --trading-mode spot || log_warning "15m Download mit Problemen"

    print_subheader "1h Daten (Trend-Kontext)"
    freqtrade download-data \
        --config user_data/config_binance_spot_longonly_rl.json \
        --timeframe 1h \
        --pairs $PAIRS \
        --days 365 \
        --exchange binance \
        --trading-mode spot || log_warning "1h Download mit Problemen"

    log_success "Daten-Download abgeschlossen!"

    # Überprüfe heruntergeladene Daten
    print_subheader "Daten-Validierung"
    for pair in "BTC_USDT" "ETH_USDT"; do
        if ls user_data/data/binance/${pair}-5m-*.json 1> /dev/null 2>&1; then
            log_success "✓ ${pair} 5m Daten verfügbar"
        else
            log_error "✗ ${pair} 5m Daten fehlen"
        fi
    done
}

train_rl_model() {
    print_header "TENSORFLOW RL MODEL TRAINING"

    log_info "Starte FreqAI RL Training..."
    echo ""
    echo "🧠 Das TensorFlow Netzwerk lernt jetzt:"
    echo "   📈 Wann ist der optimale Zeitpunkt zum KAUFEN (günstig)?"
    echo "   📉 Wann ist der optimale Zeitpunkt zum VERKAUFEN (teuer)?"
    echo "   🔍 Wie interpretiert man Indikatoren mathematisch?"
    echo "   ⚖️  Wann bestätigen VIELE Indikatoren GLEICHZEITIG?"
    echo ""

    # Erstelle Tensorboard-Verzeichnis
    mkdir -p user_data/tensorboard/BinanceSpotLongOnlyRL

    # Starte Training
    freqtrade trade \
        --config user_data/config_binance_spot_longonly_rl.json \
        --strategy BinanceSpotLongOnlyRLStrategy \
        --freqaimodel BinanceSpotLongOnlyRLModel \
        --dry-run \
        || log_warning "RL Training mit Problemen abgeschlossen"

    log_success "RL Training abgeschlossen!"

    # Zeige Tensorboard-Info
    echo ""
    log_info "📊 Tensorboard Monitoring verfügbar:"
    log_info "   Starte: tensorboard --logdir user_data/tensorboard/BinanceSpotLongOnlyRL"
    log_info "   URL: http://localhost:6006"
}

run_backtesting() {
    print_header "BACKTESTING MIT TENSORFLOW RL"

    log_info "Starte umfassendes Backtesting..."

    freqtrade backtesting \
        --config user_data/config_binance_spot_longonly_rl.json \
        --strategy BinanceSpotLongOnlyRLStrategy \
        --freqaimodel BinanceSpotLongOnlyRLModel \
        --timerange 20240801-20241003 \
        --enable-position-stacking \
        --breakdown month \
        --export trades \
        --cache none \
        || log_error "Backtesting fehlgeschlagen"

    log_success "Backtesting abgeschlossen!"

    # Analysiere Ergebnisse
    print_subheader "Ergebnis-Analyse"
    freqtrade backtesting-analysis \
        --config user_data/config_binance_spot_longonly_rl.json \
        --analysis-groups 0 1 2 \
        || log_warning "Analyse mit Problemen"
}

run_hyperopt() {
    print_header "HYPEROPT PARAMETER-OPTIMIERUNG"

    echo "Anzahl der Hyperopt-Epochen eingeben (empfohlen: 200-500):"
    read -r epochs

    if [[ -z "$epochs" ]]; then
        epochs=200
        log_info "Standard-Epochen verwendet: $epochs"
    fi

    log_info "Starte Hyperopt mit $epochs Epochen..."
    log_info "🎯 Optimiert werden:"
    log_info "   📊 RSI, MACD, Bollinger Bands Parameter"
    log_info "   🔊 Volume-Schwellenwerte"
    log_info "   🎯 Mindest-Indikator-Bestätigungen"
    log_info "   📈 Trend- und Momentum-Parameter"

    freqtrade hyperopt \
        --config user_data/config_binance_spot_longonly_rl.json \
        --strategy BinanceSpotLongOnlyRLStrategy \
        --hyperopt-loss SortinoHyperOptLoss \
        --spaces buy sell \
        --epochs $epochs \
        --timerange 20240701-20241003 \
        --enable-position-stacking \
        || log_warning "Hyperopt mit Problemen abgeschlossen"

    log_success "Hyperopt abgeschlossen!"

    # Zeige beste Ergebnisse
    print_subheader "Beste Parameter"
    freqtrade hyperopt-show -n 5 \
        --config user_data/config_binance_spot_longonly_rl.json \
        --print-json > user_data/best_params_$(date +%Y%m%d_%H%M%S).json

    log_info "Beste Parameter gespeichert in user_data/"
}

start_dry_run() {
    print_header "DRY-RUN MIT TENSORFLOW RL"

    log_info "Starte Dry-Run Trading..."
    log_info "�� Trading-Regeln:"
    log_info "   ✅ Nur Long-Positionen (kein Short)"
    log_info "   ✅ Nur bei VIELEN Indikator-Bestätigungen"
    log_info "   ✅ Günstig kaufen (überverkauft, untere BB)"
    log_info "   ✅ Teuer verkaufen (überkauft, obere BB)"
    log_info "   ✅ Kontinuierliches RL-Learning"

    echo ""
    log_info "🚀 Starte FreqTrade mit TensorFlow RL..."
    echo ""

    freqtrade trade \
        --config user_data/config_binance_spot_longonly_rl.json \
        --strategy BinanceSpotLongOnlyRLStrategy \
        --freqaimodel BinanceSpotLongOnlyRLModel \
        || log_error "Trading-Bot Fehler"
}

create_live_config() {
    print_header "LIVE-TRADING KONFIGURATION"

    log_warning "⚠️  LIVE-TRADING VORBEREITUNG ⚠️"
    echo ""
    log_info "Erstelle Live-Trading Konfiguration..."

    # Kopiere und modifiziere Konfiguration
    cp user_data/config_binance_spot_longonly_rl.json user_data/config_live_binance_spot_rl.json

    # Setze Live-Trading Parameter
    sed -i 's/"dry_run": true/"dry_run": false/' user_data/config_live_binance_spot_rl.json
    sed -i 's/"dry_run_wallet": 10000/"dry_run_wallet": 0/' user_data/config_live_binance_spot_rl.json
    sed -i 's/"stake_amount": "unlimited"/"stake_amount": 50/' user_data/config_live_binance_spot_rl.json
    sed -i 's/"max_open_trades": 3/"max_open_trades": 2/' user_data/config_live_binance_spot_rl.json

    log_success "Live-Konfiguration erstellt: user_data/config_live_binance_spot_rl.json"

    echo ""
    log_warning "🔑 WICHTIGE SCHRITTE VOR LIVE-TRADING:"
    echo "1. Binance API Keys in config_live_binance_spot_rl.json eintragen"
    echo "2. API Permissions überprüfen (nur Spot Trading!)"
    echo "3. Mit KLEINEN Beträgen starten (stake_amount: 10-50 USDT)"
    echo "4. Dry-Run Ergebnisse gründlich analysieren"
    echo "5. Risk Management Parameter anpassen"
    echo ""
    echo "🚀 Live-Trading starten:"
    echo "freqtrade trade --config user_data/config_live_binance_spot_rl.json --strategy BinanceSpotLongOnlyRLStrategy --freqaimodel BinanceSpotLongOnlyRLModel"
}

show_monitoring() {
    print_header "MONITORING & ANALYTICS"

    echo "📊 VERFÜGBARE MONITORING-TOOLS:"
    echo ""
    echo "1. 🌐 FreqUI (Web-Interface):"
    echo "   URL: http://localhost:8082"
    echo "   Username: admin"
    echo "   Password: SpotRL2025Secure!"
    echo ""
    echo "2. 📈 TensorBoard (RL-Training Metrics):"
    echo "   Start: tensorboard --logdir user_data/tensorboard/BinanceSpotLongOnlyRL"
    echo "   URL: http://localhost:6006"
    echo ""
    echo "3. 📋 API Documentation:"
    echo "   URL: http://localhost:8082/docs"
    echo ""
    echo "4. 📊 Performance Analysis:"
    echo "   Backtest Results: user_data/backtest_results/"
    echo "   Trade History: user_data/tradesv3.sqlite"
    echo ""
    echo "5. 🔍 Log Files:"
    echo "   Logs: user_data/logs/"
    echo "   Models: user_data/models/BinanceSpotLongOnlyRL/"
}

# ================================================================
# HAUPTMENÜ
# ================================================================

show_menu() {
    clear
    echo ""
    echo "================================================================"
    echo -e "${PURPLE}🎯 BINANCE SPOT LONG-ONLY TENSORFLOW RL SYSTEM${NC}"
    echo -e "${CYAN}   Günstig kaufen, teuer verkaufen - Nur Long-Positionen${NC}"
    echo "================================================================"
    echo ""
    echo "Wählen Sie eine Option:"
    echo ""
    echo "1) 🔧 System-Check & Vorbereitung"
    echo "2) 📥 Daten herunterladen"
    echo "3) 🧠 TensorFlow RL Model trainieren"
    echo "4) 📊 Backtesting durchführen"
    echo "5) ⚙️  Hyperopt Parameter-Optimierung"
    echo "6) �� Dry-Run starten"
    echo "7) 🔴 Live-Trading Konfiguration"
    echo "8) 📈 Monitoring & Analytics"
    echo "9) 🔄 Kompletter Workflow (1-6)"
    echo "0) ❌ Beenden"
    echo ""
    echo -n "Ihre Wahl: "
}

# ================================================================
# MAIN LOOP
# ================================================================

main() {
    while true; do
        show_menu
        read -r choice

        case $choice in
            1)
                check_system
                echo ""
                read -p "Drücken Sie Enter um fortzufahren..."
                ;;
            2)
                download_data
                echo ""
                read -p "Drücken Sie Enter um fortzufahren..."
                ;;
            3)
                train_rl_model
                echo ""
                read -p "Drücken Sie Enter um fortzufahren..."
                ;;
            4)
                run_backtesting
                echo ""
                read -p "Drücken Sie Enter um fortzufahren..."
                ;;
            5)
                run_hyperopt
                echo ""
                read -p "Drücken Sie Enter um fortzufahren..."
                ;;
            6)
                start_dry_run
                ;;
            7)
                create_live_config
                echo ""
                read -p "Drücken Sie Enter um fortzufahren..."
                ;;
            8)
                show_monitoring
                echo ""
                read -p "Drücken Sie Enter um fortzufahren..."
                ;;
            9)
                log_info "🔄 Starte kompletten Workflow..."
                check_system
                download_data
                train_rl_model
                run_backtesting
                run_hyperopt
                echo ""
                log_success "🎉 Kompletter Workflow abgeschlossen!"
                log_info "System bereit für Dry-Run oder Live-Trading!"
                echo ""
                read -p "Drücken Sie Enter um fortzufahren..."
                ;;
            0)
                echo ""
                log_info "👋 Auf Wiedersehen!"
                exit 0
                ;;
            *)
                echo ""
                log_error "Ungültige Auswahl. Bitte versuchen Sie es erneut."
                sleep 2
                ;;
        esac
    done
}

# Starte das Programm
main
