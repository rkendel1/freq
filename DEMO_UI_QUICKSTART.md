# Demo UI - Quick Reference

## Starting the Demo

### Ultra-Quick Start (No Setup Needed)

```bash
# Install Flask (if not already installed)
pip install flask

# Run the demo
python -m freqtrade.ui.demo_server

# Open http://127.0.0.1:5000
```

**That's it!** No virtual environment, Docker, or complex setup required for the demo.

### Using the Startup Scripts (Recommended)

**Linux/Mac:**
```bash
./start_demo.sh
```

**Windows:**
```powershell
./start_demo.ps1
```

The scripts automatically:
- ✅ Check if you're in a virtual environment (optional, not required)
- ✅ Check Python version
- ✅ Install Flask if needed
- ✅ Start the server

Then open: **http://127.0.0.1:5000**

## Do I Need a Virtual Environment?

**Short answer:** ❌ **No, not for the demo UI**

**Longer answer:**
- For **demo only**: Direct install is fine
- For **development**: Virtual environment recommended
- For **production**: Use Docker or virtual environment

See **[SETUP.md](SETUP.md)** for complete setup guide covering:
- Virtual environment setup (when and why)
- Docker setup
- Different installation methods
- Troubleshooting

## What You'll See

The demo shows a **6-step flow visualization**:

1. **Initial State** - Starting capital and positions
2. **Execution State** - Data sent to exploit module
3. **Actions Generated** - Trading actions proposed by exploit
4. **Risk Checks** - Actions validated against limits (✅ or ❌)
5. **Execution Results** - Results from executing approved actions
6. **Final State** - Updated capital and positions

## Available Scenarios

| Scenario | What It Does |
|----------|--------------|
| Open Long Position | Opens 10% long position (✅ approved) |
| Open Short Position | Opens 15% short position (✅ approved) |
| Multiple Positions | Opens 2 positions simultaneously |
| Risk Rejection | Tries 95% position (should be rejected) |
| Close Position | Closes existing position |
| No Action | Generates no actions |

## Key Features

- **Real-time State Display** - See capital, positions, and PnL update instantly
- **Step-by-Step Flow** - Watch data transform through each component
- **Execution History** - Complete timeline of all actions
- **Interactive** - Select scenarios and execute step-by-step

## Running Tests

```bash
# Run all demo tests
python -m pytest tests/ui/test_demo_e2e.py -v

# Or run directly without pytest
python -c "
from tests.ui.test_demo_e2e import TestDemoEndToEnd
test = TestDemoEndToEnd()
test.test_complete_flow_open_long()
print('✓ Tests passed!')
"
```

## Full Documentation

See [freqtrade/ui/README.md](freqtrade/ui/README.md) for complete documentation including:
- Detailed setup instructions
- API endpoints
- Troubleshooting
- Architecture details
- Example walkthroughs

## Why This Matters

This demo proves the architecture works as designed:

✅ **Intent ↔ Execution Separation** - Clear boundary between decision and execution  
✅ **Explicit State Flow** - No hidden mutations, all changes are visible  
✅ **Risk Enforcement** - Actions validated before execution  
✅ **Testability** - Complete end-to-end testing with predictable results
