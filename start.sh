#!/bin/bash
# Quick start script for Linux/macOS

set -e  # Exit on error

echo "========================================"
echo "Real-Time Voice Assistant"
echo "========================================"
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "[1/5] Creating virtual environment..."
    python3 -m venv .venv
else
    echo "[1/5] Virtual environment found"
fi

# Activate virtual environment
echo "[2/5] Activating virtual environment..."
source .venv/bin/activate

# Check if dependencies are installed
echo "[3/5] Checking dependencies..."
if ! python -c "import aiohttp" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
else
    echo "Dependencies already installed"
fi

# Check if .env file exists
echo "[4/5] Checking configuration..."
if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo ""
    echo "IMPORTANT: Please edit .env file with your API keys before running!"
    echo "Opening .env file..."
    ${EDITOR:-nano} .env
    echo ""
    echo "After saving your API keys, press Enter to continue..."
    read
fi

# Start the server
echo "[5/5] Starting server..."
echo ""
echo "========================================"
echo "Server starting..."
echo "WebSocket: ws://localhost:8000"
echo "Health:    http://localhost:8001/health"
echo "Metrics:   http://localhost:8001/metrics"
echo "Dashboard: http://localhost:8001/dashboard"
echo "========================================"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python src/main.py

# If server exits with error
if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Server exited with error"
    echo "Check the error messages above"
    read -p "Press Enter to exit..."
fi
