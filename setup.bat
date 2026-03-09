@echo off
REM Setup script for Real-Time Voice Assistant (Windows)

echo.
echo 🎙️  Real-Time Voice Assistant Setup
echo ====================================
echo.

REM Check Python version
echo Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python is not installed or not in PATH
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set python_version=%%i
echo ✅ Python %python_version% detected
echo.

REM Create virtual environment
echo Creating virtual environment...
if exist ".venv" (
    echo ⚠️  Virtual environment already exists, skipping creation
) else (
    python -m venv .venv
    echo ✅ Virtual environment created
)
echo.

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat
echo ✅ Virtual environment activated
echo.

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1
echo ✅ pip upgraded
echo.

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt >nul 2>&1
echo ✅ Core dependencies installed
echo.

REM Ask about dev dependencies
set /p install_dev="Install development dependencies? (y/n) "
if /i "%install_dev%"=="y" (
    echo Installing development dependencies...
    pip install -r requirements-dev.txt >nul 2>&1
    echo ✅ Development dependencies installed
    echo.
)

REM Create .env file if it doesn't exist
if not exist ".env" (
    echo Creating .env file from template...
    copy .env.example .env >nul
    echo ✅ .env file created
    echo.
    echo ⚠️  IMPORTANT: Edit .env and add your API keys before running the application
    echo.
) else (
    echo ⚠️  .env file already exists, skipping creation
    echo.
)

REM Create recordings directory
if not exist "recordings" (
    mkdir recordings
    echo ✅ Created recordings directory
    echo.
)

echo ====================================
echo ✅ Setup complete!
echo.
echo Next steps:
echo 1. Activate the virtual environment: .venv\Scripts\activate.bat
echo 2. Edit .env and add your API keys
echo 3. Run the application: python -m src.main
echo.
echo For more information, see README.md
echo.
pause
