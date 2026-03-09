# Step-by-Step Running Instructions

Follow these exact steps to run the application manually.

## ✅ Step 1: Open Terminal

Open your terminal/command prompt in the project directory.

**Windows:** Right-click in the project folder → "Open in Terminal" or "Open PowerShell here"  
**Mac:** Right-click folder → "New Terminal at Folder"  
**Linux:** Right-click → "Open Terminal Here"

---

## ✅ Step 2: Activate Virtual Environment

### Windows (PowerShell or CMD):
```bash
.venv\Scripts\activate
```

### Linux/Mac:
```bash
source .venv/bin/activate
```

**✓ Success indicator:** You should see `(.venv)` at the start of your command prompt.

**If virtual environment doesn't exist:**
```bash
# Windows
python -m venv .venv

# Linux/Mac
python3 -m venv .venv
```

---

## ✅ Step 3: Install Dependencies (First Time Only)

```bash
pip install -r requirements.txt
```

**Wait for installation to complete.** You should see:
```
Successfully installed <packages>...
```

---

## ✅ Step 4: Set Up API Keys

### Check if .env file exists:
```bash
# Windows
dir .env

# Linux/Mac
ls .env
```

### If .env doesn't exist:
```bash
# Copy the example file
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

### Edit .env file:

**Windows:**
```bash
notepad .env
```

**Linux/Mac:**
```bash
nano .env
# or
vim .env
```

**Add your API keys:**
```bash
WHISPER_API_KEY=sk-your-actual-whisper-key-here
GEMINI_API_KEY=your-actual-gemini-key-here
ELEVENLABS_API_KEY=your-actual-elevenlabs-key-here
ELEVENLABS_VOICE_ID=your-actual-voice-id-here
```

**Save and close the file:**
- Notepad: File → Save, then close
- Nano: Press `Ctrl+X`, then `Y`, then `Enter`
- Vim: Press `Esc`, type `:wq`, press `Enter`

---

## ✅ Step 5: Run the Application

### First, verify your setup (recommended):
```bash
python check_setup.py
```

This will check:
- Python version
- Virtual environment
- Dependencies
- .env file
- API keys
- Required directories
- Module imports

If all checks pass, proceed to run the application.

### Run the application:
```bash
python -m src.main
```

**✓ Success indicator:** You should see output like:

```
INFO: Loading configuration...
INFO: Configuration loaded successfully
INFO: Initializing structured logger...
INFO: Logger initialized with level: INFO
INFO: Initializing system health monitor...
INFO: Creating circuit breakers...
INFO: Initializing ASR service...
INFO: Initializing LLM service...
INFO: Initializing TTS service...
INFO: Initializing metrics aggregator...
INFO: Starting metrics dashboard on 0.0.0.0:8001...
INFO: Starting health check server on 0.0.0.0:8001...
INFO: Starting WebSocket server on 0.0.0.0:8000...
INFO: ======================================
INFO: Real-Time Voice Assistant Started
INFO: ======================================
INFO: WebSocket: ws://0.0.0.0:8000
INFO: Metrics: http://0.0.0.0:8001/metrics
INFO: Dashboard: http://0.0.0.0:8001/dashboard
INFO: Health: http://0.0.0.0:8001/health
INFO: ======================================
```

**⚠️ Keep this terminal window open!** The application is now running.

---

## ✅ Step 6: Test the Application

### Open a NEW terminal window (keep the first one running!)

### Activate virtual environment in the new terminal:
```bash
# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

### Test 1: Health Check
```bash
curl http://localhost:8001/health/live
```

**Expected output:**
```json
{"status": "healthy"}
```

### Test 2: View Metrics
```bash
curl http://localhost:8001/metrics
```

**Expected output:** JSON with latency statistics

### Test 3: Open Dashboard in Browser

**Windows:**
```bash
start http://localhost:8001/dashboard
```

**Mac:**
```bash
open http://localhost:8001/dashboard
```

**Linux:**
```bash
xdg-open http://localhost:8001/dashboard
```

Or manually open your browser and go to: `http://localhost:8001/dashboard`

---

## ✅ Step 7: Run Example Client (Optional)

In the same NEW terminal (with venv activated):

```bash
python examples/voice_client.py --server ws://localhost:8000
```

**Follow the on-screen instructions** to test voice interaction.

---

## ✅ Step 8: View Logs

### In another NEW terminal:

```bash
# Activate venv first
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate

# View logs
python scripts/view_logs.py
```

**Options:**
```bash
# Show only errors
python scripts/view_logs.py --level error

# Show last 50 lines
python scripts/view_logs.py --limit 50

# Filter by component
python scripts/view_logs.py --component asr
```

---

## ✅ Step 9: Stop the Application

Go back to the FIRST terminal (where the application is running).

Press: **`Ctrl + C`**

**✓ Success indicator:** You should see:
```
INFO: Received shutdown signal
INFO: Stopping WebSocket server...
INFO: Stopping metrics server...
INFO: Cleaning up sessions...
INFO: Shutdown complete
```

---

## 🔧 Troubleshooting

### Problem: "Port 8000 already in use"

**Solution 1:** Find and stop the process using the port

**Windows:**
```bash
# Find process
netstat -ano | findstr :8000

# Kill process (replace PID with actual number)
taskkill /PID <PID> /F
```

**Linux/Mac:**
```bash
# Find process
lsof -i :8000

# Kill process (replace PID with actual number)
kill -9 <PID>
```

**Solution 2:** Change the port in `.env`:
```bash
WEBSOCKET_PORT=8002
METRICS_PORT=8003
```

---

### Problem: "ModuleNotFoundError: No module named 'src'"

**Solution:**
```bash
# Make sure you're in the project root directory
# You should see these folders: src/, tests/, config/

# Check current directory
# Windows: cd
# Linux/Mac: pwd

# If not in project root, navigate there
cd /path/to/realtime-voice-assistant

# Make sure venv is activated (see (.venv) in prompt)
# Reinstall dependencies
pip install -r requirements.txt
```

---

### Problem: "Configuration error: Missing required configuration: WHISPER_API_KEY"

**Solution:**
```bash
# Check if .env file exists
# Windows: dir .env
# Linux/Mac: ls .env

# View .env contents
# Windows: type .env
# Linux/Mac: cat .env

# Make sure it has your API keys with NO SPACES around =
# Correct:   WHISPER_API_KEY=abc123
# Wrong:     WHISPER_API_KEY = abc123

# Edit .env and fix
# Windows: notepad .env
# Linux/Mac: nano .env
```

---

### Problem: Virtual environment not activating

**Windows:**
```bash
# If you get execution policy error
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then try activating again
.venv\Scripts\activate
```

**Linux/Mac:**
```bash
# Make sure script is executable
chmod +x .venv/bin/activate

# Try activating again
source .venv/bin/activate
```

---

## 📋 Quick Command Reference

```bash
# Activate venv
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run application
python -m src.main

# Test health (in new terminal)
curl http://localhost:8001/health/live

# View logs (in new terminal)
python scripts/view_logs.py

# Run tests (in new terminal)
pytest

# Stop application
Ctrl+C
```

---

##  What's Next?

1. **Explore the API:** Check `docs/api.md`
2. **Customize configuration:** Edit `.env` file
3. **Run tests:** `pytest`
4. **Read architecture:** `docs/architecture.md`
5. **Try examples:** Check `examples/` directory

---

##  Need Help?

- Check logs: `python scripts/view_logs.py`
- View health: `curl http://localhost:8001/health`
- Read troubleshooting: `docs/troubleshooting.md`
- Check full manual: `MANUAL_SETUP_GUIDE.md`

---

**You're all set! Happy coding! 🚀**
