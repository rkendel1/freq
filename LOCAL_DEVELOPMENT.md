# Local Development Guide

Complete guide for setting up and running the entire platform locally for development and testing.

## 🚀 Quick Start (Pushbutton Setup)

**Just want to get started? Run this:**

```bash
# Linux/Mac
./start.sh

# Windows
./start.ps1
```

This single command will:
- ✅ Check Python version (3.11+ required)
- ✅ Install all dependencies
- ✅ Start the demo UI server
- ✅ Open your browser to http://127.0.0.1:5000

---

## Prerequisites

### Required
- **Python 3.11 or higher** - Check with `python --version` or `python3 --version`
- **pip** - Python package installer (comes with Python)

### Optional (Recommended)
- **Virtual environment** - For isolated dependencies
- **Git** - For version control

---

## Installation Options

### Option 1: Quick Install (Recommended for First-Time Users)

This is the fastest way to get everything running:

```bash
# 1. Clone the repository (if you haven't already)
git clone https://github.com/rkendel1/freq.git
cd freq

# 2. Run the unified startup script
./start.sh          # Linux/Mac
./start.ps1         # Windows

# The script will:
# - Check Python version
# - Create virtual environment (optional)
# - Install dependencies
# - Start the demo UI
# - Open browser to http://127.0.0.1:5000
```

### Option 2: Manual Setup (For Developers)

For more control over the installation:

#### Step 1: Create Virtual Environment (Recommended)

**Linux/Mac:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows:**
```powershell
python -m venv .venv
.venv\Scripts\activate
```

You should see `(.venv)` in your terminal prompt.

#### Step 2: Install Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# For development (includes testing tools, linters, etc.)
pip install -r requirements-dev.txt
```

#### Step 3: Verify Installation

```bash
# Check freqtrade is installed
python -m freqtrade --version

# Check Flask is installed (for demo UI)
python -c "import flask; print(f'Flask {flask.__version__}')"
```

---

## Running the Platform

### Demo UI - Quick Start

**Recommended: Use the unified startup script**

```bash
./start.sh      # Linux/Mac
./start.ps1     # Windows

# Then open: http://localhost:5000
```

**Or try the live demo:** [https://freq-0x5y.onrender.com/](https://freq-0x5y.onrender.com/)

**Alternative methods:**

```bash
# Direct Python execution
python -m freqtrade.ui.demo_server

# Legacy demo-only script (still works)
./start_demo.sh     # Linux/Mac
./start_demo.ps1    # Windows
```

### Trading Bot Backend (Dry Run Mode)

To run the trading bot in dry-run mode (no real trading):

```bash
# Step 1: Create a user directory
python -m freqtrade create-userdir --userdir user_data

# Step 2: Copy example config
cp config_examples/config_quickstart.example.json user_data/config.json

# Step 3: Edit the config (optional)
# Open user_data/config.json and customize as needed
# Make sure "dry_run": true is set!

# Step 4: Run in dry-run mode
python -m freqtrade trade --config user_data/config.json

# Note: Even in dry-run mode, you may need exchange API keys
# for market data. For fully local testing, use the demo UI instead.
```

**Alternative: Use NullExploitModule for Testing**

To test the engine without any trading logic:

```bash
# Create user directory
python -m freqtrade create-userdir --userdir user_data

# Copy example config
cp config_examples/config_quickstart.example.json user_data/config.json

# Edit config to use NullExploitModule (does nothing, just runs)
# Add to config.json:
# "exploit_module": "freqtrade.exploits.exploit_module.NullExploitModule"

# Run the bot
python -m freqtrade trade --config user_data/config.json
```

This proves the execution engine is decoupled from decision-making.


### Complete Platform (Backend + UI)

Run both the backend and demo UI simultaneously:

```bash
# Use the unified startup script (starts demo UI only)
./start.sh          # Linux/Mac
./start.ps1         # Windows

# To run both backend AND demo UI, use separate terminals:

# Terminal 1: Start backend (if you have exchange API keys)
python -m freqtrade create-userdir --userdir user_data
cp config_examples/config_quickstart.example.json user_data/config.json
# Edit user_data/config.json with your exchange keys
python -m freqtrade trade --config user_data/config.json

# Terminal 2: Start demo UI
python -m freqtrade.ui.demo_server
```

**Note:** For most development and testing, the demo UI alone is sufficient. The backend is only needed when you want to:
- Connect to real exchange APIs
- Run live or dry-run trading
- Test your custom exploit modules with market data

See [examples/README.md](examples/README.md) for more backend examples.


---

## Testing Your Setup

### 1. Test Demo UI

```bash
# Start the demo server
python -m freqtrade.ui.demo_server

# In another terminal, test the API
curl http://127.0.0.1:5000/api/state

# Expected output: JSON with capital, trades, etc.
```

### 2. Run Unit Tests

```bash
# Install dev dependencies first
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run only demo UI tests
pytest tests/ui/test_demo_e2e.py -v

# Run specific test
pytest tests/ui/test_demo_e2e.py::TestDemoEndToEnd::test_complete_flow_open_long -v
```

### 3. Test Trading Bot Commands

```bash
# List available exchanges
python -m freqtrade list-exchanges

# List available strategies
python -m freqtrade list-strategies

# Show current config
python -m freqtrade show-config --config user_data/config.json
```

---

## Project Structure

```
freq/
├── freqtrade/              # Core execution engine
│   ├── core/              # Core components (state, risk, actions)
│   ├── exchange/          # Exchange connectors
│   ├── exploits/          # Exploit modules (trading logic interface)
│   ├── persistence/       # Database models
│   ├── ui/                # Demo UI
│   │   ├── demo_server.py # Flask server
│   │   └── templates/     # HTML templates
│   └── main.py            # Main entry point
├── tests/                 # Test suite
├── requirements.txt       # Core dependencies
├── requirements-dev.txt   # Development dependencies
├── start.sh              # Unified startup (Linux/Mac)
├── start.ps1             # Unified startup (Windows)
├── start_demo.sh         # Demo UI only (Linux/Mac)
└── start_demo.ps1        # Demo UI only (Windows)
```

---

## Common Tasks

### Start Fresh

```bash
# Deactivate virtual environment
deactivate

# Delete virtual environment
rm -rf .venv

# Recreate and reinstall
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### Update Dependencies

```bash
# Update all packages
pip install -r requirements.txt --upgrade

# Update specific package
pip install --upgrade flask
```

### Run Linters and Type Checks

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run ruff linter
ruff check freqtrade/

# Run mypy type checker
mypy freqtrade/
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'X'"

**Solution:** Install dependencies
```bash
pip install -r requirements.txt
# or for dev
pip install -r requirements-dev.txt
```

### "python3: command not found" (Windows)

**Solution:** Use `python` instead of `python3`
```bash
python --version
```

### "Permission denied" (Linux/Mac)

**Solution:** Make scripts executable
```bash
chmod +x start.sh start_demo.sh
```

### "Port 5000 already in use"

**Solution:** Find and kill the process
```bash
# Linux/Mac
lsof -ti:5000 | xargs kill -9

# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### "HTTP ERROR 403" or "Access Denied" when accessing 127.0.0.1:5000

**This has been fixed!** The server now runs without debug mode by default, which resolves this issue.

**Cause:** Flask 3.1.0's debug mode can cause 403 errors due to debugger PIN protection and stricter security settings.

**Solution:** The fix is already applied. The server runs in non-debug mode by default. If you still encounter this issue:
1. Make sure you're running the latest version of the code
2. Try restarting the server
3. Clear your browser cache
4. Try accessing from a different browser

**For Developers:** If you need debug mode for development, you can enable it:
```bash
# Linux/Mac
FLASK_DEBUG=true ./start.sh

# Windows PowerShell
$env:FLASK_DEBUG='true'; python -m freqtrade.ui.demo_server
```

### Virtual Environment Won't Activate (Windows)

**Solution:** Allow script execution
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.venv\Scripts\activate
```

### Demo UI Shows Errors

**Solution:** Make sure you're in the virtual environment with all dependencies
```bash
source .venv/bin/activate  # Linux/Mac
pip install -r requirements-dev.txt
python -m freqtrade.ui.demo_server
```

---

## Development Workflow

### 1. Initial Setup
```bash
git clone https://github.com/rkendel1/freq.git
cd freq
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### 2. Make Changes
Edit files in `freqtrade/` directory

### 3. Test Changes
```bash
# Run specific tests
pytest tests/ui/ -v

# Run all tests
pytest
```

### 4. Run Locally
```bash
# Test demo UI
python -m freqtrade.ui.demo_server

# Test backend
python -m freqtrade trade --config user_data/config.json
```

---

## Additional Resources

- **[README.md](README.md)** - Project overview and architecture
- **[DEMO_UI_QUICKSTART.md](DEMO_UI_QUICKSTART.md)** - Quick reference for demo UI
- **[SETUP.md](SETUP.md)** - Detailed setup options
- **[freqtrade/ui/README.md](freqtrade/ui/README.md)** - Complete demo UI documentation
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture details

---

## Getting Help

If you encounter issues:

1. Check this guide's [Troubleshooting](#troubleshooting) section
2. Check [SETUP.md](SETUP.md) for more setup options
3. Open an issue on GitHub with:
   - Your Python version (`python --version`)
   - Your OS (Windows/Linux/Mac)
   - Complete error message
   - Steps to reproduce

---

## Next Steps

After getting the platform running:

1. **Explore the Demo UI** - http://127.0.0.1:5000
   - Try different scenarios
   - Watch how data flows through the system
   - See risk checks in action

2. **Read the Architecture** - [ARCHITECTURE.md](ARCHITECTURE.md)
   - Understand the Intent → Execution separation
   - Learn about exploit modules
   - See how state flows through components

3. **Create Your Own Exploit Module**
   - See [README.md](README.md) for examples
   - Implement the `ExploitModule` interface
   - Connect your trading logic

4. **Run Backtests**
   - Download historical data
   - Test your strategy
   - Analyze results

---

**Happy trading! 🚀**
