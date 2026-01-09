# Quick Start Script for Demo UI (Windows)
#
# This script checks dependencies and starts the demo server.
# It works with or without a virtual environment.
#

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Execution Engine Demo - Quick Start" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Check if in virtual environment
if ($env:VIRTUAL_ENV) {
    Write-Host "✓ Running in virtual environment: $env:VIRTUAL_ENV" -ForegroundColor Green
} else {
    Write-Host "ℹ️  Not in a virtual environment (this is fine for demo)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   Tip: For cleaner setup, consider using a virtual environment:" -ForegroundColor Gray
    Write-Host "   python -m venv .venv && .venv\Scripts\activate" -ForegroundColor Gray
}
Write-Host ""

# Check Python version
Write-Host "Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
Write-Host "✓ $pythonVersion" -ForegroundColor Green
Write-Host ""

# Check if Flask is installed
Write-Host "Checking Flask installation..." -ForegroundColor Yellow
try {
    $flaskVersion = python -c "import flask; print(flask.__version__)" 2>&1
    Write-Host "✓ Flask $flaskVersion installed" -ForegroundColor Green
} catch {
    Write-Host "✗ Flask not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "Installing Flask..." -ForegroundColor Yellow
    pip install flask
    Write-Host "✓ Flask installed" -ForegroundColor Green
}
Write-Host ""

# Navigate to the script directory
Set-Location $PSScriptRoot

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Starting Demo Server" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "The demo UI will be available at:" -ForegroundColor White
Write-Host ""
Write-Host "    http://127.0.0.1:5000" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host "Tip: Set `$env:FLASK_DEBUG='true' to enable debug mode" -ForegroundColor Gray
Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Start the server
python -m freqtrade.ui.demo_server
