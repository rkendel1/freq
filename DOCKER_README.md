# FreqTrade Docker Workflow - Quick Start

This guide provides a quick overview of the complete Docker workflow for FreqTrade.

## 📚 Documentation

- **[DOCKER_WORKFLOW.md](DOCKER_WORKFLOW.md)** - Comprehensive workflow documentation covering all 7 steps
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Detailed deployment strategies for various environments
- **[Makefile.docker](Makefile.docker)** - All available Docker commands
- **[.env.docker.example](.env.docker.example)** - Environment configuration template

## 🚀 Quick Start (5 Minutes)

### 1. Setup Environment

```bash
# Copy environment template
cp .env.docker.example .env

# Edit with your settings (optional for dry-run)
nano .env
```

### 2. Start FreqTrade

```bash
# Using Makefile (recommended)
make -f Makefile.docker docker-up

# Or using docker compose directly
docker compose up -d
```

### 3. Verify Installation

```bash
# Check status
make -f Makefile.docker docker-ps

# View logs
make -f Makefile.docker docker-logs

# Health check
make -f Makefile.docker docker-health
```

## 🎯 Complete Workflow Steps

The complete Docker workflow implements all 7 required steps:

### 1️⃣ Docker-Image erstellen (Build Docker Image)

```bash
# Standard build
make -f Makefile.docker docker-build

# Custom build with dependencies
make -f Makefile.docker docker-build-custom

# Pull from registry
make -f Makefile.docker docker-pull
```

### 2️⃣ Container starten (Start Container)

```bash
# Development
make -f Makefile.docker docker-up

# Production
make -f Makefile.docker docker-prod-up

# With specific profile
docker compose -f docker-compose.prod.yml --profile monitoring up -d
```

### 3️⃣ Umgebungsvariablen konfigurieren (Configure Environment Variables)

```bash
# Create .env from template
make -f Makefile.docker docker-env

# Edit environment variables
nano .env
```

**Important variables:**
- `FREQTRADE_MODE` - Operating mode (dry_run/live)
- `EXCHANGE_KEY` - Exchange API key
- `EXCHANGE_SECRET` - Exchange API secret
- `DB_URL` - Database connection string
- `LOG_LEVEL` - Logging level

### 4️⃣ Volumes für Datenpersistenz einrichten (Setup Volumes for Data Persistence)

Volumes are automatically configured in docker-compose files:

```yaml
volumes:
  - freqtrade-data:/freqtrade/user_data/data      # Market data
  - freqtrade-logs:/freqtrade/user_data/logs      # Logs
  - freqtrade-db:/freqtrade/user_data             # Database
```

**Manage volumes:**
```bash
# List volumes
make -f Makefile.docker docker-volumes

# Backup volumes
make -f Makefile.docker docker-backup

# Restore volumes
make -f Makefile.docker docker-restore BACKUP=filename.tar.gz
```

### 5️⃣ Netzwerk für Containerkommunikation konfigurieren (Configure Network)

Network is automatically configured:

```yaml
networks:
  freqtrade-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16
```

**Multi-container setup** (with PostgreSQL, Redis, etc.):
```bash
# Start with database
docker compose -f docker-compose.prod.yml --profile postgres up -d

# Start with cache
docker compose -f docker-compose.prod.yml --profile cache up -d

# Start with monitoring
docker compose -f docker-compose.prod.yml --profile monitoring up -d
```

### 6️⃣ Automatisierte Tests im Container ausführen (Run Automated Tests)

```bash
# All tests
make -f Makefile.docker docker-test

# Unit tests only
make -f Makefile.docker docker-test-unit

# Integration tests
make -f Makefile.docker docker-test-integration

# Linting
make -f Makefile.docker docker-lint

# Backtesting validation
make -f Makefile.docker docker-backtest
```

**Test configuration:**
```bash
# Run specific test suite
docker compose -f docker-compose.test.yml run --rm freqtrade-test \
  pytest tests/ -v -k test_name
```

### 7️⃣ Bereitstellung auf einer Produktionsumgebung (Production Deployment)

```bash
# Validate configuration
make -f Makefile.docker docker-config-prod

# Deploy to production
make -f Makefile.docker docker-prod-up

# Monitor deployment
make -f Makefile.docker docker-prod-logs

# Health check
make -f Makefile.docker docker-health
```

**Production checklist:**
- [ ] Configure production .env file
- [ ] Set FREQTRADE_MODE=live
- [ ] Use strong passwords
- [ ] Configure SSL/TLS
- [ ] Setup monitoring
- [ ] Configure backups
- [ ] Test disaster recovery

## 📊 Monitoring & Management

### View Logs
```bash
# Real-time logs
make -f Makefile.docker docker-logs-follow

# Last 100 lines
make -f Makefile.docker docker-logs
```

### Resource Usage
```bash
# Container stats
make -f Makefile.docker docker-stats

# Container status
make -f Makefile.docker docker-ps
```

### Health Checks
```bash
# Run health check
make -f Makefile.docker docker-health

# Check API
curl http://localhost:8080/api/v1/ping
```

## 🔧 Common Tasks

### Update FreqTrade
```bash
# Pull latest image
make -f Makefile.docker docker-pull

# Restart with new image
make -f Makefile.docker docker-restart
```

### Backup & Restore
```bash
# Create backup
make -f Makefile.docker docker-backup

# Restore from backup
make -f Makefile.docker docker-restore BACKUP=freqtrade-20241201.tar.gz
```

### Shell Access
```bash
# Open shell in container
make -f Makefile.docker docker-shell

# Execute command
make -f Makefile.docker docker-exec CMD='freqtrade --version'
```

### Cleanup
```bash
# Stop and remove containers
make -f Makefile.docker docker-down

# Remove volumes (WARNING: deletes data!)
make -f Makefile.docker docker-clean

# Prune unused resources
make -f Makefile.docker docker-prune
```

## 🎨 Workflow Variations

### Development Workflow
```bash
# 1. Setup
make -f Makefile.docker docker-dev-setup

# 2. Start with Jupyter
docker compose -f docker-compose.yml -f docker-compose-jupyter.yml up -d

# 3. Access Jupyter at http://localhost:8888
```

### Testing Workflow
```bash
# 1. Run linting
make -f Makefile.docker docker-lint

# 2. Run unit tests
make -f Makefile.docker docker-test-unit

# 3. Run integration tests
make -f Makefile.docker docker-test-integration

# 4. Run backtest validation
make -f Makefile.docker docker-backtest
```

### Production Workflow
```bash
# 1. Configure environment
cp .env.docker.example .env.prod
# Edit .env.prod with production settings

# 2. Validate configuration
docker compose -f docker-compose.prod.yml config

# 3. Deploy
make -f Makefile.docker docker-prod-up

# 4. Monitor
make -f Makefile.docker docker-prod-logs

# 5. Health check
make -f Makefile.docker docker-health
```

## 🔄 CI/CD Integration

GitHub Actions workflow is automatically configured in `.github/workflows/docker-workflow.yml`:

**Workflow stages:**
1. Build and Test
2. Automated Tests
3. Security Scanning
4. Performance Testing
5. Multi-platform Build
6. Generate Reports
7. Production Deployment

**Trigger workflow:**
- Push to develop/stable branches
- Pull request
- Release creation
- Manual trigger

## 📖 Detailed Documentation

For comprehensive information, refer to:

1. **[DOCKER_WORKFLOW.md](DOCKER_WORKFLOW.md)** - Complete workflow guide
   - Detailed explanations of each step
   - Configuration examples
   - Troubleshooting guides
   - Best practices

2. **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Deployment strategies
   - Development deployment
   - Staging deployment
   - Production deployment
   - Cloud deployments (AWS, GCP, Azure)
   - High availability setup
   - Monitoring and alerts

3. **[Makefile.docker](Makefile.docker)** - Command reference
   - All available make targets
   - Usage examples
   - Command descriptions

## 🆘 Getting Help

### Common Issues

**Container won't start:**
```bash
docker compose logs freqtrade
docker compose config
```

**Network issues:**
```bash
docker compose exec freqtrade ping -c 3 google.com
```

**Volume permissions:**
```bash
sudo chown -R 1000:1000 ./user_data
```

### Resources
- [FreqTrade Documentation](https://www.freqtrade.io/)
- [Docker Documentation](https://docs.docker.com/)
- [Community Forum](https://github.com/freqtrade/freqtrade/discussions)

## 📝 Summary

This Docker workflow provides:

✅ **Reproduzierbarkeit** - Consistent environments across development and production  
✅ **Effizienz** - Automated testing and deployment  
✅ **Sicherheit** - Security scanning and best practices  
✅ **Skalierbarkeit** - Easy scaling with Docker Swarm/Kubernetes  
✅ **Wartbarkeit** - Comprehensive monitoring and logging  
✅ **Datenpersistenz** - Reliable volume management and backups  
✅ **Flexibilität** - Support for various deployment scenarios  

---

**Start your FreqTrade journey with Docker today!** 🚀

For questions and support, visit the [FreqTrade Community](https://github.com/freqtrade/freqtrade/discussions).
