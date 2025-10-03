#!/bin/bash

# Stoppe bestehende Freqtrade-Instanzen
echo "Stoppe bestehende Freqtrade-Instanzen..."
pkill -f "freqtrade webserver" || true

# Warte kurz
sleep 2

# Starte den Webserver ohne Authentifizierung
echo "Starte Freqtrade Webserver ohne Authentifizierung..."
freqtrade webserver \
    --config user_data/config_webserver_no_auth.json \
    --logfile user_data/logs/webserver_no_auth.log

echo "Webserver gestartet auf http://127.0.0.1:8090"
echo "Keine Authentifizierung erforderlich!"