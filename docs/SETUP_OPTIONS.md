# Setup Options - Choose Your Path

Multiple ways to get the Real-Time Voice Assistant running. Choose the method that works best for you.

##  Quick Comparison

| Method | Time | Difficulty | Best For |
|--------|------|------------|----------|
| **Automated Scripts** | 2 min |  Easy | Quick testing |
| **Manual Setup** | 5 min |  Medium | Learning the system |
| **Docker** | 3 min |  Medium | Production deployment |

---

## Option 1: Automated Scripts (Fastest)

**Time:** ~2 minutes  
**Difficulty:**  Easy

### Windows:
```bash
start.bat
```

### Linux/Mac:
```bash
chmod +x start.sh
./start.sh
```

**What it does:**
- Creates virtual environment automatically
- Installs all dependencies
- Prompts for API keys
- Starts the server

**When to use:**
- You want to test quickly
- You're new to Python
- You don't want to deal with setup details

**Documentation:** Built-in prompts guide you through

---

## Option 2: Manual Setup (Recommended)

**Time:** ~5 minutes  
**Difficulty:**  Medium

### Quick Guide:
See [QUICK_START_MANUAL.md](QUICK_START_MANUAL.md)

### Step-by-Step Guide:
See [RUN_INSTRUCTIONS.md](RUN_INSTRUCTIONS.md)

### Complete Manual:
See [MANUAL_SETUP_GUIDE.md](MANUAL_SETUP_GUIDE.md)

**What you'll do:**
1. Create virtual environment
2. Install dependencies
3. Configure API keys
4. Run the application
5. Test and verify

**When to use:**
- You want to understand the setup
- You need to customize configuration
- You're comfortable with command line
- You want full control

**Advantages:**
- Learn how the system works
- Easy to troubleshoot
- Full control over configuration
- No Docker required

---

## Option 3: Docker (Production Ready)

**Time:** ~3 minutes  
**Difficulty:**  Medium

### Quick Start:
See [docker/DOCKER_QUICK_START.md](docker/DOCKER_QUICK_START.md)

### Complete Guide:
See [docker/README.md](docker/README.md)

**What you'll do:**
```bash
cd docker
make up          # Production
# or
make up-dev      # Development with hot-reload
```

**When to use:**
- You're deploying to production
- You want isolated environment
- You need consistent deployment
- You're familiar with Docker

**Advantages:**
- Isolated environment
- Easy deployment
- Consistent across systems
- Production-ready

---

## Detailed Guides

### For Beginners
1. Start with [QUICK_START_MANUAL.md](QUICK_START_MANUAL.md) - 5-minute setup
2. If you get stuck, check [RUN_INSTRUCTIONS.md](RUN_INSTRUCTIONS.md) - step-by-step with screenshots
3. For deep dive, read [MANUAL_SETUP_GUIDE.md](MANUAL_SETUP_GUIDE.md) - complete manual

### For Developers
1. Use [MANUAL_SETUP_GUIDE.md](MANUAL_SETUP_GUIDE.md) for full understanding
2. Check [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md) for development setup
3. Review [docs/configuration.md](docs/configuration.md) for customization

### For DevOps/Production
1. Start with [docker/DOCKER_QUICK_START.md](docker/DOCKER_QUICK_START.md)
2. Read [docker/README.md](docker/README.md) for complete Docker guide
3. Review [docs/production_architecture.md](docs/production_architecture.md)

---

## Prerequisites

All methods require:

### Required
- Python 3.11 or higher
- pip (Python package manager)
- API keys:
  - OpenAI Whisper: https://platform.openai.com/api-keys
  - Google Gemini: https://makersuite.google.com/app/apikey
  - ElevenLabs: https://elevenlabs.io/app/settings/api-keys

### Optional (for Docker)
- Docker 20.10+
- Docker Compose 2.0+

---

## What Happens After Setup?

Once running, you'll have:

1. **WebSocket Server** at `ws://localhost:8000`
   - Accepts audio input
   - Streams audio output

2. **Metrics Dashboard** at `http://localhost:8001/dashboard`
   - Real-time latency metrics
   - Performance statistics

3. **Health Endpoints**
   - Health: `http://localhost:8001/health`
   - Live: `http://localhost:8001/health/live`
   - Ready: `http://localhost:8001/health/ready`

4. **Logs** in `logs/` directory
   - Structured JSON logs
   - Timestamp-based files

---

## Testing Your Setup

After starting the application:

### 1. Health Check
```bash
curl http://localhost:8001/health/live
```
Expected: `{"status": "healthy"}`

### 2. View Dashboard
Open browser: `http://localhost:8001/dashboard`

### 3. Run Example Client
```bash
# Activate venv first
python examples/voice_client.py
```

### 4. View Logs
```bash
python scripts/view_logs.py
```

---

## Troubleshooting

### Common Issues

**Port already in use:**
- Change ports in `.env` file
- Or kill the process using the port

**Module not found:**
- Make sure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

**API key errors:**
- Check `.env` file exists
- Verify no spaces around `=` in `.env`
- Ensure keys are valid

**For detailed troubleshooting:**
- [RUN_INSTRUCTIONS.md](RUN_INSTRUCTIONS.md) - Common problems and solutions
- [MANUAL_SETUP_GUIDE.md](MANUAL_SETUP_GUIDE.md) - Comprehensive troubleshooting
- [docs/troubleshooting.md](docs/troubleshooting.md) - System-specific issues

---

## Next Steps

After successful setup:

1. **Explore the API**
   - Read [docs/api.md](docs/api.md)
   - Try example clients in `examples/`

2. **Customize Configuration**
   - Edit `.env` file
   - Check [docs/configuration.md](docs/configuration.md)

3. **Run Tests**
   ```bash
   pytest
   ```

4. **Read Documentation**
   - [docs/architecture.md](docs/architecture.md) - System design
   - [docs/HOW_TO_RUN.md](docs/HOW_TO_RUN.md) - Running guide
   - [docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) - Command reference

---

## Getting Help

1. **Check logs:** `python scripts/view_logs.py`
2. **View health:** `curl http://localhost:8001/health`
3. **Read docs:** Check `docs/` directory
4. **Review examples:** Check `examples/` directory

---

## Summary

Choose your path:

- **Just want to test?** → Use automated scripts (`start.bat` or `start.sh`)
- **Want to learn?** → Follow [RUN_INSTRUCTIONS.md](RUN_INSTRUCTIONS.md)
- **Need production?** → Use [Docker](docker/DOCKER_QUICK_START.md)

All paths lead to the same running system. Pick what works for you! 🚀
