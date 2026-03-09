# Production Architecture

## Module Organization

The real-time voice assistant is organized into 7 main packages, each with a specific responsibility:

```
┌─────────────────────────────────────────────────────────────────┐
│                         main.py                                  │
│                   (Application Entry Point)                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
        ┌───────▼────────┐       ┌───────▼────────┐
        │  Infrastructure │       │  Observability  │
        │                 │       │                 │
        │  • Config       │       │  • Health       │
        │  • Logging      │       │  • Metrics      │
        │  • Resilience   │       │  • Latency      │
        └────────┬────────┘       └────────┬────────┘
                 │                         │
        ┌────────▼─────────────────────────▼────────┐
        │              Core Domain                   │
        │                                            │
        │  • Events (AudioFrame, TranscriptEvent)    │
        │  • Models (AudioBuffer, Session)           │
        └────────┬───────────────────────────────────┘
                 │
        ┌────────┴────────┬────────────┬────────────┐
        │                 │            │            │
   ┌────▼─────┐    ┌─────▼────┐  ┌───▼────┐  ┌───▼────┐
   │ Services │    │ Session  │  │  API   │  │  API   │
   │          │    │          │  │        │  │        │
   │ • ASR    │    │ • Manager│  │• WS    │  │• Health│
   │ • LLM    │    │ • Recorder│  │        │  │        │
   │ • TTS    │    │ • Replay │  │        │  │        │
   └──────────┘    └──────────┘  └────────┘  └────────┘
```

## Package Responsibilities

### 1. Core (`src/core/`)
**Purpose**: Domain models and event schemas

**Contains**:
- `events.py`: Event schemas (AudioFrame, TranscriptEvent, LLMTokenEvent, TTSAudioEvent, ErrorEvent)
- `models.py`: Data models (AudioBuffer, TokenBuffer, ConversationContext, Session)

**Dependencies**: None (foundation layer)

**Used by**: All other packages

### 2. Infrastructure (`src/infrastructure/`)
**Purpose**: Cross-cutting infrastructure concerns

**Contains**:
- `config.py`: Configuration management (SystemConfig, ConfigLoader)
- `logging.py`: Structured logging (StructuredLogger)
- `resilience/`: Resilience patterns
  - `circuit_breaker.py`: Circuit breaker pattern
  - `retry.py`: Retry with exponential backoff
  - `timeout.py`: Timeout enforcement

**Dependencies**: None

**Used by**: All other packages

### 3. Services (`src/services/`)
**Purpose**: External API integrations

**Contains**:
- `asr/service.py`: ASRService (Whisper integration)
- `llm/service.py`: ReasoningService (Gemini integration)
- `tts/service.py`: TTSService (ElevenLabs integration)

**Dependencies**: Core, Infrastructure

**Used by**: Session, API

### 4. Observability (`src/observability/`)
**Purpose**: Monitoring, metrics, and health checks

**Contains**:
- `health.py`: SystemHealth (component health tracking)
- `metrics.py`: MetricsAggregator, MetricsDashboard
- `latency.py`: LatencyTracker, LatencyMonitor, LatencyBudget

**Dependencies**: Core, Infrastructure

**Used by**: API, Session, Main

### 5. Session (`src/session/`)
**Purpose**: Session lifecycle management

**Contains**:
- `manager.py`: SessionManager (session creation, cleanup)
- `recorder.py`: SessionRecorder (session recording)
- `replay.py`: ReplaySystem (session replay for debugging)

**Dependencies**: Core, Services, Observability, Infrastructure

**Used by**: API

### 6. API (`src/api/`)
**Purpose**: External interfaces (WebSocket, HTTP)

**Contains**:
- `websocket.py`: WebSocketServer (real-time audio streaming)
- `health_server.py`: HealthCheckServer (health check endpoints)

**Dependencies**: Core, Session, Observability, Infrastructure

**Used by**: Main

## Data Flow

### Audio-to-Audio Pipeline

```
Client
  │
  │ WebSocket
  ▼
┌─────────────────┐
│ WebSocketServer │ (API Layer)
└────────┬────────┘
         │ AudioFrame
         ▼
┌─────────────────┐
│  SessionManager │ (Session Layer)
└────────┬────────┘
         │
    ┌────┴────┬────────┬────────┐
    │         │        │        │
    ▼         ▼        ▼        ▼
┌────────┐ ┌────┐  ┌────┐  ┌────┐
│  ASR   │→│LLM │→│TTS │→│ WS │
│Service │ │Svc │ │Svc │ │Out │
└────────┘ └────┘ └────┘ └────┘
    │         │      │      │
    │         │      │      │
    ▼         ▼      ▼      ▼
  Transcript Token Audio  Client
   Event     Event Event
```

### Event Pipeline Architecture

Each session has isolated asyncio.Queue instances:

```
audio_queue → ASR Service → transcript_queue
                              ↓
                         LLM Service → token_queue
                                         ↓
                                    TTS Service → tts_queue
                                                    ↓
                                              WebSocket Client
```

## Resilience Patterns

### Circuit Breaker Protection

```
┌──────────────┐
│   Service    │
│   Request    │
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌─────────┐
│   Circuit    │────▶│  CLOSED │ (Normal)
│   Breaker    │     └─────────┘
└──────┬───────┘           │
       │              Failures exceed
       │              threshold
       │                   │
       ▼                   ▼
┌──────────────┐     ┌─────────┐
│  External    │     │  OPEN   │ (Reject requests)
│  API Call    │     └─────────┘
└──────────────┘           │
                      Timeout expires
                           │
                           ▼
                     ┌─────────┐
                     │HALF_OPEN│ (Test recovery)
                     └─────────┘
```

### Retry with Exponential Backoff

```
Attempt 1: Fail → Wait 100ms
Attempt 2: Fail → Wait 200ms
Attempt 3: Fail → Wait 400ms
Attempt 4: Success ✓
```

## Observability

### Health Check Endpoints

```
GET /health        → Detailed health status (all components)
GET /health/ready  → Readiness probe (critical components)
GET /health/live   → Liveness probe (process alive)
```

### Metrics Dashboard

```
GET /metrics       → JSON metrics (latency statistics)
GET /dashboard     → HTML dashboard (auto-refresh)
```

### Latency Tracking

```
┌──────────────┐
│ Audio Arrives│
└──────┬───────┘
       │ Mark: audio_received
       ▼
┌──────────────┐
│ ASR Complete │
└──────┬───────┘
       │ Measure: asr_latency
       ▼
┌──────────────┐
│ LLM First    │
│ Token        │
└──────┬───────┘
       │ Measure: llm_first_token
       ▼
┌──────────────┐
│ TTS Complete │
└──────┬───────┘
       │ Measure: tts_latency
       ▼
┌──────────────┐
│ Audio Sent   │
└──────────────┘
       │ Measure: end_to_end
```

## Configuration Management

```
Environment Variables
        │
        ▼
┌──────────────────┐
│  ConfigLoader    │
└────────┬─────────┘
         │
    ┌────┴────┬────────┬────────┬────────┐
    │         │        │        │        │
    ▼         ▼        ▼        ▼        ▼
┌────────┐ ┌────┐  ┌────┐  ┌────┐  ┌────┐
│  API   │ │Srv │ │Pipe│ │Res │ │Obs │
│ Config │ │Cfg │ │Cfg │ │Cfg │ │Cfg │
└────────┘ └────┘ └────┘ └────┘ └────┘
```

## Deployment Architecture

```
┌─────────────────────────────────────────┐
│           Docker Container               │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │         main.py                    │ │
│  │  (Application Entry Point)         │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌──────────────┐  ┌──────────────────┐ │
│  │ WebSocket    │  │ HTTP Servers     │ │
│  │ Server       │  │ • Health Checks  │ │
│  │ Port: 8000   │  │ • Metrics        │ │
│  │              │  │ Port: 8001       │ │
│  └──────────────┘  └──────────────────┘ │
│                                          │
│  ┌──────────────────────────────────────┐ │
│  │ Session Manager                      │ │
│  │ • ASR Service (Whisper)              │ │
│  │ • LLM Service (Gemini)               │ │
│  │ • TTS Service (ElevenLabs)           │ │
│  └──────────────────────────────────────┘ │
│                                          │
│  ┌──────────────────────────────────────┐ │
│  │ Recordings Volume                    │ │
│  │ /recordings                          │ │
│  └──────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## Testing Strategy

### Unit Tests
- Test individual components in isolation
- Mock external dependencies
- Fast execution

### Integration Tests
- Test component interactions
- Use mock services
- Verify event pipeline

### End-to-End Tests
- Test complete audio-to-audio flow
- Test concurrent sessions
- Test error recovery

### Performance Tests
- Validate latency budgets
- Test under load
- Measure throughput

## Best Practices

### 1. Dependency Injection
Services are injected into components, making them easy to test and swap:
```python
session_manager = SessionManager(
    asr_service=asr_service,
    llm_service=llm_service,
    tts_service=tts_service
)
```

### 2. Async/Await
All I/O operations use async/await for non-blocking execution:
```python
async def process_audio_stream(self, audio_queue, transcript_queue):
    while True:
        frame = await audio_queue.get()
        result = await self._transcribe(frame)
        await transcript_queue.put(result)
```

### 3. Structured Logging
All logs include context for debugging:
```python
logger.info(
    "Session created",
    session_id=session_id,
    active_sessions=len(self.sessions)
)
```

### 4. Circuit Breakers
External API calls are protected:
```python
result = await self.circuit_breaker.call(
    self._call_external_api,
    data
)
```

### 5. Configuration Management
All configuration is externalized:
```python
config = ConfigLoader.load()
asr_service = ASRService(
    api_key=config.api.whisper_api_key,
    timeout=config.api.whisper_timeout
)
```

## Scalability Considerations

### Horizontal Scaling
- Stateless design allows multiple instances
- WebSocket connections can be load balanced
- Session state is ephemeral

### Vertical Scaling
- Async I/O maximizes CPU utilization
- Queue-based pipeline prevents memory exhaustion
- Backpressure prevents overload

### Monitoring
- Health checks for orchestration
- Metrics for performance monitoring
- Latency tracking for SLA compliance

## Security Considerations

### API Keys
- Stored in environment variables
- Never logged or exposed
- Validated at startup

### Input Validation
- Audio frames validated before processing
- WebSocket messages validated
- Configuration validated at load time

### Error Handling
- Errors logged but not exposed to clients
- Circuit breakers prevent cascading failures
- Graceful degradation for non-critical components
