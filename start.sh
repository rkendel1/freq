#!/bin/bash
#
# Unified Startup Script for Freq Platform
#
# This script provides a complete "pushbutton" setup and startup experience.
# It handles dependency installation and starts the demo UI server.
#

set -e

echo "=========================================================="
echo "  MYCELIUM - Unified Startup"
echo "=========================================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Navigate to script directory
cd "$(dirname "$0")"

# Function to print colored output
print_status() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check Python version
print_status "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.11 or higher."
    exit 1
fi

python_version=$(python3 --version 2>&1 | awk '{print $2}')
python_major=$(echo $python_version | cut -d. -f1)
python_minor=$(echo $python_version | cut -d. -f2)

if [ "$python_major" -lt 3 ] || ([ "$python_major" -eq 3 ] && [ "$python_minor" -lt 11 ]); then
    print_error "Python 3.11 or higher is required. Found: Python $python_version"
    exit 1
fi

print_success "Python $python_version detected"
echo ""

# Check if in virtual environment
if [ -n "$VIRTUAL_ENV" ]; then
    print_success "Running in virtual environment: $VIRTUAL_ENV"
    echo ""
else
    print_warning "Not in a virtual environment"
    echo ""
    echo "  For a cleaner setup, consider using a virtual environment:"
    echo "    ${BLUE}python3 -m venv .venv${NC}"
    echo "    ${BLUE}source .venv/bin/activate${NC}"
    echo ""
    
    # Ask if user wants to create venv
    read -p "  Create and activate virtual environment now? (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Creating virtual environment..."
        python3 -m venv .venv
        print_success "Virtual environment created"
        
        print_status "Activating virtual environment..."
        source .venv/bin/activate
        print_success "Virtual environment activated"
        echo ""
    fi
fi

# Check and install dependencies
print_status "Checking dependencies..."
echo ""

# Check if requirements are already satisfied
if python3 -c "import flask, sqlalchemy, pydantic" 2>/dev/null; then
    print_success "Core dependencies already installed"
else
    print_warning "Some dependencies are missing"
    print_status "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
    print_success "Core dependencies installed"
fi
echo ""

# Check Flask specifically (needed for demo UI)
if python3 -c "import flask" 2>/dev/null; then
    flask_version=$(python3 -c "import flask; print(flask.__version__)")
    print_success "Flask $flask_version installed"
else
    print_status "Installing Flask for demo UI..."
    pip install flask
    print_success "Flask installed"
fi
echo ""

# Final verification
print_status "Verifying installation..."
if python3 -c "import freqtrade; import flask; import sqlalchemy; import pydantic" 2>/dev/null; then
    print_success "All core components verified"
else
    print_error "Installation verification failed"
    echo ""
    echo "  Please try manually installing dependencies:"
    echo "    ${BLUE}pip install -r requirements.txt${NC}"
    echo "    ${BLUE}pip install flask${NC}"
    exit 1
fi
echo ""

# Display startup information
echo "=========================================================="
echo "  Starting Platform"
echo "=========================================================="
echo ""
print_status "Demo UI will be available at:"
echo ""
echo "    ${GREEN}http://127.0.0.1:5000${NC}"
echo ""
print_warning "Press Ctrl+C to stop the server"
echo ""
echo "  For backend trading bot, see: ${BLUE}LOCAL_DEVELOPMENT.md${NC}"
echo "  To enable debug mode: ${BLUE}FLASK_DEBUG=true ./start.sh${NC}"
echo ""
echo "=========================================================="
echo ""

# Start the demo server
print_status "Starting demo UI server..."
echo ""
python3 -m freqtrade.ui.demo_server
