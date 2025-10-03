# 🚀 Freqtrade Setup mit TensorFlow, PyTorch & FreqAI

Dieses Repository ist vollständig eingerichtet für die Nutzung von Freqtrade mit allen Machine Learning-Features.

## ✅ Installierte Pakete & Versionen

### 🐍 Python Environment

- **Python**: 3.12.11 (via pyenv)
- **Freqtrade**: 2025.10-dev-5542febef

### 🧠 Machine Learning Libraries

- **TensorFlow**: 2.20.0
- **PyTorch**: 2.8.0+cu128 (mit CUDA Support)
- **Scikit-learn**: 1.7.2
- **XGBoost**: 3.0.5
- **LightGBM**: 4.6.0
- **CatBoost**: 1.2.8

### 📊 Data Science & Analysis

- **NumPy**: 2.3.3
- **Pandas**: 2.3.2
- **Matplotlib**: 3.10.6
- **Plotly**: 6.3.0

### 📈 Technical Analysis

- **TA-Lib**: 0.6.7
- **ft-pandas-ta**: 0.3.16
- **Technical**: 1.5.3

## 🏗️ Projektstruktur

```
/workspaces/freqtrade/
├── user_data/
│   ├── config.json                    # Grundkonfiguration
│   ├── config_freqai.json            # FreqAI Konfiguration
│   ├── strategies/
│   │   ├── sample_strategy.py        # Standard Beispielstrategie
│   │   └── FreqAI_TensorFlow_Strategy.py  # ML-basierte Strategie
│   ├── data/binance/                 # Marktdaten (BTC/USDT, ETH/USDT)
│   └── backtest_results/             # Backtesting Ergebnisse
├── docker-compose.yml                # Docker Konfiguration
├── Dockerfile                        # Docker Build-Datei
└── setup_complete.sh                 # Setup-Verifikations-Script
```

## 🎯 Verfügbare Features

### 1. **Traditionelles Trading**

```bash
# Backtesting mit Standard-Strategie
freqtrade backtesting --config user_data/config.json --strategy SampleStrategy

# Live Trading (Dry Run)
freqtrade trade --config user_data/config.json
```

### 2. **FreqAI Machine Learning**

```bash
# FreqAI mit TensorFlow/PyTorch
freqtrade backtesting --config user_data/config_freqai.json --strategy FreqAI_TensorFlow_Strategy

# FreqAI Training
freqtrade freqai-train --config user_data/config_freqai.json --strategy FreqAI_TensorFlow_Strategy
```

### 3. **Web-Interface (FreqUI)**

```bash
# Starte Web-Interface
freqtrade webserver --config user_data/config.json

# Zugriff über: http://localhost:8080
# Username: freqtrader
# Password: SuperSecurePassword
```

### 4. **Daten-Management**

```bash
# Lade zusätzliche Marktdaten
freqtrade download-data --config user_data/config.json --pairs BTC/USDT ETH/USDT ADA/USDT --timeframes 5m 15m 1h --days 30

# Datenanalyse
freqtrade plot-dataframe --config user_data/config.json --strategy SampleStrategy --pairs BTC/USDT
```

## 🐳 Docker Usage

### Mit docker-compose (empfohlen)

```bash
# Starte Freqtrade
docker-compose up -d

# Logs anzeigen
docker-compose logs -f

# Stoppe Container
docker-compose down
```

### Manuell mit Docker

```bash
# Build Image
docker build -t freqtrade-ml .

# Run Container
docker run -d --name freqtrade \
  -p 8080:8080 \
  -v ./user_data:/freqtrade/user_data \
  freqtrade-ml
```

## 🔧 Konfiguration

### Exchange-API Keys hinzufügen

Bearbeite `user_data/config.json`:

```json
{
  "exchange": {
    "name": "binance",
    "key": "DEIN_API_KEY",
    "secret": "DEIN_SECRET_KEY"
  }
}
```

### FreqAI Model-Konfiguration

Bearbeite `user_data/config_freqai.json`:

```json
{
  "freqai": {
    "model_training_parameters": {
      "n_estimators": 1000,
      "learning_rate": 0.1
    }
  }
}
```

## 🧪 Testing & Validation

### 1. **Setup-Verifikation**

```bash
./setup_complete.sh
```

### 2. **ML-Libraries Test**

```bash
python -c "import tensorflow as tf; print('TensorFlow:', tf.__version__)"
python -c "import torch; print('PyTorch:', torch.__version__)"
python -c "import sklearn; print('Scikit-learn:', sklearn.__version__)"
```

### 3. **Backtesting-Test**

```bash
freqtrade backtesting --config user_data/config.json --strategy SampleStrategy --timerange 20250928-20251003
```

## 📊 FreqAI Features

### Unterstützte Modelle

- **Klassische ML**: Random Forest, XGBoost, LightGBM, CatBoost
- **Deep Learning**: TensorFlow/Keras Neural Networks
- **PyTorch**: Custom PyTorch Models
- **Ensemble Methods**: Voting Classifiers, Stacking

### Feature Engineering

- Technische Indikatoren (RSI, MACD, Bollinger Bands)
- Preis-basierte Features (Momentum, ROC, Volatilität)
- Volume-Indikatoren
- Cross-Pair Korrelationen
- Zeitbasierte Features

### Datenqualität

- Outlier Detection (SVM, DBSCAN)
- Feature Selection (PCA, Mutual Information)
- Data Integrity Monitoring
- Noise Filtering

## 🛠️ Entwicklung

### Neue Strategie erstellen

```bash
freqtrade new-strategy --strategy MyCustomStrategy
```

### FreqAI Modell entwickeln

1. Kopiere `FreqAI_TensorFlow_Strategy.py`
2. Passe `populate_indicators()` an
3. Konfiguriere `freqai` Parameter
4. Teste mit Backtesting

### Hyperparameter Optimization

```bash
freqtrade hyperopt --config user_data/config.json --strategy SampleStrategy --spaces buy sell
```

## 📚 Ressourcen

- [Freqtrade Dokumentation](https://www.freqtrade.io/)
- [FreqAI Guide](https://www.freqtrade.io/en/stable/freqai/)
- [Strategy Development](https://www.freqtrade.io/en/stable/strategy-101/)
- [Docker Setup](https://www.freqtrade.io/en/stable/docker_quickstart/)

## ⚠️ Wichtige Hinweise

1. **Dry Run**: Standardmäßig läuft alles im Dry-Run-Modus (Simulation)
2. **API-Keys**: Niemals API-Keys in Git committen
3. **Risiko**: Trading birgt Verlustrisiken - nur mit Kapital handeln, das du verlieren kannst
4. **Backtesting**: Vergangene Performance garantiert keine zukünftigen Ergebnisse

## 🎉 Status

✅ Python 3.12.11 mit pyenv  
✅ Freqtrade 2025.10-dev installiert  
✅ TensorFlow 2.20.0 verfügbar  
✅ PyTorch 2.8.0+cu128 verfügbar  
✅ Alle ML-Libraries installiert  
✅ FreqUI Web-Interface läuft  
✅ Beispielstrategien erstellt  
✅ Testdaten heruntergeladen  
✅ Backtesting erfolgreich  
✅ Docker-Setup vorbereitet  

**🚀 Alles bereit für Machine Learning Trading!**
