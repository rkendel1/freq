# Platform Setup Guide

This guide explains the different ways to set up and run the platform, including the demo UI.

## TL;DR - Quick Setup Options

### Option 1: Direct Installation (Recommended for Demo UI)
```bash
# Install dependencies and run demo
pip install flask
python -m freqtrade.ui.demo_server
# Open http://127.0.0.1:5000
```

### Option 2: Virtual Environment (Recommended for Development)
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements-dev.txt

# Run demo
python -m freqtrade.ui.demo_server
```

### Option 3: Docker (For Production/Isolated Environment)
```bash
# Build and run with Docker
docker-compose up -d
```

---

## Detailed Setup Instructions

### Do You Need a Virtual Environment?

**For the Demo UI:** ❌ **Not required** (but recommended)
- The demo UI only needs Flask
- Can install directly: `pip install flask`
- Run with: `python -m freqtrade.ui.demo_server`

**For Development:** ✅ **Recommended**
- Isolates dependencies from system Python
- Prevents conflicts with other projects
- Easy to reset if something goes wrong

**For Production Trading:** ✅✅ **Strongly Recommended**
- Use Docker (even better isolation)
- Or use virtual environment for clean dependency management

### Setup Method Comparison

| Method | When to Use | Pros | Cons |
|--------|-------------|------|------|
| **Direct Install** | Quick demo | Fastest setup | May conflict with system packages |
| **Virtual Environment** | Development | Clean, isolated, easy to manage | Need to activate each session |
| **Docker** | Production, isolation | Complete isolation, reproducible | Larger footprint, slower startup |
| **Automated Setup Script** | First time setup | Handles everything | Interactive prompts |

---

## Method 1: Direct Installation (Quickest)

### For Demo UI Only

```bash
# Install just Flask
pip install flask

# Run the demo
python -m freqtrade.ui.demo_server

# Open browser
# http://127.0.0.1:5000
```

### For Full Platform

```bash
# Install all dependencies
pip install -r requirements.txt

# For development (includes testing tools)
pip install -r requirements-dev.txt

# Run demo
python -m freqtrade.ui.demo_server
```

**Pros:**
- ✅ Fastest to get started
- ✅ No extra setup needed
- ✅ Perfect for trying the demo

**Cons:**
- ❌ May conflict with system Python packages
- ❌ Harder to clean up
- ❌ Not recommended for production

---

## Method 2: Virtual Environment (Recommended)

### Step 1: Create Virtual Environment

**Linux/Mac:**
```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# You'll see (.venv) in your prompt
```

**Windows:**
```powershell
# Create virtual environment
python -m venv .venv

# Activate it
.venv\Scripts\activate

# You'll see (.venv) in your prompt
```

### Step 2: Install Dependencies

```bash
# For demo UI only
pip install flask

# For full development
pip install -r requirements-dev.txt

# Or for just the core platform
pip install -r requirements.txt
```

### Step 3: Run the Demo

```bash
# Method 1: Use the startup script
./start_demo.sh      # Linux/Mac
./start_demo.ps1     # Windows

# Method 2: Run directly
python -m freqtrade.ui.demo_server

# Open browser to http://127.0.0.1:5000
```

### Deactivating the Virtual Environment

```bash
# When you're done
deactivate
```

**Pros:**
- ✅ Clean dependency isolation
- ✅ Easy to reset (just delete .venv and recreate)
- ✅ No conflicts with system packages
- ✅ Industry best practice

**Cons:**
- ⚠️ Must activate each time you open a new terminal
- ⚠️ Slightly more setup than direct install

---

## Method 3: Automated Setup Script

The repository includes setup scripts that handle everything automatically.

### Linux/Mac

```bash
# Run the setup script
./setup.sh

# Follow the prompts:
# - Creates .venv automatically
# - Installs dependencies
# - Sets up the platform

# After setup, activate the environment
source .venv/bin/activate

# Run the demo
python -m freqtrade.ui.demo_server
```

### Windows

```powershell
# Run the setup script
./setup.ps1

# Follow the prompts
# Then activate and run demo
```

**What the script does:**
1. Checks for Python 3.11+
2. Creates `.venv` directory
3. Installs pip/wheel/setuptools
4. Asks what dependencies you want
5. Installs everything automatically

**Pros:**
- ✅ Handles everything automatically
- ✅ Creates virtual environment for you
- ✅ Checks for proper Python version
- ✅ Installs only what you need

**Cons:**
- ⚠️ Interactive prompts (can't fully automate)
- ⚠️ May install more than needed for just demo

---

## Method 4: Docker (Production/Isolation)

### Using Docker Compose (Easiest)

```bash
# Start the platform
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the platform
docker-compose down
```

### Using Docker Directly

```bash
# Build the image
docker build -t freqtrade .

# Run the container
docker run -d --name freqtrade freqtrade

# For the demo UI (not in standard Docker setup)
# You'll need to expose port 5000 and install Flask
docker run -p 5000:5000 -it freqtrade bash
pip install flask
python -m freqtrade.ui.demo_server --host 0.0.0.0
```

**Pros:**
- ✅ Complete isolation from host system
- ✅ Reproducible environment
- ✅ Easy to deploy to servers
- ✅ All dependencies containerized

**Cons:**
- ❌ Larger footprint (~1GB+)
- ❌ Slower startup
- ❌ Demo UI requires custom setup
- ❌ More complex to customize

---

## Running the Demo UI

After setup using any method above:

### Quick Start

```bash
# If you have a virtual environment, activate it first
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Method 1: Use the startup script
./start_demo.sh      # Linux/Mac (checks dependencies)
./start_demo.ps1     # Windows (checks dependencies)

# Method 2: Run directly
python -m freqtrade.ui.demo_server

# Open browser
# http://127.0.0.1:5000
```

### Verify It's Working

```bash
# Test the API
curl http://127.0.0.1:5000/api/state

# Should return JSON with capital, trades, etc.
```

---

## Recommended Setup by Use Case

### Just Trying the Demo UI
```bash
pip install flask
python -m freqtrade.ui.demo_server
```
**No virtual environment needed. Quickest way to see the demo.**

### Development Work
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m freqtrade.ui.demo_server
```
**Use virtual environment to keep things clean.**

### Running Tests
```bash
source .venv/bin/activate  # If using venv
pip install -r requirements-dev.txt
python -m pytest tests/ui/test_demo_e2e.py -v
```

### Production Trading
```bash
# Use Docker
docker-compose up -d

# Or use virtual environment with strict dependency pinning
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'flask'"
```bash
# Solution: Install Flask
pip install flask

# Or install all dev dependencies
pip install -r requirements-dev.txt
```

### "python3: command not found"
```bash
# Try just 'python'
python --version

# If version is 3.11+, use 'python' instead of 'python3'
```

### Virtual Environment Won't Activate (Linux/Mac)
```bash
# Make sure to use 'source'
source .venv/bin/activate

# Not just:
.venv/bin/activate  # This won't work
```

### Virtual Environment Won't Activate (Windows)
```powershell
# You may need to allow script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then activate
.venv\Scripts\activate
```

### Port 5000 Already in Use
```bash
# Find what's using port 5000
lsof -i :5000  # Linux/Mac
netstat -ano | findstr :5000  # Windows

# Either stop that process or edit demo_server.py to use different port
```

---

## Summary

### Quick Decision Tree

**Do you just want to see the demo?**
→ Direct install: `pip install flask && python -m freqtrade.ui.demo_server`

**Are you developing or contributing?**
→ Virtual environment: Create `.venv`, activate, install deps

**Are you deploying to production?**
→ Docker: Use `docker-compose up -d`

**First time setting up everything?**
→ Automated script: `./setup.sh` (creates venv for you)

### What Gets Installed

**Minimal (Demo UI only):**
- Flask 3.1.0

**Full Development:**
- All core dependencies (pandas, numpy, SQLAlchemy, etc.)
- Testing tools (pytest, etc.)
- Development tools (ruff, mypy, etc.)
- Flask for demo UI

**Complete Platform:**
- Core dependencies
- Optional: hyperopt, plotting, freqai
- Exchange connectors (ccxt)
- All utilities

---

## Next Steps

After setup, see:
- **[DEMO_UI_QUICKSTART.md](DEMO_UI_QUICKSTART.md)** - Quick reference for demo
- **[freqtrade/ui/README.md](freqtrade/ui/README.md)** - Complete demo documentation
- **[README.md](README.md)** - Platform overview

**Happy trading! 🚀**
