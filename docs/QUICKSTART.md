# Quick Start Checklist

Get the Real-Time Voice Assistant up and running in 5 minutes!

## ✅ Prerequisites Checklist

- [ ] Python 3.11+ installed (`python --version`)
- [ ] OpenAI API key (for Whisper)
- [ ] Google AI API key (for Gemini)
- [ ] ElevenLabs API key (for TTS)

## 🚀 Setup Steps

### 1. Run Setup Script

**Linux/macOS:**
```bash
chmod +x setup.sh
./setup.sh
```

**Windows:**
```cmd
setup.bat
```

### 2. Configure API Keys

Edit `.env` file and add your keys:
```bash
WHISPER_API_KEY=sk-your-key-here
GEMINI_API_KEY=your-key-here
ELEVENLABS_API_KEY=your-key-here
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
```

### 3. Activate Virtual Environment

**Linux/macOS:**
```bash
source .venv/bin/activate
```

**Windows:**
```cmd
.venv\Scripts\activate.bat
```

### 4. Run the Application

```bash
python -m src.main
```

### 5. Verify It's Running

Open in your browser:
- Dashboard: http://localhost:8001/dashboard
- Health: http://localhost:8001/health

## 📋 What You Should See

When the application starts successfully:
```
✅ Configuration loaded
✅ Services initialized
✅ WebSocket server started on 0.0.0.0:8000
✅ Metrics server started on 0.0.0.0:8001
✅ Health check endpoints available
```

## 🔧 Common Issues

### "Python not found"
- Install Python 3.11+ from python.org
- Ensure Python is in your PATH

### "Invalid API key"
- Double-check keys in `.env`
- Ensure no extra spaces
- Verify keys are active

### "Port already in use"
- Change ports in `.env`:
  ```
  WEBSOCKET_PORT=8080
  METRICS_PORT=8081
  ```

### "Module not found"
- Ensure virtual environment is activated
- Run: `pip install -r requirements.txt`

## 📚 Next Steps

1. **Read the README** - Understand the architecture
2. **Review SETUP_GUIDE** - Detailed setup information
3. **Check PROJECT_STRUCTURE** - Understand the codebase
4. **Start implementing** - Follow tasks.md

## 🧪 Development Mode

If you're developing:

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Format code
make format

# Run linters
make lint
```

## 🐳 Docker Alternative

Prefer Docker?

```bash
# Build and run
docker-compose up --build

# Access at same URLs
```

## 💡 Tips

- Keep the dashboard open to monitor latency
- Enable recording for debugging: `ENABLE_RECORDING=true`
- Use DEBUG log level for troubleshooting: `LOG_LEVEL=DEBUG`
- Check `/health` endpoint if something seems wrong

## 🆘 Need Help?

1. Check SETUP_GUIDE.md for detailed troubleshooting
2. Review the documentation in docs/
3. Check the issue tracker
4. Enable DEBUG logging for more details

---

**Ready to build?** Start with Task 2 in `.kiro/specs/realtime-voice-assistant/tasks.md`
