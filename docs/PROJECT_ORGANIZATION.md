# Project Organization

This document describes the organization and structure of the Real-Time Voice Assistant project.

## Directory Structure

```
.
├── .kiro/                      # Kiro IDE configuration and specs
│   └── specs/                  # Feature specifications
├── config/                     # Configuration files (YAML)
├── docker/                     # Docker configuration
│   ├── Dockerfile             # Production image
│   ├── Dockerfile.dev         # Development image
│   ├── docker-compose.yml     # Production compose
│   ├── docker-compose.dev.yml # Development compose
│   ├── .dockerignore          # Docker ignore rules
│   ├── Makefile               # Docker commands
│   └── README.md              # Docker documentation
├── docs/                       # Documentation
│   ├── archive/               # Historical documentation
│   ├── *.md                   # Current documentation
│   └── PROJECT_ORGANIZATION.md # This file
├── examples/                   # Example code and demos
├── logs/                       # Application logs (gitignored)
├── recordings/                 # Session recordings (gitignored)
├── scripts/                    # Utility and maintenance scripts
│   ├── update_*.py            # Import refactoring scripts
│   ├── view_logs.py           # Log viewer utility
│   ├── test_logging_demo.py   # Logging demo script
│   └── README.md              # Scripts documentation
├── src/                        # Main application source code
│   ├── api/                   # API layer (WebSocket, HTTP)
│   ├── core/                  # Core models and events
│   ├── infrastructure/        # Infrastructure (config, resilience)
│   ├── observability/         # Monitoring and metrics
│   ├── services/              # Business logic (ASR, LLM, TTS)
│   ├── session/               # Session management
│   └── utils/                 # Utilities (logger, etc.)
└── tests/                      # Test suite
    ├── e2e/                   # End-to-end tests
    ├── fixtures/              # Test fixtures and mocks
    ├── integration/           # Integration tests
    ├── performance/           # Performance tests
    └── unit/                  # Unit tests

```

## Root Files

### Essential Configuration
- `README.md` - Project overview and getting started guide
- `requirements.txt` - Production dependencies
- `requirements-dev.txt` - Development dependencies
- `pyproject.toml` - Python project configuration
- `pytest.ini` - Pytest configuration
- `.env.example` - Example environment variables
- `.gitignore` - Git ignore rules

### Docker & Deployment
- `docker/` - Docker configuration directory
  - `Dockerfile` - Production image
  - `Dockerfile.dev` - Development image
  - `docker-compose.yml` - Production compose
  - `docker-compose.dev.yml` - Development compose
  - `.dockerignore` - Docker ignore rules
  - `Makefile` - Docker commands
  - `README.md` - Docker documentation
- `Makefile` - Build and deployment commands (root level)

### Setup & Launch Scripts
- `setup.sh` / `setup.bat` - Environment setup scripts
- `start.sh` / `start.bat` - Application launch scripts

## Documentation Organization

### Current Documentation (`docs/`)
- `api.md` - API documentation
- `architecture.md` - System architecture
- `configuration.md` - Configuration guide
- `logging_system.md` - Logging system documentation
- `HOW_TO_RUN.md` - Running the application
- `QUICKSTART.md` - Quick start guide
- `SETUP_GUIDE.md` - Detailed setup instructions
- Service-specific docs (asr_service.md, tts_service.md, etc.)

### Historical Documentation (`docs/archive/`)
- Implementation summaries (TASK_*.md)
- Restructuring documentation
- Feature implementation summaries
- Original project brief

## Scripts Organization

### Refactoring Scripts
One-time scripts used during project reorganization:
- `update_imports.py` - Module import updates
- `update_logging_imports.py` - Logging import updates
- `update_test_imports.py` - Test import updates

### Development Scripts
Reusable utilities for development:
- `view_logs.py` - Interactive log viewer
- `test_logging_demo.py` - Logging system demonstration

See `scripts/README.md` for detailed usage.

## Source Code Organization

### Core (`src/core/`)
- `events.py` - Event schemas (AudioFrame, TranscriptEvent, etc.)
- `models.py` - Data models (Session, buffers, etc.)

### Services (`src/services/`)
- `asr.py` - Automatic Speech Recognition service
- `llm.py` - Language Model reasoning service
- `tts.py` - Text-to-Speech synthesis service

### API Layer (`src/api/`)
- `websocket.py` - WebSocket server
- `health_server.py` - Health check endpoints

### Infrastructure (`src/infrastructure/`)
- `config.py` - Configuration management
- `resilience/` - Circuit breakers, retries, timeouts

### Observability (`src/observability/`)
- `latency.py` - Latency tracking
- `metrics.py` - Metrics aggregation
- `health.py` - Health monitoring

### Session Management (`src/session/`)
- `manager.py` - Session lifecycle management
- `recorder.py` - Session recording
- `replay.py` - Session replay system

### Utilities (`src/utils/`)
- `logger/` - Structured logging system

## Test Organization

### Unit Tests (`tests/unit/`)
Component-level tests organized by module:
- `tests/unit/core/` - Core models and events
- `tests/unit/services/` - Service components
- `tests/unit/infrastructure/` - Infrastructure components
- `tests/unit/utils/` - Utility components

### Integration Tests (`tests/integration/`)
Multi-component integration tests

### End-to-End Tests (`tests/e2e/`)
Complete system flow tests

### Performance Tests (`tests/performance/`)
Latency and throughput tests

### Fixtures (`tests/fixtures/`)
- `mocks.py` - Mock services and clients
- `conftest.py` - Pytest configuration and fixtures

## Configuration Files

### Application Config (`config/`)
- `development.yaml` - Development environment
- `staging.yaml` - Staging environment
- `production.yaml` - Production environment
- `testing.yaml` - Test environment
- `example.yaml` - Configuration template

## Generated Directories

### Logs (`logs/`)
Application logs with timestamp-based filenames:
- `voice_assistant_YYYYMMDD_HHMMSS.log`

### Recordings (`recordings/`)
Session recordings for debugging:
- `<session_id>/metadata.json`
- `<session_id>/events.json.gz`
- `<session_id>/audio.json.gz`

## Best Practices

### Adding New Features
1. Create a spec in `.kiro/specs/`
2. Implement in appropriate `src/` module
3. Add tests in corresponding `tests/` directory
4. Update documentation in `docs/`

### Adding Documentation
- Current docs → `docs/`
- Historical/archived docs → `docs/archive/`
- Code examples → `examples/`

### Adding Scripts
- Maintenance scripts → `scripts/`
- Example code → `examples/`
- Update `scripts/README.md` with usage

### Configuration
- Environment-specific → `config/`
- Secrets → `.env` (not committed)
- Examples → `.env.example`

## Maintenance

### Cleaning Up
- Logs are auto-rotated (keep last 30 days)
- Recordings should be manually cleaned periodically
- `.coverage` files are regenerated on test runs

### Updating Dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Running Tests
```bash
pytest                    # All tests
pytest tests/unit/        # Unit tests only
pytest tests/e2e/         # E2E tests only
pytest --cov=src          # With coverage
```

## Related Documentation

- [Architecture Overview](architecture.md)
- [API Documentation](api.md)
- [Configuration Guide](configuration.md)
- [Setup Guide](SETUP_GUIDE.md)
- [Quick Start](QUICKSTART.md)
- [Scripts README](../scripts/README.md)
