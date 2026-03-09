# Quick Reference Card

```
╔═══════════════════════════════════════════════════════════════════╗
║           Real-Time Voice Assistant - Quick Reference             ║
╚═══════════════════════════════════════════════════════════════════╝

┌───────────────────────────────────────────────────────────────────┐
│ 🚀 QUICK START                                                    │
└───────────────────────────────────────────────────────────────────┘

  Windows:        start.bat
  Linux/macOS:    ./start.sh

┌───────────────────────────────────────────────────────────────────┐
│ 📋 MANUAL SETUP                                                   │
└───────────────────────────────────────────────────────────────────┘

  1. python -m venv .venv
  2. .\.venv\Scripts\Activate.ps1  (Windows)
     source .venv/bin/activate     (Linux/macOS)
  3. pip install -r requirements.txt
  4. copy .env.example .env  (edit with API keys)
  5. python src/main.py

┌───────────────────────────────────────────────────────────────────┐
│ 🔑 API KEYS NEEDED                                                │
└───────────────────────────────────────────────────────────────────┘

  OpenAI:      https://platform.openai.com/api-keys
  Gemini:      https://makersuite.google.com/app/apikey
  ElevenLabs:  https://elevenlabs.io/app/settings/api-keys

┌───────────────────────────────────────────────────────────────────┐
│ 📊 ENDPOINTS                                                      │
└───────────────────────────────────────────────────────────────────┘

  WebSocket:   ws://localhost:8000
  Health:      http://localhost:8001/health
  Ready:       http://localhost:8001/health/ready
  Live:        http://localhost:8001/health/live
  Metrics:     http://localhost:8001/metrics
  Dashboard:   http://localhost:8001/dashboard

┌───────────────────────────────────────────────────────────────────┐
│ 🧪 TESTING                                                        │
└───────────────────────────────────────────────────────────────────┘

  All tests:        pytest tests/ -v
  Unit tests:       pytest tests/unit/ -v
  Integration:      pytest tests/integration/ -v
  E2E:              pytest tests/e2e/ -v
  Performance:      pytest tests/performance/ -v
  With coverage:    pytest tests/ --cov=src --cov-report=html

┌───────────────────────────────────────────────────────────────────┐
│ 🔍 VERIFICATION                                                   │
└───────────────────────────────────────────────────────────────────┘

  Check health:     curl http://localhost:8001/health
  View metrics:     curl http://localhost:8001/metrics
  Open dashboard:   start http://localhost:8001/dashboard

┌───────────────────────────────────────────────────────────────────┐
│ 🛑 STOP SERVER                                                    │
└───────────────────────────────────────────────────────────────────┘

  Graceful:         Ctrl+C
  Force (Windows):  taskkill /F /IM python.exe
  Force (Linux):    pkill -9 python

┌───────────────────────────────────────────────────────────────────┐
│ 🐛 TROUBLESHOOTING                                                │
└───────────────────────────────────────────────────────────────────┘

  Port in use:
    Windows:  netstat -ano | findstr :8000
              taskkill /PID <pid> /F
    Linux:    lsof -i :8000
              kill -9 <pid>

  Import errors:
    - Check you're in project root
    - Activate virtual environment
    - Reinstall: pip install -r requirements.txt

  Missing API keys:
    - Check .env file exists
    - Verify all keys are set

┌───────────────────────────────────────────────────────────────────┐
│ 📁 PROJECT STRUCTURE                                              │
└───────────────────────────────────────────────────────────────────┘

  src/
    ├── core/              # Domain models and events
    ├── infrastructure/    # Config, logging, resilience
    ├── services/          # ASR, LLM, TTS integrations
    ├── observability/     # Health, metrics, latency
    ├── session/           # Session management
    └── api/               # WebSocket and HTTP

  tests/
    ├── unit/              # Unit tests (mirrors src/)
    ├── integration/       # Integration tests
    ├── e2e/               # End-to-end tests
    ├── performance/       # Performance tests
    └── fixtures/          # Shared test fixtures

┌───────────────────────────────────────────────────────────────────┐
│ 📚 DOCUMENTATION                                                  │
└───────────────────────────────────────────────────────────────────┘

  Quick Start:      RUNNING_LOCALLY.md
  Detailed Guide:   QUICKSTART_LOCAL.md
  How to Run:       HOW_TO_RUN.md
  API Reference:    docs/api.md
  Architecture:     docs/production_architecture.md
  Configuration:    docs/configuration.md
  Testing:          tests/README.md
  Troubleshooting:  docs/troubleshooting.md

┌───────────────────────────────────────────────────────────────────┐
│ 🎯 COMMON COMMANDS                                                │
└───────────────────────────────────────────────────────────────────┘

  # Activate venv
  .\.venv\Scripts\Activate.ps1  # Windows PowerShell
  .venv\Scripts\activate.bat     # Windows CMD
  source .venv/bin/activate      # Linux/macOS

  # Install deps
  pip install -r requirements.txt

  # Run server
  python src/main.py

  # Run tests
  pytest tests/ -v

  # Check health
  curl http://localhost:8001/health

  # View logs with formatting
  python src/main.py | jq .

  # Run with debug logging
  LOG_LEVEL=DEBUG python src/main.py

┌───────────────────────────────────────────────────────────────────┐
│ 🐳 DOCKER                                                         │
└───────────────────────────────────────────────────────────────────┘

  Build:   docker build -t voice-assistant .
  Run:     docker run -p 8000:8000 -p 8001:8001 \
             -e WHISPER_API_KEY=... \
             -e GEMINI_API_KEY=... \
             -e ELEVENLABS_API_KEY=... \
             -e ELEVENLABS_VOICE_ID=... \
             voice-assistant
  Compose: docker-compose up -d

┌───────────────────────────────────────────────────────────────────┐
│ ✅ SUCCESS CHECKLIST                                              │
└───────────────────────────────────────────────────────────────────┘

  □ Python 3.11+ installed
  □ Virtual environment created
  □ Dependencies installed
  □ API keys in .env file
  □ Server starts without errors
  □ Health endpoint responds (200 OK)
  □ Dashboard accessible
  □ Tests passing

┌───────────────────────────────────────────────────────────────────┐
│ 🎤 EXAMPLE CLIENT                                                 │
└───────────────────────────────────────────────────────────────────┘

  cd examples
  pip install -r requirements.txt
  python voice_client.py --server ws://localhost:8000

┌───────────────────────────────────────────────────────────────────┐
│ 📊 MONITORING                                                     │
└───────────────────────────────────────────────────────────────────┘

  View logs:        python src/main.py | jq .
  Watch metrics:    watch -n 1 curl -s http://localhost:8001/metrics
  Dashboard:        http://localhost:8001/dashboard
  Health check:     curl http://localhost:8001/health

╔═══════════════════════════════════════════════════════════════════╗
║  Need help? See HOW_TO_RUN.md or QUICKSTART_LOCAL.md             ║
╚═══════════════════════════════════════════════════════════════════╝
```
