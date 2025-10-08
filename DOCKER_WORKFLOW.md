# Optimaler Docker-Workflow für Freqtrade

Dieses Dokument beschreibt den optimalen Docker-Workflow für Freqtrade, der alle Aspekte von der Entwicklung bis zur Produktionsbereitstellung abdeckt.

## 📋 Inhaltsverzeichnis

1. [Überblick](#überblick)
2. [Voraussetzungen](#voraussetzungen)
3. [1. Docker-Image erstellen](#1-docker-image-erstellen)
4. [2. Container starten](#2-container-starten)
5. [3. Umgebungsvariablen konfigurieren](#3-umgebungsvariablen-konfigurieren)
6. [4. Volumes für Datenpersistenz](#4-volumes-für-datenpersistenz)
7. [5. Netzwerk-Konfiguration](#5-netzwerk-konfiguration)
8. [6. Automatisierte Tests](#6-automatisierte-tests)
9. [7. Produktionsbereitstellung](#7-produktionsbereitstellung)
10. [Makefile-Befehle](#makefile-befehle)
11. [Troubleshooting](#troubleshooting)

## Überblick

Dieser Workflow bietet:
- ✅ Reproduzierbare Build-Prozesse
- ✅ Konsistente Entwicklungs- und Produktionsumgebungen
- ✅ Automatisierte Tests in isolierten Containern
- ✅ Effiziente Datenpersistenz
- ✅ Sichere Netzwerkkonfiguration
- ✅ Skalierbare Deployment-Strategie

## Voraussetzungen

```bash
# Docker und Docker Compose installieren
docker --version  # >= 20.10
docker compose version  # >= 2.0

# Optional: Make für vereinfachte Befehle
make --version
```

## 1. Docker-Image erstellen

### Standard-Image bauen

```bash
# Mit Make (empfohlen)
make docker-build

# Oder direkt mit Docker
docker build -t freqtrade:local .
```

### Benutzerdefiniertes Image mit zusätzlichen Abhängigkeiten

```bash
# 1. Dockerfile.custom anpassen
cp docker/Dockerfile.custom Dockerfile.custom
# Fügen Sie Ihre Abhängigkeiten hinzu

# 2. Image bauen
make docker-build-custom
# Oder:
docker build -f Dockerfile.custom -t freqtrade:custom .
```

### Multi-Stage Build für Optimierung

Das Standard-Dockerfile nutzt Multi-Stage Builds:
- **base**: Grundsystem mit Python
- **python-deps**: Dependencies kompilieren
- **runtime-image**: Finales schlankes Image

### Image-Varianten

| Image Tag | Beschreibung | Verwendung |
|-----------|-------------|------------|
| `freqtradeorg/freqtrade:stable` | Stabile Version | Produktion |
| `freqtradeorg/freqtrade:develop` | Entwicklungsversion | Testing |
| `freqtradeorg/freqtrade:develop_plot` | Mit Plotting-Tools | Analyse |
| `freqtradeorg/freqtrade:develop_freqai` | Mit FreqAI/ML | Machine Learning |
| `freqtradeorg/freqtrade:develop_hyperopt` | Mit Hyperopt | Optimierung |

## 2. Container starten

### Entwicklungsumgebung

```bash
# Standard-Konfiguration
make docker-up

# Mit interaktiver Shell
make docker-shell

# Im Hintergrund starten
docker compose up -d
```

### Mit spezifischer Konfiguration

```bash
# FreqAI Trading
docker compose -f docker-compose.yml -f docker-compose-freqai.yml up -d

# Mit Jupyter Notebook für Analyse
docker compose -f docker-compose.yml -f docker-compose-jupyter.yml up -d
```

### Container-Überwachung

```bash
# Status prüfen
docker compose ps

# Logs anzeigen
docker compose logs -f freqtrade

# Ressourcennutzung
docker stats freqtrade
```

## 3. Umgebungsvariablen konfigurieren

### .env Datei erstellen

```bash
# Template kopieren
cp .env.docker.example .env

# Oder mit Make
make docker-env
```

### Wichtige Umgebungsvariablen

**Grundkonfiguration:**
```bash
# .env
# Freqtrade-Modus
FREQTRADE_MODE=dry_run  # oder: live

# Logging
LOG_LEVEL=info
TZ=Europe/Berlin

# API Server
FREQTRADE_API_PORT=8080
FREQTRADE_API_USERNAME=freqtrade
FREQTRADE_API_PASSWORD=your-secure-password
```

**Exchange API (für Live-Trading):**
```bash
# Exchange-Konfiguration (niemals committen!)
EXCHANGE_NAME=binance
EXCHANGE_KEY=your_api_key
EXCHANGE_SECRET=your_api_secret
```

**Ressourcen-Limits:**
```bash
# Docker-Ressourcen
DOCKER_CPU_LIMIT=4.0
DOCKER_MEMORY_LIMIT=4G
```

**FreqAI-Konfiguration:**
```bash
# FreqAI/ML-Einstellungen
FREQAI_ENABLED=true
FREQAI_CPU_COUNT=4
TENSORBOARD_PORT=6006
```

### Umgebungsvariablen in docker-compose.yml nutzen

```yaml
services:
  freqtrade:
    environment:
      - LOG_LEVEL=${LOG_LEVEL:-info}
      - TZ=${TZ:-UTC}
    env_file:
      - .env
```

### Secrets Management

**Für Produktion - Docker Secrets verwenden:**
```bash
# Secret erstellen
echo "my-api-key" | docker secret create exchange_key -

# In docker-compose.yml referenzieren
secrets:
  exchange_key:
    external: true
```

## 4. Volumes für Datenpersistenz

### Standard Volume-Struktur

```yaml
volumes:
  # Benutzerdaten (Strategien, Konfiguration, Logs)
  - "./user_data:/freqtrade/user_data"
  
  # Für bessere Performance: Named Volumes
  - "freqtrade-data:/freqtrade/user_data/data"
  - "freqtrade-models:/freqtrade/user_data/models"
```

### Detaillierte Volume-Konfiguration

```yaml
volumes:
  # Konfigurationsdateien (read-only)
  - "./user_data/config.json:/freqtrade/user_data/config.json:ro"
  
  # Strategien (read-only in Produktion)
  - "./user_data/strategies:/freqtrade/user_data/strategies:ro"
  
  # Daten (read-write)
  - "freqtrade-data:/freqtrade/user_data/data"
  
  # Logs (read-write)
  - "freqtrade-logs:/freqtrade/user_data/logs"
  
  # Datenbank
  - "freqtrade-db:/freqtrade/user_data/db"
  
  # FreqAI Modelle
  - "freqtrade-models:/freqtrade/user_data/models"
```

### Volume-Management

```bash
# Named Volumes erstellen
docker volume create freqtrade-data
docker volume create freqtrade-logs
docker volume create freqtrade-db

# Volume-Status prüfen
docker volume ls
docker volume inspect freqtrade-data

# Backup erstellen
make docker-backup
# Oder manuell:
docker run --rm -v freqtrade-data:/data -v $(pwd)/backup:/backup \
  alpine tar czf /backup/data-$(date +%Y%m%d).tar.gz -C /data .

# Restore
docker run --rm -v freqtrade-data:/data -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/data-20241201.tar.gz -C /data
```

### Tmpfs für Performance

Für temporäre Dateien:
```yaml
tmpfs:
  - /tmp
  - /freqtrade/user_data/tmp:size=1G
```

## 5. Netzwerk-Konfiguration

### Standard-Netzwerk

```yaml
networks:
  freqtrade-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16
```

### Multi-Container Setup

```yaml
services:
  freqtrade:
    networks:
      - freqtrade-network
    ports:
      - "127.0.0.1:8080:8080"  # Nur localhost
  
  postgresql:
    networks:
      - freqtrade-network
    # Keine externe Port-Freigabe
  
  redis:
    networks:
      - freqtrade-network

networks:
  freqtrade-network:
    driver: bridge
```

### Externe Netzwerke

```yaml
# Verbindung mit bestehendem Netzwerk
networks:
  freqtrade-network:
    external: true
    name: my-existing-network
```

### Port-Konfiguration

**Entwicklung:**
```yaml
ports:
  - "8080:8080"  # API
  - "8888:8888"  # Jupyter
  - "6006:6006"  # TensorBoard
```

**Produktion (sicher):**
```yaml
ports:
  - "127.0.0.1:8080:8080"  # Nur localhost
```

### Reverse Proxy Integration

**Mit Nginx:**
```nginx
# /etc/nginx/sites-available/freqtrade
upstream freqtrade {
    server 127.0.0.1:8080;
}

server {
    listen 80;
    server_name freqtrade.example.com;
    
    location / {
        proxy_pass http://freqtrade;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 6. Automatisierte Tests

### Test-Container starten

```bash
# Unit-Tests
make docker-test

# Oder direkt:
docker compose -f docker-compose.test.yml up --abort-on-container-exit
```

### Test-Konfiguration (docker-compose.test.yml)

```yaml
services:
  freqtrade-test:
    build:
      context: .
      dockerfile: Dockerfile
    command: pytest tests/ -v
    volumes:
      - ./tests:/freqtrade/tests
    environment:
      - PYTEST_OPTS=--cov=freqtrade --cov-report=xml
```

### Verschiedene Test-Typen

```bash
# Unit-Tests
docker compose -f docker-compose.test.yml run --rm freqtrade-test \
  pytest tests/ -v

# Integration-Tests
docker compose -f docker-compose.test.yml run --rm freqtrade-test \
  pytest tests/ -v -m integration

# Performance-Tests
docker compose -f docker-compose.test.yml run --rm freqtrade-test \
  pytest tests/ -v -m slow

# Backtesting (als Test)
docker compose run --rm freqtrade backtesting \
  --strategy SampleStrategy \
  --timerange 20230101-20230201
```

### Kontinuierliche Integration

Die Tests laufen automatisch bei jedem Push über GitHub Actions:
- `.github/workflows/ci.yml` - Standard CI-Tests
- `.github/workflows/docker-build.yml` - Docker-Build und Tests

### Lokale Test-Ausführung

```bash
# Alle Tests
make test

# Spezifische Tests
make test-unit
make test-integration
make test-exchange

# Mit Coverage
make test-coverage
```

## 7. Produktionsbereitstellung

### Vorbereitung

1. **Konfiguration validieren:**
```bash
# Konfiguration testen
docker compose config

# Dry-run Test
docker compose run --rm freqtrade \
  trade --config /freqtrade/user_data/config.json --dry-run
```

2. **Secrets einrichten:**
```bash
# .env für Produktion (NIEMALS committen!)
cp .env.example .env.prod
# Bearbeiten und sichere Werte eintragen

# Oder Docker Secrets verwenden
echo "api-key" | docker secret create exchange_key -
echo "api-secret" | docker secret create exchange_secret -
```

3. **Ressourcen-Limits setzen:**
```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 4G
    reservations:
      cpus: '1.0'
      memory: 2G
```

### Deployment-Strategien

#### A. Docker Compose (Single Host)

```bash
# 1. Image pullen/bauen
docker compose pull
# oder
docker compose build

# 2. Container starten
docker compose up -d

# 3. Health-Check
make docker-health
# oder
docker compose ps
curl http://localhost:8080/api/v1/ping

# 4. Logs überwachen
docker compose logs -f --tail=100
```

#### B. Docker Swarm (Multi-Host)

```bash
# 1. Swarm initialisieren
docker swarm init

# 2. Stack deployen
docker stack deploy -c docker-compose.prod.yml freqtrade

# 3. Status prüfen
docker stack services freqtrade
docker stack ps freqtrade

# 4. Skalieren
docker service scale freqtrade_freqtrade=3
```

#### C. Kubernetes

Siehe `k8s/` Verzeichnis für Kubernetes-Manifests:

```bash
# Namespace erstellen
kubectl create namespace freqtrade

# Secrets erstellen
kubectl create secret generic freqtrade-secrets \
  --from-literal=exchange-key=your-key \
  --from-literal=exchange-secret=your-secret \
  -n freqtrade

# Deployment
kubectl apply -f k8s/ -n freqtrade

# Status
kubectl get pods -n freqtrade
kubectl logs -f deployment/freqtrade -n freqtrade
```

### Monitoring und Logging

**1. Container-Logs:**
```bash
# Live-Logs
docker compose logs -f

# Logs mit Zeitstempel
docker compose logs -f --timestamps

# Logs in Datei
docker compose logs > logs-$(date +%Y%m%d).log
```

**2. Health Checks:**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/api/v1/ping"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

**3. Externes Monitoring:**
```yaml
# Prometheus Exporter
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
```

### Rollback-Strategie

```bash
# Vorheriges Image wiederherstellen
docker compose down
docker compose up -d --force-recreate freqtrade:previous-tag

# Oder mit Docker Swarm
docker service rollback freqtrade_freqtrade
```

### Backup und Disaster Recovery

```bash
# Automatisches Backup (täglich)
# Cronjob einrichten:
0 2 * * * cd /path/to/freqtrade && make docker-backup

# Backup-Script
#!/bin/bash
BACKUP_DIR="/backup/freqtrade/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Volume-Backup
docker run --rm \
  -v freqtrade-data:/data \
  -v $BACKUP_DIR:/backup \
  alpine tar czf /backup/data.tar.gz -C /data .

# Datenbank-Backup
docker compose exec freqtrade \
  sqlite3 /freqtrade/user_data/tradesv3.sqlite \
  ".backup $BACKUP_DIR/tradesv3.sqlite"
```

### Zero-Downtime Updates

```bash
# 1. Neues Image bauen/pullen
docker compose pull

# 2. Rolling Update (mit Docker Swarm)
docker service update \
  --image freqtradeorg/freqtrade:stable \
  --update-parallelism 1 \
  --update-delay 10s \
  freqtrade_freqtrade

# 3. Oder Blue-Green Deployment
docker compose -f docker-compose.blue.yml up -d
# Test durchführen
# Traffic umleiten
docker compose -f docker-compose.green.yml down
```

## Makefile-Befehle

Alle wichtigen Befehle sind im Makefile zusammengefasst:

```bash
# Image-Management
make docker-build          # Standard-Image bauen
make docker-build-custom   # Custom-Image bauen
make docker-pull           # Images aktualisieren

# Container-Management
make docker-up             # Container starten
make docker-down           # Container stoppen
make docker-restart        # Container neustarten
make docker-shell          # Shell im Container öffnen

# Tests
make docker-test           # Tests ausführen
make docker-test-unit      # Unit-Tests
make docker-test-integration # Integration-Tests

# Monitoring
make docker-logs           # Logs anzeigen
make docker-ps             # Container-Status
make docker-stats          # Ressourcennutzung

# Wartung
make docker-clean          # Container und Volumes löschen
make docker-backup         # Backup erstellen
make docker-restore        # Backup wiederherstellen

# Deployment
make docker-health         # Health-Check
make docker-prod           # Produktions-Deployment
```

## Troubleshooting

### Problem: Container startet nicht

```bash
# Logs prüfen
docker compose logs freqtrade

# Container-Status
docker compose ps

# Events anzeigen
docker events --filter container=freqtrade

# Konfiguration validieren
docker compose config
```

### Problem: Datenpersistenz funktioniert nicht

```bash
# Volume-Inhalt prüfen
docker run --rm -v freqtrade-data:/data alpine ls -la /data

# Berechtigungen prüfen
docker compose exec freqtrade ls -la /freqtrade/user_data

# Volume neu erstellen
docker volume rm freqtrade-data
docker volume create freqtrade-data
```

### Problem: Netzwerk-Konnektivität

```bash
# Netzwerk prüfen
docker network inspect freqtrade_default

# DNS testen
docker compose exec freqtrade ping -c 3 google.com

# Port-Binding prüfen
netstat -tulpn | grep 8080
```

### Problem: Performance-Probleme

```bash
# Ressourcennutzung prüfen
docker stats freqtrade

# Logs auf Fehler prüfen
docker compose logs --tail=100 | grep -i error

# tmpfs für temporäre Dateien nutzen
# In docker-compose.yml:
tmpfs:
  - /tmp:size=1G
```

### Problem: Build-Fehler

```bash
# Cache löschen und neu bauen
docker compose build --no-cache

# Multi-stage Build debuggen
docker build --target=python-deps -t debug .
docker run --rm -it debug /bin/bash

# BuildKit-Logs
BUILDKIT_PROGRESS=plain docker compose build
```

## Best Practices

1. **Niemals Secrets committen** - Verwenden Sie .env-Dateien und fügen Sie sie zu .gitignore hinzu
2. **Regelmäßige Updates** - Halten Sie Images aktuell: `docker compose pull`
3. **Resource Limits** - Setzen Sie immer CPU/Memory-Limits
4. **Health Checks** - Implementieren Sie Health-Checks für alle Services
5. **Logging** - Konfigurieren Sie Log-Rotation und zentrales Logging
6. **Backups** - Automatisieren Sie regelmäßige Backups
7. **Monitoring** - Implementieren Sie Monitoring und Alerting
8. **Testing** - Testen Sie vor Produktion im Dry-Run-Modus
9. **Documentation** - Dokumentieren Sie Ihre spezifische Konfiguration
10. **Security** - Verwenden Sie nicht-privilegierte User, scannen Sie Images

## Weitere Ressourcen

- [Freqtrade Dokumentation](https://www.freqtrade.io/)
- [Docker Dokumentation](https://docs.docker.com/)
- [Docker Compose Dokumentation](https://docs.docker.com/compose/)
- [Dockerfile Best Practices](https://docs.docker.com/develop/dev-best-practices/)

---

**Viel Erfolg mit Ihrem optimierten Docker-Workflow!** 🚀
