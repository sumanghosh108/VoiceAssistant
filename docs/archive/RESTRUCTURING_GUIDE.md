# Production-Ready Module Restructuring

## New Structure

```
src/
├── __init__.py
├── main.py                          # Application entry point
├── core/                            # Core domain models and events
│   ├── __init__.py
│   ├── events.py                    # Event schemas (AudioFrame, TranscriptEvent, etc.)
│   └── models.py                    # Data models (AudioBuffer, TokenBuffer, Session, etc.)
├── services/                        # External service integrations
│   ├── __init__.py
│   ├── asr/                         # ASR service module
│   │   ├── __init__.py
│   │   └── service.py               # ASRService
│   ├── llm/                         # LLM service module
│   │   ├── __init__.py
│   │   └── service.py               # ReasoningService
│   └── tts/                         # TTS service module
│       ├── __init__.py
│       └── service.py               # TTSService
├── infrastructure/                  # Infrastructure concerns
│   ├── __init__.py
│   ├── config.py                    # Configuration management
│   ├── logging.py                   # Structured logging
│   └── resilience/                  # Resilience patterns
│       ├── __init__.py
│       ├── circuit_breaker.py       # CircuitBreaker, CircuitState
│       ├── retry.py                 # RetryConfig, with_retry
│       └── timeout.py               # with_timeout
├── observability/                   # Monitoring and observability
│   ├── __init__.py
│   ├── health.py                    # SystemHealth
│   ├── metrics.py                   # MetricsAggregator, MetricsDashboard
│   └── latency.py                   # LatencyTracker, LatencyMonitor
├── session/                         # Session management
│   ├── __init__.py
│   ├── manager.py                   # SessionManager
│   ├── recorder.py                  # SessionRecorder
│   └── replay.py                    # ReplaySystem
└── api/                            # API layer (WebSocket, HTTP)
    ├── __init__.py
    ├── websocket.py                 # WebSocketServer
    ├── metrics_dashboard.py         # MetricsDashboard HTTP endpoints
    └── health_server.py             # HealthCheckServer HTTP endpoints
```

## Import Migration Map

### Old → New Imports

```python
# Events
from src.events import AudioFrame
→ from src.core.events import AudioFrame

# Models
from src.buffers import AudioBuffer, TokenBuffer, ConversationContext
→ from src.core.models import AudioBuffer, TokenBuffer, ConversationContext

from src.session import Session, SessionManager
→ from src.core.models import Session
→ from src.session.manager import SessionManager

# Services
from src.asr_service import ASRService
→ from src.services.asr import ASRService

from src.reasoning_service import ReasoningService
→ from src.services.llm import ReasoningService

from src.tts_service import TTSService
→ from src.services.tts import TTSService

# Infrastructure
from src.config import SystemConfig, ConfigLoader
→ from src.infrastructure.config import SystemConfig, ConfigLoader

from src.logger import logger
→ from src.infrastructure.logging import logger

from src.resilience import CircuitBreaker, RetryConfig, with_retry, with_timeout
→ from src.infrastructure.resilience import CircuitBreaker, RetryConfig, with_retry, with_timeout

# Observability
from src.health import SystemHealth, HealthCheckServer
→ from src.observability.health import SystemHealth
→ from src.api.health_server import HealthCheckServer

from src.latency import LatencyTracker, LatencyMonitor
→ from src.observability.latency import LatencyTracker, LatencyMonitor

from src.metrics_dashboard import MetricsDashboard
→ from src.api.metrics_dashboard import MetricsDashboard

# Session
from src.session_recorder import SessionRecorder
→ from src.session.recorder import SessionRecorder

from src.replay_system import ReplaySystem
→ from src.session.replay import ReplaySystem

# API
from src.websocket_server import WebSocketServer
→ from src.api.websocket import WebSocketServer
```

## Benefits of This Structure

### 1. **Clear Separation of Concerns**
- **Core**: Domain models and events (business logic)
- **Services**: External API integrations (ASR, LLM, TTS)
- **Infrastructure**: Cross-cutting concerns (config, logging, resilience)
- **Observability**: Monitoring, metrics, health checks
- **Session**: Session lifecycle management
- **API**: External interfaces (WebSocket, HTTP)

### 2. **Scalability**
- Easy to add new services (e.g., `src/services/stt/`)
- Easy to add new resilience patterns
- Easy to add new observability features

### 3. **Testability**
- Each package can be tested independently
- Clear dependencies between packages
- Easy to mock external services

### 4. **Maintainability**
- Related code is grouped together
- Clear module boundaries
- Easy to navigate and understand

### 5. **Production-Ready**
- Follows industry best practices
- Similar to microservices architecture
- Easy to extract into separate services if needed

## Package Dependencies

```
main.py
  ├── infrastructure (config, logging)
  ├── observability (health, metrics, latency)
  ├── services (asr, llm, tts)
  ├── session (manager)
  └── api (websocket, health_server, metrics_dashboard)

api
  ├── core (events, models)
  ├── session (manager)
  ├── observability (health, metrics)
  └── infrastructure (logging)

services
  ├── core (events, models)
  ├── infrastructure (resilience, logging)
  └── observability (latency)

session
  ├── core (models)
  ├── services (asr, llm, tts)
  ├── observability (latency)
  └── infrastructure (logging)

observability
  ├── core (events)
  └── infrastructure (logging, resilience)

infrastructure
  └── (no internal dependencies)

core
  └── (no internal dependencies)
```

## Next Steps

1. ✅ Create new package structure
2. ✅ Move files to new locations
3. ⏳ Update all import statements
4. ⏳ Update test imports
5. ⏳ Run tests to verify
6. ⏳ Update documentation

## Files Moved

- ✅ `src/events.py` → `src/core/events.py`
- ✅ `src/buffers.py` → Split into `src/core/models.py`
- ✅ `src/session.py` → Split into `src/core/models.py` (Session) and `src/session/manager.py` (SessionManager)
- ✅ `src/asr_service.py` → `src/services/asr/service.py`
- ✅ `src/reasoning_service.py` → `src/services/llm/service.py`
- ✅ `src/tts_service.py` → `src/services/tts/service.py`
- ✅ `src/config.py` → `src/infrastructure/config.py`
- ✅ `src/logger.py` → `src/infrastructure/logging.py`
- ✅ `src/resilience.py` → Split into `src/infrastructure/resilience/` (circuit_breaker.py, retry.py, timeout.py)
- ✅ `src/health.py` → `src/observability/health.py` (SystemHealth) + `src/api/health_server.py` (HealthCheckServer)
- ✅ `src/latency.py` → `src/observability/latency.py`
- ✅ `src/metrics_dashboard.py` → `src/observability/metrics.py` + `src/api/metrics_dashboard.py`
- ✅ `src/session_recorder.py` → `src/session/recorder.py`
- ✅ `src/replay_system.py` → `src/session/replay.py`
- ✅ `src/websocket_server.py` → `src/api/websocket.py`
