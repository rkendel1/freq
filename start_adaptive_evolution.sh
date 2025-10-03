#!/bin/bash

echo "🧬 ADAPTIVE EVOLUTION SYSTEM STARTUP"
echo "====================================="

# Erstelle notwendige Verzeichnisse
mkdir -p adaptive_evolution_results
mkdir -p logs
mkdir -p user_data/data

# Überprüfe Docker Installation
if ! command -v docker &> /dev/null; then
    echo "❌ Docker ist nicht installiert!"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker-Compose ist nicht installiert!"
    exit 1
fi

echo "✅ Docker ist verfügbar"

# Stoppe eventuell laufende Container
echo "🛑 Stoppe laufende Evolution-Container..."
docker-compose -f docker-compose.adaptive-evolution.yml down

# Erstelle Images
echo "🔨 Erstelle Evolution-Images..."
docker-compose -f docker-compose.adaptive-evolution.yml build

# Starte Evolution-System
echo "🚀 Starte Adaptive Evolution System..."
docker-compose -f docker-compose.adaptive-evolution.yml up -d

echo ""
echo "🎯 EVOLUTION SYSTEM GESTARTET!"
echo "================================"
echo ""
echo "📊 Dienste:"
echo "   - Evolution Engine: Kontinuierliche Parameter-Optimierung"
echo "   - Performance Monitor: Echtzeit-Überwachung"
echo "   - Data Generator: Dynamische Marktszenarien"
echo "   - Web UI: http://localhost:8080 (user: evolution, pass: evolution123)"
echo ""
echo "📁 Ausgabeverzeichnisse:"
echo "   - adaptive_evolution_results/: Evolution-Ergebnisse"
echo "   - logs/: System-Logs"
echo ""
echo "🔍 Logs verfolgen:"
echo "   docker-compose -f docker-compose.adaptive-evolution.yml logs -f"
echo ""
echo "🛑 System stoppen:"
echo "   docker-compose -f docker-compose.adaptive-evolution.yml down"
echo ""
echo "🎉 EVOLUTION ZUR PERFEKTION LÄUFT!"

# Zeige Live-Logs für 30 Sekunden
echo ""
echo "📊 Live-Logs (30 Sekunden):"
timeout 30 docker-compose -f docker-compose.adaptive-evolution.yml logs -f || true

echo ""
echo "🎯 Evolution läuft im Hintergrund weiter..."
echo "Verwende 'docker-compose -f docker-compose.adaptive-evolution.yml logs -f' für weitere Logs"