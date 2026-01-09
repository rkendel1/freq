# Unified Startup Script for Freq Platform (Windows)
#
# This script provides a complete "pushbutton" setup and startup experience.
# It handles dependency installation and starts the demo UI server.
#

# Set error action preference
$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Freq Platform - Unified Startup" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# Navigate to script directory
Set-Location $PSScriptRoot

# Function to print colored output
function Print-Status {
    param($message)
    Write-Host "==> $message" -ForegroundColor Blue
}

function Print-Success {
    param($message)
    Write-Host "✓ $message" -ForegroundColor Green
}

function Print-Warning {
    param($message)
    Write-Host "⚠ $message" -ForegroundColor Yellow
}

function Print-Error {
    param($message)
    Write-Host "✗ $message" -ForegroundColor Red
}

# Check Python version
Print-Status "Checking Python installation..."
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Print-Error "Python is not installed or not in PATH"
        Write-Host ""
        Write-Host "  Please install Python 3.11 or higher from:" -ForegroundColor Yellow
        Write-Host "  https://www.python.org/downloads/" -ForegroundColor Cyan
        exit 1
    }
    
    $versionMatch = $pythonVersion -match "Python (\d+)\.(\d+)\.(\d+)"
    if ($versionMatch) {
        $majorVersion = [int]$matches[1]
        $minorVersion = [int]$matches[2]
        
        if ($majorVersion -lt 3 -or ($majorVersion -eq 3 -and $minorVersion -lt 11)) {
            Print-Error "Python 3.11 or higher is required. Found: $pythonVersion"
            exit 1
        }
        
        Print-Success "Python $($matches[1]).$($matches[2]).$($matches[3]) detected"
    }
} catch {
    Print-Error "Failed to check Python version"
    exit 1
}
Write-Host ""

# Check if in virtual environment
if ($env:VIRTUAL_ENV) {
    Print-Success "Running in virtual environment: $env:VIRTUAL_ENV"
    Write-Host ""
} else {
    Print-Warning "Not in a virtual environment"
    Write-Host ""
    Write-Host "  For a cleaner setup, consider using a virtual environment:" -ForegroundColor Gray
    Write-Host "    python -m venv .venv" -ForegroundColor Blue
    Write-Host "    .venv\Scripts\activate" -ForegroundColor Blue
    Write-Host ""
    
    # Ask if user wants to create venv
    $response = Read-Host "  Create and activate virtual environment now? (y/N)"
    if ($response -match '^[Yy]$') {
        Print-Status "Creating virtual environment..."
        python -m venv .venv
        Print-Success "Virtual environment created"
        
        Print-Status "Activating virtual environment..."
        & .\.venv\Scripts\activate
        Print-Success "Virtual environment activated"
        Write-Host ""
    }
}

# Check and install dependencies
Print-Status "Checking dependencies..."
Write-Host ""

# Check if requirements are already satisfied
try {
    $null = python -c "import flask, sqlalchemy, pydantic" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Print-Success "Core dependencies already installed"
    } else {
        throw "Dependencies missing"
    }
} catch {
    Print-Warning "Some dependencies are missing"
    Print-Status "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
    Print-Success "Core dependencies installed"
}
Write-Host ""

# Check Flask specifically (needed for demo UI)
try {
    $null = python -c "import flask" 2>&1
    if ($LASTEXITCODE -eq 0) {
        $flaskVersion = python -c "import flask; print(flask.__version__)"
        Print-Success "Flask $flaskVersion installed"
    } else {
        throw "Flask missing"
    }
} catch {
    Print-Status "Installing Flask for demo UI..."
    pip install flask
    Print-Success "Flask installed"
}
Write-Host ""

# Final verification
Print-Status "Verifying installation..."
try {
    $null = python -c "import freqtrade; import flask; import sqlalchemy; import pydantic" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Print-Success "All core components verified"
    } else {
        throw "Verification failed"
    }
} catch {
    Print-Error "Installation verification failed"
    Write-Host ""
    Write-Host "  Please try manually installing dependencies:" -ForegroundColor Yellow
    Write-Host "    pip install -r requirements.txt" -ForegroundColor Blue
    Write-Host "    pip install flask" -ForegroundColor Blue
    exit 1
}
Write-Host ""

# Display startup information
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Starting Platform" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""
Print-Status "Demo UI will be available at:"
Write-Host ""
Write-Host "    http://127.0.0.1:5000" -ForegroundColor Green
Write-Host ""
Print-Warning "Press Ctrl+C to stop the server"
Write-Host ""
Write-Host "  For backend trading bot, see: LOCAL_DEVELOPMENT.md" -ForegroundColor Gray
Write-Host "  To enable debug mode: `$env:FLASK_DEBUG='true'; python -m freqtrade.ui.demo_server" -ForegroundColor Blue
Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# Start the demo server
Print-Status "Starting demo UI server..."
Write-Host ""
python -m freqtrade.ui.demo_server
