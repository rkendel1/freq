# Render.com Deployment Guide

This guide walks you through deploying the Freqtrade Execution Engine to Render.com using the containerized Docker environment.

## Prerequisites

- A [Render.com](https://render.com) account (free tier available)
- Your repository pushed to GitHub
- Basic familiarity with environment variables and Docker

## Quick Deploy

### Option 1: Deploy from Blueprint (Recommended)

1. **Fork/Clone this repository** to your GitHub account

2. **Create a new Blueprint Instance** on Render:
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New" → "Blueprint"
   - Connect your GitHub repository
   - Select this repository
   - Render will automatically detect `render.yaml`

3. **Configure Environment Variables** (optional):
   - The blueprint includes sensible defaults
   - You can override them in the Render dashboard
   - **Important**: Set `STREAMLIT_PASSWORD` for security!

4. **Deploy**:
   - Click "Apply" to deploy
   - Render will build the Docker image and deploy it
   - Wait for the service to start (first build takes 5-10 minutes)

5. **Access Your Application**:
   - Find your service URL in the Render dashboard
   - It will be: `https://your-service-name.onrender.com`
   - All dashboards are accessible through this URL

### Option 2: Manual Web Service Creation

1. **Create a new Web Service** on Render:
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New" → "Web Service"
   - Connect your GitHub repository

2. **Configure the Service**:
   - **Name**: `freqtrade-app` (or your choice)
   - **Environment**: Docker
   - **Region**: Choose your preferred region (Oregon recommended)
   - **Branch**: `main` (or your deployment branch)
   - **Dockerfile Path**: `./Dockerfile.dev`
   - **Docker Context**: `.` (root directory)
   - **Docker Command**: `supervisord -c /etc/supervisor/supervisord.conf`

3. **Set Instance Type**:
   - **Free Tier**: 512MB RAM (limited, may be slow)
   - **Starter**: 2GB RAM, 1 CPU (recommended - $7/month)
   - **Standard**: 4GB RAM, 2 CPU (for production - $25/month)

4. **Add Persistent Disk**:
   - Click "Add Disk"
   - **Name**: `user-data`
   - **Mount Path**: `/freqtrade/user_data`
   - **Size**: 1GB (sufficient for logs, config, and database)

5. **Configure Environment Variables**:
   See the [Environment Variables](#environment-variables) section below

6. **Deploy**:
   - Click "Create Web Service"
   - Render will build and deploy your application

## Environment Variables

### Required Variables

These are automatically set by Render:

- `PORT` - Main application port (provided by Render, defaults to 5000)
- `RENDER` - Flag indicating running on Render
- `RENDER_EXTERNAL_URL` - Your public URL

### Core Configuration

Set these in the Render dashboard under "Environment":

```bash
# Deployment Mode
DRY_RUN=true                    # Set to false for live trading (BE VERY CAREFUL!)

# Initial Capital
INITIAL_CAPITAL=10000.0         # Starting capital in USD

# Exchange
EXCHANGE_NAME=binance           # Exchange name (binance, hyperliquid, bybit, etc.)

# Logging
LOG_LEVEL=INFO                  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Security (IMPORTANT!)

```bash
# Configuration Dashboard Password
STREAMLIT_PASSWORD=your_secure_password_here

# CRITICAL: Always set this to protect your config dashboard!
# Generate a strong password and keep it safe
```

### Optional Advanced Settings

```bash
# Process Configuration
PROCESS_THROTTLE_SECS=5         # Seconds between exploit evaluations

# QuestDB Integration (Future Feature)
QUESTDB_ENABLED=false           # Enable QuestDB for time-series metrics
QUESTDB_HOST=questdb            # QuestDB service hostname
QUESTDB_PORT=9000               # QuestDB port

# Monitoring
MONITOR_REFRESH_INTERVAL=10     # Dashboard auto-refresh interval (seconds)
MAX_LOG_LINES=500               # Maximum log lines in dashboards
```

### Exchange API Credentials (Optional)

**WARNING**: Never commit API keys to version control!

For live trading (when `DRY_RUN=false`), you'll need to set these:

```bash
EXCHANGE_API_KEY=your_api_key_here
EXCHANGE_API_SECRET=your_api_secret_here
EXCHANGE_API_PASSPHRASE=your_passphrase_here  # Only for some exchanges (e.g., KuCoin)
```

**Best Practice**: Use Render's secret file feature or configure keys via the Configuration Dashboard after deployment.

## Accessing Your Deployment

Once deployed, your application is accessible at: `https://your-service-name.onrender.com`

### Available Services

All services run in a single container managed by supervisord:

1. **Demo UI** (Main Port)
   - URL: `https://your-service-name.onrender.com`
   - Interactive demo of the execution engine
   - Manual and automated trading modes

2. **Configuration Dashboard** (Port 8501)
   - URL: `https://your-service-name.onrender.com` (proxied)
   - Manage ExploitModules
   - Configure exchange settings
   - Set risk limits
   - **Protected by STREAMLIT_PASSWORD**

3. **Monitoring Dashboard** (Port 8502)
   - URL: `https://your-service-name.onrender.com` (proxied)
   - Real-time capital state
   - Open positions
   - PnL tracking
   - Live logs

**Note**: On Render, all dashboards are accessible through the main service URL. Render handles port mapping automatically.

## Health Checks

The deployment includes a built-in health check endpoint:

- **Endpoint**: `/health`
- **Full URL**: `https://your-service-name.onrender.com/health`
- **Expected Response**: `{"status": "ok", "message": "Demo server is running"}`

Render automatically monitors this endpoint. If it fails, the service will be restarted.

## Persistent Data

Your deployment uses Render's persistent disk feature:

- **Mount Point**: `/freqtrade/user_data`
- **Contents**:
  - `config.prod.json` - Configuration file
  - `tradesv3.sqlite` - Trade database
  - `logs/` - Application logs
  - `exploits/` - Custom ExploitModules

**Important**: Data persists across deploys and restarts!

## Deployment Workflow

### Auto-Deploy

By default, Render auto-deploys on every push to your `main` branch:

1. Push changes to GitHub
2. Render detects the push
3. Builds new Docker image
4. Deploys with zero downtime
5. Switches traffic to new version

### Manual Deploy

You can also trigger manual deploys:

1. Go to your service in Render dashboard
2. Click "Manual Deploy"
3. Select "Deploy latest commit"

### Viewing Logs

Real-time logs are available in the Render dashboard:

1. Go to your service
2. Click "Logs" tab
3. View live streaming logs from all services

Logs include:
- Supervisor startup
- Freqtrade engine logs
- Demo UI logs
- Dashboard logs
- Health check results

## Troubleshooting

### Service Won't Start

**Problem**: Service shows "Deploy failed" or crashes on startup

**Solutions**:
1. Check the Render logs for error messages
2. Verify environment variables are set correctly
3. Ensure `STREAMLIT_PASSWORD` is set (recommended)
4. Check that disk is properly mounted at `/freqtrade/user_data`

### Health Check Failing

**Problem**: Service restarts frequently due to failed health checks

**Solutions**:
1. Check logs for Python errors
2. Verify the demo UI server is starting (port 5000)
3. Ensure no port conflicts
4. Check memory usage (upgrade instance type if needed)

### Can't Access Dashboards

**Problem**: Main URL works but dashboards don't load

**Solutions**:
1. Verify all services are running: Check Render logs for supervisor status
2. Check that ports are properly configured in environment variables
3. Wait 30-60 seconds after deployment for all services to start
4. Clear browser cache and try again

### Out of Memory

**Problem**: Service crashes with memory errors

**Solutions**:
1. Upgrade from Free tier to Starter ($7/month) for 2GB RAM
2. Reduce `MAX_LOG_LINES` to use less memory
3. Disable QuestDB if enabled
4. Monitor resource usage in Render dashboard

### Database Issues

**Problem**: Trades not persisting or database corruption

**Solutions**:
1. Verify persistent disk is mounted correctly
2. Check disk space usage (1GB should be sufficient)
3. Restart the service to reset the database connection
4. If corrupted, delete `user_data/tradesv3.sqlite` (will lose trade history)

### Build Failures with Python 3.13

**Problem**: Build fails with "Read-only file system" error during Rust compilation or pydantic-core installation

**Root Cause**: Render is detecting the service as a Python app instead of a Docker service, and older pydantic versions require Rust compilation which fails in Render's Python build environment.

**Solutions**:
1. **Verify Service Configuration**: In the Render dashboard, check that:
   - Service type is set to "Docker" (not "Python")
   - Dockerfile path is set to `./Dockerfile.dev`
   - Build command is empty (or uses Docker)
   
2. **Recreate Service from Blueprint**: 
   - Delete the existing service
   - Create a new Blueprint Instance from `render.yaml`
   - This ensures Docker mode is used
   
3. **Use Updated Dependencies**: The `requirements.txt` file has been updated to use:
   - `pydantic>=2.10.0` (has pre-built wheels for Python 3.13)
   - `dspy-ai>=3.0.0` (compatible with newer pydantic)
   - These versions avoid Rust compilation issues

4. **Check Branch Configuration**: Ensure the service is deploying from the correct branch:
   - Default is `main` as specified in `render.yaml`
   - If deploying from a different branch, verify it has the updated dependencies

**Note**: Even if Render builds as a Python service, the updated `requirements.txt` should work correctly with Python 3.13 without compilation errors.

## Security Best Practices

1. **Always Set Passwords**:
   - Set `STREAMLIT_PASSWORD` to protect your configuration dashboard
   - Use strong, unique passwords

2. **Never Commit Secrets**:
   - Don't commit API keys to Git
   - Use Render's environment variables or secret files

3. **Use Dry-Run Mode**:
   - Keep `DRY_RUN=true` until you're ready for live trading
   - Test thoroughly before enabling live mode

4. **Monitor Your Deployment**:
   - Check logs regularly
   - Set up Render notifications for service issues
   - Review trade history and PnL

5. **Backup Your Data**:
   - Download your database periodically
   - Keep copies of your configuration
   - Export trade history for your records

## Cost Estimation

### Free Tier
- **Cost**: $0/month
- **Resources**: 512MB RAM, 0.1 CPU
- **Limitations**: 
  - Service sleeps after 15 minutes of inactivity
  - 750 hours/month free (shared across all services)
  - Slower performance
- **Best For**: Testing and demos

### Starter Plan
- **Cost**: $7/month
- **Resources**: 2GB RAM, 1 CPU
- **Benefits**:
  - Always on (no sleep)
  - Better performance
  - Suitable for light production use
- **Best For**: Personal use, small-scale trading

### Standard Plan
- **Cost**: $25/month
- **Resources**: 4GB RAM, 2 CPU
- **Benefits**:
  - Production-ready performance
  - Can handle higher trading volume
  - More reliable
- **Best For**: Serious trading, production deployment

### Persistent Disk
- **Cost**: $0.25/GB/month
- **Recommendation**: 1GB disk = $0.25/month

**Total Example**: Starter Plan + 1GB Disk = **$7.25/month**

## Scaling Considerations

As your trading volume grows, you may need to:

1. **Upgrade Instance Type**:
   - More RAM for more simultaneous positions
   - More CPU for faster processing

2. **Add QuestDB Service**:
   - Separate time-series database
   - Better metrics storage
   - See commented section in `render.yaml`

3. **Horizontal Scaling**:
   - Multiple instances for different exchanges
   - Separate services for different strategies
   - Load balancing (custom setup)

## Migration Path

### From Local Development

If you're currently running locally and want to migrate to Render:

1. Export your configuration:
   ```bash
   cp user_data/config.prod.json config.backup.json
   ```

2. Deploy to Render (see Quick Deploy above)

3. Once deployed, upload your configuration:
   - Use the Configuration Dashboard
   - Or manually edit via Render Shell

4. Verify in dry-run mode before going live

### From Other Cloud Providers

If migrating from AWS, GCP, Azure, etc.:

1. Export your database:
   ```bash
   cp user_data/tradesv3.sqlite tradesv3.backup.sqlite
   ```

2. Deploy to Render

3. Upload your database via Render Shell:
   ```bash
   # In Render Shell
   cd /freqtrade/user_data
   # Upload tradesv3.sqlite via SCP or paste
   ```

4. Restart the service

## Advanced Configuration

### Custom ExploitModules

To deploy custom ExploitModules:

1. Add them to your repository in `user_data/exploits/`
2. Push to GitHub
3. Render will auto-deploy

Alternatively, upload via Render Shell after deployment.

### QuestDB Integration

To enable QuestDB for time-series metrics:

1. Uncomment the QuestDB service in `render.yaml`
2. Set `QUESTDB_ENABLED=true` in environment variables
3. Redeploy

QuestDB will be available for metrics storage and analysis.

### Custom Docker Build

If you need custom Python packages:

1. Add them to `requirements.txt`
2. Push to GitHub
3. Render will rebuild with new dependencies

## Support and Resources

- **Render Documentation**: https://render.com/docs
- **Render Community**: https://community.render.com
- **Project Issues**: https://github.com/your-repo/issues
- **Architecture Guide**: See `ARCHITECTURE.md`
- **Local Development**: See `LOCAL_DEVELOPMENT.md`

## Next Steps

After successful deployment:

1. ✅ Access your deployment URL
2. ✅ Set up Configuration Dashboard password
3. ✅ Configure your exchange settings (dry-run mode)
4. ✅ Select and configure ExploitModules
5. ✅ Monitor the system in the Monitoring Dashboard
6. ✅ Review logs and trades
7. ✅ When ready, switch to live mode (carefully!)

---

**Remember**: Always test in dry-run mode first. Never deploy with live trading enabled until you've thoroughly tested your configuration!
