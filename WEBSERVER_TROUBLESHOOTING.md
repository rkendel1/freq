# Freqtrade Webserver Problembehebung

## Identifizierte Probleme und Lösungen

### 1. Authentifizierungsproblem (401 Fehler)

**Problem**: Der Webserver erforderte Authentifizierung mit Username/Passwort, was zu 401-Fehlern führte.

**Lösung**:

- Neue Konfigurationsdatei `config_webserver_no_auth.json` erstellt ohne Authentifizierung
- Startskript `start_webserver_no_auth.sh` erstellt für einfachen Start

**Verwendung**:

```bash
# Webserver ohne Authentifizierung starten
./start_webserver_no_auth.sh

# Oder manuell:
freqtrade webserver --config user_data/config_webserver_no_auth.json
```

### 2. FreqAI Konfigurationsfehler

**Problem**: Bei Backtest-Versuchen fehlen erforderliche FreqAI-Parameter (`feature_parameters`).

**Lösung**:

- Neue Konfigurationsdatei `config_webserver_fixed.json` mit vollständiger FreqAI-Konfiguration
- FreqAI standardmäßig deaktiviert für Webserver-Only-Betrieb

**FreqAI-Parameter hinzugefügt**:

- `feature_parameters` mit erforderlichen Feldern
- `data_split_parameters` für Datenaufteilung
- Minimal aber vollständig konfiguriert

### 3. Aktuelle Webserver-Anmeldedaten

Falls Sie die ursprüngliche Konfiguration mit Authentifizierung verwenden möchten:

- **Username**: admin
- **Passwort**: WebServer2025!

### 4. Webserver-URLs

- **Haupt-URL**: <http://127.0.0.1:8090>
- **API-Dokumentation**: <http://127.0.0.1:8090/docs>
- **Logs-Endpunkt**: <http://127.0.0.1:8090/logs>

### 5. Verfügbare Konfigurationsdateien

1. **config_webserver_only.json** - Original mit Authentifizierung
2. **config_webserver_no_auth.json** - Ohne Authentifizierung (empfohlen)
3. **config_webserver_fixed.json** - Mit korrigierter FreqAI-Konfiguration
4. **config_binance_spot_longonly_rl.json** - Vollständige RL-Konfiguration

### 6. Nützliche Befehle

```bash
# Webserver-Status prüfen
ps aux | grep freqtrade

# Webserver-Logs anzeigen
tail -f user_data/logs/webserver.log

# Webserver stoppen
pkill -f "freqtrade webserver"

# API-Status testen
curl http://127.0.0.1:8090/api/v1/ping
```

### 7. Troubleshooting-Tipps

- Bei Port-Konflikten anderen Port verwenden: `--listen-port 8091`
- Bei Authentifizierungsproblemen: Konfiguration ohne auth verwenden
- Bei FreqAI-Fehlern: FreqAI in der Konfiguration deaktivieren
- Bei Backtest-Problemen: Separate Konfiguration ohne FreqAI verwenden

### 8. Log-Analyse

Die wichtigsten Log-Muster:

- `401` = Authentifizierungsfehler
- `502` = Bot nicht im korrekten Zustand (normal für Webserver-Only)
- `feature_parameters is a required property` = FreqAI-Konfigurationsfehler

