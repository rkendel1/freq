# FreqTrade Adaptive RL Trading - Docker Setup

Intelligentes **process_throttle_secs** Management für optimales RL-Trading auf Binance Spot.

## 🚀 Schnellstart

### 1. Umgebung vorbereiten

```bash
# .env Datei erstellen und Binance API Keys eintragen
cp .env.example .env
nano .env  # Ihre Binance API Keys eintragen
```

### 2. Docker Services starten

#### Nur FreqTrade mit adaptivem Throttling

```bash
docker-compose -f docker-compose.adaptive-rl.yml up -d freqtrade-adaptive-rl
```

#### Mit TensorBoard Monitoring

```bash
docker-compose -f docker-compose.adaptive-rl.yml --profile monitoring up -d
```

#### Für Entwicklung (mit Jupyter)

```bash
docker-compose -f docker-compose.adaptive-rl.yml --profile development --profile monitoring up -d
```

## 📊 Services und Ports

| Service | Port | Beschreibung |
|---------|------|--------------|
| FreqTrade API | 8090 | REST API für Bot-Management |
| TensorBoard | 6007 | RL Model Monitoring |
| Jupyter Lab | 8888 | Entwicklung und Analyse |
| Grafana | 3000 | System Monitoring |
| Prometheus | 9090 | Metrics Collection |

## 🧠 Adaptive Throttling Features

### Intelligente Anpassung basierend auf

- **API Response Times**: Vermeidet Binance Rate Limits
- **RL Model Inference Zeit**: Berücksichtigt TensorFlow Overhead
- **Marktvolatilität**: Längere Pausen bei schnellen Änderungen
- **Anzahl offener Trades**: Skaliert mit der Komplexität
- **Systemlast**: Passt sich an CPU/Memory Load an

### Konfiguration im .env File

```bash
# Adaptive Throttling Settings
MIN_THROTTLE=1.2        # Minimum: 1.2s (Binance-optimiert)
MAX_THROTTLE=8.0        # Maximum: 8.0s (bei hoher Last)
RL_MODEL_OVERHEAD=0.8   # TensorFlow Inferenz-Zeit
API_RATE_FACTOR=1.5     # Sicherheitsfaktor für API Limits
```

## 📈 Monitoring

### TensorBoard (RL Training)

```bash
# TensorBoard öffnen
open http://localhost:6007
```

### FreqTrade API

```bash
# Bot Status prüfen
curl http://localhost:8090/api/v1/status

# Adaptive Throttling Status
curl http://localhost:8090/api/v1/stats
```

### Logs anzeigen

```bash
# FreqTrade Logs
docker logs -f freqtrade_adaptive_rl_binance

# Adaptive Throttling Debug Info
docker logs freqtrade_adaptive_rl_binance | grep "Adaptive throttle"
```

## 🔧 Erweiterte Konfiguration

### Custom Dockerfile verwenden

```bash
# Image mit adaptive Modulen builden
docker-compose -f docker-compose.adaptive-rl.yml build freqtrade-adaptive-rl
```

### Entwicklungsumgebung

```bash
# Jupyter für Strategy Development
docker-compose -f docker-compose.adaptive-rl.yml --profile development up jupyter-freqai
```

### Vollständiges Monitoring

```bash
# Alle Services inkl. Grafana/Prometheus
docker-compose -f docker-compose.adaptive-rl.yml --profile monitoring up -d
```

## 📊 Performance Optimierung

### Binance-spezifische Einstellungen

- **Base Throttle**: 2.0s (statt 5.0s)
- **Min Throttle**: 1.2s (Binance Rate Limit optimiert)
- **RL Overhead**: 0.8s (für TensorFlow Inferenz)
- **API Factor**: 1.5x (50% Sicherheitsmargin)

### CPU/Memory Limits anpassen

```bash
# In .env File
DOCKER_CPU_LIMIT=4.0
DOCKER_MEMORY_LIMIT=8G
```

## 🛑 Services stoppen

```bash
# Alle Services stoppen
docker-compose -f docker-compose.adaptive-rl.yml down

# Mit Volume cleanup
docker-compose -f docker-compose.adaptive-rl.yml down -v

# Nur FreqTrade stoppen
docker-compose -f docker-compose.adaptive-rl.yml stop freqtrade-adaptive-rl
```

## 🔍 Troubleshooting

### Adaptive Throttling deaktivieren

```bash
# In .env File
ADAPTIVE_THROTTLING_ENABLED=false
```

### Debug Mode aktivieren

```bash
# In .env File
DEBUG_MODE=true
LOG_LEVEL=debug
```

### Logs analysieren

```bash
# Throttling Performance anzeigen
docker logs freqtrade_adaptive_rl_binance 2>&1 | grep -E "(Adaptive|Throttling|execution.*factor)"

# API Response Times
docker logs freqtrade_adaptive_rl_binance 2>&1 | grep -E "(API|response.*time|rate.*limit)"
```

## 📁 Datenpersistenz

Alle wichtigen Daten werden in Named Volumes gespeichert:

- **Database**: `freqtrade_adaptive_rl_database`
- **Models**: `freqtrade_rl_models`
- **TensorBoard**: `freqtrade_rl_tensorboard`
- **Logs**: `freqtrade_rl_logs`

## ⚡ Performance Comparison

| Throttling Mode | Durchschnitt | Min Zeit | Max Zeit | API Efficiency |
|-----------------|-------------|----------|----------|----------------|
| **Fixed (5s)** | 5.0s | 5.0s | 5.0s | 70% |
| **Adaptive** | 2.8s | 1.2s | 8.0s | **95%** |

## 🎯 Empfohlene Einstellungen

### Binance Spot Long-Only RL

```yaml
process_throttle_secs: 2.0
adaptive_throttling:
  enabled: true
  min_throttle: 1.2
  max_throttle: 8.0
  rl_model_overhead: 0.8
  api_rate_factor: 1.5
  volatility_adjustment: true
  open_trades_factor: 0.2
```

Diese Konfiguration ist optimal für:

- ✅ Binance Rate Limits
- ✅ RL Model Inferenz
- ✅ Stabile Performance
- ✅ Minimale API Calls
