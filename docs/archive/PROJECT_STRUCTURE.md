# Project Structure

This document describes the organization of the Real-Time Voice Assistant codebase.

## Directory Layout

```
realtime-voice-assistant/
├── .kiro/                          # Kiro specification files
│   └── specs/
│       └── realtime-voice-assistant/
│           ├── requirements.md     # System requirements
│           ├── design.md          # Architecture and design
│           ├── tasks.md           # Implementation tasks
│           └── .config            # Spec configuration
│
├── src/                           # Application source code
│   ├── __init__.py               # Package initialization
│   ├── main.py                   # Application entry point (Task 20)
│   │
│   ├── events/                   # Event schemas and data models (Task 2)
│   │   ├── __init__.py
│   │   ├── schemas.py           # AudioFrame, TranscriptEvent, etc.
│   │   └── buffers.py           # AudioBuffer, TokenBuffer, etc.
│   │
│   ├── services/                 # External service integrations
│   │   ├── __init__.py
│   │   ├── asr_service.py       # Whisper ASR integration (Task 8)
│   │   ├── llm_service.py       # Gemini LLM integration (Task 9)
│   │   └── tts_service.py       # ElevenLabs TTS integration (Task 10)
│   │
│   ├── server/                   # WebSocket server (Task 13)
│   │   ├── __init__.py
│   │   └── websocket_server.py  # WebSocket connection handling
│   │
│   ├── pipeline/                 # Event pipeline and session management
│   │   ├── __init__.py
│   │   ├── session.py           # Session dataclass (Task 12)
│   │   └── session_manager.py   # SessionManager (Task 12)
│   │
│   ├── resilience/               # Fault tolerance patterns (Task 7)
│   │   ├── __init__.py
│   │   ├── circuit_breaker.py   # Circuit breaker implementation
│   │   ├── retry.py             # Retry with exponential backoff
│   │   └── timeout.py           # Timeout utilities
│   │
│   ├── observability/            # Monitoring and logging
│   │   ├── __init__.py
│   │   ├── logger.py            # Structured logging (Task 4)
│   │   ├── latency.py           # Latency tracking (Task 5)
│   │   ├── metrics.py           # Metrics aggregation (Task 5)
│   │   └── dashboard.py         # Metrics dashboard (Task 18)
│   │
│   ├── health/                   # Health check system (Task 19)
│   │   ├── __init__.py
│   │   ├── system_health.py     # Health tracking
│   │   └── health_server.py     # Health check endpoints
│   │
│   └── recording/                # Session recording and replay
│       ├── __init__.py
│       ├── recorder.py          # Session recording (Task 15)
│       └── replay.py            # Replay system (Task 16)
│
├── tests/                        # Test suite
│   ├── __init__.py
│   │
│   ├── unit/                    # Unit tests
│   │   ├── __init__.py
│   │   ├── test_events.py       # Event schema tests (Task 2.2)
│   │   ├── test_buffers.py      # Buffer tests (Task 2.4)
│   │   ├── test_config.py       # Configuration tests (Task 3.3)
│   │   ├── test_logger.py       # Logging tests (Task 4.2)
│   │   ├── test_latency.py      # Latency tracking tests (Task 5.4)
│   │   ├── test_circuit_breaker.py  # Circuit breaker tests (Task 7.2)
│   │   ├── test_retry.py        # Retry tests (Task 7.5)
│   │   ├── test_asr.py          # ASR service tests (Task 8.2)
│   │   ├── test_llm.py          # LLM service tests (Task 9.2)
│   │   ├── test_tts.py          # TTS service tests (Task 10.2)
│   │   ├── test_session.py      # Session management tests (Task 12.3)
│   │   ├── test_websocket.py    # WebSocket tests (Task 13.4)
│   │   ├── test_recorder.py     # Recording tests (Task 15.2)
│   │   ├── test_replay.py       # Replay tests (Task 16.2)
│   │   ├── test_dashboard.py    # Dashboard tests (Task 18.2)
│   │   └── test_health.py       # Health check tests (Task 19.3)
│   │
│   ├── integration/             # Integration tests
│   │   ├── __init__.py
│   │   ├── test_pipeline.py     # Pipeline integration (Task 14.3)
│   │   └── test_e2e.py          # End-to-end tests (Task 24.1)
│   │
│   ├── property/                # Property-based tests
│   │   ├── __init__.py
│   │   ├── test_event_properties.py     # Event properties (Task 2.2)
│   │   ├── test_config_properties.py    # Config properties (Task 3.4)
│   │   ├── test_logging_properties.py   # Logging properties (Task 4.3)
│   │   ├── test_latency_properties.py   # Latency properties (Task 5.5)
│   │   ├── test_timeout_properties.py   # Timeout properties (Task 7.8)
│   │   ├── test_retry_properties.py     # Retry properties (Task 7.6)
│   │   ├── test_circuit_properties.py   # Circuit breaker properties (Task 7.3)
│   │   ├── test_asr_properties.py       # ASR properties (Task 8.3)
│   │   ├── test_llm_properties.py       # LLM properties (Task 9.3)
│   │   ├── test_tts_properties.py       # TTS properties (Task 10.3)
│   │   ├── test_session_properties.py   # Session properties (Task 12.4)
│   │   ├── test_websocket_properties.py # WebSocket properties (Task 13.5)
│   │   ├── test_pipeline_properties.py  # Pipeline properties (Task 14.2)
│   │   ├── test_recording_properties.py # Recording properties (Task 15.3)
│   │   ├── test_replay_properties.py    # Replay properties (Task 16.3)
│   │   └── test_health_properties.py    # Health properties (Task 19.4)
│   │
│   └── fixtures/                # Test fixtures and mocks (Task 24.3)
│       ├── __init__.py
│       ├── mock_whisper.py      # Mock Whisper API
│       ├── mock_gemini.py       # Mock Gemini API
│       ├── mock_elevenlabs.py   # Mock ElevenLabs API
│       └── test_data.py         # Test audio data generators
│
├── config/                       # Configuration module (Task 3)
│   ├── __init__.py
│   ├── settings.py              # Configuration dataclasses
│   └── loader.py                # ConfigLoader implementation
│
├── examples/                     # Example applications (Task 22)
│   ├── __init__.py
│   ├── client.py                # Example Python client
│   └── README.md                # Client documentation
│
├── docs/                         # Documentation (Task 23)
│   ├── api.md                   # API documentation
│   ├── architecture.md          # Architecture diagrams
│   ├── configuration.md         # Configuration guide
│   └── troubleshooting.md       # Troubleshooting guide
│
├── recordings/                   # Session recordings (created at runtime)
│   └── <session-id>/
│       ├── metadata.json
│       ├── events.json.gz
│       └── audio.json.gz
│
├── .env                         # Environment configuration (not in git)
├── .env.example                 # Environment template
├── .gitignore                   # Git ignore rules
├── Makefile                     # Development commands
├── pyproject.toml               # Python project configuration
├── pytest.ini                   # Pytest configuration
├── README.md                    # Project overview
├── SETUP_GUIDE.md              # Setup instructions
├── PROJECT_STRUCTURE.md        # This file
├── requirements.txt             # Core dependencies
├── requirements-dev.txt         # Development dependencies
├── setup.sh                     # Setup script (Linux/macOS)
└── setup.bat                    # Setup script (Windows)
```

## Module Responsibilities

### src/events/
Event schemas and data models that flow through the pipeline. All events are dataclasses with timestamp metadata.

**Key files:**
- `schemas.py`: AudioFrame, TranscriptEvent, LLMTokenEvent, TTSAudioEvent, ErrorEvent
- `buffers.py`: AudioBuffer, TokenBuffer, ConversationContext

### src/services/
External API integrations with resilience patterns (timeouts, retries, circuit breakers).

**Key files:**
- `asr_service.py`: Whisper API integration for speech recognition
- `llm_service.py`: Gemini API integration for language understanding
- `tts_service.py`: ElevenLabs API integration for speech synthesis

### src/server/
WebSocket server for bidirectional audio streaming with clients.

**Key files:**
- `websocket_server.py`: Connection handling, audio receive/send loops

### src/pipeline/
Session management and event pipeline orchestration.

**Key files:**
- `session.py`: Session dataclass with queues and tasks
- `session_manager.py`: Session lifecycle management

### src/resilience/
Fault tolerance patterns for robust operation.

**Key files:**
- `circuit_breaker.py`: Circuit breaker pattern implementation
- `retry.py`: Exponential backoff retry mechanism
- `timeout.py`: Timeout utilities for async operations

### src/observability/
Monitoring, logging, and metrics collection.

**Key files:**
- `logger.py`: Structured JSON logging
- `latency.py`: Latency tracking and measurement
- `metrics.py`: Metrics aggregation and statistics
- `dashboard.py`: HTTP server for metrics visualization

### src/health/
Health check system for monitoring and orchestration.

**Key files:**
- `system_health.py`: Component health tracking
- `health_server.py`: Health check HTTP endpoints

### src/recording/
Session recording and replay for debugging.

**Key files:**
- `recorder.py`: Record sessions to disk
- `replay.py`: Replay recorded sessions

### config/
Configuration management with environment variables and YAML files.

**Key files:**
- `settings.py`: Configuration dataclasses
- `loader.py`: Configuration loading and validation

### tests/
Comprehensive test suite with unit, integration, and property-based tests.

**Test categories:**
- `unit/`: Test individual components in isolation
- `integration/`: Test component interactions
- `property/`: Property-based tests using Hypothesis
- `fixtures/`: Mock services and test data

## Implementation Order

The tasks are designed to be implemented in order:

1. **Tasks 1-6**: Core infrastructure (events, config, logging, latency, resilience)
2. **Tasks 7-11**: Service implementations (ASR, LLM, TTS)
3. **Tasks 12-14**: Pipeline and session management
4. **Tasks 15-17**: Recording, replay, and observability
5. **Tasks 18-20**: Health checks, dashboard, and main entry point
6. **Tasks 21-23**: Deployment, examples, and documentation
7. **Task 24**: Final integration and testing

## Key Design Patterns

### Event-Driven Architecture
Components communicate via typed events through asyncio queues. This provides loose coupling and easy testing.

### Async/Await Throughout
All I/O operations use Python's asyncio for non-blocking execution and high concurrency.

### Dependency Injection
Services are injected into components, making them easy to mock and test.

### Circuit Breaker Pattern
External API calls are protected by circuit breakers to prevent cascading failures.

### Structured Logging
All logs are JSON-formatted with consistent fields for easy parsing and analysis.

## Testing Strategy

### Unit Tests
Test individual components in isolation with mocked dependencies.

### Integration Tests
Test component interactions with real asyncio queues and event flow.

### Property-Based Tests
Use Hypothesis to verify universal properties across many generated inputs.

### Performance Tests
Verify latency budgets are met under various conditions.

## Configuration Management

Configuration is loaded from:
1. Environment variables (highest priority)
2. `.env` file
3. YAML configuration file (if specified)
4. Default values (lowest priority)

All configuration is validated at startup with clear error messages.

## Observability

### Metrics
- Latency measurements for each pipeline stage
- Percentile statistics (p50, p95, p99)
- Throughput and active session count

### Logging
- Structured JSON logs with millisecond timestamps
- Session IDs for tracing events through the pipeline
- Component names for filtering

### Health Checks
- `/health`: Overall system health
- `/health/ready`: Readiness for traffic
- `/health/live`: Process liveness

### Dashboard
- Real-time metrics visualization
- Latency breakdown by stage
- Budget violation highlighting

## Development Workflow

1. Activate virtual environment
2. Create feature branch
3. Implement task from tasks.md
4. Write tests (unit + property)
5. Run tests: `pytest`
6. Format code: `black` and `isort`
7. Lint code: `flake8` and `mypy`
8. Commit changes
9. Submit pull request

## Additional Resources

- See `README.md` for project overview
- See `SETUP_GUIDE.md` for setup instructions
- See `.kiro/specs/realtime-voice-assistant/design.md` for detailed architecture
- See `.kiro/specs/realtime-voice-assistant/requirements.md` for requirements
- See `.kiro/specs/realtime-voice-assistant/tasks.md` for implementation tasks
