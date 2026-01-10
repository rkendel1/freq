# Render Deployment Guide

This guide explains how the Freq demo UI is deployed on Render.

## Live Demo

🌐 **Live URL:** [https://freq-0x5y.onrender.com/](https://freq-0x5y.onrender.com/)

## Deployment Configuration

The demo server is configured to work seamlessly with Render's deployment requirements:

### Environment Variables

The application reads the following environment variables:

- **`PORT`** - The port to bind to (provided by Render automatically)
  - Default: `5000`
  - Render sets this automatically to their assigned port
  
- **`HOST`** - The host address to bind to
  - Default: `0.0.0.0` (binds to all interfaces, required for Render)
  - This allows Render to route external traffic to the application
  
- **`FLASK_DEBUG`** - Enable/disable Flask debug mode
  - Default: `false`
  - Set to `true`, `1`, or `yes` to enable
  - **Note:** Debug mode should be disabled in production

### Network Binding

The application binds to `0.0.0.0` by default, which is required for cloud deployments like Render. This allows external traffic to reach the application.

**Key difference from local development:**
- **Local development:** Can use `127.0.0.1` (localhost only)
- **Render deployment:** Must use `0.0.0.0` (all interfaces)

### Port Configuration

Render automatically assigns a port and sets the `PORT` environment variable. The application will:
1. Check for `PORT` environment variable
2. Fall back to port `5000` if not set

## Render Setup

To deploy your own instance on Render:

1. **Create a new Web Service** on [Render](https://render.com/)

2. **Connect your repository**
   - Link to your GitHub repository
   - Select the branch to deploy

3. **Configure the service:**
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python3 -m freqtrade.ui.demo_server`
   - **Environment:** Python 3.11 or higher

4. **Environment Variables (Optional):**
   - `FLASK_DEBUG=false` (recommended for production)
   - `PORT` and `HOST` are automatically configured

5. **Deploy!**
   - Render will automatically deploy on every push to your branch
   - The service will be available at `https://<your-service-name>.onrender.com/`

## Health Check

The demo server includes a health check endpoint at `/health` that returns:

```json
{
  "status": "ok",
  "message": "Demo server is running"
}
```

You can use this endpoint for Render's health checks or monitoring.

## Local Testing for Render Compatibility

To test the Render deployment configuration locally:

```bash
# Simulate Render's environment
PORT=10000 HOST=0.0.0.0 python3 -m freqtrade.ui.demo_server
```

The server will start on `http://0.0.0.0:10000`, accessible via:
- `http://localhost:10000`
- `http://127.0.0.1:10000`
- Your local IP address on port 10000

## Troubleshooting

### "No open ports detected on 0.0.0.0"

This error occurs when the application binds to `127.0.0.1` instead of `0.0.0.0`. 

**Solution:** The application now defaults to `0.0.0.0`. If you see this error, ensure:
1. You're using the latest version of `demo_server.py`
2. The `HOST` environment variable is not set to `127.0.0.1`

### Port Binding Issues

If the application fails to start:
1. Check Render logs for port conflicts
2. Ensure `PORT` environment variable is being read correctly
3. Verify the application logs show: `Starting demo server on http://0.0.0.0:<PORT>`

### Performance Considerations

Render's free tier has limitations:
- Services may spin down after inactivity
- First request after spin-down may be slow (cold start)
- Consider upgrading to a paid tier for production use

## Monitoring

Monitor your Render deployment:
- **Render Dashboard:** View logs, metrics, and deployment status
- **Health Endpoint:** `GET /health` for programmatic health checks
- **Application Logs:** Check for INFO messages from the demo server

## Security Notes

For production deployments:
1. **Always disable debug mode** (`FLASK_DEBUG=false`)
2. Consider adding authentication for production use
3. Use HTTPS (Render provides this automatically)
4. Review Flask security best practices
5. Consider using a production WSGI server (e.g., Gunicorn) instead of Flask's built-in server

## Migration from Localhost

If migrating from local development:
- Update any hardcoded `http://127.0.0.1:5000` references to use the Render URL
- The application automatically detects the environment
- No code changes needed in the demo server itself

## Related Documentation

- [README.md](README.md) - General project overview
- [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md) - Local development setup
- [DEMO_UI_QUICKSTART.md](DEMO_UI_QUICKSTART.md) - Demo UI user guide
- [Render Documentation](https://render.com/docs) - Official Render docs
