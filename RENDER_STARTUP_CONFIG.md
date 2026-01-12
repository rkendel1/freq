# Render Startup and Install Configuration Guide

## Overview

This document explains exactly what happens when you deploy to Render, from initial build to running services.

## Deployment Stages

### Stage 1: Build Phase

When you deploy to Render, the following happens automatically:

#### 1.1 Repository Clone
```bash
# Render clones your GitHub repository
git clone https://github.com/your-username/freq.git
cd freq
```

#### 1.2 Docker Build
Render uses your `Dockerfile.dev` to build the container:

```dockerfile
# From Dockerfile.dev - Multi-stage build

# Stage 1: Base image
FROM python:3.12-slim AS base
# - Sets up environment variables
# - Installs system dependencies (sudo, curl, sqlite3, etc.)
# - Creates ftuser (non-root user)
# - Creates directories: /freqtrade, /var/log/supervisor

# Stage 2: Python dependencies
FROM base AS python-deps
# - Installs build tools (gcc, cmake, etc.)
# - Copies requirements.txt and pyproject.toml
# - Installs Python packages:
#   - Core freqtrade dependencies (ccxt, SQLAlchemy, pandas, etc.)
#   - Streamlit + plotly for dashboards
#   - Flask for demo UI
#   - QuestDB client (future-ready)

# Stage 3: Runtime image
FROM base AS runtime
# - Copies Python packages from python-deps stage
# - Copies application code
# - Installs freqtrade in development mode
# - Copies supervisor configuration
# - Copies entrypoint script
# - Exposes ports: 5000, 8501, 8502
# - Sets up volume mount: /freqtrade/user_data
```

**Build time**: 5-10 minutes (first build), 2-3 minutes (subsequent builds with cache)

#### 1.3 Image Size
- Final image: ~1.2GB
- Includes all dependencies, no external downloads needed at runtime

### Stage 2: Deployment

After build completes, Render deploys your container:

#### 2.1 Environment Variables Injection

Render injects environment variables defined in `render.yaml` or dashboard:

```bash
# Automatically provided by Render
PORT=10000                           # Dynamic port assigned by Render
RENDER=true                          # Flag indicating Render environment
RENDER_EXTERNAL_URL=https://your-app.onrender.com

# User-configured (from render.yaml)
DRY_RUN=true
INITIAL_CAPITAL=10000.0
EXCHANGE_NAME=binance
LOG_LEVEL=INFO
STREAMLIT_PASSWORD=<generated>       # Auto-generated secure password
PROCESS_THROTTLE_SECS=5
QUESTDB_ENABLED=false
MONITOR_REFRESH_INTERVAL=10
MAX_LOG_LINES=500
```

#### 2.2 Persistent Disk Mount

Render mounts the persistent disk:
```bash
# Disk configuration (from render.yaml)
Name: user-data
Size: 1GB
Mount: /freqtrade/user_data

# This directory persists across deployments!
```

#### 2.3 Container Start

Render runs the container with the configured command:
```bash
# From render.yaml
docker run \
  -e PORT=10000 \
  -e RENDER=true \
  -e DRY_RUN=true \
  # ... all other env vars ...
  -v /mnt/data:/freqtrade/user_data \
  -p 10000:$PORT \
  your-image \
  supervisord -c /etc/supervisor/supervisord.conf
```

### Stage 3: Initialization (Entrypoint)

The entrypoint script (`docker/entrypoint.sh`) runs first:

#### 3.1 Port Configuration
```bash
# Detects Render environment and configures ports
DEMO_UI_PORT="${PORT:-5000}"              # Uses Render's PORT (10000)
CONFIG_DASHBOARD_PORT="${CONFIG_PORT:-8501}"  # Default 8501
MONITOR_DASHBOARD_PORT="${MONITOR_PORT:-8502}" # Default 8502

# Exports these for supervisor to use
export DEMO_UI_PORT
export CONFIG_DASHBOARD_PORT
export MONITOR_DASHBOARD_PORT
```

#### 3.2 Directory Structure Creation
```bash
# Creates user_data subdirectories if they don't exist
mkdir -p /freqtrade/user_data/logs
mkdir -p /freqtrade/user_data/data
mkdir -p /freqtrade/user_data/strategies
mkdir -p /freqtrade/user_data/exploits
```

#### 3.3 Permission Fix
```bash
# Ensures correct ownership (only if needed)
chown -R ftuser:ftuser /freqtrade/user_data
```

#### 3.4 Configuration Generation

If `config.prod.json` doesn't exist, creates default:
```json
{
  "max_open_trades": 3,
  "stake_currency": "USDT",
  "dry_run": true,
  "initial_capital": 10000.0,
  "exploit_modules": [],
  "exchange": {
    "name": "binance",
    "key": "",
    "secret": ""
  },
  "risk_limits": {
    "max_position_size": 0.2,
    "max_total_exposure": 0.8,
    "max_open_positions": 3
  }
}
```

#### 3.5 Database Initialization
```bash
# Creates SQLite database if it doesn't exist
touch /freqtrade/user_data/tradesv3.sqlite
```

#### 3.6 README Creation
```bash
# Creates helpful README in user_data directory
# Explains directory structure and how to use services
```

### Stage 4: Service Startup (Supervisord)

Supervisord starts all services as configured in `docker/supervisord.conf`:

#### 4.1 Supervisor Master Process
```bash
# Starts as root, then switches to ftuser for all child processes
supervisord -c /etc/supervisor/supervisord.conf
```

#### 4.2 Service Programs

**4.2.1 Freqtrade Engine**
```bash
# Program: freqtrade
Command: freqtrade trade \
  --config /freqtrade/user_data/config.prod.json \
  --logfile /freqtrade/user_data/logs/freqtrade.log

Status: Running (dry-run mode by default)
Auto-restart: Yes
Logs: /var/log/supervisor/freqtrade.log
```

**4.2.2 Demo UI (Main Service)**
```bash
# Program: demo_ui
Command: python -m freqtrade.ui.demo_server

Environment:
  FLASK_RUN_HOST=0.0.0.0
  FLASK_RUN_PORT=$DEMO_UI_PORT (10000 on Render)

Port: $PORT (Render-assigned)
Status: Running
Auto-restart: Yes
Logs: /var/log/supervisor/demo_ui.log
```

**4.2.3 Configuration Dashboard**
```bash
# Program: config_dashboard
Command: streamlit run freqtrade/ui/prod_config.py \
  --server.port $CONFIG_DASHBOARD_PORT \
  --server.address 0.0.0.0 \
  --server.headless true

Port: 8501 (internal)
Status: Running
Auto-restart: Yes
Logs: /var/log/supervisor/config_dashboard.log
Password: $STREAMLIT_PASSWORD (required)
```

**4.2.4 Monitoring Dashboard**
```bash
# Program: monitor_dashboard
Command: streamlit run freqtrade/ui/prod_monitor.py \
  --server.port $MONITOR_DASHBOARD_PORT \
  --server.address 0.0.0.0 \
  --server.headless true

Port: 8502 (internal)
Status: Running
Auto-restart: Yes
Logs: /var/log/supervisor/monitor_dashboard.log
```

### Stage 5: Health Checks

Render begins monitoring the health endpoint:

```bash
# Health check configuration (from render.yaml)
Path: /health
Interval: Every 30 seconds
Timeout: 10 seconds
Start Period: 30 seconds (grace period)

# Expected response:
HTTP 200 OK
{"status": "ok", "message": "Demo server is running"}

# If health check fails 3 times in a row:
# - Service is marked unhealthy
# - Render automatically restarts the container
```

### Stage 6: Ready for Traffic

Once healthy, Render routes traffic to your service:

```
https://your-app.onrender.com → PORT 10000 (Demo UI)
```

## Complete Startup Timeline

```
Time    Stage                           Action
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
0:00    Repository Clone                Git clone from GitHub
0:30    Docker Build Start              FROM python:3.12-slim
1:00    System Dependencies             apt-get install
2:00    Python Dependencies             pip install requirements
5:00    Application Install             pip install -e .
6:00    Image Build Complete            Final image: 1.2GB
6:30    Container Start                 docker run
6:35    Entrypoint Execution            Port config, directories
6:40    Supervisor Start                supervisord launch
6:45    Service Programs Start          All 4 services starting
7:00    Freqtrade Engine Ready          Engine running (dry-run)
7:05    Demo UI Ready                   Flask listening on PORT
7:10    Config Dashboard Ready          Streamlit on 8501
7:15    Monitor Dashboard Ready         Streamlit on 8502
7:20    Health Check Pass               /health returns 200 OK
7:30    Traffic Routing Active          Service is LIVE ✓
```

**Total time**: ~7-8 minutes for first deployment

## Configuration Files Reference

### render.yaml
**Purpose**: Defines Render service configuration  
**Location**: Root directory  
**Key Settings**:
- Service type: web
- Environment: docker
- Dockerfile path: ./Dockerfile.dev
- Docker command: supervisord -c /etc/supervisor/supervisord.conf
- Health check: /health
- Disk: 1GB at /freqtrade/user_data
- Environment variables: 10 variables with defaults

### Dockerfile.dev
**Purpose**: Builds the Docker image  
**Location**: Root directory  
**Stages**:
1. base - System setup and user creation
2. python-deps - Install Python dependencies
3. runtime - Final image with application code

### docker/entrypoint.sh
**Purpose**: Initialize environment and start services  
**Location**: docker/entrypoint.sh  
**Responsibilities**:
- Configure ports based on environment
- Create directory structure
- Generate default configuration
- Initialize database
- Fix permissions
- Display startup info
- Execute supervisord

### docker/supervisord.conf
**Purpose**: Define and manage service processes  
**Location**: docker/supervisord.conf  
**Managed Services**:
1. freqtrade - Trading engine
2. demo_ui - Flask web interface
3. config_dashboard - Streamlit config UI
4. monitor_dashboard - Streamlit monitoring UI

## Environment-Specific Behavior

### Local Development
```bash
# Ports
DEMO_UI_PORT=5000
CONFIG_DASHBOARD_PORT=8501
MONITOR_DASHBOARD_PORT=8502

# URLs
http://localhost:5000       # Demo UI
http://localhost:8501       # Config Dashboard
http://localhost:8502       # Monitor Dashboard
```

### Render Production
```bash
# Ports
DEMO_UI_PORT=$PORT (e.g., 10000)  # Render-assigned
CONFIG_DASHBOARD_PORT=8501        # Internal only
MONITOR_DASHBOARD_PORT=8502       # Internal only

# URLs
https://your-app.onrender.com     # Main service (Demo UI)
# Note: Other services accessible internally, not exposed
```

## Persistence

### What Persists Across Deployments
- ✅ `/freqtrade/user_data/config.prod.json` - Configuration
- ✅ `/freqtrade/user_data/tradesv3.sqlite` - Trade database
- ✅ `/freqtrade/user_data/logs/*.log` - Log files
- ✅ `/freqtrade/user_data/exploits/` - Custom modules
- ✅ `/freqtrade/user_data/data/` - Market data cache

### What Gets Rebuilt
- ❌ Docker image - Rebuilt on every deploy
- ❌ Python packages - Reinstalled (unless cached)
- ❌ System packages - Reinstalled
- ❌ Temporary files - Cleared

## Troubleshooting Install/Startup

### Build Failures

**Problem**: Docker build fails  
**Check**:
```bash
# View build logs in Render dashboard
# Common issues:
# - requirements.txt dependency conflicts
# - System package not available
# - Dockerfile syntax errors
```

### Startup Failures

**Problem**: Container starts but crashes  
**Check**:
```bash
# View logs in Render dashboard
# Common issues:
# - PORT not being used correctly
# - Permission issues on /freqtrade/user_data
# - Supervisor configuration errors
```

### Health Check Failures

**Problem**: Health checks failing  
**Check**:
```bash
# Verify demo UI is starting:
tail /var/log/supervisor/demo_ui.log

# Test health endpoint manually:
curl http://localhost:$PORT/health

# Common issues:
# - Flask not listening on correct port
# - Demo server crashed on startup
# - Import errors in Python code
```

## Manual Verification Commands

If you need to debug, access Render Shell and run:

```bash
# Check supervisor status
supervisorctl status

# View supervisor logs
tail -f /var/log/supervisor/supervisord.log

# View individual service logs
tail -f /var/log/supervisor/demo_ui.log
tail -f /var/log/supervisor/config_dashboard.log
tail -f /var/log/supervisor/monitor_dashboard.log
tail -f /var/log/supervisor/freqtrade.log

# Check environment variables
env | grep -E "PORT|RENDER|DRY_RUN|CAPITAL"

# Verify ports are listening
netstat -tlnp | grep -E "5000|8501|8502|$PORT"

# Test health endpoint
curl http://localhost:$DEMO_UI_PORT/health

# Check disk mount
df -h /freqtrade/user_data
ls -la /freqtrade/user_data

# Restart a service
supervisorctl restart demo_ui
supervisorctl restart config_dashboard

# Stop/start all services
supervisorctl stop all
supervisorctl start all
```

## Customizing Install/Startup

### Adding Python Packages

Edit `requirements.txt` or `pyproject.toml`:
```bash
# In requirements.txt, add:
your-package==1.0.0

# Commit and push - Render will rebuild automatically
```

### Adding System Packages

Edit `Dockerfile.dev`:
```dockerfile
# In the base stage, add to apt-get install:
RUN apt-get update && apt-get install -y \
    your-system-package \
    && apt-get clean
```

### Changing Startup Behavior

Edit `docker/entrypoint.sh`:
```bash
# Add custom initialization logic before:
exec "$@"
```

### Adding/Removing Services

Edit `docker/supervisord.conf`:
```ini
# Add new service:
[program:your_service]
command=/path/to/your/service
user=ftuser
autostart=true
autorestart=true
```

## Summary

The Render deployment follows this sequence:

1. **Build** (5-10 min): Clone → Docker build → Push image
2. **Deploy** (30 sec): Inject env vars → Mount disk → Start container
3. **Initialize** (1 min): Entrypoint → Configure ports → Create dirs → Generate config
4. **Start Services** (1 min): Supervisor → 4 programs → All running
5. **Health Check** (30 sec): Monitor /health → Pass 3 checks → Route traffic
6. **Live** (total ~8 min): Service available at https://your-app.onrender.com

All configuration is in:
- `render.yaml` - Render service definition
- `Dockerfile.dev` - Image build instructions
- `docker/entrypoint.sh` - Initialization logic
- `docker/supervisord.conf` - Service management

No manual configuration needed - everything is automated!
