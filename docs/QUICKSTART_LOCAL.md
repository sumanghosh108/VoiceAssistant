# Quick Start Guide - Running Locally

## Prerequisites

### Required Software
- **Python 3.11+** (Python 3.12 recommended)
- **pip** (Python package manager)
- **Git** (for cloning the repository)

### Required API Keys
You'll need API keys from these services:
1. **OpenAI Whisper API** - For speech recognition
2. **Google Gemini API** - For LLM responses
3. **ElevenLabs API** - For text-to-speech

## Step 1: Clone and Setup

```bash
# Navigate to your project directory
cd C:\RTM

# Verify you're in the right directory
dir
# You should see: src/, tests/, docs/, etc.
```

## Step 2: Create Virtual Environment

### On Windows (PowerShell)
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# If you get an execution policy error, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### On Windows (CMD)
```cmd
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate.bat
```

### On Linux/macOS
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate
```

## Step 3: Install Dependencies

```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install production dependencies
pip install -r requirements.txt

# Install development dependencies (for testing)
pip install -r requirements-dev.txt
```

## Step 4: Configure Environment Variables

### Option A: Using .env file (Recommended)

```bash
# Copy the example environment file
copy .env.example .env    # Windows
cp .env.example .env      # Linux/macOS

# Edit .env file with your API keys
notepad .env              # Windows
nano .env                 # Linux/macOS
```

Edit the `.env` file:
```bash
# Required API Keys
WHISPER_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_google_gemini_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
ELEVENLABS_VOICE_ID=your_preferred_voice_id_here

# Optional Configuration (defaults shown)
WEBSOCKET_HOST=0.0.0.0
WEBSOCKET_PORT=8000
METRICS_HOST=0.0.0.0
METRICS_PORT=8001
AUDIO_BUFFER_DURATION_MS=500
TOKEN_BUFFER_SIZE=10
MAX_CONVERSATION_TURNS=10
ENABLE_RECORDING=false
LOG_LEVEL=INFO
```

### Option B: Set Environment Variables Directly

#### Windows (PowerShell)
```powershell
$env:WHISPER_API_KEY="your_openai_api_key_here"
$env:GEMINI_API_KEY="your_google_gemini_api_key_here"
$env:ELEVENLABS_API_KEY="your_elevenlabs_api_key_here"
$env:ELEVENLABS_VOICE_ID="your_voice_id_here"
```

#### Linux/macOS
```bash
export WHISPER_API_KEY="your_openai_api_key_here"
export GEMINI_API_KEY="your_google_gemini_api_key_here"
export ELEVENLABS_API_KEY="your_elevenlabs_api_key_here"
export ELEVENLABS_VOICE_ID="your_voice_id_here"
```

## Step 5: Verify Installation

```bash
# Run tests to verify everything is set up correctly
pytest tests/unit/core/test_models.py -v

# You should see: 19 passed
```

## Step 6: Run the Application

```bash
# Start the server
python src/main.py
```

You should see output like:
```
{"timestamp": "2024-01-15T10:30:00.123Z", "level": "INFO", "message": "SessionManager initialized", ...}
{"timestamp": "2024-01-15T10:30:00.456Z", "level": "INFO", "message": "WebSocket server starting", ...}
{"timestamp": "2024-01-15T10:30:00.789Z", "level": "INFO", "message": "Metrics dashboard starting", ...}
{"timestamp": "2024-01-15T10:30:01.012Z", "level": "INFO", "message": "Health check server starting", ...}
```

## Step 7: Verify the Server is Running

### Check Health Endpoints

Open a new terminal and run:

```bash
# Check if server is alive
curl http://localhost:8001/health/live

# Check if server is ready
curl http://localhost:8001/health/ready

# Check detailed health status
curl http://localhost:8001/health
```

### View Metrics Dashboard

Open your browser and navigate to:
```
http://localhost:8001/dashboard
```

You should see a metrics dashboard with latency statistics.

### View Metrics API

```bash
# Get metrics as JSON
curl http://localhost:8001/metrics
```

## Step 8: Test with Example Client

### Install Client Dependencies

```bash
# Navigate to examples directory
cd examples

# Install client requirements
pip install -r requirements.txt
```

### Run the Example Client

```bash
# Run the voice client
python voice_client.py --server ws://localhost:8000

# Or with custom settings
python voice_client.py --server ws://localhost:8000 --sample-rate 16000
```

## Common Issues and Solutions

### Issue 1: Port Already in Use

**Error**: `Address already in use: 8000` or `8001`

**Solution**:
```bash
# Find process using the port (Windows)
netstat -ano | findstr :8000

# Kill the process (Windows)
taskkill /PID <process_id> /F

# Find process using the port (Linux/macOS)
lsof -i :8000

# Kill the process (Linux/macOS)
kill -9 <process_id>
```

Or change the port in your `.env` file:
```bash
WEBSOCKET_PORT=8080
METRICS_PORT=8081
```

### Issue 2: Missing API Keys

**Error**: `ValueError: Missing required configuration: WHISPER_API_KEY`

**Solution**: Make sure you've set all required environment variables or created a `.env` file with your API keys.

### Issue 3: Import Errors

**Error**: `ModuleNotFoundError: No module named 'src'`

**Solution**:
```bash
# Make sure you're in the project root directory
cd C:\RTM

# Make sure virtual environment is activated
.\.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate      # Linux/macOS

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue 4: Python Version

**Error**: `Python 3.11+ required`

**Solution**:
```bash
# Check your Python version
python --version

# If version is < 3.11, install Python 3.11 or 3.12
# Download from: https://www.python.org/downloads/
```

### Issue 5: Virtual Environment Not Activating

**Windows PowerShell Error**: `Execution policy error`

**Solution**:
```powershell
# Run PowerShell as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then try activating again
.\.venv\Scripts\Activate.ps1
```

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test category
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/e2e/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# View coverage report
start htmlcov/index.html  # Windows
open htmlcov/index.html   # macOS
```

### Running with Auto-Reload

For development, you can use a tool like `watchdog` to auto-reload on file changes:

```bash
# Install watchdog
pip install watchdog

# Run with auto-reload
watchmedo auto-restart --directory=./src --pattern=*.py --recursive -- python src/main.py
```

### Debugging

```bash
# Run with debug logging
LOG_LEVEL=DEBUG python src/main.py

# Run with Python debugger
python -m pdb src/main.py
```

## Configuration Options

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WHISPER_API_KEY` | Yes | - | OpenAI Whisper API key |
| `GEMINI_API_KEY` | Yes | - | Google Gemini API key |
| `ELEVENLABS_API_KEY` | Yes | - | ElevenLabs API key |
| `ELEVENLABS_VOICE_ID` | Yes | - | ElevenLabs voice ID |
| `WEBSOCKET_HOST` | No | 0.0.0.0 | WebSocket server host |
| `WEBSOCKET_PORT` | No | 8000 | WebSocket server port |
| `METRICS_HOST` | No | 0.0.0.0 | Metrics server host |
| `METRICS_PORT` | No | 8001 | Metrics server port |
| `AUDIO_BUFFER_DURATION_MS` | No | 500 | Audio buffer duration |
| `TOKEN_BUFFER_SIZE` | No | 10 | Token buffer size |
| `MAX_CONVERSATION_TURNS` | No | 10 | Max conversation history |
| `ENABLE_RECORDING` | No | false | Enable session recording |
| `LOG_LEVEL` | No | INFO | Logging level |

### YAML Configuration

You can also use YAML configuration files in the `config/` directory:

```bash
# Use development config
python src/main.py --config config/development.yaml

# Use production config
python src/main.py --config config/production.yaml
```

## Monitoring

### View Logs

Logs are output to stdout in JSON format:

```bash
# View logs in real-time
python src/main.py | jq .

# Save logs to file
python src/main.py > logs/app.log 2>&1
```

### Monitor Metrics

```bash
# Watch metrics in real-time
watch -n 1 curl -s http://localhost:8001/metrics | jq .

# Or use the dashboard
open http://localhost:8001/dashboard
```

### Check Health

```bash
# Continuous health check
while true; do curl -s http://localhost:8001/health | jq .; sleep 5; done
```

## Stopping the Server

### Graceful Shutdown

Press `Ctrl+C` in the terminal where the server is running. The server will:
1. Stop accepting new connections
2. Complete processing of active sessions
3. Save any recordings
4. Clean up resources
5. Exit

### Force Stop

If the server doesn't stop gracefully:

**Windows**:
```powershell
# Find the process
Get-Process python

# Kill the process
Stop-Process -Name python -Force
```

**Linux/macOS**:
```bash
# Find the process
ps aux | grep python

# Kill the process
kill -9 <process_id>
```

## Next Steps

1. **Read the Documentation**
   - [API Documentation](docs/api.md)
   - [Architecture Documentation](docs/architecture.md)
   - [Configuration Guide](docs/configuration.md)

2. **Try the Examples**
   - [Voice Client Example](examples/README.md)
   - [Metrics Dashboard Example](examples/metrics_dashboard_example.py)

3. **Run Tests**
   - [Test Documentation](tests/README.md)

4. **Deploy to Production**
   - [Docker Deployment](docker-compose.yml)
   - [Production Configuration](config/production.yaml)

## Getting Help

### Check Logs
```bash
# View recent logs
python src/main.py 2>&1 | tail -n 50
```

### Run Diagnostics
```bash
# Check configuration
python -c "from src.infrastructure.config import ConfigLoader; print(ConfigLoader.load())"

# Check imports
python -c "import src; print('OK')"

# Check dependencies
pip list
```

### Common Commands Reference

```bash
# Activate virtual environment
.\.venv\Scripts\Activate.ps1  # Windows PowerShell
.venv\Scripts\activate.bat     # Windows CMD
source .venv/bin/activate      # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Run server
python src/main.py

# Run tests
pytest tests/ -v

# Check health
curl http://localhost:8001/health

# View metrics
curl http://localhost:8001/metrics

# Stop server
Ctrl+C
```

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│              Real-Time Voice Assistant                   │
│                  Quick Reference                         │
└─────────────────────────────────────────────────────────┘

Setup:
  1. python -m venv .venv
  2. .\.venv\Scripts\Activate.ps1
  3. pip install -r requirements.txt
  4. copy .env.example .env (edit with API keys)

Run:
  python src/main.py

Endpoints:
  WebSocket:  ws://localhost:8000
  Health:     http://localhost:8001/health
  Metrics:    http://localhost:8001/metrics
  Dashboard:  http://localhost:8001/dashboard

Test:
  pytest tests/ -v

Stop:
  Ctrl+C

Help:
  See QUICKSTART_LOCAL.md for detailed instructions
```

## Success Checklist

- [ ] Python 3.11+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed
- [ ] API keys configured in .env file
- [ ] Tests passing (`pytest tests/unit/core/ -v`)
- [ ] Server starts without errors
- [ ] Health endpoint responds (`curl http://localhost:8001/health`)
- [ ] Metrics dashboard accessible (http://localhost:8001/dashboard)
- [ ] Example client can connect

If all items are checked, you're ready to use the voice assistant! 🎉
