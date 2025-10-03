#!/bin/bash

# 🚀 OPTIMIERTES FREQAI RL TRADING - Enhanced Multi-Timeframe V2.0
# Startet das optimierte FreqAI RL Trading mit erweiterten Features

echo "🚀 STARTE OPTIMIERTES FREQAI RL TRADING - Enhanced Multi-Timeframe V2.0"
echo "======================================================================"
echo ""

# Aktiviere Virtual Environment falls vorhanden
if [ -d "venv" ]; then
    echo "📦 Aktiviere Virtual Environment..."
    source venv/bin/activate
fi

# Prüfe Python Dependencies
echo "🔍 Prüfe Dependencies..."
python -c "import tensorflow, pandas, numpy, talib" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Fehlende Dependencies! Installiere..."
    pip install -r requirements-freqai-rl.txt
fi

# Erstelle Log-Verzeichnis
mkdir -p user_data/logs/

# Konfiguration Details
echo "⚙️  KONFIGURATION:"
echo "   📈 Strategie: BinanceSpotLongOnlyRLStrategy_Optimized"
echo "   🧠 FreqAI Model: BinanceSpotLongOnlyRLModel_Optimized"
echo "   ⏰ Timeframe: 3m (optimiert für schnelle Signale)"
echo "   📊 Multi-Timeframe: 15m/1h/4h Analysis"
echo "   💰 Trading Mode: Binance Spot (Long-Only)"
echo "   🎯 Enhanced Features: 50+ Technical Indicators"
echo ""

# Start FreqTrade mit optimierter Konfiguration
echo "🎯 Starte FreqTrade mit optimierter Multi-Timeframe RL Konfiguration..."
echo ""

freqtrade trade \
    --config user_data/config_binance_spot_longonly_rl.json \
    --strategy BinanceSpotLongOnlyRLStrategy_Optimized \
    --freqaimodel BinanceSpotLongOnlyRLModel_Optimized \
    --logfile user_data/logs/freqtrade_optimized_$(date +%Y%m%d_%H%M%S).log \
    --verbosity 1

echo ""
echo "🏁 FreqTrade Optimized beendet."