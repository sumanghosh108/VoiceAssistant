# Real-Time Voice Assistant - Production-Ready Architecture

## 🎯 Overview

This project has been restructured from a flat file structure into a production-ready modular architecture with clear separation of concerns, following industry best practices.

## 📁 New Structure

```
src/
├── core/                    # Domain models and events (no dependencies)
├── infrastructure/          # Config, logging, resilience patterns
├── services/               # External API integrations (ASR, LLM, TTS)
├── observability/          # Health, metrics, latency tracking
├── session/                # Session lifecycle management
└── api/                    # WebSocket and HTTP endpoints
```

## 🚀 Quick Start

### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Running the Application
```bash
# Start the server
python src/main.py

# The server will start on:
# - WebSocket: ws://localhost:8000
# - Health checks: http://localhost:8001/health
# - Metrics: http://localhost:8001/metrics
```

### Running Tests
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test suites
python -m pytest tests/test_buffers.py -v
python -m pytest tests/test_config.py -v
python -m pytest tests/test_e2e_integration.py -v
```

## 📦 Package Structure

### Core (`src/core/`)
Foundation layer with no dependencies.

```python
from src.core.events import AudioFrame, TranscriptEvent
from src.core.models import AudioBuffer, Session
```

**Contains**:
- Event schemas (AudioFrame, TranscriptEvent, LLMTokenEvent, TTSAudioEvent)
- Data models (AudioBuffer, TokenBuffer, ConversationContext, Session)

### Infrastructure (`src/infrastructure/`)
Cross-cutting concerns used by all packages.

```python
from src.infrastructure.config import ConfigLoader
from src.infrastructure.logging import logger
from src.infrastructure.resilience import CircuitBreaker, with_retry
```

**Contains**:
- Configuration management
- Structured logging
- Resilience patterns (circuit breakers, retries, timeouts)

### Services (`src/services/`)
External API integrations with resilience patterns.

```python
from src.services.asr import ASRService
from src.services.llm import ReasoningService
from src.services.tts import TTSService
```

**Contains**:
- ASR Service (Whisper integration)
- LLM Service (Gemini integration)
- TTS Service (ElevenLabs integration)

### Observability (`src/observability/`)
Monitoring, metrics, and health checks.

```python
from src.observability.health import SystemHealth
from src.observability.metrics import MetricsAggregator
from src.observability.latency import LatencyTracker
```

**Contains**:
- System health tracking
- Metrics aggregation and dashboard
- Latency tracking and monitoring

### Session (`src/session/`)
Session lifecycle management.

```python
from src.session.manager import SessionManager
from src.session.recorder import SessionRecorder
from src.session.replay import ReplaySystem
```

**Contains**:
- Session creation and cleanup
- Session recording for debugging
- Session replay system

### API (`src/api/`)
External interfaces (WebSocket, HTTP).

```python
from src.api.websocket import WebSocketServer
from src.api.health_server import HealthCheckServer
```

**Contains**:
- WebSocket server for real-time audio streaming
- Health check HTTP endpoints

## 🔄 Data Flow

```
Client → WebSocket → SessionManager → ASR → LLM → TTS → WebSocket → Client
```

Each session has isolated event queues:
```
audio_queue → ASR → transcript_queue → LLM → token_queue → TTS → tts_queue
```

## 🛡️ Resilience Patterns

### Circuit Breaker
Prevents cascading failures by opening when error rate exceeds threshold.

```python
circuit_breaker = CircuitBreaker(
    failure_threshold=0.5,  # 50% failure rate
    window_size=10,         # Over 10 requests
    timeout_seconds=30      # Open for 30 seconds
)

result = await circuit_breaker.call(external_api_call, data)
```

### Retry with Exponential Backoff
Automatically retries failed operations with increasing delays.

```python
@with_retry(RetryConfig(
    max_attempts=3,
    initial_delay_ms=100,
    max_delay_ms=5000
))
async def call_api():
    # API call that may fail
    pass
```

### Timeout Enforcement
Prevents operations from hanging indefinitely.

```python
result = await with_timeout(
    api_call(),
    timeout_seconds=3.0,
    operation_name="whisper_transcription"
)
```

## 📊 Observability

### Health Checks
```bash
# Detailed health status
curl http://localhost:8001/health

# Readiness probe (for Kubernetes)
curl http://localhost:8001/health/ready

# Liveness probe
curl http://localhost:8001/health/live
```

### Metrics Dashboard
```bash
# JSON metrics
curl http://localhost:8001/metrics

# HTML dashboard (auto-refresh)
open http://localhost:8001/dashboard
```

### Latency Tracking
Automatic latency tracking for all pipeline stages:
- ASR latency (budget: 500ms)
- LLM first token latency (budget: 300ms)
- TTS latency (budget: 400ms)
- End-to-end latency (budget: 2000ms)

## 🧪 Testing

### Test Structure
```
tests/
├── test_buffers.py              # Core models
├── test_config.py               # Configuration
├── test_logger.py               # Logging
├── test_resilience.py           # Resilience patterns
├── test_asr_service.py          # ASR service
├── test_reasoning_service.py    # LLM service
├── test_tts_service.py          # TTS service
├── test_session.py              # Session management
├── test_websocket_server.py     # WebSocket server
├── test_e2e_integration.py      # End-to-end tests
└── test_performance.py          # Performance tests
```

### Running Tests
```bash
# All tests
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=src --cov-report=html

# Specific test suite
python -m pytest tests/test_e2e_integration.py -v

# Performance tests
python -m pytest tests/test_performance.py -v
```

## 🐳 Docker Deployment

### Build and Run
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
```

### Docker Compose
```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 📝 Configuration

### Environment Variables
```bash
# Required
WHISPER_API_KEY=your_whisper_api_key
GEMINI_API_KEY=your_gemini_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_VOICE_ID=your_voice_id

# Optional (with defaults)
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
```yaml
# config/production.yaml
api:
  whisper_api_key: ${WHISPER_API_KEY}
  gemini_api_key: ${GEMINI_API_KEY}
  elevenlabs_api_key: ${ELEVENLABS_API_KEY}
  elevenlabs_voice_id: ${ELEVENLABS_VOICE_ID}

server:
  websocket_host: 0.0.0.0
  websocket_port: 8000
  metrics_host: 0.0.0.0
  metrics_port: 8001

pipeline:
  audio_buffer_duration_ms: 500
  token_buffer_size: 10
  max_conversation_turns: 10
```

## 🔧 Development

### Adding a New Service
1. Create package: `src/services/new_service/`
2. Implement service: `src/services/new_service/service.py`
3. Add to exports: `src/services/__init__.py`
4. Write tests: `tests/test_new_service.py`

### Adding a New Resilience Pattern
1. Create module: `src/infrastructure/resilience/new_pattern.py`
2. Add to exports: `src/infrastructure/resilience/__init__.py`
3. Write tests: `tests/test_resilience.py`

### Adding a New Observability Feature
1. Create module: `src/observability/new_feature.py`
2. Add to exports: `src/observability/__init__.py`
3. Write tests: `tests/test_new_feature.py`

## 📚 Documentation

- [Production Architecture](docs/production_architecture.md) - Detailed architecture documentation
- [API Documentation](docs/api.md) - WebSocket and HTTP API reference
- [Configuration Guide](docs/configuration.md) - Configuration options
- [Troubleshooting Guide](docs/troubleshooting.md) - Common issues and solutions

## 🎓 Best Practices

### 1. Dependency Injection
```python
# Good: Dependencies injected
session_manager = SessionManager(
    asr_service=asr_service,
    llm_service=llm_service,
    tts_service=tts_service
)

# Bad: Hard-coded dependencies
session_manager = SessionManager()  # Creates services internally
```

### 2. Async/Await
```python
# Good: Non-blocking I/O
async def process_audio(audio_queue):
    frame = await audio_queue.get()
    result = await transcribe(frame)
    return result

# Bad: Blocking I/O
def process_audio(audio_queue):
    frame = audio_queue.get()  # Blocks thread
    result = transcribe(frame)  # Blocks thread
    return result
```

### 3. Structured Logging
```python
# Good: Structured with context
logger.info(
    "Session created",
    session_id=session_id,
    active_sessions=count
)

# Bad: Unstructured
logger.info(f"Session {session_id} created, {count} active")
```

### 4. Error Handling
```python
# Good: Specific error handling
try:
    result = await api_call()
except TimeoutError:
    logger.error("API timeout", operation="transcribe")
    raise
except ValueError as e:
    logger.error("Invalid input", error=str(e))
    raise

# Bad: Generic error handling
try:
    result = await api_call()
except Exception as e:
    print(f"Error: {e}")
```

## 🤝 Contributing

1. Follow the existing package structure
2. Write tests for new features
3. Update documentation
4. Run tests before committing: `python -m pytest tests/ -v`
5. Check code style: `python -m pylint src/`

## 📄 License

[Your License Here]

## 🙏 Acknowledgments

- OpenAI Whisper for ASR
- Google Gemini for LLM
- ElevenLabs for TTS

## 📞 Support

For issues and questions:
- GitHub Issues: [Your Repo URL]
- Documentation: [Your Docs URL]
- Email: [Your Email]
