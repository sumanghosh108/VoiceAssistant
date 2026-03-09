# Real-Time Voice Assistant

A production-ready streaming voice assistant application that processes audio input through an asynchronous event pipeline. The system receives audio via WebSocket, transcribes it using Whisper ASR, generates responses using Gemini LLM, synthesizes speech using ElevenLabs TTS, and streams audio back to the client—all with comprehensive latency tracking and fault tolerance.

## Features

### Core Capabilities
- **Real-time audio streaming** - Bidirectional WebSocket connections for low-latency audio I/O
- **Speech recognition** - OpenAI Whisper API with partial and final transcription results
- **Intelligent responses** - Google Gemini LLM with streaming token-by-token generation
- **Natural speech synthesis** - ElevenLabs TTS with streaming audio output
- **Low latency** - End-to-end processing under 2 seconds (ASR: 500ms, LLM first token: 300ms, TTS: 400ms)
- **Concurrent sessions** - Support for 100+ simultaneous voice conversations

### Architecture Highlights
- **Async/await throughout** - Non-blocking I/O using Python's asyncio for high concurrency
- **Event-driven pipeline** - Loosely coupled components communicating via typed events
- **Streaming-first** - Minimal buffering, process data as it arrives
- **Session isolation** - Independent queues and tasks per session prevent cross-contamination
- **Modular design** - Clear interfaces enable independent testing and component replacement

### Resilience & Reliability
- **Timeout handling** - Configurable timeouts on all external API calls (ASR: 3s, LLM: 5s, TTS: 3s)
- **Retry mechanisms** - Exponential backoff with configurable max attempts (default: 3)
- **Circuit breakers** - Prevent cascading failures (opens at 50% failure rate, recovers after 30s)
- **Graceful degradation** - Continue operating when non-critical components fail
- **Error isolation** - Failures in one session don't affect others

### Observability
- **Comprehensive latency tracking** - Measure every pipeline stage with millisecond precision
- **Metrics dashboard** - Real-time visualization with percentile statistics (p50, p95, p99)
- **Structured logging** - JSON logs with timestamps, session IDs, and component context
- **Health check endpoints** - `/health`, `/health/ready`, `/health/live` for orchestration
- **Session recording** - Capture all events and audio for debugging
- **Replay system** - Reproduce issues by replaying recorded sessions

## Quick Start

### 📖 Choose Your Setup Method

1. ** Quick Start (Automated)** - Use start scripts for fastest setup
   - Windows: Run `start.bat`
   - Linux/Mac: Run `./start.sh`

---

###  Fastest Way - Automated Scripts

#### Windows:
```bash
# Just run this!
start.bat
```

#### Linux/macOS:
```bash
# Make executable (first time only)
chmod +x start.sh

# Run
./start.sh
```

The script will automatically:
1. Create virtual environment
2. Install dependencies
3. Set up configuration
4. Start the server

---

###  Manual Setup (Recommended for Learning)

**See [RUN_INSTRUCTIONS.md](RUN_INSTRUCTIONS.md) for complete step-by-step instructions with troubleshooting.**

Quick version:

```bash
# 1. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up API keys
cp .env.example .env
# Edit .env with your API keys

# 4. Run the application
python -m src.main

# 5. Test it (in new terminal)
curl http://localhost:8001/health/live
```

---

### Prerequisites
- Python 3.11 or higher
- API keys for:
  - OpenAI (Whisper) - [Get API key](https://platform.openai.com/api-keys)
  - Google AI (Gemini) - [Get API key](https://makersuite.google.com/app/apikey)
  - ElevenLabs (TTS) - [Get API key](https://elevenlabs.io/app/settings/api-keys)

### Manual Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd realtime-voice-assistant
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. For development (includes testing tools):
```bash
pip install -r requirements-dev.txt
```

### Configuration

Create a `.env` file in the project root (see `.env.example` for reference):

```bash
# API Keys (required)
WHISPER_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_google_ai_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_VOICE_ID=your_voice_id

# Server Configuration (optional, defaults shown)
WEBSOCKET_HOST=0.0.0.0
WEBSOCKET_PORT=8000
METRICS_HOST=0.0.0.0
METRICS_PORT=8001

# Timeouts (optional, in seconds)
ASR_TIMEOUT=3.0
LLM_TIMEOUT=5.0
TTS_TIMEOUT=3.0

# Pipeline Configuration (optional)
AUDIO_BUFFER_DURATION_MS=1000
TOKEN_BUFFER_SIZE=10
MAX_CONVERSATION_TURNS=10

# Observability (optional)
ENABLE_RECORDING=false
LOG_LEVEL=INFO
```

For complete configuration documentation, see [docs/configuration.md](docs/configuration.md).

### Running the Application

Start the voice assistant server:
```bash
python -m src.main
```

The server will start:
- **WebSocket server** on port 8000 (audio streaming)
- **Metrics dashboard** at http://localhost:8001/dashboard
- **Health checks** at http://localhost:8001/health

For detailed running instructions, see [docs/running_the_application.md](docs/running_the_application.md).

### Using Docker

Build and run with Docker Compose:
```bash
docker-compose up --build
```

Access the services:
- WebSocket: `ws://localhost:8000`
- Metrics: http://localhost:8001/dashboard
- Health: http://localhost:8001/health

### Example Client

A complete Python client example is provided in `examples/voice_client.py`:

```bash
# Install client dependencies
pip install -r examples/requirements.txt

# Run the example client
python examples/voice_client.py --server ws://localhost:8000
```

The example client demonstrates:
- Audio capture from microphone
- WebSocket communication with the server
- Audio playback of responses
- Error handling and automatic reconnection

For more options and detailed documentation, see [examples/README.md](examples/README.md).

## Architecture Overview

### System Components

The Real-Time Voice Assistant uses an asynchronous event pipeline architecture where components communicate via typed events through asyncio queues:

```
┌─────────────────┐
│ Client App      │
│ (Browser/Mobile)│
└────────┬────────┘
         │ WebSocket (Audio Stream)
         ↓
┌─────────────────────────────────────────────────────────────┐
│                    Voice Assistant System                    │
│                                                              │
│  ┌──────────────┐    ┌─────────────────────────────────┐   │
│  │  WebSocket   │───→│      Event Pipeline             │   │
│  │   Server     │←───│   (AsyncIO Queues)              │   │
│  └──────────────┘    └─────────────────────────────────┘   │
│                               │                              │
│         ┌─────────────────────┼─────────────────────┐       │
│         ↓                     ↓                     ↓       │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐ │
│  │ ASR Service │      │ LLM Service │      │ TTS Service │ │
│  │  (Whisper)  │      │  (Gemini)   │      │(ElevenLabs) │ │
│  └─────────────┘      └─────────────┘      └─────────────┘ │
│         │                     │                     │       │
│         └─────────────────────┴─────────────────────┘       │
│                               │                              │
│  ┌────────────────────────────┼──────────────────────────┐  │
│  │         Cross-Cutting Concerns                        │  │
│  │  • Latency Tracker    • Session Recorder             │  │
│  │  • Circuit Breakers   • Structured Logger            │  │
│  │  • Health Monitor     • Metrics Aggregator           │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────────────────────────┐
│  Observability Layer                                         │
│  • Metrics Dashboard (HTTP :8001/dashboard)                 │
│  • Health Endpoints (HTTP :8001/health)                     │
│  • Session Recordings (Filesystem)                          │
└─────────────────────────────────────────────────────────────┘
```

### Event Flow

A typical voice interaction flows through the pipeline as follows:

1. **Audio Input** → Client sends audio chunks via WebSocket
2. **Audio Buffering** → WebSocket server creates `AudioFrame` events
3. **Speech Recognition** → ASR service transcribes audio, emits `TranscriptEvent`
4. **Language Understanding** → LLM service generates response, streams `LLMTokenEvent`
5. **Speech Synthesis** → TTS service synthesizes audio, emits `TTSAudioEvent`
6. **Audio Output** → WebSocket server sends audio back to client

Each stage is tracked for latency, logged with structured context, and protected by resilience patterns (timeouts, retries, circuit breakers).

### Key Design Principles

1. **Streaming-First Architecture** - Every component operates on streaming data with minimal buffering
2. **Async/Await Throughout** - Non-blocking I/O using Python's asyncio for high concurrency
3. **Event-Driven Pipeline** - Loosely coupled components communicating via typed events
4. **Observable by Default** - Comprehensive instrumentation for latency, errors, and state transitions
5. **Resilient by Design** - Timeouts, retries, circuit breakers, and graceful degradation
6. **Debuggable** - Session recording and replay for post-mortem analysis

### Session Management

Each WebSocket connection creates an isolated session with:
- Unique session ID
- Dedicated event queues (audio, transcript, token, TTS)
- Independent processing tasks (ASR, LLM, TTS)
- Session-scoped latency tracker
- Optional session recorder

Sessions are isolated to prevent failures from affecting other concurrent conversations.

For detailed architecture documentation, see:
- [Architecture Overview](docs/architecture.md)
- [Event Pipeline Architecture](docs/event_pipeline_architecture.md)
- [Session Management](docs/session_management.md)

## Documentation

### Getting Started
- [Running the Application](docs/running_the_application.md) - Detailed setup and deployment instructions
- [Configuration Guide](docs/configuration.md) - Complete configuration reference
- [Example Client](examples/README.md) - Client integration examples

### Architecture & Design
- [Architecture Overview](docs/architecture.md) - System design and component interactions
- [Event Pipeline Architecture](docs/event_pipeline_architecture.md) - Event-driven pipeline details
- [Session Management](docs/session_management.md) - Session lifecycle and isolation

### Core Services
- [WebSocket Server](docs/websocket_server.md) - Audio streaming protocol and implementation
- [ASR Service](docs/asr_service.md) - Speech recognition with Whisper
- [Reasoning Service](docs/reasoning_service.md) - LLM integration with Gemini
- [TTS Service](docs/tts_service.md) - Speech synthesis with ElevenLabs

### Resilience & Reliability
- [Resilience Patterns](docs/resilience_patterns.md) - Timeouts, retries, and circuit breakers
- [Health System](docs/health_system.md) - Health checks and graceful degradation

### Observability
- [Metrics Dashboard](docs/metrics_dashboard.md) - Real-time latency visualization
- [Session Recording](docs/session_recording.md) - Recording sessions for debugging
- [Replay System](docs/replay_system.md) - Replaying recorded sessions

### API Reference
- [API Documentation](docs/api.md) - WebSocket protocol, HTTP endpoints, and event schemas

### Troubleshooting
- [Troubleshooting Guide](docs/troubleshooting.md) - Common issues and solutions

## Example Usage

### Basic Voice Interaction

1. Start the server:
```bash
python -m src.main
```

2. Connect a client:
```bash
python examples/voice_client.py
```

3. Speak into your microphone - the system will:
   - Transcribe your speech using Whisper
   - Generate a response using Gemini
   - Synthesize speech using ElevenLabs
   - Stream the audio response back to you

### Monitoring Performance

Access the metrics dashboard at http://localhost:8001/dashboard to view:
- Real-time latency breakdown by pipeline stage
- Percentile statistics (p50, p95, p99)
- Active session count
- Latency budget violations

### Checking System Health

Query the health endpoint:
```bash
curl http://localhost:8001/health
```

Response includes:
- Overall system health status
- Individual component status (ASR, LLM, TTS)
- Circuit breaker states
- Degraded components (if any)

### Recording and Replaying Sessions

Enable session recording in `.env`:
```bash
ENABLE_RECORDING=true
```

Recordings are saved to `recordings/<session_id>/` with:
- `metadata.json` - Session information
- `events.json.gz` - All events during the session
- `audio.json.gz` - Audio frames

Replay a session for debugging:
```python
from src.replay_system import ReplaySystem

replay = ReplaySystem(services, storage_path="recordings")
results = await replay.replay(session_id="abc-123", speed=1.0)
```

### Custom Client Integration

Integrate with your own client application:

```python
import asyncio
import websockets
import struct

async def voice_assistant_client():
    uri = "ws://localhost:8000"
    async with websockets.connect(uri) as websocket:
        # Send audio frame
        timestamp = time.time()
        sequence = 0
        audio_data = b'...'  # PCM 16-bit, 16kHz, mono
        
        message = struct.pack('>d', timestamp)  # 8 bytes: timestamp
        message += struct.pack('>I', sequence)  # 4 bytes: sequence number
        message += audio_data
        
        await websocket.send(message)
        
        # Receive audio response
        response = await websocket.recv()
        sequence = struct.unpack('>I', response[:4])[0]
        is_final = response[4]
        audio_data = response[5:]
        
        # Play audio_data...

asyncio.run(voice_assistant_client())
```

For complete protocol documentation, see [API Documentation](docs/api.md).

## Development

### Project Structure

```
realtime-voice-assistant/
├── src/                    # Application source code
│   ├── buffers.py         # Audio and token buffering
│   ├── config.py          # Configuration management
│   ├── logger.py          # Structured logging
│   ├── latency.py         # Latency tracking
│   ├── resilience.py      # Circuit breakers, retries, timeouts
│   ├── asr_service.py     # Whisper ASR integration
│   ├── reasoning_service.py  # Gemini LLM integration
│   ├── tts_service.py     # ElevenLabs TTS integration
│   ├── session.py         # Session management
│   ├── websocket_server.py   # WebSocket server
│   ├── health.py          # Health check system
│   ├── metrics_dashboard.py  # Metrics visualization
│   ├── session_recorder.py   # Session recording
│   ├── replay_system.py   # Session replay
│   └── main.py            # Application entry point
├── tests/                 # Test suite
│   ├── test_*.py         # Unit and integration tests
│   └── property/         # Property-based tests (optional)
├── docs/                 # Documentation
├── examples/             # Example client applications
├── requirements.txt      # Core dependencies
├── requirements-dev.txt  # Development dependencies
├── Dockerfile            # Docker container definition
├── docker-compose.yml    # Docker Compose configuration
└── README.md            # This file
```

### Running Tests

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=src --cov-report=html
```

Run specific test file:
```bash
pytest tests/test_asr_service.py
```

### Code Quality

Format code:
```bash
black src/ tests/
isort src/ tests/
```

Lint code:
```bash
flake8 src/ tests/
mypy src/
```

## Technologies

### Core Technologies
- **Python 3.11+** - Modern async/await support and performance improvements
- **asyncio** - Asynchronous I/O for high-concurrency event processing
- **websockets** - WebSocket server implementation
- **aiohttp** - Async HTTP server for metrics and health endpoints

### External Services
- **OpenAI Whisper API** - Automatic speech recognition with high accuracy
- **Google Gemini API** - Large language model for intelligent responses
- **ElevenLabs API** - Natural text-to-speech synthesis

### Testing & Quality
- **pytest** - Test framework with async support
- **pytest-asyncio** - Async test utilities
- **hypothesis** - Property-based testing (optional)
- **pytest-cov** - Code coverage reporting
- **black** - Code formatting
- **isort** - Import sorting
- **flake8** - Linting
- **mypy** - Static type checking

### Deployment
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration

## Performance

### Latency Targets
- **ASR Latency**: < 500ms (audio receipt to transcript)
- **LLM First Token**: < 300ms (transcript to first token)
- **TTS Latency**: < 400ms (token to audio emission)
- **End-to-End**: < 2000ms (audio input to audio output)

### Throughput
- **Concurrent Sessions**: 100+ simultaneous voice conversations
- **Audio Processing**: Real-time streaming with minimal buffering
- **Token Streaming**: Sub-second response initiation

### Resource Usage
- **Memory**: ~100MB base + ~10MB per active session
- **CPU**: Scales with concurrent sessions (primarily I/O bound)
- **Network**: Depends on audio quality and API response times

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License



## Acknowledgments

- OpenAI Whisper for speech recognition
- Google Gemini for language understanding
- ElevenLabs for natural speech synthesis
