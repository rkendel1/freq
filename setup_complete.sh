#!/bin/bash

# Freqtrade Docker Setup Script
# Dieses Script bereitet das Freqtrade-Repository für Docker-Nutzung vor

echo "🚀 Freqtrade Docker Setup wird gestartet..."

# Überprüfe Python-Version
echo "📋 Überprüfe Python-Version..."
python --version

# Überprüfe installierte Pakete
echo "📦 Überprüfe wichtige Pakete..."
python -c "import tensorflow as tf; print('✅ TensorFlow:', tf.__version__)"
python -c "import torch; print('✅ PyTorch:', torch.__version__)"
python -c "import numpy as np; print('✅ NumPy:', np.__version__)"
python -c "import pandas as pd; print('✅ Pandas:', pd.__version__)"
python -c "import sklearn; print('✅ Scikit-learn:', sklearn.__version__)"

# Überprüfe Freqtrade
echo "🤖 Überprüfe Freqtrade..."
freqtrade --version

# Zeige verfügbare Strategien
echo "📈 Verfügbare Strategien:"
ls -la user_data/strategies/

# Zeige Konfiguration
echo "⚙️ Konfigurationsdatei erstellt: user_data/config.json"

echo ""
echo "✅ Setup erfolgreich abgeschlossen!"
echo ""
echo "🎯 Nächste Schritte:"
echo "1. Bearbeite user_data/config.json für deine Exchange-Einstellungen"
echo "2. Füge API-Keys hinzu (falls Live-Trading gewünscht)"
echo "3. Teste mit: freqtrade backtesting --config user_data/config.json --strategy SampleStrategy"
echo "4. Starte Web-UI mit: freqtrade webserver --config user_data/config.json"
echo ""
echo "🐳 Docker-Befehle (wenn Docker verfügbar ist):"
echo "docker-compose up -d    # Startet Freqtrade in Docker"
echo "docker-compose logs -f  # Zeigt Logs an"
echo "docker-compose down     # Stoppt Container"
echo ""
echo "🔬 FreqAI Features sind verfügbar mit TensorFlow, PyTorch und allen ML-Bibliotheken!"