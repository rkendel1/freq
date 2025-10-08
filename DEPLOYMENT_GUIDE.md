# FreqTrade Docker Deployment Guide

Comprehensive guide for deploying FreqTrade using Docker in various environments.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Development Deployment](#development-deployment)
- [Staging Deployment](#staging-deployment)
- [Production Deployment](#production-deployment)
- [Cloud Deployments](#cloud-deployments)
- [High Availability Setup](#high-availability-setup)
- [Monitoring and Alerts](#monitoring-and-alerts)
- [Backup and Recovery](#backup-and-recovery)
- [Security Best Practices](#security-best-practices)

## Quick Start

### Prerequisites

```bash
# Check Docker installation
docker --version  # >= 20.10
docker compose version  # >= 2.0

# Check system resources
free -h  # At least 4GB RAM recommended
df -h    # At least 20GB free space
```

### Basic Deployment

```bash
# 1. Clone repository
git clone https://github.com/freqtrade/freqtrade.git
cd freqtrade

# 2. Create environment configuration
cp .env.docker.example .env
# Edit .env with your settings
nano .env

# 3. Start services
docker compose up -d

# 4. Check status
docker compose ps
docker compose logs -f
```

## Development Deployment

### Local Development Setup

```bash
# Use Makefile for convenience
make -f Makefile.docker docker-dev-setup

# Or manually:
docker compose -f docker-compose.yml up -d

# Access services:
# - FreqTrade API: http://localhost:8080
# - Logs: docker compose logs -f
```

### Development with Hot Reload

```yaml
# docker-compose.override.yml
services:
  freqtrade:
    volumes:
      - ./freqtrade:/freqtrade/freqtrade:ro  # Mount source code
      - ./user_data:/freqtrade/user_data
    environment:
      - DEBUG=true
    command: >
      trade --config /freqtrade/user_data/config.json --strategy SampleStrategy
```

### Development with Jupyter

```bash
# Start with Jupyter notebook
docker compose -f docker-compose.yml -f docker-compose-jupyter.yml up -d

# Access Jupyter at http://localhost:8888
# Token will be shown in logs:
docker compose logs jupyter
```

## Staging Deployment

### Staging Environment Setup

```yaml
# docker-compose.staging.yml
services:
  freqtrade:
    image: freqtradeorg/freqtrade:develop
    restart: unless-stopped
    environment:
      - FREQTRADE_MODE=dry_run
      - LOG_LEVEL=debug
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
```

```bash
# Deploy to staging
docker compose -f docker-compose.staging.yml up -d

# Run staging tests
make -f Makefile.docker docker-test

# Monitor staging
docker compose -f docker-compose.staging.yml logs -f
```

### Staging Validation Checklist

- [ ] Configuration validated
- [ ] Dry-run mode enabled
- [ ] Test trades executed successfully
- [ ] API endpoints responding
- [ ] Monitoring dashboards working
- [ ] Backup/restore tested
- [ ] Resource limits appropriate
- [ ] Logs being collected

## Production Deployment

### Production Preparation

1. **Security Hardening:**

```bash
# Generate secure passwords
openssl rand -hex 32  # For JWT secret
openssl rand -hex 16  # For API password

# Update .env with production values
FREQTRADE_MODE=live
FREQTRADE_API_PASSWORD=<secure-password>
FREQTRADE_API_JWT_SECRET=<jwt-secret>

# Exchange API keys (read-only if possible)
EXCHANGE_KEY=<your-key>
EXCHANGE_SECRET=<your-secret>
```

2. **Database Setup:**

```bash
# For production, use PostgreSQL
docker compose --profile postgres up -d postgresql

# Update DB_URL in .env
DB_URL=postgresql://freqtrade:password@postgresql:5432/freqtrade
```

3. **Resource Planning:**

```yaml
# docker-compose.prod.yml
deploy:
  resources:
    limits:
      cpus: '4.0'
      memory: 4G
    reservations:
      cpus: '2.0'
      memory: 2G
```

### Production Deployment

```bash
# 1. Validate configuration
docker compose -f docker-compose.prod.yml config

# 2. Pull latest images
docker compose -f docker-compose.prod.yml pull

# 3. Deploy
docker compose -f docker-compose.prod.yml up -d

# 4. Verify health
make -f Makefile.docker docker-health

# 5. Monitor startup
docker compose -f docker-compose.prod.yml logs -f
```

### Production Monitoring Setup

```bash
# Start with monitoring stack
docker compose -f docker-compose.prod.yml --profile monitoring up -d

# Access monitoring:
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000
```

## Cloud Deployments

### AWS EC2 Deployment

```bash
# 1. Launch EC2 instance (t3.medium or larger)
# 2. Install Docker
sudo yum update -y
sudo yum install -y docker
sudo systemctl start docker
sudo usermod -aG docker ec2-user

# 3. Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 4. Clone and deploy
git clone https://github.com/freqtrade/freqtrade.git
cd freqtrade
cp .env.docker.example .env
# Edit .env
docker compose -f docker-compose.prod.yml up -d

# 5. Setup CloudWatch logging (optional)
# Configure Docker to send logs to CloudWatch
```

### AWS ECS Deployment

```bash
# Create task definition
aws ecs create-task-definition \
  --cli-input-json file://ecs-task-definition.json

# Create service
aws ecs create-service \
  --cluster freqtrade-cluster \
  --service-name freqtrade \
  --task-definition freqtrade:1 \
  --desired-count 1
```

### Google Cloud Platform (GCP)

```bash
# 1. Create VM instance
gcloud compute instances create freqtrade-instance \
  --machine-type=e2-standard-2 \
  --boot-disk-size=50GB \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud

# 2. SSH and install Docker
gcloud compute ssh freqtrade-instance
# Follow AWS EC2 Docker installation steps

# 3. Deploy with Docker Compose
# Same as AWS EC2 deployment
```

### Digital Ocean Droplet

```bash
# 1. Create Droplet with Docker pre-installed
# Select "Docker" from Marketplace

# 2. SSH to droplet
ssh root@your-droplet-ip

# 3. Deploy FreqTrade
git clone https://github.com/freqtrade/freqtrade.git
cd freqtrade
cp .env.docker.example .env
# Edit .env
docker compose -f docker-compose.prod.yml up -d
```

### Azure Container Instances

```bash
# Create container instance
az container create \
  --resource-group freqtrade-rg \
  --name freqtrade \
  --image freqtradeorg/freqtrade:stable \
  --cpu 2 --memory 4 \
  --environment-variables \
    FREQTRADE_MODE=live \
    LOG_LEVEL=info \
  --ports 8080 \
  --protocol TCP
```

## High Availability Setup

### Docker Swarm Deployment

```bash
# 1. Initialize Swarm
docker swarm init

# 2. Deploy stack
docker stack deploy -c docker-compose.prod.yml freqtrade

# 3. Scale service
docker service scale freqtrade_freqtrade=3

# 4. Monitor services
docker service ls
docker service ps freqtrade_freqtrade

# 5. Rolling updates
docker service update --image freqtradeorg/freqtrade:stable freqtrade_freqtrade
```

### Kubernetes Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: freqtrade
spec:
  replicas: 2
  selector:
    matchLabels:
      app: freqtrade
  template:
    metadata:
      labels:
        app: freqtrade
    spec:
      containers:
      - name: freqtrade
        image: freqtradeorg/freqtrade:stable
        resources:
          limits:
            memory: "4Gi"
            cpu: "2000m"
          requests:
            memory: "2Gi"
            cpu: "1000m"
        env:
        - name: FREQTRADE_MODE
          value: "live"
        volumeMounts:
        - name: config
          mountPath: /freqtrade/user_data
      volumes:
      - name: config
        persistentVolumeClaim:
          claimName: freqtrade-data
```

```bash
# Deploy to Kubernetes
kubectl apply -f k8s/

# Check status
kubectl get pods -l app=freqtrade
kubectl logs -f deployment/freqtrade

# Scale
kubectl scale deployment freqtrade --replicas=3
```

## Monitoring and Alerts

### Prometheus Configuration

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'freqtrade'
    static_configs:
      - targets: ['freqtrade:8080']
```

### Grafana Dashboards

```bash
# Start Grafana
docker compose -f docker-compose.prod.yml --profile monitoring up -d grafana

# Access Grafana at http://localhost:3000
# Default credentials: admin/admin

# Import FreqTrade dashboard
# Dashboard ID: <create-your-own>
```

### Health Monitoring Script

```bash
#!/bin/bash
# health-monitor.sh

API_URL="http://localhost:8080/api/v1"

# Check API health
if ! curl -sf "${API_URL}/ping" > /dev/null; then
    echo "ALERT: FreqTrade API is down!"
    # Send alert (email, Slack, etc.)
    exit 1
fi

# Check trades
TRADES=$(curl -s "${API_URL}/trades" | jq '.trades | length')
echo "Active trades: ${TRADES}"

# Check balance
BALANCE=$(curl -s "${API_URL}/balance" | jq '.total')
echo "Total balance: ${BALANCE}"
```

### Alerting with AlertManager

```yaml
# monitoring/alertmanager.yml
route:
  receiver: 'email'

receivers:
  - name: 'email'
    email_configs:
      - to: 'your-email@example.com'
        from: 'alertmanager@example.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'your-email@example.com'
        auth_password: 'your-password'
```

## Backup and Recovery

### Automated Backup Script

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/freqtrade"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Backup volumes
docker run --rm \
  -v freqtrade_user_data:/data \
  -v "${BACKUP_DIR}":/backup \
  alpine tar czf "/backup/freqtrade-${DATE}.tar.gz" -C /data .

# Backup database
docker compose exec freqtrade \
  sqlite3 /freqtrade/user_data/tradesv3.sqlite \
  ".backup ${BACKUP_DIR}/tradesv3-${DATE}.sqlite"

# Keep only last 30 days of backups
find "${BACKUP_DIR}" -name "freqtrade-*.tar.gz" -mtime +30 -delete

echo "Backup completed: freqtrade-${DATE}.tar.gz"
```

### Cronjob Setup

```bash
# Add to crontab
crontab -e

# Backup daily at 2 AM
0 2 * * * /path/to/backup.sh >> /var/log/freqtrade-backup.log 2>&1
```

### Disaster Recovery Plan

1. **Regular Backups:** Daily automated backups
2. **Off-site Storage:** Copy backups to S3, Google Cloud Storage, etc.
3. **Test Restores:** Monthly restore tests
4. **Documentation:** Keep deployment documentation updated
5. **Emergency Contacts:** List of people to contact during incidents

## Security Best Practices

### 1. API Security

```yaml
# docker-compose.prod.yml
services:
  freqtrade:
    ports:
      - "127.0.0.1:8080:8080"  # Bind to localhost only
```

### 2. Secrets Management

```bash
# Use Docker secrets for production
echo "api-key" | docker secret create exchange_key -
echo "api-secret" | docker secret create exchange_secret -

# Reference in compose file
secrets:
  exchange_key:
    external: true
```

### 3. Network Isolation

```yaml
networks:
  freqtrade-internal:
    internal: true  # No external access
  freqtrade-external:
    internal: false
```

### 4. Regular Updates

```bash
# Update images regularly
docker compose pull
docker compose up -d --force-recreate

# Check for security updates
docker scout cves freqtradeorg/freqtrade:stable
```

### 5. Firewall Configuration

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP
sudo ufw allow 443/tcp # HTTPS
sudo ufw enable

# Block direct access to container ports
sudo ufw deny 8080/tcp
```

### 6. SSL/TLS with Nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/freqtrade
server {
    listen 443 ssl http2;
    server_name freqtrade.example.com;

    ssl_certificate /etc/letsencrypt/live/freqtrade.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/freqtrade.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Troubleshooting Common Deployment Issues

### Container Won't Start

```bash
# Check logs
docker compose logs freqtrade

# Check resource usage
docker stats

# Validate configuration
docker compose config
```

### Out of Memory

```bash
# Increase memory limit
# In docker-compose.yml:
deploy:
  resources:
    limits:
      memory: 8G
```

### Network Issues

```bash
# Check network connectivity
docker compose exec freqtrade ping -c 3 google.com

# Check DNS
docker compose exec freqtrade nslookup exchange.com

# Restart networking
docker network prune
docker compose down && docker compose up -d
```

### Volume Permissions

```bash
# Fix permissions
sudo chown -R 1000:1000 ./user_data

# Or use volume with proper ownership
docker run --rm -v freqtrade_user_data:/data alpine chown -R 1000:1000 /data
```

## Maintenance Windows

### Planned Maintenance

```bash
# 1. Notify users
echo "Maintenance starting at $(date)" | mail -s "FreqTrade Maintenance" users@example.com

# 2. Stop trading
docker compose exec freqtrade freqtrade stop

# 3. Backup
./backup.sh

# 4. Perform updates
docker compose pull
docker compose up -d --force-recreate

# 5. Verify
make -f Makefile.docker docker-health

# 6. Resume trading
docker compose exec freqtrade freqtrade start
```

## Performance Tuning

### Database Optimization

```sql
-- For PostgreSQL
VACUUM ANALYZE;
REINDEX DATABASE freqtrade;
```

### Container Resources

```yaml
# Optimize for trading bot
deploy:
  resources:
    limits:
      cpus: '4.0'
      memory: 4G
    reservations:
      cpus: '2.0'
      memory: 2G
```

### Logging Optimization

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "5"
    compress: "true"
```

---

## Support and Resources

- [FreqTrade Documentation](https://www.freqtrade.io/)
- [Docker Documentation](https://docs.docker.com/)
- [Community Forum](https://github.com/freqtrade/freqtrade/discussions)
- [Issue Tracker](https://github.com/freqtrade/freqtrade/issues)

**Remember:** Always test in dry-run mode before going live! 🚀
