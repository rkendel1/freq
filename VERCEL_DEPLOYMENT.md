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
   - It will install dependencies from `requirements.txt`
   - It will deploy the FastAPI app from `api/app.py`

3. **Auto-Deploy on Commit:**
   - Once connected, Vercel will automatically deploy when you push to the configured branch
   - You can also enable preview deployments for pull requests in Vercel settings

## Configuration

The `vercel.json` file configures:
- Python version: 3.11
- Entry point: `api/app.py`
- Routes: All requests go to the FastAPI app

## What Gets Deployed

The Vercel deployment runs the **FastAPI version** of the demo server (`api/app.py`), which provides:
- Interactive demo UI at the root URL (`/`)
- All API endpoints (`/api/*`)
- Manual mode for step-by-step execution
- Automated mode with market simulation
- DSPy integration for parameter suggestions
- Exploit parameter management

## Local Development

For local development, you can still use:
```bash
./start.sh
```

This runs the original Flask version of the demo server at `http://127.0.0.1:5000`.

## Testing the FastAPI Version Locally

To test the Vercel-compatible FastAPI version locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Run with uvicorn
uvicorn api.app:app --host 127.0.0.1 --port 8000
```

Then visit `http://127.0.0.1:8000` in your browser.

## Troubleshooting

### Deployment fails with "No fastapi entrypoint found"
- Make sure `vercel.json` exists in the root directory
- Make sure `api/app.py` exists
- Check that FastAPI is in `requirements.txt`

### Build errors
- Check the Vercel build logs
- Ensure all dependencies are in `requirements.txt`
- Verify Python version compatibility (requires Python 3.11+)

### Demo UI not loading
- Check that `freqtrade/ui/templates/demo.html` exists
- Verify all imports in `api/app.py` are working
- Check browser console for errors

## Environment Variables

You can set environment variables in Vercel dashboard if needed:
- `FLASK_DEBUG`: Not used (this is FastAPI)
- Add any custom environment variables for your deployment

## Monitoring

- Check deployment status at [vercel.com/dashboard](https://vercel.com/dashboard)
- View logs in the Vercel dashboard
- Use the `/health` endpoint to verify the app is running
