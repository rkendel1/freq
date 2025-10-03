#!/bin/bash

# Systematisches Datendownload-Skript für TensorFlow RL
echo "🚀 Starte systematischen Datendownload für TensorFlow RL..."

# Definiere Zeiträume für verschiedene Analysezwecke
declare -A timeframes=(
    ["5m"]="Haupt-Trading-Zeitrahmen"
    ["15m"]="Mittelfristige Trends"
    ["1h"]="Langfristige Analyse"
    ["4h"]="Makro-Trends"
)

# Definiere Datenperioden für verschiedene ML-Zwecke
declare -A periods=(
    ["training"]="--days 90"
    ["validation"]="--days 180" 
    ["backtesting"]="--days 365"
)

# Haupt-Pairs für Spot-Trading
MAIN_PAIRS="BTC/USDT ETH/USDT"
CORRELATION_PAIRS="ADA/USDT DOT/USDT LINK/USDT SOL/USDT MATIC/USDT AVAX/USDT"

# Funktion für Datendownload
download_data() {
    local timeframe=$1
    local period=$2
    local pairs=$3
    local description=$4
    
    echo "📊 Download $description für $timeframe..."
    freqtrade download-data \
        --config user_data/config_spot_rl.json \
        --timeframe $timeframe \
        --pairs $pairs \
        $period \
        --exchange binance \
        --trading-mode spot
}

# 1. Haupt-Trading-Daten (5m für RL-Agent)
echo "=== Phase 1: Haupt-Trading-Daten ==="
download_data "5m" "--days 180" "$MAIN_PAIRS" "Haupt-RL-Training"

# 2. Korrelations-Daten für Feature Engineering
echo "=== Phase 2: Korrelations-Daten ==="
download_data "5m" "--days 90" "$CORRELATION_PAIRS" "Korrelations-Features"

# 3. Multi-Timeframe-Daten für umfassende Analyse
echo "=== Phase 3: Multi-Timeframe-Analyse ==="
for tf in "15m" "1h" "4h"; do
    download_data "$tf" "--days 365" "$MAIN_PAIRS $CORRELATION_PAIRS" "Multi-Timeframe-Features"
done

# 4. Erweiterte Backtesting-Daten
echo "=== Phase 4: Erweiterte Backtesting-Daten ==="
download_data "5m" "--days 730" "$MAIN_PAIRS" "Langzeit-Backtesting"

echo "✅ Systematischer Datendownload abgeschlossen!"
echo "📋 Nächster Schritt: TensorFlow RL Konfiguration"
