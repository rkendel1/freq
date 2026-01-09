#!/bin/bash
#
# Quick Start Script for Demo UI
#
# This script checks dependencies and starts the demo server.
# It works with or without a virtual environment.
#

set -e

echo "=================================================="
echo "  Execution Engine Demo - Quick Start"
echo "=================================================="
echo ""

# Check if in virtual environment
if [ -n "$VIRTUAL_ENV" ]; then
    echo "✓ Running in virtual environment: $VIRTUAL_ENV"
else
    echo "ℹ️  Not in a virtual environment (this is fine for demo)"
    echo ""
    echo "   Tip: For cleaner setup, consider using a virtual environment:"
    echo "   python3 -m venv .venv && source .venv/bin/activate"
fi
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python $python_version"
echo ""

# Check if Flask is installed
echo "Checking Flask installation..."
if python3 -c "import flask" 2>/dev/null; then
    flask_version=$(python3 -c "import flask; print(flask.__version__)")
    echo "✓ Flask $flask_version installed"
else
    echo "✗ Flask not found"
    echo ""
    echo "Installing Flask..."
    pip install flask
    echo "✓ Flask installed"
fi
echo ""

# Navigate to the correct directory
cd "$(dirname "$0")"

echo "=================================================="
echo "  Starting Demo Server"
echo "=================================================="
echo ""
echo "The demo UI will be available at:"
echo ""
echo "    http://127.0.0.1:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo "Tip: Set FLASK_DEBUG=true to enable debug mode"
echo ""
echo "=================================================="
echo ""

# Start the server
python3 -m freqtrade.ui.demo_server
