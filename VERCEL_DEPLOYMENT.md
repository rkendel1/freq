# Vercel Deployment Guide

This repository can be deployed to Vercel to provide a public demo of the Execution Engine UI.

## Quick Deploy

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/rkendel1/freq)

## Manual Setup

1. **Connect to Vercel:**
   - Go to [vercel.com](https://vercel.com)
   - Import your GitHub repository
   - Select the branch you want to deploy (e.g., `main`)

2. **Automatic Deployment:**
   - Vercel will automatically detect the `vercel.json` configuration
   - It will install dependencies from `requirements.txt` (minimal set for demo)
   - It will deploy the FastAPI app from `api/app.py`

3. **Auto-Deploy on Commit:**
   - Once connected, Vercel will automatically deploy when you push to the configured branch
   - You can also enable preview deployments for pull requests in Vercel settings

## Configuration

The `vercel.json` file configures:
- Rewrites: All requests are routed to the FastAPI app at `/api/app`
- Entry point: `api/app.py` (auto-detected by Vercel)
- Python version: Uses Vercel's default Python runtime (3.9+)
- Function settings: Can be configured in Vercel dashboard if needed (memory, max duration, etc.)

### Deployment Optimization

To keep the deployment under Vercel's 250MB limit, this repository uses several optimization strategies:

1. **`.vercelignore`** - Excludes large unnecessary files from the repository:
   - Tests directory (22MB+)
   - Build helpers with wheel files (41MB+)
   - Documentation files
   - Development tools

2. **`vercel.json` Function Exclusions** - Uses `excludeFiles` to exclude unnecessary modules from the serverless function bundle:
   - Excludes 4.2MB of freqtrade modules not needed by the API (exchange integrations, backtesting, database persistence, etc.)
   - Keeps only 568KB of essential modules (core, exploits, ui, metrics)
   - Reduces serverless function code size by 87%

3. **Minimal Dependencies** - `requirements.txt` contains only essential packages:
   - FastAPI, uvicorn (web server)
   - numpy (for market simulator)
   - pydantic, python-dateutil (utilities)
   
   Full dependencies are available in `requirements-full.txt` for local development.

4. **Conditional Imports** - Heavy dependencies (pandas, SQLAlchemy, ccxt) are imported conditionally with proper fallbacks and gracefully degrade if not available.

## What Gets Deployed

The Vercel deployment runs the **FastAPI version** of the demo server (`api/app.py`), which provides:
- Interactive demo UI at the root URL (`/`)
- All API endpoints (`/api/*`)
- Manual mode for step-by-step execution
- Automated mode with market simulation
- DSPy integration for parameter suggestions
- Exploit parameter management

**Note:** The demo uses simplified market simulation and doesn't require exchange connectivity or database persistence.

## Local Development

For full local development with all features:
```bash
# Install full dependencies
pip install -r requirements-full.txt
# or
pip install -e .[dev]

# Run the original Flask version
./start.sh
```

This runs the Flask version of the demo server at `http://127.0.0.1:5000`.

## Testing the FastAPI Version Locally

To test the Vercel-compatible FastAPI version locally:

```bash
# Install minimal dependencies (same as Vercel)
pip install -r requirements.txt

# Run with uvicorn
uvicorn api.app:app --host 127.0.0.1 --port 8000
```

Then visit `http://127.0.0.1:8000` in your browser.

## Troubleshooting

### Deployment fails with "pattern doesn't match any Serverless Functions"
- This error occurs if `vercel.json` has an incorrect `functions` configuration
- Solution: Remove the `functions` block or use correct glob patterns
- Vercel auto-detects Python files in `api/` directory
- Function settings can be configured in Vercel dashboard instead

### Deployment fails with "Serverless Function has exceeded the unzipped maximum size"
- The repository has been optimized to stay under the 250MB limit
- Ensure `.vercelignore` is present and properly configured
- Check that `requirements.txt` contains only minimal dependencies
- If you added new dependencies, verify they're not too large

### Deployment fails with "No fastapi entrypoint found"
- Make sure `vercel.json` exists in the root directory
- Make sure `api/app.py` exists
- Check that FastAPI is in `requirements.txt`

### Build errors with missing modules
- The minimal `requirements.txt` only includes essentials for the demo
- Some advanced features (like production exploits) may not work on Vercel
- For local development, use `requirements-full.txt`

### Demo UI not loading
- Check that `freqtrade/ui/templates/demo.html` exists
- Verify all imports in `api/app.py` are working
- Check browser console for errors

## Environment Variables

You can set environment variables in the Vercel dashboard if needed:
- Python version: Managed by Vercel's default runtime (typically Python 3.9+)
- Add any custom environment variables for your deployment in the Vercel dashboard

## Monitoring

- Check deployment status at [vercel.com/dashboard](https://vercel.com/dashboard)
- View logs in the Vercel dashboard
- Use the `/health` endpoint to verify the app is running

## Size Breakdown

Current deployment size breakdown (approximate, uncompressed):
- Python packages: ~50-70MB (minimal set: FastAPI, numpy, etc.)
- Source code: ~732KB (api + dspy + essential freqtrade modules)
- **Total: ~70-80MB** - Well under 250MB limit ✅

For comparison, without optimizations the deployment would be ~200-300MB+, exceeding the limit.

### What's Excluded from Deployment

The `vercel.json` configuration excludes these freqtrade modules from the serverless function:
- `freqtrade/exchange/` - Exchange integrations (2.7MB)
- `freqtrade/data/` - Data processing
- `freqtrade/optimize/` - Backtesting & optimization
- `freqtrade/persistence/` - Database models
- `freqtrade/strategy/` - Strategy framework
- `freqtrade/commands/` - CLI commands
- `freqtrade/configuration/` - Config parsing
- And 10 other directories not needed for the demo API

These exclusions are safe because:
1. The API only uses core functionality (state management, actions, exploits)
2. Excluded modules have proper import fallbacks
3. The demo doesn't require exchange connectivity or database persistence
