# Setup Guide - Real-Time Voice Assistant

This guide will walk you through setting up the Real-Time Voice Assistant development environment.

## Prerequisites

Before you begin, ensure you have:

1. **Python 3.11 or higher** installed
   - Check your version: `python --version` or `python3 --version`
   - Download from: https://www.python.org/downloads/

2. **API Keys** from the following services:
   - **OpenAI** (for Whisper ASR): https://platform.openai.com/api-keys
   - **Google AI** (for Gemini LLM): https://makersuite.google.com/app/apikey
   - **ElevenLabs** (for TTS): https://elevenlabs.io/app/settings/api-keys

3. **Git** (optional, for version control)

## Quick Setup

### Option 1: Automated Setup (Recommended)

#### On Linux/macOS:
```bash
chmod +x setup.sh
./setup.sh
```

#### On Windows:
```cmd
setup.bat
```

The setup script will:
- Create a Python virtual environment
- Install all dependencies
- Create a `.env` file from the template
- Create necessary directories

### Option 2: Manual Setup

#### Step 1: Create Virtual Environment

**Linux/macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows:**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

#### Step 2: Upgrade pip
```bash
pip install --upgrade pip
```

#### Step 3: Install Dependencies

**Core dependencies only:**
```bash
pip install -r requirements.txt
```

**With development tools (recommended for contributors):**
```bash
pip install -r requirements-dev.txt
```

#### Step 4: Configure Environment

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```bash
WHISPER_API_KEY=sk-your-openai-api-key-here
GEMINI_API_KEY=your-google-ai-api-key-here
ELEVENLABS_API_KEY=your-elevenlabs-api-key-here
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
```

#### Step 5: Create Recordings Directory
```bash
mkdir recordings
```

## Obtaining API Keys

### OpenAI (Whisper)

1. Go to https://platform.openai.com/
2. Sign up or log in
3. Navigate to API Keys section
4. Click "Create new secret key"
5. Copy the key (starts with `sk-`)
6. Add to `.env` as `WHISPER_API_KEY`

**Note:** OpenAI API usage is paid. Check pricing at https://openai.com/pricing

### Google AI (Gemini)

1. Go to https://makersuite.google.com/
2. Sign in with your Google account
3. Click "Get API Key"
4. Create a new API key or use an existing one
5. Copy the key
6. Add to `.env` as `GEMINI_API_KEY`

**Note:** Gemini API has a free tier. Check quotas at https://ai.google.dev/pricing

### ElevenLabs (TTS)

1. Go to https://elevenlabs.io/
2. Sign up or log in
3. Navigate to Profile → API Keys
4. Copy your API key
5. Add to `.env` as `ELEVENLABS_API_KEY`

**For Voice ID:**
1. Go to Voice Library: https://elevenlabs.io/app/voice-library
2. Choose a voice or use your own
3. Copy the Voice ID
4. Add to `.env` as `ELEVENLABS_VOICE_ID`

**Note:** ElevenLabs has a free tier with limited characters. Check pricing at https://elevenlabs.io/pricing

## Verifying Installation

### Check Python Environment

```bash
# Ensure virtual environment is activated
which python  # Linux/macOS
where python  # Windows

# Should point to .venv/bin/python or .venv\Scripts\python.exe
```

### Check Installed Packages

```bash
pip list
```

You should see packages like:
- websockets
- aiohttp
- pydantic
- openai
- google-generativeai
- elevenlabs

### Run Tests (if dev dependencies installed)

```bash
pytest --version
pytest
```

## Running the Application

### Start the Server

```bash
python -m src.main
```

You should see output indicating:
- WebSocket server started on port 8000
- Metrics server started on port 8001
- Health check endpoints available

### Access the Dashboard

Open your browser and navigate to:
- **Metrics Dashboard**: http://localhost:8001/dashboard
- **Health Check**: http://localhost:8001/health

### Test with a Client

The example client will be available after implementing the client module (Task 22).

## Development Workflow

### Activate Virtual Environment

Always activate the virtual environment before working:

**Linux/macOS:**
```bash
source .venv/bin/activate
```

**Windows:**
```cmd
.venv\Scripts\activate.bat
```

### Using Make Commands (Linux/macOS)

```bash
# See all available commands
make help

# Run tests
make test

# Format code
make format

# Run linters
make lint

# Run the application
make run
```

### Manual Commands (All Platforms)

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=html

# Format code
black src/ tests/
isort src/ tests/

# Lint code
flake8 src/ tests/
mypy src/

# Run application
python -m src.main
```

## Configuration Options

The `.env` file supports many configuration options. See `.env.example` for a complete list with descriptions.

### Key Configuration Sections

1. **API Keys** (required)
   - WHISPER_API_KEY
   - GEMINI_API_KEY
   - ELEVENLABS_API_KEY
   - ELEVENLABS_VOICE_ID

2. **Server Settings** (optional)
   - WEBSOCKET_HOST, WEBSOCKET_PORT
   - METRICS_HOST, METRICS_PORT

3. **Timeouts** (optional)
   - ASR_TIMEOUT, LLM_TIMEOUT, TTS_TIMEOUT

4. **Pipeline Settings** (optional)
   - AUDIO_BUFFER_DURATION_MS
   - TOKEN_BUFFER_SIZE
   - MAX_CONVERSATION_TURNS

5. **Observability** (optional)
   - ENABLE_RECORDING
   - LOG_LEVEL

## Troubleshooting

### Virtual Environment Issues

**Problem:** `python` command not found after activation

**Solution:** Use `python3` instead, or ensure Python is in your PATH

---

**Problem:** Permission denied when running setup.sh

**Solution:** Make the script executable:
```bash
chmod +x setup.sh
```

### Dependency Installation Issues

**Problem:** PyAudio installation fails

**Solution:** Install system dependencies first:

**Ubuntu/Debian:**
```bash
sudo apt-get install portaudio19-dev python3-dev
```

**macOS:**
```bash
brew install portaudio
```

**Windows:**
Download pre-built wheel from https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio

---

**Problem:** SSL certificate errors during pip install

**Solution:** Update certificates or use trusted host:
```bash
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

### API Key Issues

**Problem:** "Invalid API key" errors

**Solution:**
1. Verify the key is correctly copied (no extra spaces)
2. Check the key hasn't expired
3. Ensure you have credits/quota remaining
4. Verify the key has the correct permissions

---

**Problem:** Rate limit errors

**Solution:**
1. Check your API usage quotas
2. Implement rate limiting in your client
3. Consider upgrading your API plan

### Runtime Issues

**Problem:** Port already in use

**Solution:** Change ports in `.env`:
```bash
WEBSOCKET_PORT=8080
METRICS_PORT=8081
```

---

**Problem:** High latency

**Solution:**
1. Check your internet connection
2. Review metrics dashboard for bottlenecks
3. Adjust timeout values in `.env`
4. Check API service status

## Next Steps

After successful setup:

1. **Read the README.md** for architecture overview
2. **Review the design document** in `.kiro/specs/realtime-voice-assistant/design.md`
3. **Start implementing tasks** from `tasks.md`
4. **Run tests frequently** to ensure correctness
5. **Monitor the metrics dashboard** during development

## Getting Help

If you encounter issues:

1. Check this guide's troubleshooting section
2. Review the README.md
3. Check the project's issue tracker
4. Review API provider documentation
5. Enable DEBUG logging in `.env` for more details

## Additional Resources

- **Python asyncio**: https://docs.python.org/3/library/asyncio.html
- **WebSockets**: https://websockets.readthedocs.io/
- **OpenAI API**: https://platform.openai.com/docs
- **Google Gemini**: https://ai.google.dev/docs
- **ElevenLabs**: https://docs.elevenlabs.io/

---

Happy coding! 🎙️
