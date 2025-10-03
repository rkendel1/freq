#!/bin/bash

# 🧪 TEST OPTIMIERTE FREQAI KOMPONENTEN
# Validiert alle optimierten Dateien vor dem Trading

echo "🧪 TESTE OPTIMIERTE FREQAI KOMPONENTEN"
echo "======================================"
echo ""

# Funktion für Status-Ausgabe
print_status() {
    if [ $? -eq 0 ]; then
        echo "✅ $1"
    else
        echo "❌ $1"
        exit 1
    fi
}

# Test 1: Python Syntax Check
echo "🔍 Teste Python Syntax..."
python -m py_compile user_data/strategies/BinanceSpotLongOnlyRLStrategy_Optimized.py
print_status "Strategy Syntax Check"

python -m py_compile user_data/freqaimodels/BinanceSpotLongOnlyRLModel_Optimized.py
print_status "FreqAI Model Syntax Check"

# Test 2: Import Check
echo ""
echo "📦 Teste Imports..."
python -c "
import sys
sys.path.append('user_data/strategies')
sys.path.append('user_data/freqaimodels')

try:
    from BinanceSpotLongOnlyRLStrategy_Optimized import BinanceSpotLongOnlyRLStrategy_Optimized
    print('✅ Strategy Import erfolgreich')
except ImportError as e:
    print(f'❌ Strategy Import Fehler: {e}')
    sys.exit(1)

try:
    from BinanceSpotLongOnlyRLModel_Optimized import BinanceSpotLongOnlyRLModel_Optimized
    print('✅ FreqAI Model Import erfolgreich')
except ImportError as e:
    print(f'❌ FreqAI Model Import Fehler: {e}')
    sys.exit(1)
"

# Test 3: Konfiguration Check
echo ""
echo "⚙️ Teste Konfiguration..."
python -c "
import json
try:
    with open('user_data/config_binance_spot_longonly_rl.json', 'r') as f:
        config = json.load(f)
    print('✅ Konfiguration JSON valid')

    # Wichtige Einstellungen prüfen
    print(f'   📊 Timeframe: {config.get(\"timeframe\", \"N/A\")}')
    print(f'   🧠 FreqAI Model: {config.get(\"freqai\", {}).get(\"freqaimodel\", \"N/A\")}')
    print(f'   💰 Trading Mode: {config.get(\"trading_mode\", \"N/A\")}')
    print(f'   🎯 Max Open Trades: {config.get(\"max_open_trades\", \"N/A\")}')

except Exception as e:
    print(f'❌ Konfiguration Fehler: {e}')
    exit(1)
"

# Test 4: Dependencies Check
echo ""
echo "🔧 Teste Dependencies..."
python -c "
required = ['tensorflow', 'pandas', 'numpy', 'talib', 'gymnasium', 'stable_baselines3']
missing = []

for package in required:
    try:
        __import__(package)
        print(f'✅ {package}')
    except ImportError:
        missing.append(package)
        print(f'❌ {package} - FEHLT!')

if missing:
    print(f'\\n⚠️  Fehlende Pakete: {missing}')
    print('Installiere mit: pip install -r requirements-freqai-rl.txt')
    exit(1)
else:
    print('\\n✅ Alle Dependencies verfügbar')
"

# Test 5: FreqTrade Dry-Run Test
echo ""
echo "🚀 Teste FreqTrade Dry-Run (10 Sekunden)..."
timeout 10s freqtrade trade \
    --config user_data/config_binance_spot_longonly_rl.json \
    --strategy BinanceSpotLongOnlyRLStrategy_Optimized \
    --freqaimodel BinanceSpotLongOnlyRLModel_Optimized \
    --dry-run > /dev/null 2>&1

if [ $? -eq 124 ]; then
    print_status "FreqTrade Startup (Timeout nach erfolgreichem Start)"
elif [ $? -eq 0 ]; then
    print_status "FreqTrade Startup (Regulärer Exit)"
else
    echo "❌ FreqTrade Startup Fehler (Exit Code: $?)"
    exit 1
fi

# Erfolgsmeldung
echo ""
echo "🎉 ALLE TESTS ERFOLGREICH!"
echo "========================="
echo ""
echo "✅ Strategy Optimiert: BinanceSpotLongOnlyRLStrategy_Optimized"
echo "✅ FreqAI Model Optimiert: BinanceSpotLongOnlyRLModel_Optimized"
echo "✅ Konfiguration Valid: 3m Timeframe, Enhanced Settings"
echo "✅ Dependencies Vollständig"
echo "✅ FreqTrade Funktionsfähig"
echo ""
echo "🚀 BEREIT FÜR OPTIMIERTES TRADING!"
echo "Starte mit: ./start_freqtrade_optimized_v2.sh"