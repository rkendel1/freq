# DSPy UI Troubleshooting Guide

## HTTP 403 "Access Denied" Error

If you're getting an HTTP 403 error when accessing `http://127.0.0.1:5000`, this is **NOT** a bug in the code. The server is working correctly. This is an environment-specific issue on your machine.

### Common Causes and Solutions

#### 1. **Port Already in Use**
Another application might be using port 5000.

**Solution:**
```bash
# Check what's using port 5000
lsof -i :5000  # On Mac/Linux
netstat -ano | findstr :5000  # On Windows

# Kill the process or use a different port
# Edit demo_server.py and change: server.run(port=5001)
```

#### 2. **Firewall/Antivirus Blocking**
Your firewall or antivirus might be blocking localhost connections.

**Solution:**
- Temporarily disable your firewall/antivirus
- Add an exception for Python/Flask
- Check your security software's logs

#### 3. **Browser Security Settings**
Some browsers or browser extensions block localhost.

**Solution:**
- Try a different browser (Chrome, Firefox, Safari)
- Disable browser extensions
- Try incognito/private mode
- Clear browser cache and cookies

#### 4. **Proxy Settings**
System or browser proxy settings might be interfering.

**Solution:**
```bash
# Temporarily disable proxy
export HTTP_PROXY=
export HTTPS_PROXY=
```

#### 5. **Hosts File Issues**
Your `/etc/hosts` file might have incorrect localhost mapping.

**Solution:**
Check that `/etc/hosts` contains:
```
127.0.0.1   localhost
```

### Verification Steps

1. **Test the server is running:**
```bash
curl http://127.0.0.1:5000/health
```

Expected output:
```json
{"status":"ok","message":"Demo server is running"}
```

2. **Check server logs:**
Look for error messages in the terminal where you started the server.

3. **Try alternate access methods:**
```bash
# Try with curl
curl http://127.0.0.1:5000/

# Try with wget
wget http://127.0.0.1:5000/

# Try different localhost aliases
http://localhost:5000/
http://0.0.0.0:5000/
```

### Still Not Working?

If none of the above solutions work:

1. **Check Python/Flask installation:**
```bash
python --version
pip list | grep -i flask
```

2. **Run the test script:**
```bash
cd /path/to/freq
python -c "
from freqtrade.ui.demo_server import DemoServer
server = DemoServer()
print('Server initialized successfully!')
"
```

3. **Check for error details:**
```bash
# Start server with verbose logging
FLASK_DEBUG=1 python -m freqtrade.ui.demo_server
```

### It's Working!

Once you can access the UI, you should see:
- ✅ Execution Engine Demo page loads
- ✅ Controls for Manual/Automated modes
- ✅ **NEW: DSPy Advisor section at the bottom**
- ✅ Parameter controls with suggestions side-by-side

## DSPy UI Features

### What's New

The DSPy UI adds three sections at the bottom of the demo:

1. **⚙️ Current Parameters** - Adjust trading parameters with input fields
2. **💡 DSPy Suggestions** - View AI-generated parameter optimization suggestions
3. **📈 Performance Metrics** - See Sharpe ratio, win rate, capital efficiency, etc.

### How to Use

1. **Start Automated Mode:**
   - Switch to "🤖 Automated" mode
   - Select a market condition
   - Click "▶️ Start Auto"

2. **Let it trade:**
   - Wait for at least 5 trades to complete
   - DSPy needs data to generate suggestions

3. **View suggestions:**
   - Suggestions appear automatically every 5 seconds
   - Each suggestion shows:
     - Current value → Suggested value
     - Confidence level (color-coded bar)
     - Rationale explaining why

4. **Apply suggestions:**
   - Click "Apply" next to any suggestion
   - Or manually adjust parameters
   - Click "💾 Update Parameters"

### Example Workflow

```
1. Reset demo → Start with $10,000
2. Start Automated mode (Mixed market)
3. Wait for trades to execute
4. After 5+ trades, DSPy generates suggestions:
   - "Reduce position size from 0.15 to 0.12 (Low Sharpe ratio)"
   - Confidence: 85%
5. Click "Apply" → Parameters updated
6. Continue trading with optimized parameters
```

## Technical Details

### API Endpoints Added

- `GET /api/dspy/suggestions` - Get current DSPy suggestions
- `GET /api/dspy/metrics` - Get performance metrics
- `GET /api/dspy/parameters` - Get current parameter values
- `POST /api/dspy/update-parameters` - Update trading parameters
- `GET /health` - Health check endpoint

### Server Logs

Look for these log messages to verify DSPy is working:

```
INFO:dspy.advisor:DSPy Advisory Layer initialized (READ-ONLY mode)
INFO:dspy.advisor:  - Guardrails: ENABLED
INFO:demo_server:Recorded trade #1 to DSPy advisor: P&L=120.50
INFO:dspy.advisor:DSPy generated 1 suggestion(s) - LOGGED ONLY, NOT APPLIED
```

### Browser Console

Open browser dev tools (F12) and check the Console tab for:
- No JavaScript errors
- Successful API calls to `/api/dspy/*` endpoints
- Parameter update confirmations

## Support

If you're still experiencing issues after trying all troubleshooting steps:

1. Include in your report:
   - Operating system and version
   - Python version (`python --version`)
   - Flask version (`pip show flask`)
   - Browser and version
   - Complete error message from browser
   - Server console output
   - Output of `curl http://127.0.0.1:5000/health`

2. File an issue with the above information

## Success Indicators

You'll know everything is working when:

✅ Server starts without errors  
✅ Browser shows the demo UI  
✅ You can execute manual steps  
✅ Automated mode runs  
✅ DSPy section appears at bottom  
✅ Parameters can be adjusted  
✅ Suggestions appear after 5+ trades  
✅ Applying suggestions updates parameters  
✅ Metrics update in real-time  

**If you can see the "🤖 DSPy Advisor - Parameter Optimization" section, the UI is working correctly!**
