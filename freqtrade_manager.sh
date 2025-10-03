#!/bin/bash

# Freqtrade Management Script
# Bietet sowohl Docker- als auch direkten Python-Betrieb

clear
echo "=================================="
echo "🚀 FREQTRADE MANAGEMENT SCRIPT 🚀"
echo "=================================="
echo "Datum: $(date)"
echo "Arbeitsverzeichnis: $(pwd)"
echo ""

# Funktionen definieren
check_docker() {
    if command -v docker &> /dev/null && docker info &> /dev/null; then
        return 0
    else
        return 1
    fi
}

stop_all_docker() {
    echo "🛑 Stoppe alle Docker-Container..."
    if [ "$(docker ps -q)" ]; then
        echo "Laufende Container:"
        docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
        docker stop $(docker ps -q)
        echo "✅ Alle Container gestoppt"
    else
        echo "ℹ️  Keine laufenden Container gefunden"
    fi
}

stop_freqtrade_processes() {
    echo "🛑 Stoppe Freqtrade-Prozesse..."
    if pgrep -f "freqtrade" > /dev/null; then
        pkill -f "freqtrade"
        echo "✅ Freqtrade-Prozesse gestoppt"
    else
        echo "ℹ️  Keine laufenden Freqtrade-Prozesse gefunden"
    fi
}

# Überprüfe System-Status
echo "🔍 SYSTEM-STATUS:"
echo "=================="

# Docker-Status
if check_docker; then
    echo "✅ Docker ist verfügbar"
    DOCKER_AVAILABLE=true
    if [ "$(docker ps -q)" ]; then
        echo "⚠️  Laufende Docker-Container gefunden:"
        docker ps --format "   {{.Names}} ({{.Image}})"
    fi
else
    echo "❌ Docker ist nicht verfügbar"
    DOCKER_AVAILABLE=false
fi

# Python-Status
PYTHON_PATH="/home/ftuser/.pyenv/versions/3.12.11/bin/python"
if [ -f "$PYTHON_PATH" ]; then
    echo "✅ Python verfügbar: $($PYTHON_PATH --version)"
    PYTHON_AVAILABLE=true
else
    echo "❌ Python nicht unter $PYTHON_PATH gefunden"
    if command -v python3 &> /dev/null; then
        PYTHON_PATH="python3"
        echo "✅ System-Python verfügbar: $(python3 --version)"
        PYTHON_AVAILABLE=true
    else
        echo "❌ Kein Python verfügbar"
        PYTHON_AVAILABLE=false
    fi
fi

# Freqtrade-Status
if [ "$PYTHON_AVAILABLE" = true ]; then
    if $PYTHON_PATH -c "import freqtrade; print(f'✅ Freqtrade Version: {freqtrade.__version__}')" 2>/dev/null; then
        FREQTRADE_AVAILABLE=true
    else
        echo "❌ Freqtrade nicht installiert"
        FREQTRADE_AVAILABLE=false
    fi
fi

# Konfiguration prüfen
CONFIG_FILE="./user_data/config.json"
if [ -f "$CONFIG_FILE" ]; then
    echo "✅ Konfigurationsdatei gefunden"
    CONFIG_AVAILABLE=true
else
    echo "❌ Konfigurationsdatei nicht gefunden: $CONFIG_FILE"
    CONFIG_AVAILABLE=false
fi

echo ""
echo "🎯 VERFÜGBARE OPTIONEN:"
echo "======================="
echo ""

# Hauptmenü
while true; do
    echo "Wählen Sie eine Option:"
    echo ""

    if [ "$DOCKER_AVAILABLE" = true ]; then
        echo "📦 DOCKER-OPTIONEN:"
        echo "  1) Alle Docker-Container stoppen"
        echo "  2) Freqtrade mit optimiertem Docker starten"
        echo "  3) Docker-Logs anzeigen"
        echo ""
    fi

    if [ "$PYTHON_AVAILABLE" = true ] && [ "$FREQTRADE_AVAILABLE" = true ]; then
        echo "🐍 PYTHON-OPTIONEN:"
        echo "  4) Alle Freqtrade-Prozesse stoppen"
        echo "  5) Freqtrade direkt starten (Trading)"
        echo "  6) Freqtrade Web UI starten"
        echo "  7) Backtesting durchführen"
        echo "  8) Daten herunterladen"
        echo ""
    fi

    echo "🔧 SYSTEM-OPTIONEN:"
    echo "  9) Alle Prozesse stoppen (Docker + Python)"
    echo "  10) System-Status aktualisieren"
    echo "  11) Konfiguration anzeigen"
    echo "  0) Beenden"
    echo ""

    read -p "Ihre Wahl (0-11): " choice
    echo ""

    case $choice in
        1)
            if [ "$DOCKER_AVAILABLE" = true ]; then
                stop_all_docker
            else
                echo "❌ Docker nicht verfügbar"
            fi
            ;;
        2)
            if [ "$DOCKER_AVAILABLE" = true ]; then
                echo "🚀 Starte optimiertes Docker-Setup..."
                stop_all_docker
                echo ""
                if [ -f "docker-compose.optimized.yml" ]; then
                    docker-compose -f docker-compose.optimized.yml up -d
                else
                    docker-compose up -d
                fi
                echo ""
                echo "📊 Container-Status:"
                docker ps
                echo ""
                echo "💡 API verfügbar unter: http://localhost:8080"
            else
                echo "❌ Docker nicht verfügbar"
            fi
            ;;
        3)
            if [ "$DOCKER_AVAILABLE" = true ] && docker ps | grep -q freqtrade; then
                echo "📝 Freqtrade Docker-Logs:"
                docker logs freqtrade --tail 30
            else
                echo "❌ Kein Freqtrade-Container läuft"
            fi
            ;;
        4)
            stop_freqtrade_processes
            ;;
        5)
            if [ "$FREQTRADE_AVAILABLE" = true ] && [ "$CONFIG_AVAILABLE" = true ]; then
                echo "🚀 Starte Freqtrade Trading direkt..."
                stop_freqtrade_processes
                echo ""
                echo "💡 Logs werden in user_data/logs/freqtrade.log gespeichert"
                echo "💡 Beenden mit Ctrl+C"
                echo ""
                $PYTHON_PATH -m freqtrade trade \
                    --config $CONFIG_FILE \
                    --strategy SampleStrategy \
                    --logfile user_data/logs/freqtrade.log \
                    --db-url sqlite:///user_data/tradesv3.sqlite
            else
                echo "❌ Freqtrade oder Konfiguration nicht verfügbar"
            fi
            ;;
        6)
            if [ "$FREQTRADE_AVAILABLE" = true ] && [ "$CONFIG_AVAILABLE" = true ]; then
                echo "🌐 Starte Freqtrade Web UI..."
                stop_freqtrade_processes
                echo ""
                echo "💡 Web UI verfügbar unter: http://localhost:8080"
                echo "💡 Beenden mit Ctrl+C"
                echo ""
                $PYTHON_PATH -m freqtrade webserver --config $CONFIG_FILE
            else
                echo "❌ Freqtrade oder Konfiguration nicht verfügbar"
            fi
            ;;
        7)
            if [ "$FREQTRADE_AVAILABLE" = true ] && [ "$CONFIG_AVAILABLE" = true ]; then
                echo "📈 Starte Backtesting..."
                read -p "Zeitraum eingeben (z.B. 20231101-20231201) [Enter für Standard]: " timerange
                $PYTHON_PATH -m freqtrade backtesting \
                    --config $CONFIG_FILE \
                    --strategy SampleStrategy \
                    --timerange ${timerange:-20231101-20231201}
            else
                echo "❌ Freqtrade oder Konfiguration nicht verfügbar"
            fi
            ;;
        8)
            if [ "$FREQTRADE_AVAILABLE" = true ] && [ "$CONFIG_AVAILABLE" = true ]; then
                echo "📉 Lade Daten herunter..."
                read -p "Zeitraum eingeben (z.B. 20231101-20231201) [Enter für Standard]: " timerange
                $PYTHON_PATH -m freqtrade download-data \
                    --config $CONFIG_FILE \
                    --timerange ${timerange:-20231101-20231201}
            else
                echo "❌ Freqtrade oder Konfiguration nicht verfügbar"
            fi
            ;;
        9)
            echo "🛑 Stoppe alle Freqtrade-Prozesse..."
            if [ "$DOCKER_AVAILABLE" = true ]; then
                stop_all_docker
            fi
            stop_freqtrade_processes
            echo "✅ Alle Prozesse gestoppt"
            ;;
        10)
            echo "🔄 Aktualisiere System-Status..."
            exec "$0"
            ;;
        11)
            if [ "$CONFIG_AVAILABLE" = true ]; then
                echo "📋 Aktuelle Konfiguration:"
                echo "   • Exchange: $(grep -o '"name": "[^"]*"' $CONFIG_FILE | cut -d'"' -f4 2>/dev/null || echo 'Unbekannt')"
                echo "   • Dry Run: $(grep -o '"dry_run": [^,}]*' $CONFIG_FILE | cut -d':' -f2 | tr -d ' ' 2>/dev/null || echo 'Unbekannt')"
                echo "   • Stake Currency: $(grep -o '"stake_currency": "[^"]*"' $CONFIG_FILE | cut -d'"' -f4 2>/dev/null || echo 'Unbekannt')"
                echo "   • Max Open Trades: $(grep -o '"max_open_trades": [^,}]*' $CONFIG_FILE | cut -d':' -f2 | tr -d ' ' 2>/dev/null || echo 'Unbekannt')"
            else
                echo "❌ Keine Konfiguration verfügbar"
            fi
            ;;
        0)
            echo "👋 Auf Wiedersehen!"
            exit 0
            ;;
        *)
            echo "❌ Ungültige Auswahl"
            ;;
    esac

    echo ""
    echo "=================================="
    echo ""
done