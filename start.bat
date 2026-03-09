@echo off
REM Quick start script for Windows

echo ========================================
echo Real-Time Voice Assistant
echo ========================================
echo.

REM Check if virtual environment exists
if not exist ".venv" (
    echo [1/5] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        echo Make sure Python 3.11+ is installed
        pause
        exit /b 1
    )
) else (
    echo [1/5] Virtual environment found
)

REM Activate virtual environment
echo [2/5] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

REM Check if dependencies are installed
echo [3/5] Checking dependencies...
python -c "import aiohttp" 2>nul
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
) else (
    echo Dependencies already installed
)

REM Check if .env file exists
echo [4/5] Checking configuration...
if not exist ".env" (
    echo WARNING: .env file not found
    echo Creating .env from .env.example...
    copy .env.example .env
    echo.
    echo IMPORTANT: Please edit .env file with your API keys before running!
    echo Press any key to open .env file...
    pause >nul
    notepad .env
    echo.
    echo After saving your API keys, press any key to continue...
    pause >nul
)

REM Start the server
echo [5/5] Starting server...
echo.
echo ========================================
echo Server starting...
echo WebSocket: ws://localhost:8000
echo Health:    http://localhost:8001/health
echo Metrics:   http://localhost:8001/metrics
echo Dashboard: http://localhost:8001/dashboard
echo ========================================
echo.
echo Press Ctrl+C to stop the server
echo.

python src/main.py

REM If server exits with error
if errorlevel 1 (
    echo.
    echo ERROR: Server exited with error
    echo Check the error messages above
    pause
)
