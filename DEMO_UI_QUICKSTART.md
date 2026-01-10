# Demo UI - Quick Reference

## Live Demo (No Installation Required)

🌐 **Try it now:** [https://freq-0x5y.onrender.com/](https://freq-0x5y.onrender.com/)

No setup needed - access the full demo UI instantly in your browser!

---

## Starting the Demo Locally

### Ultra-Quick Start (No Setup Needed)

```bash
# Install Flask (if not already installed)
pip install flask

# Run the demo
python -m freqtrade.ui.demo_server

# Open http://localhost:5000
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

Then open: **http://localhost:5000**

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

The demo shows a **6-step flow visualization** that demonstrates **how the system makes money**:

1. **Initial State** - Starting capital and positions
2. **Execution State** - Data sent to exploit module
3. **Actions Generated** - Trading actions proposed by exploit
4. **Risk Checks** - Actions validated against limits (✅ or ❌)
5. **Execution Results** - Results from executing approved actions **with profit shown**
6. **Final State** - Updated capital and positions **showing gains**

**💡 Key Feature:** The "Profitable Trade Cycle" scenario shows the complete money-making flow:
- **Step 1:** Opens a position (deploys capital)
- **Step 2:** Closes position with 8% profit (capital returns with gains)
- **Result:** You can clearly see capital increase and profit being realized!

## Available Scenarios

| Scenario | What It Does |
|----------|--------------|
| **💰 Profitable Trade Cycle** | **RECOMMENDED - Shows complete money-making flow!** Opens position, then closes it with 8% profit to demonstrate how the system makes money |
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
- **Profit Visualization** - See exactly how money is made when positions close with gains

## How to See Money Being Made

**Follow these steps to see a complete profitable trade:**

1. **Reset** - Click "🔄 Reset" to start fresh with $10,000
2. **Select "Profitable Trade Cycle"** from the dropdown (the top option)
3. **Execute Step 1** - Click "▶️ Execute Step" to open a position
   - You'll see $1,500 move from Available to Deployed capital
4. **Execute Step 2** - Click "▶️ Execute Step" again to close with profit
   - 🎉 You'll see the position close with **8% profit (~$120)**
   - Capital returns to Available **plus the profit**
   - Realized PnL shows your gains!

**Result:** Your capital is now $10,120 instead of $10,000. You made money! 💰

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

## DSPy Advisor Integration (NEW!)

The demo now includes a **DSPy Advisor UI** that provides AI-powered parameter optimization suggestions:

### Features

1. **⚙️ Current Parameters** - View and adjust trading parameters:
   - Position Size (0.01 - 0.50)
   - Profit Target (0.01 - 0.20)
   - Stop Loss (0.01 - 0.15)

2. **💡 DSPy Suggestions** - Get AI recommendations:
   - Side-by-side comparison: Current → Suggested
   - Confidence scores with color-coded bars
   - Detailed rationale for each suggestion
   - One-click "Apply" buttons

3. **📈 Performance Metrics** - Real-time tracking:
   - Sharpe Ratio
   - Win Rate
   - Capital Efficiency
   - Total Trades

### How to Use DSPy

1. **Start Automated Mode:**
   ```
   Mode: 🤖 Automated
   Market: Mixed (Realistic)
   Click "▶️ Start Auto"
   ```

2. **Wait for Data:**
   - DSPy needs at least 5 completed trades
   - Suggestions auto-refresh every 5 seconds
   - Watch metrics update in real-time

3. **Review Suggestions:**
   - Check confidence scores (higher = more reliable)
   - Read rationale to understand why
   - Compare current vs. suggested values

4. **Apply Changes:**
   - Click "Apply" next to any suggestion
   - Or manually adjust in the input fields
   - Click "💾 Update Parameters" to save

### Example Output

After 10 trades with mixed performance, DSPy might suggest:

```
Position Size: 0.15 → 0.12 (-20%)
Confidence: 85%
Rationale: Low Sharpe ratio (0.45) suggests reducing exposure
```

You can then apply this suggestion with one click!

### Screenshot

![DSPy Advisor UI](https://github.com/user-attachments/assets/6f1b5eb2-9815-4157-9f15-cb1238176cb2)

The DSPy section appears at the bottom of the demo page, showing:
- Current parameters with editable inputs
- Suggested values side-by-side
- Performance metrics dashboard
- Real-time updates as trades execute

## Why This Matters

This demo proves the architecture works as designed:

✅ **Intent ↔ Execution Separation** - Clear boundary between decision and execution  
✅ **Explicit State Flow** - No hidden mutations, all changes are visible  
✅ **Risk Enforcement** - Actions validated before execution  
✅ **Testability** - Complete end-to-end testing with predictable results  
✅ **AI-Powered Optimization** - DSPy provides intelligent parameter suggestions (NEW!)
