#!/bin/bash

# Alternative Script für direkten Python-Betrieb von Freqtrade
# Nutzen Sie dieses Script, wenn Docker-Probleme auftreten

echo "=== Freqtrade Direct Python Execution ==="
echo "Datum: $(date)"
echo ""

# Python-Path aus der Umgebungskonfiguration
PYTHON_PATH="/home/ftuser/.pyenv/versions/3.12.11/bin/python"

# Überprüfe Python-Installation
echo "🐍 Überprüfe Python-Umgebung..."
if [ -f "$PYTHON_PATH" ]; then
    echo "✅ Python gefunden: $($PYTHON_PATH --version)"
else
    echo "❌ Python nicht gefunden unter: $PYTHON_PATH"
    echo "Verwende System-Python..."
    PYTHON_PATH="python3"
fi

# Überprüfe Freqtrade-Installation
echo "📦 Überprüfe Freqtrade-Installation..."
if $PYTHON_PATH -c "import freqtrade; print(f'Freqtrade Version: {freqtrade.__version__}')" 2>/dev/null; then
    echo "✅ Freqtrade ist installiert"
else
    echo "❌ Freqtrade ist nicht installiert"
    echo "Installiere Freqtrade..."
    pip install -e .
fi

# Stoppe eventuell laufende Freqtrade-Prozesse
echo ""
echo "🛑 Stoppe laufende Freqtrade-Prozesse..."
pkill -f "freqtrade" 2>/dev/null && echo "✅ Freqtrade-Prozesse gestoppt" || echo "ℹ️  Keine laufenden Freqtrade-Prozesse gefunden"

# Überprüfe Konfiguration
CONFIG_FILE="./user_data/config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Konfigurationsdatei nicht gefunden: $CONFIG_FILE"
    exit 1
fi

echo "✅ Konfigurationsdatei gefunden: $CONFIG_FILE"

# Erstelle notwendige Verzeichnisse
echo ""
echo "📁 Bereite Verzeichnisse vor..."
mkdir -p user_data/logs
mkdir -p user_data/data
mkdir -p user_data/plot
mkdir -p user_data/backtest_results

# Zeige aktuelle Konfiguration
echo ""
echo "📋 Aktuelle Konfiguration:"
echo "   • Exchange: $(grep -o '"name": "[^"]*"' $CONFIG_FILE | cut -d'"' -f4)"
echo "   • Dry Run: $(grep -o '"dry_run": [^,]*' $CONFIG_FILE | cut -d':' -f2 | tr -d ' ')"
echo "   • Stake Currency: $(grep -o '"stake_currency": "[^"]*"' $CONFIG_FILE | cut -d'"' -f4)"
echo "   • Max Open Trades: $(grep -o '"max_open_trades": [^,]*' $CONFIG_FILE | cut -d':' -f2 | tr -d ' ')"

echo ""
echo "🚀 Verfügbare Freqtrade-Befehle:"
echo ""
echo "1. 📊 Trading starten (Dry Run):"
echo "   $PYTHON_PATH -m freqtrade trade --config $CONFIG_FILE --strategy SampleStrategy"
echo ""
echo "2. 📈 Backtesting durchführen:"
echo "   $PYTHON_PATH -m freqtrade backtesting --config $CONFIG_FILE --strategy SampleStrategy --timerange 20231101-20231201"
echo ""
echo "3. 📉 Daten herunterladen:"
echo "   $PYTHON_PATH -m freqtrade download-data --config $CONFIG_FILE --timerange 20231101-20231201"
echo ""
echo "4. 🔧 Hyperopt (Optimierung):"
echo "   $PYTHON_PATH -m freqtrade hyperopt --config $CONFIG_FILE --hyperopt-loss SharpeHyperOptLoss --strategy SampleStrategy --epochs 100"
echo ""
echo "5. 🌐 Web UI starten:"
echo "   $PYTHON_PATH -m freqtrade webserver --config $CONFIG_FILE"
echo ""

# Frage nach gewünschter Aktion
echo "❓ Was möchten Sie tun?"
echo "1) Trading starten (Dry Run)"
echo "2) Backtesting durchführen"
echo "3) Daten herunterladen"
echo "4) Web UI starten"
echo "5) Interaktive Shell"
echo "6) Beenden"
echo ""

read -p "Wählen Sie eine Option (1-6): " choice

case $choice in
    1)
        echo ""
        echo "🚀 Starte Trading (Dry Run)..."
        $PYTHON_PATH -m freqtrade trade \
            --config $CONFIG_FILE \
            --strategy SampleStrategy \
            --logfile user_data/logs/freqtrade.log \
            --db-url sqlite:///user_data/tradesv3.sqlite
        ;;
    2)
        echo ""
        echo "📈 Starte Backtesting..."
        read -p "Zeitraum eingeben (z.B. 20231101-20231201): " timerange
        $PYTHON_PATH -m freqtrade backtesting \
            --config $CONFIG_FILE \
            --strategy SampleStrategy \
            --timerange ${timerange:-20231101-20231201}
        ;;
    3)
        echo ""
        echo "📉 Lade Daten herunter..."
        read -p "Zeitraum eingeben (z.B. 20231101-20231201): " timerange
        $PYTHON_PATH -m freqtrade download-data \
            --config $CONFIG_FILE \
            --timerange ${timerange:-20231101-20231201}
        ;;
    4)
        echo ""
        echo "🌐 Starte Web UI..."
        echo "Zugriff über: http://localhost:8080"
        $PYTHON_PATH -m freqtrade webserver \
            --config $CONFIG_FILE
        ;;
    5)
        echo ""
        echo "🐚 Starte interaktive Freqtrade-Shell..."
        $PYTHON_PATH -c "
import freqtrade
from freqtrade.configuration import Configuration
from freqtrade.resolvers import StrategyResolver
print('Freqtrade Shell - Verfügbare Module:')
print('- freqtrade')
print('- Configuration, StrategyResolver')
print('Beispiel: config = Configuration.from_files([\"$CONFIG_FILE\"])')
import IPython
IPython.embed()
"
        ;;
    6)
        echo "👋 Auf Wiedersehen!"
        exit 0
        ;;
    *)
        echo "❌ Ungültige Auswahl"
        exit 1
        ;;
esac

echo ""
echo "✅ Befehl abgeschlossen!"