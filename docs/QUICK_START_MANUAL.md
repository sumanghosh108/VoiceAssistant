# Quick Start - Manual Setup

Get running in 5 minutes without Docker.

## 1. Setup Virtual Environment

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 2. Install Dependencies

```bash
pip install -r requirements.txt
```

## 3. Configure API Keys

```bash
# Copy template
cp .env.example .env

# Edit .env and add your keys:
# WHISPER_API_KEY=your_key
# GEMINI_API_KEY=your_key
# ELEVENLABS_API_KEY=your_key
# ELEVENLABS_VOICE_ID=your_voice_id
```

## 4. Run Application

**First, verify your setup (optional but recommended):**
```bash
python check_setup.py
```

**Then run the application:**
```bash
python -m src.main
```

## 5. Verify It's Working

**New terminal:**
```bash
# Test health
curl http://localhost:8001/health/live

# View dashboard
# Open browser: http://localhost:8001/dashboard
```

## 6. Test with Client

```bash
# Activate venv first
python examples/voice_client.py
```

## 7. Stop Application

Press `Ctrl+C` in the terminal running the application.

---

## Troubleshooting

### Port in use?
```bash
# Change ports in .env:
WEBSOCKET_PORT=8002
METRICS_PORT=8003
```

### Module not found?
```bash
# Make sure you're in project root
# and venv is activated (see (.venv) in prompt)
pip install -r requirements.txt
```

### API key error?
```bash
# Check .env file exists and has your keys
cat .env  # or: type .env on Windows
```

---

## Useful Commands

```bash
# View logs
python scripts/view_logs.py

# Run tests
pytest

# View metrics
curl http://localhost:8001/metrics
```

---

**Need more details?** See [MANUAL_SETUP_GUIDE.md](MANUAL_SETUP_GUIDE.md) for complete instructions.
