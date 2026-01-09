# Demo UI - Quick Reference

## Starting the Demo

### Option 1: Quick Start Script (Recommended)

**Linux/Mac:**
```bash
./start_demo.sh
```

**Windows:**
```powershell
./start_demo.ps1
```

Then open: **http://127.0.0.1:5000**

### Option 2: Manual Start

```bash
# Install Flask (if not already installed)
pip install flask

# Start the server
python -m freqtrade.ui.demo_server

# Open browser to http://127.0.0.1:5000
```

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
