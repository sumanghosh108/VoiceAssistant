# Running Locally - Quick Guide

## 🚀 Fastest Way to Start

### Windows
```bash
# Double-click start.bat
# OR run in terminal:
start.bat
```

### Linux/macOS
```bash
# Make executable (first time only)
chmod +x start.sh

# Run
./start.sh
```

The script will:
1. ✅ Create virtual environment (if needed)
2. ✅ Install dependencies (if needed)
3. ✅ Create .env file (if needed)
4. ✅ Start the server

## 📋 Prerequisites

1. **Python 3.11+** installed
2. **API Keys** from:
   - OpenAI (Whisper)
   - Google (Gemini)
   - ElevenLabs

## 🔑 Get API Keys

### OpenAI Whisper
1. Go to https://platform.openai.com/api-keys
2. Create new API key
3. Copy the key

### Google Gemini
1. Go to https://makersuite.google.com/app/apikey
2. Create API key
3. Copy the key

### ElevenLabs
1. Go to https://elevenlabs.io/
2. Sign up/Login
3. Go to Profile → API Keys
4. Copy your API key
5. Go to Voices → Select a voice → Copy Voice ID

## ⚙️ Configuration

Edit the `.env` file with your API keys:

```bash
WHISPER_API_KEY=sk-...your-key-here
GEMINI_API_KEY=AI...your-key-here
ELEVENLABS_API_KEY=...your-key-here
ELEVENLABS_VOICE_ID=...voice-id-here
```

## ✅ Verify It's Working

### 1. Check Server Started
You should see:
```
{"level": "INFO", "message": "WebSocket server starting", ...}
{"level": "INFO", "message": "Metrics dashboard starting", ...}
```

### 2. Test Health Endpoint
Open new terminal:
```bash
curl http://localhost:8001/health
```

Should return:
```json
{
  "healthy": true,
  "critical_healthy": true,
  ...
}
```

### 3. View Dashboard
Open browser:
```
http://localhost:8001/dashboard
```

## 🎤 Test with Client

```bash
# In a new terminal
cd examples
pip install -r requirements.txt
python voice_client.py --server ws://localhost:8000
```

## 🛑 Stop Server

Press `Ctrl+C` in the terminal where server is running.

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <process_id> /F

# Linux/macOS
lsof -i :8000
kill -9 <process_id>
```

### Missing Dependencies
```bash
# Activate virtual environment
.\.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate      # Linux/macOS

# Reinstall
pip install -r requirements.txt
```

### API Key Errors
Make sure your `.env` file has all required keys:
- WHISPER_API_KEY
- GEMINI_API_KEY
- ELEVENLABS_API_KEY
- ELEVENLABS_VOICE_ID

## 📚 More Information

- **Detailed Guide**: See [QUICKSTART_LOCAL.md](QUICKSTART_LOCAL.md)
- **API Documentation**: See [docs/api.md](docs/api.md)
- **Architecture**: See [docs/production_architecture.md](docs/production_architecture.md)
- **Testing**: See [tests/README.md](tests/README.md)

## 🎯 Quick Commands

```bash
# Start server
python src/main.py

# Run tests
pytest tests/ -v

# Check health
curl http://localhost:8001/health

# View metrics
curl http://localhost:8001/metrics

# Open dashboard
start http://localhost:8001/dashboard  # Windows
open http://localhost:8001/dashboard   # macOS
```

## 📊 Endpoints

| Endpoint | URL | Description |
|----------|-----|-------------|
| WebSocket | `ws://localhost:8000` | Audio streaming |
| Health | `http://localhost:8001/health` | Detailed health status |
| Ready | `http://localhost:8001/health/ready` | Readiness probe |
| Live | `http://localhost:8001/health/live` | Liveness probe |
| Metrics | `http://localhost:8001/metrics` | JSON metrics |
| Dashboard | `http://localhost:8001/dashboard` | HTML dashboard |

## ✨ That's It!

You're now running the real-time voice assistant locally! 🎉

For more advanced usage, see the detailed documentation in [QUICKSTART_LOCAL.md](QUICKSTART_LOCAL.md).
