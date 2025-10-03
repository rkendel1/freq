# FreqTrade Docker Setup mit FreqAI und Hyperopt

Diese erweiterte Docker-Konfiguration bietet optimierte Setups für FreqTrade mit FreqAI und Hyperopt-Funktionalitäten.

## 🚀 Verfügbare Images

| Image | Beschreibung | Verwendung |
|-------|-------------|------------|
| `freqtradeorg/freqtrade:stable` | Standard FreqTrade | Normaler Trading-Bot |
| `freqtradeorg/freqtrade:develop_freqai` | FreqTrade + FreqAI | Machine Learning Trading |
| `freqtradeorg/freqtrade:develop_hyperopt` | FreqTrade + Hyperopt | Parameteroptimierung |
| `freqtradeorg/freqtrade:develop_freqai_hyperopt` | FreqTrade + FreqAI + Hyperopt | ML + Optimierung |
| `freqtradeorg/freqtrade:develop_plot` | FreqTrade + Plotting | Datenanalyse |

## 📁 Projekt-Struktur

```
freqtrade/
├── user_data/
│   ├── config/              # Konfigurationsdateien
│   ├── data/               # Marktdaten
│   ├── logs/               # Log-Dateien
│   ├── strategies/         # Trading-Strategien
│   ├── hyperopts/          # Hyperopt-Konfigurationen
│   ├── models/             # FreqAI-Modelle
│   └── hyperopt_results/   # Optimierungsergebnisse
├── notebooks/              # Jupyter Notebooks
├── docker-compose.yml      # Standard Docker Setup
├── docker-compose.advanced.yml # Erweiterte Konfiguration
└── freqtrade_docker.sh     # Setup-Hilfsskript
```

## 🛠️ Schnellstart

### 1. Ersteinrichtung

```bash
# Repository klonen (falls nicht bereits geschehen)
git clone https://github.com/freqtrade/freqtrade.git
cd freqtrade

# Initiale Einrichtung
./freqtrade_docker.sh setup
```

### 2. Standard Trading

```bash
# Standard FreqTrade starten
./freqtrade_docker.sh standard

# Oder direkt mit Docker Compose
docker-compose up -d freqtrade
```

### 3. FreqAI Trading

```bash
# FreqAI-aktiviertes Trading
./freqtrade_docker.sh freqai

# Oder mit erweiteter Konfiguration
docker-compose -f docker-compose.advanced.yml --profile freqai up -d freqtrade-freqai
```

### 4. Hyperopt Optimierung

```bash
# Hyperopt-Optimierung durchführen
./freqtrade_docker.sh hyperopt

# Oder manuell
docker-compose -f docker-compose.advanced.yml --profile hyperopt up freqtrade-hyperopt
```

### 5. FreqAI + Hyperopt

```bash
# Kombinierte ML und Optimierung
./freqtrade_docker.sh freqai-hyperopt
```

## 📊 Zusätzliche Services

### Jupyter Notebook für Analyse

```bash
# Jupyter starten
./freqtrade_docker.sh jupyter

# Zugriff auf http://localhost:8888
```

### PostgreSQL Datenbank

```bash
# Datenbank starten
./freqtrade_docker.sh database

# Verbindung: localhost:5432
# User: freqtrade
# Password: freqtrade
# Database: freqtrade
```

## 🔧 Konfiguration

### FreqAI Konfiguration

Beispiel `user_data/config_freqai.json`:

```json
{
    "freqai": {
        "enabled": true,
        "purge_old_models": true,
        "train_period_days": 30,
        "backtest_period_days": 7,
        "identifier": "example",
        "feature_parameters": {
            "include_timeframes": ["5m", "15m", "4h"],
            "include_corr_pairlist": ["ETH/USDT", "LINK/USDT"],
            "label_period_candles": 24,
            "include_shifted_candles": 2,
            "DI_threshold": 0.9,
            "weight_factor": 0.9,
            "principal_component_analysis": false,
            "use_SVM_to_remove_outliers": true,
            "indicator_periods_candles": [10, 20, 50]
        },
        "data_split_parameters": {
            "test_size": 0.33,
            "shuffle": false
        },
        "model_training_parameters": {
            "n_estimators": 1000
        }
    }
}
```

### GPU-Unterstützung aktivieren

Für FreqAI mit NVIDIA GPU:

```yaml
services:
  freqtrade-freqai:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

## 📈 Performance-Optimierungen

### 1. CPU-Optimierung

```bash
# Anzahl der CPU-Kerne für Hyperopt
export HYPEROPT_PARALLEL_JOBS=4
export OMP_NUM_THREADS=1
```

### 2. Speicher-Optimierung

```bash
# Für große Datasets
export FREQAI_PARALLEL_TRAINING=true
docker-compose up --memory="4g" freqtrade-freqai
```

### 3. Festplatten-Cache

```bash
# Redis für Caching
docker-compose --profile cache up -d redis
```

## 🧪 Testing und Validierung

### Backtest mit FreqAI

```bash
docker run --rm -v $(pwd)/user_data:/freqtrade/user_data \
  freqtradeorg/freqtrade:develop_freqai \
  backtesting \
  --strategy FreqAIExampleStrategy \
  --timerange 20231001-20231201 \
  --config user_data/config_freqai.json
```

### Hyperopt Validierung

```bash
docker run --rm -v $(pwd)/user_data:/freqtrade/user_data \
  freqtradeorg/freqtrade:develop_hyperopt \
  hyperopt \
  --hyperopt-loss SharpeHyperOptLoss \
  --strategy HyperOptStrategy \
  --epochs 100 \
  --spaces buy sell roi
```

## 🐛 Troubleshooting

### Logs anzeigen

```bash
# Service-Logs anzeigen
./freqtrade_docker.sh logs freqtrade-freqai

# Oder direkt
docker-compose logs -f freqtrade-freqai
```

### Status prüfen

```bash
# Alle Services
./freqtrade_docker.sh status

# Spezifischer Container
docker ps | grep freqtrade
```

### Häufige Probleme

1. **GPU nicht erkannt**:

   ```bash
   # NVIDIA Container Toolkit installieren
   docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi
   ```

2. **Speicher-Probleme**:

   ```bash
   # Speicher-Limit erhöhen
   docker-compose up --memory="8g" freqtrade-freqai
   ```

3. **Port-Konflikte**:

   ```bash
   # Ports in docker-compose.yml anpassen
   ports:
     - "127.0.0.1:8081:8080"  # FreqAI auf Port 8081
   ```

## 📚 Nützliche Befehle

```bash
# Setup-Skript Hilfe
./freqtrade_docker.sh

# Alle Services stoppen
./freqtrade_docker.sh stop

# Container aufräumen
docker system prune -a

# Images aktualisieren
docker-compose pull
```

## 🔗 Weiterführende Links

- [FreqTrade Dokumentation](https://www.freqtrade.io/)
- [FreqAI Dokumentation](https://www.freqtrade.io/en/stable/freqai/)
- [Hyperopt Dokumentation](https://www.freqtrade.io/en/stable/hyperopt/)
- [Docker Dokumentation](https://docs.docker.com/)

## 📄 Lizenz

Dieses Projekt steht unter der MIT-Lizenz. Siehe [LICENSE](LICENSE) für Details.
