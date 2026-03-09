# How to Run the Real-Time Voice Assistant

## 🎯 Three Ways to Run

### 1. 🚀 Easiest: Use Start Scripts

#### Windows
```bash
start.bat
```

#### Linux/macOS
```bash
chmod +x start.sh  # First time only
./start.sh
```

**What it does:**
- ✅ Creates virtual environment
- ✅ Installs dependencies
- ✅ Sets up configuration
- ✅ Starts the server

---

### 2. 📝 Manual: Step by Step

```bash
# 1. Create virtual environment
python -m venv .venv

# 2. Activate it
.\.venv\Scripts\Activate.ps1  # Windows PowerShell
source .venv/bin/activate      # Linux/macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure API keys
copy .env.example .env  # Windows
cp .env.example .env    # Linux/macOS
# Edit .env with your API keys

# 5. Run the server
python src/main.py
```

---

### 3. 🐳 Docker: Containerized

```bash
# Build image
docker build -t voice-assistant .

# Run container
docker run -p 8000:8000 -p 8001:8001 \
  -e WHISPER_API_KEY=your_key \
  -e GEMINI_API_KEY=your_key \
  -e ELEVENLABS_API_KEY=your_key \
  -e ELEVENLABS_VOICE_ID=your_voice_id \
  voice-assistant

# Or use docker-compose
docker-compose up -d
```

---

## 🔑 Getting API Keys

### OpenAI Whisper
1. Visit: https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the key (starts with `sk-`)

### Google Gemini
1. Visit: https://makersuite.google.com/app/apikey
2. Click "Create API key"
3. Copy the key (starts with `AI`)

### ElevenLabs
1. Visit: https://elevenlabs.io/
2. Sign up/Login
3. Go to Profile → API Keys
4. Copy your API key
5. Go to Voices → Select a voice → Copy Voice ID

---

## ✅ Verify It's Working

### 1. Check Server Output
You should see:
```
{"level": "INFO", "message": "WebSocket server starting on 0.0.0.0:8000"}
{"level": "INFO", "message": "Metrics dashboard starting on 0.0.0.0:8001"}
{"level": "INFO", "message": "Health check server starting on 0.0.0.0:8001"}
```

### 2. Test Health Endpoint
```bash
curl http://localhost:8001/health
```

Expected response:
```json
{
  "healthy": true,
  "critical_healthy": true,
  "components": {
    "asr": true,
    "llm": true,
    "tts": true
  }
}
```

### 3. Open Dashboard
```
http://localhost:8001/dashboard
```

You should see a metrics dashboard with latency statistics.

---

## 🎤 Test with Example Client

```bash
# In a new terminal
cd examples

# Install client dependencies
pip install -r requirements.txt

# Run the voice client
python voice_client.py --server ws://localhost:8000
```

---

## 📊 Available Endpoints

| Type | URL | Description |
|------|-----|-------------|
| **WebSocket** | `ws://localhost:8000` | Audio streaming endpoint |
| **Health** | `http://localhost:8001/health` | Detailed health status |
| **Ready** | `http://localhost:8001/health/ready` | Readiness probe (K8s) |
| **Live** | `http://localhost:8001/health/live` | Liveness probe (K8s) |
| **Metrics** | `http://localhost:8001/metrics` | JSON metrics API |
| **Dashboard** | `http://localhost:8001/dashboard` | HTML metrics dashboard |

---

## 🛑 Stopping the Server

### Graceful Shutdown
Press `Ctrl+C` in the terminal. The server will:
1. Stop accepting new connections
2. Complete active sessions
3. Save recordings
4. Clean up resources

### Force Stop (if needed)

**Windows:**
```powershell
Get-Process python | Stop-Process -Force
```

**Linux/macOS:**
```bash
pkill -9 python
```

---

## 🐛 Common Issues

### Issue: Port Already in Use

**Windows:**
```bash
netstat -ano | findstr :8000
taskkill /PID <process_id> /F
```

**Linux/macOS:**
```bash
lsof -i :8000
kill -9 <process_id>
```

**Or change the port:**
Edit `.env`:
```bash
WEBSOCKET_PORT=8080
METRICS_PORT=8081
```

---

### Issue: Missing API Keys

**Error:**
```
ValueError: Missing required configuration: WHISPER_API_KEY
```

**Solution:**
1. Check `.env` file exists
2. Verify all required keys are set:
   - WHISPER_API_KEY
   - GEMINI_API_KEY
   - ELEVENLABS_API_KEY
   - ELEVENLABS_VOICE_ID

---

### Issue: Import Errors

**Error:**
```
ModuleNotFoundError: No module named 'src'
```

**Solution:**
```bash
# Make sure you're in project root
cd C:\RTM  # or your project directory

# Activate virtual environment
.\.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate      # Linux/macOS

# Reinstall dependencies
pip install -r requirements.txt
```

---

### Issue: Python Version

**Error:**
```
Python 3.11+ required
```

**Solution:**
1. Check version: `python --version`
2. If < 3.11, download from: https://www.python.org/downloads/
3. Install Python 3.11 or 3.12
4. Recreate virtual environment

---

## 🧪 Running Tests

```bash
# Activate virtual environment first
.\.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate      # Linux/macOS

# Run all tests
pytest tests/ -v

# Run specific category
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/e2e/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

---

## 📝 Configuration

### Environment Variables

Create a `.env` file:

```bash
# Required
WHISPER_API_KEY=sk-...
GEMINI_API_KEY=AI...
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...

# Optional (defaults shown)
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

### YAML Configuration

Or use YAML files in `config/`:

```bash
python src/main.py --config config/development.yaml
python src/main.py --config config/production.yaml
```

---

## 📚 Documentation

- **Quick Start**: [RUNNING_LOCALLY.md](RUNNING_LOCALLY.md)
- **Detailed Guide**: [QUICKSTART_LOCAL.md](QUICKSTART_LOCAL.md)
- **API Reference**: [docs/api.md](docs/api.md)
- **Architecture**: [docs/production_architecture.md](docs/production_architecture.md)
- **Configuration**: [docs/configuration.md](docs/configuration.md)
- **Testing**: [tests/README.md](tests/README.md)
- **Troubleshooting**: [docs/troubleshooting.md](docs/troubleshooting.md)

---

## 🎯 Quick Command Reference

```bash
# Setup
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate      # Linux/macOS
pip install -r requirements.txt

# Run
python src/main.py

# Test
pytest tests/ -v

# Check
curl http://localhost:8001/health
curl http://localhost:8001/metrics

# Stop
Ctrl+C
```

---

## ✨ Success Checklist

- [ ] Python 3.11+ installed
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] API keys configured in `.env`
- [ ] Server starts without errors
- [ ] Health endpoint responds
- [ ] Dashboard accessible
- [ ] Tests passing

**All checked? You're ready to go! 🎉**

---

## 🆘 Need Help?

1. **Check logs**: Look at server output for errors
2. **Run diagnostics**: `pytest tests/unit/core/ -v`
3. **Read docs**: See documentation links above
4. **Check configuration**: Verify `.env` file
5. **Restart fresh**: Delete `.venv`, recreate, reinstall

---

## 🚀 Next Steps

1. **Try the example client**: `cd examples && python voice_client.py`
2. **View the dashboard**: http://localhost:8001/dashboard
3. **Read the architecture**: [docs/production_architecture.md](docs/production_architecture.md)
4. **Run the tests**: `pytest tests/ -v`
5. **Deploy to production**: See Docker instructions above

---

**Happy coding! 🎤✨**
