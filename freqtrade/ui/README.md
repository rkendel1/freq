# Demo UI - Execution Engine Flow Visualization

## Quick Access

🌐 **Live Demo:** [https://freq-0x5y.onrender.com/](https://freq-0x5y.onrender.com/) - Try it now, no installation required!

📖 **Local Setup:** See below for running locally

---

## Overview

This demo UI provides a visual, step-by-step walkthrough of how data flows through the execution engine. It demonstrates the complete journey from initial state through exploit evaluation, risk checks, execution, and final state updates.

## What This Demonstrates

The UI shows the end-to-end flow of the execution engine:

1. **Initial State** - Starting capital, positions, and system state
2. **Execution State** - Data prepared for the exploit module
3. **Action Generation** - Exploit module proposes trading actions
4. **Risk Checks** - Risk manager validates actions against limits
5. **Execution** - Approved actions are executed
6. **Final State** - Updated capital, positions, and PnL

This visualization makes it clear:
- How one component's output becomes another's input
- Where data transforms as it flows through the system
- Why certain actions are approved or rejected
- How capital moves from available to deployed and back

## Quick Start - Local Setup

### Prerequisites

Before starting the demo UI locally, ensure you have:

1. **Python 3.11+** installed
2. **Flask** web framework installed

### Step 1: Install Dependencies

From the repository root directory:

```bash
# Install Flask (required for the demo UI)
pip install flask

# Or install all dev dependencies (includes Flask)
pip install -r requirements-dev.txt
```

### Step 2: Start the Demo Server

Run the demo server using one of these methods:

**Method 1: Direct Python execution**
```bash
python -m freqtrade.ui.demo_server
```

**Method 2: Using the module directly**
```bash
cd freqtrade/ui
python demo_server.py
```

You should see output like:
```
INFO:freqtrade.ui.demo_server:Starting demo server on http://127.0.0.1:5000
 * Running on http://127.0.0.1:5000
```

### Step 3: Access the UI

Open your web browser and navigate to:

```
http://127.0.0.1:5000
```

You should see the **Execution Engine Demo** interface.

## Using the Demo UI

### Interface Overview

The demo UI has several sections:

1. **Header** - Title and description
2. **Controls** - Scenario selector and action buttons
3. **State Panel** - Real-time display of capital, positions, and statistics
4. **Flow Visualization** - Step-by-step breakdown of the current execution
5. **Execution History** - Timeline of all executed scenarios

### Available Scenarios

The demo includes several pre-configured scenarios:

| Scenario | Description | Expected Result |
|----------|-------------|-----------------|
| **💰 Profitable Trade Cycle** | **RECOMMENDED** - Complete money-making cycle: opens position, then closes with 8% profit | ✅ Shows how money is made! |
| **Open Long Position** | Opens a 10% long position | ✅ Approved and executed |
| **Open Short Position** | Opens a 15% short position | ✅ Approved and executed |
| **Multiple Positions** | Opens two positions (BTC & ETH) | ✅ Both executed |
| **Risk Rejection** | Tries to open 95% position | ❌ Rejected (exceeds limits) |
| **Close Position** | Closes an open position | ✅ If positions exist (8% profit) |
| **No Action** | Generates no actions | ℹ️ No changes to state |

**💡 To see how the system makes money:** Select "Profitable Trade Cycle" and click Execute twice:
1. First click opens a position (deploys $1,500)
2. Second click closes it with profit (returns $1,500 + ~$120)
3. Watch your capital grow from $10,000 to $10,120!

### Step-by-Step Execution

1. **Select a Scenario** from the dropdown menu
2. **Click "▶️ Execute Step"** to run the scenario
3. **Watch the Flow Visualization** appear, showing all 6 steps
4. **Review the State Panel** to see capital changes
5. **Check Execution History** to see the cumulative record

### Understanding the Flow

Each execution shows 6 detailed steps:

#### Step 1: Initial State
- Starting capital (available vs deployed)
- Number of open positions
- Current PnL

#### Step 2: Execution State
- Data package sent to exploit module
- Current symbol and price
- Available capital for new positions

#### Step 3: Actions Generated
- Actions proposed by the exploit module
- Each action shows type, symbol, size, and reason
- This is the exploit's "intent"

#### Step 4: Risk Checks
- Each action validated against risk limits
- Shows required vs available capital
- Displays approval or rejection reason
- ✅ Green = Approved | ❌ Red = Rejected

#### Step 5: Execution Results
- Only approved actions are executed
- Shows filled size and fees
- Displays any execution errors

#### Step 6: Final State
- Updated capital (available and deployed)
- Capital change from initial state
- New position count

### Reset the Demo

Click **🔄 Reset** to return to initial state:
- Capital: $10,000
- Deployed: $0
- Positions: 0
- History cleared

## Example Walkthrough

Let's walk through a complete example showing **how money is made**:

### Scenario: Profitable Trade Cycle (RECOMMENDED)

This scenario demonstrates the complete money-making flow from start to finish.

#### Part 1: Opening the Position

1. **Start**: You have $10,000 available capital
2. **Select**: "💰 Profitable Trade Cycle" scenario
3. **Execute**: Click "▶️ Execute Step" (first time)

**What happens:**

```
Initial State:
  Available: $10,000
  Deployed: $0
  Realized PnL: $0

↓ Exploit Evaluation

Action Generated:
  OPEN LONG BTC/USDT
  Size: 15% ($1,500)
  Reason: "Demo: Opening position for profitable trade cycle"

↓ Risk Check

Risk Validation:
  Required: $1,500
  Available: $10,000
  Result: ✅ APPROVED

↓ Execution

Execution Result:
  ✅ SUCCESS
  Filled: 15%
  Fees: $1.50

↓ Final State

State After Opening:
  Available: $8,500
  Deployed: $1,500
  Realized PnL: $0
  Capital Change: -$1,500 (moved to deployed)
```

**At this point:** Capital is deployed but no profit yet. This is normal!

---

#### Part 2: Closing with Profit (THIS IS WHERE WE MAKE MONEY!)

4. **Execute Again**: Click "▶️ Execute Step" (second time)

**What happens:**

```
Current State:
  Available: $8,500
  Deployed: $1,500
  Realized PnL: $0

↓ Exploit Evaluation

Action Generated:
  CLOSE LONG BTC/USDT
  Size: 100%
  Reason: "Demo: Closing position with profit - THIS IS WHERE WE MAKE MONEY!"

↓ Risk Check

Risk Validation:
  N/A (closing positions are always allowed)

↓ Execution (with simulated 8% profit)

Execution Result:
  ✅ SUCCESS
  Filled: 100%
  Fees: $1.62
  💰 PROFIT: $118.50 (8.0%)  ← THIS IS THE KEY LINE!

↓ Final State

State After Closing:
  Available: $10,118.50  ← Capital returned WITH profit!
  Deployed: $0
  Realized PnL: $118.50  ← PROFIT MADE!
  Capital Change: +$118.50 (MONEY MADE!)
```

**🎉 SUCCESS MESSAGE DISPLAYED:**
```
SUCCESS! We made money! Capital increased by $118.50
```

---

### Result Summary

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Total Capital | $10,000.00 | $10,118.50 | **+$118.50** |
| Realized PnL | $0.00 | $118.50 | **+$118.50** |
| Status | No trades | Completed 1 profitable trade | ✅ **Money Made!** |

**This is how the system makes money!** The complete cycle of:
1. Deploy capital (open position)
2. Market moves in your favor (simulated 8% gain)
3. Close position and realize profit
4. Capital returns with gains added

---

### Other Example: Open Long Position Only

1. **Start**: You have $10,000 available capital
2. **Select**: "Open Long Position" scenario
3. **Execute**: Click the Execute button

**What happens:**

```
Initial State:
  Available: $10,000
  Deployed: $0

↓ Exploit Evaluation

Action Generated:
  OPEN LONG BTC/USDT
  Size: 10% ($1,000)
  Reason: "Demo: Opening long position for visualization"

↓ Risk Check

Risk Validation:
  Required: $1,000
  Available: $10,000
  Result: ✅ APPROVED

↓ Execution

Execution Result:
  ✅ SUCCESS
  Filled: 10%
  Fees: $1.00

↓ Final State

Final State:
  Available: $9,000
  Deployed: $1,000
  Capital Change: -$1,000 (moved to deployed)
```

### Scenario: Risk Rejection

1. **Select**: "Risk Rejection (Too Large)" scenario
2. **Execute**: Click the Execute button

**What happens:**

```
Action Generated:
  OPEN LONG BTC/USDT
  Size: 95% ($9,500)
  Reason: "Demo: Large position that will be rejected by risk"

↓ Risk Check

Risk Validation:
  Required: $9,500
  Max Position Size: 20%
  Result: ❌ REJECTED
  Reason: "Position exceeds maximum size limit"

↓ No Execution

Final State:
  Unchanged (action was rejected)
```

## Running Automated Tests

The demo includes comprehensive end-to-end tests that validate the complete flow.

### Run All Demo Tests

```bash
# Install pytest if not already installed
pip install pytest

# Run the demo tests
python -m pytest tests/ui/test_demo_e2e.py -v
```

### Expected Output

```
tests/ui/test_demo_e2e.py::TestDemoEndToEnd::test_complete_flow_open_long PASSED
tests/ui/test_demo_e2e.py::TestDemoEndToEnd::test_complete_flow_risk_rejection PASSED
tests/ui/test_demo_e2e.py::TestDemoEndToEnd::test_complete_flow_multiple_positions PASSED
tests/ui/test_demo_e2e.py::TestDemoEndToEnd::test_complete_flow_no_action PASSED
tests/ui/test_demo_e2e.py::TestDemoEndToEnd::test_capital_state_transitions PASSED
tests/ui/test_demo_e2e.py::TestDemoEndToEnd::test_exploit_scenario_switching PASSED
tests/ui/test_demo_e2e.py::TestDemoIntegration::test_full_position_lifecycle PASSED
tests/ui/test_demo_e2e.py::TestDemoIntegration::test_demo_state_consistency PASSED

8 passed in 0.05s
```

### Run Specific Test

```bash
# Test only the open long flow
python -m pytest tests/ui/test_demo_e2e.py::TestDemoEndToEnd::test_complete_flow_open_long -v

# Test risk rejection
python -m pytest tests/ui/test_demo_e2e.py::TestDemoEndToEnd::test_complete_flow_risk_rejection -v
```

## API Endpoints

The demo server exposes these endpoints:

### GET /
Returns the HTML demo interface

### GET /api/state
Returns current engine state (capital, positions, statistics)

**Response:**
```json
{
  "capital": {
    "available": 10000.0,
    "deployed": 0.0,
    "pnl_realized": 0.0,
    "pnl_unrealized": 0.0
  },
  "open_trades": 0,
  "closed_trades": 0,
  "total_actions": 0,
  "successful_actions": 0,
  "failed_actions": 0
}
```

### POST /api/execute-step
Execute a scenario and return flow trace

**Request:**
```json
{
  "scenario": "open_long"
}
```

**Response:**
```json
{
  "step": 1,
  "scenario": "open_long",
  "timestamp": 1704823537,
  "flow": {
    "1_initial_state": {...},
    "2_execution_state": {...},
    "3_actions_generated": [...],
    "4_risk_checks": [...],
    "5_execution_results": [...],
    "6_final_state": {...}
  },
  "state_changes": {
    "capital_change": -1000.0,
    "deployed_change": 1000.0
  }
}
```

### POST /api/reset
Reset demo to initial state

### GET /api/history
Get execution history

## Troubleshooting

### "Module not found" error

If you see:
```
ModuleNotFoundError: No module named 'flask'
```

**Solution:** Install Flask:
```bash
pip install flask
```

### Port already in use

If you see:
```
OSError: [Errno 48] Address already in use
```

**Solution 1:** Stop the existing process on port 5000
```bash
# Find the process
lsof -ti:5000 | xargs kill -9
```

**Solution 2:** Use a different port
```bash
# Edit demo_server.py and change the port:
server.run(host="127.0.0.1", port=5001)
```

### Cannot connect to server

**Check:** Is the server running?
```bash
# You should see "Running on http://127.0.0.1:5000"
```

**Check:** Are you using the correct URL?
```
http://127.0.0.1:5000  ✅ Correct
http://localhost:5000   ✅ Also works
https://127.0.0.1:5000  ❌ Wrong (no HTTPS)
```

## Architecture

### Component Flow

```
Browser (UI)
    ↕ HTTP
Flask Server (demo_server.py)
    ↕ Function Calls
Demo Exploit (demo_exploit.py)
    ↕ Actions
Core Engine (state.py, risk.py, actions.py)
```

### Key Files

- `freqtrade/ui/demo_server.py` - Flask server and flow orchestration
- `freqtrade/ui/demo_exploit.py` - Demo exploit module with scenarios
- `freqtrade/ui/templates/demo.html` - Web interface
- `tests/ui/test_demo_e2e.py` - End-to-end tests

## Why This Demo Matters

This demo proves several key architectural principles:

1. **Intent → Execution Separation**
   - Exploits propose actions (intent)
   - Engine executes actions (execution)
   - No hidden coupling

2. **Explicit State Flow**
   - Every state transition is visible
   - Capital moves explicitly
   - No hidden mutations

3. **Risk Enforcement**
   - All actions validated before execution
   - Rejections happen early
   - Limits are enforced uniformly

4. **Testability**
   - Complete flow can be tested end-to-end
   - State is predictable and inspectable
   - No side effects

## Next Steps

After exploring the demo:

1. **Read the Code** - Check `demo_exploit.py` to see how scenarios work
2. **Run Tests** - Validate the system with automated tests
3. **Customize Scenarios** - Add your own scenarios to demo_exploit.py
4. **Build Your Exploit** - Implement the ExploitModule interface for real trading logic

## Support

For issues or questions:
- Check the main [README.md](../../README.md)
- Review [ARCHITECTURE.md](../../ARCHITECTURE.md)
- See example exploits in `freqtrade/exploits/`
