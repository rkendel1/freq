#!/bin/bash

# Script für optimierten Docker-only Betrieb von Freqtrade
# Stoppt alle laufenden Container und startet Freqtrade optimiert

echo "=== Freqtrade Docker Optimization Script ==="
echo "Datum: $(date)"
echo ""

# Schritt 1: Alle laufenden Docker-Container stoppen
echo "🛑 Stoppe alle laufenden Docker-Container..."
if command -v docker &> /dev/null; then
    # Stoppe alle laufenden Container
    if [ "$(docker ps -q)" ]; then
        echo "Gefundene laufende Container:"
        docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
        echo ""
        echo "Stoppe alle Container..."
        docker stop $(docker ps -q)
        echo "✅ Container gestoppt"
    else
        echo "ℹ️  Keine laufenden Container gefunden"
    fi

    # Optional: Entferne gestoppte Container
    if [ "$(docker ps -aq)" ]; then
        echo "🗑️  Entferne gestoppte Container..."
        docker rm $(docker ps -aq)
        echo "✅ Container entfernt"
    fi

    # Bereinige nicht verwendete Netzwerke
    echo "🧹 Bereinige Docker-Netzwerke..."
    docker network prune -f

    # Bereinige nicht verwendete Volumes (optional - vorsichtig verwenden!)
    # docker volume prune -f

else
    echo "❌ Docker ist nicht installiert oder nicht verfügbar"
    exit 1
fi

echo ""
echo "🔧 Vorbereitung für optimierten Freqtrade-Start..."

# Schritt 2: Überprüfe Freqtrade-Konfiguration
CONFIG_FILE="./user_data/config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Konfigurationsdatei nicht gefunden: $CONFIG_FILE"
    exit 1
fi

# Schritt 3: Erstelle notwendige Verzeichnisse
echo "📁 Erstelle notwendige Verzeichnisse..."
mkdir -p user_data/logs
mkdir -p user_data/data
mkdir -p user_data/plot
mkdir -p user_data/backtest_results
mkdir -p logs

# Schritt 4: Setze korrekte Berechtigungen
echo "🔐 Setze Berechtigungen..."
sudo chown -R 1000:1000 user_data/
sudo chown -R 1000:1000 logs/ 2>/dev/null || true

# Schritt 5: Starte optimierte Freqtrade-Container
echo ""
echo "🚀 Starte optimierten Freqtrade-Container..."

# Verwende die optimierte docker-compose Konfiguration
if [ -f "docker-compose.optimized.yml" ]; then
    echo "Verwende optimierte Konfiguration: docker-compose.optimized.yml"
    docker-compose -f docker-compose.optimized.yml up -d
else
    echo "Verwende Standard-Konfiguration: docker-compose.yml"
    docker-compose up -d
fi

# Schritt 6: Warte auf Container-Start und zeige Status
echo ""
echo "⏳ Warte auf Container-Start..."
sleep 5

echo ""
echo "📊 Container-Status:"
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "📝 Freqtrade-Logs (letzte 20 Zeilen):"
sleep 2
if docker ps | grep -q freqtrade; then
    docker logs freqtrade --tail 20
else
    echo "❌ Freqtrade-Container läuft nicht"
fi

echo ""
echo "🎯 Freqtrade-Setup Informationen:"
echo "   • API verfügbar unter: http://localhost:8080"
echo "   • Logs-Verzeichnis: ./user_data/logs/"
echo "   • Konfiguration: ./user_data/config.json"
echo "   • Datenverzeichnis: ./user_data/data/"
echo ""
echo "💡 Nützliche Befehle:"
echo "   • Container-Logs anzeigen: docker logs freqtrade -f"
echo "   • Container stoppen: docker-compose down"
echo "   • Container neustarten: docker-compose restart"
echo "   • In Container einloggen: docker exec -it freqtrade bash"
echo ""

# Schritt 7: Healthcheck
echo "🏥 Führe Healthcheck durch..."
sleep 5
if curl -s http://localhost:8080/api/v1/ping > /dev/null 2>&1; then
    echo "✅ API ist erreichbar"
else
    echo "⚠️  API noch nicht erreichbar (normal beim ersten Start)"
fi

echo ""
echo "✅ Setup abgeschlossen!"
echo "==================================="