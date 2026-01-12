# Docker Development Environment

Modern single-container Docker setup for the Freqtrade execution engine with all services included.

## Quick Start

```bash
# Start everything
docker compose -f docker-compose.dev.yml up

# Start in background
docker compose -f docker-compose.dev.yml up -d

# Build and start
docker compose -f docker-compose.dev.yml up --build
```

## Services Included

All services run in a single container managed by supervisord:

1. **Freqtrade Engine** (dry-run mode by default)
2. **Demo UI** - Port 5000
3. **Configuration Dashboard** - Port 8501 (Streamlit)
4. **Monitoring Dashboard** - Port 8502 (Streamlit)

## Access Points

After starting the container:

- **Demo UI**: http://localhost:5000
- **Configuration Dashboard**: http://localhost:8501
- **Monitoring Dashboard**: http://localhost:8502

## Auto-Initialization

On first run, the container automatically:

✅ Creates `user_data/` directory structure  
✅ Generates default `config.prod.json`  
✅ Initializes SQLite database  
✅ Sets up logging directories  
✅ Creates helpful README files  

## Environment Variables

Configure via `docker/.env` file or command line:

### Security

```bash
STREAMLIT_PASSWORD=your_secure_password    # Protect config dashboard
```

### Core Settings

```bash
DRY_RUN=true                               # Safe mode (default)
INITIAL_CAPITAL=10000.0                    # Starting capital
EXCHANGE_NAME=binance                      # Any CCXT exchange
LOG_LEVEL=INFO                             # DEBUG|INFO|WARNING|ERROR
```

### QuestDB (Optional - Future Feature)

```bash
QUESTDB_ENABLED=false                      # Enable metrics logging
QUESTDB_HOST=questdb
QUESTDB_PORT=9000
```

## Data Persistence

All data is stored in `./user_data/` (volume-mounted):

```
user_data/
├── config.prod.json          # Main configuration
├── tradesv3.sqlite           # Trade database
├── logs/                     # Application logs
├── data/                     # Market data cache
├── exploits/                 # Custom ExploitModules
└── strategies/               # Custom strategies (if any)
```

## Custom ExploitModules

### Method 1: Copy to user_data

```bash
# Copy your modules to user_data/exploits/
cp my_exploit.py user_data/exploits/

# They'll be auto-discovered by the config dashboard
```

### Method 2: Volume Mount

Edit `docker-compose.dev.yml`:

```yaml
volumes:
  - ./user_data:/freqtrade/user_data
  - ./my_exploits:/freqtrade/custom_exploits:ro
```

## Useful Commands

### View Logs

```bash
# All services
docker compose -f docker-compose.dev.yml logs -f

# Specific service
docker compose -f docker-compose.dev.yml logs -f freqtrade-dev

# Inside container (supervisor logs)
docker compose -f docker-compose.dev.yml exec freqtrade-dev tail -f /var/log/supervisor/freqtrade.log
```

### Shell Access

```bash
# Get a shell in the running container
docker compose -f docker-compose.dev.yml exec freqtrade-dev /bin/bash

# Or for a non-running container
docker compose -f docker-compose.dev.yml run --rm freqtrade-dev /bin/bash
```

### Restart Services

```bash
# Restart everything
docker compose -f docker-compose.dev.yml restart

# Restart single service (inside container)
docker compose -f docker-compose.dev.yml exec freqtrade-dev supervisorctl restart freqtrade
docker compose -f docker-compose.dev.yml exec freqtrade-dev supervisorctl restart demo_ui
docker compose -f docker-compose.dev.yml exec freqtrade-dev supervisorctl restart config_dashboard
docker compose -f docker-compose.dev.yml exec freqtrade-dev supervisorctl restart monitor_dashboard
```

### Clean Up

```bash
# Stop and remove containers
docker compose -f docker-compose.dev.yml down

# Stop and remove with volumes (WARNING: deletes data)
docker compose -f docker-compose.dev.yml down -v

# Remove images
docker compose -f docker-compose.dev.yml down --rmi all
```

## Building

### Build Locally

```bash
# Build image
docker build -f Dockerfile.dev -t freqtrade-dev .

# Run without compose
docker run -d \
  -p 5000:5000 \
  -p 8501:8501 \
  -p 8502:8502 \
  -v $(pwd)/user_data:/freqtrade/user_data \
  -e STREAMLIT_PASSWORD=mypassword \
  -e DRY_RUN=true \
  freqtrade-dev
```

### Multi-Stage Build

The Dockerfile uses multi-stage builds:

1. **base** - System dependencies, user creation
2. **python-deps** - Build dependencies, Python packages
3. **runtime** - Final image with application code

This keeps the final image size reasonable while ensuring reproducible builds.

## Troubleshooting

### Ports Already in Use

Change port mappings in `docker-compose.dev.yml`:

```yaml
ports:
  - "5001:5000"   # Demo UI -> local 5001
  - "8503:8501"   # Config -> local 8503
  - "8504:8502"   # Monitor -> local 8504
```

### Permission Issues

```bash
# Fix permissions on user_data
sudo chown -R 1000:1000 user_data/
```

### Service Won't Start

Check supervisor status:

```bash
docker compose -f docker-compose.dev.yml exec freqtrade-dev supervisorctl status
```

View specific service logs:

```bash
docker compose -f docker-compose.dev.yml exec freqtrade-dev tail -100 /var/log/supervisor/freqtrade_err.log
```

### Config Dashboard Password Not Working

Ensure environment variable is set:

```bash
# In .env file
echo "STREAMLIT_PASSWORD=mypassword" >> docker/.env

# Or in docker-compose.dev.yml
environment:
  - STREAMLIT_PASSWORD=mypassword

# Restart
docker compose -f docker-compose.dev.yml restart
```

### Database Locked

```bash
# Stop all services accessing the database
docker compose -f docker-compose.dev.yml down

# Start again
docker compose -f docker-compose.dev.yml up
```

## QuestDB Integration (Future)

To enable QuestDB for time-series metrics:

1. Uncomment the `questdb` service in `docker-compose.dev.yml`
2. Set `QUESTDB_ENABLED=true` in environment
3. Restart: `docker compose -f docker-compose.dev.yml up -d`

QuestDB will be available at:
- REST API: http://localhost:9000
- PostgreSQL wire: localhost:8812
- InfluxDB line protocol: localhost:9009

## Development Workflow

### Hot Reload

Mount source code for live changes:

```yaml
volumes:
  - ./user_data:/freqtrade/user_data
  - ./freqtrade:/freqtrade/freqtrade:ro
```

Then restart the specific service:

```bash
docker compose -f docker-compose.dev.yml exec freqtrade-dev supervisorctl restart freqtrade
```

### Running Tests Inside Container

```bash
docker compose -f docker-compose.dev.yml exec freqtrade-dev bash -c "cd /freqtrade && pytest tests/"
```

## Resource Limits

Default limits in `docker-compose.dev.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
    reservations:
      cpus: '0.5'
      memory: 512M
```

Adjust based on your system capabilities.

## Security Considerations

⚠️ **For development/demo only** - Do not expose to public internet without:

1. Setting strong `STREAMLIT_PASSWORD`
2. Using HTTPS/TLS termination
3. Firewall rules restricting access
4. Regular security updates
5. Proper secret management (not hardcoded in compose file)

For production:
- Use separate containers for each service
- Implement proper secret management (Docker secrets, Vault, etc.)
- Enable authentication on all services
- Use reverse proxy with TLS
- Regular backups of `user_data/`

## Additional Resources

- **Main README**: [../README.md](../README.md)
- **Architecture**: [../ARCHITECTURE.md](../ARCHITECTURE.md)
- **Local Development**: [../LOCAL_DEVELOPMENT.md](../LOCAL_DEVELOPMENT.md)
- **QuestDB Integration**: [../docs/questdb.md](../docs/questdb.md)
