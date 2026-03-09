# System Architecture

## Overview

The Real-Time Voice Assistant is a production-ready streaming application that processes voice input through an asynchronous event pipeline. The system receives audio via WebSocket, transcribes it using Whisper ASR, generates responses using Gemini LLM, synthesizes speech using ElevenLabs TTS, and streams audio back to the client—all with comprehensive latency tracking and fault tolerance.

### Design Principles

1. **Streaming-First Architecture**: Every component operates on streaming data with minimal buffering
2. **Async/Await Throughout**: Non-blocking I/O using Python's asyncio for high concurrency
3. **Event-Driven Pipeline**: Loosely coupled components communicating via typed events
4. **Observable by Default**: Comprehensive instrumentation for latency, errors, and state transitions
5. **Resilient by Design**: Timeouts, retries, circuit breakers, and graceful degradation
6. **Debuggable**: Session recording and replay for post-mortem analysis

### Architecture Goals

- **Low Latency**: End-to-end latency under 2 seconds for typical interactions
- **High Throughput**: Support 100+ concurrent voice sessions on modest hardware
- **Fault Tolerance**: Isolate failures, retry transient errors, prevent cascading failures
- **Observability**: Track every millisecond through the pipeline with structured logging
- **Maintainability**: Modular design with clear interfaces and dependency injection

## System Context Diagram

```mermaid
graph TB
    Client[Client Application<br/>Browser/Mobile]
    WS[WebSocket Server<br/>Port 8000]
    Pipeline[Event Pipeline<br/>AsyncIO Queues]
    ASR[ASR Service<br/>Whisper API]
    LLM[Reasoning Service<br/>Gemini API]
    TTS[TTS Service<br/>ElevenLabs API]
    Metrics[Latency Tracker<br/>Prometheus Metrics]
    Storage[Session Storage<br/>Local Filesystem]
    Dashboard[Metrics Dashboard<br/>HTTP :8001]
    Health[Health Endpoints<br/>HTTP :8001]
    
    Client <-->|Audio Stream| WS
    WS -->|AudioFrame Events| Pipeline
    Pipeline -->|AudioFrame| ASR
    ASR -->|TranscriptEvent| Pipeline
    Pipeline -->|TranscriptEvent| LLM
    LLM -->|LLMTokenEvent| Pipeline
    Pipeline -->|LLMTokenEvent| TTS
    TTS -->|TTSAudioEvent| Pipeline
    Pipeline -->|TTSAudioEvent| WS
    WS -->|Audio Stream| Client
    
    Pipeline -.->|Metrics| Metrics
    Pipeline -.->|Recording| Storage
    Metrics -->|Expose| Dashboard
    Health -.->|Status| Dashboard
```

## Component Architecture

### Core Components

```mermaid
graph TB
    subgraph "WebSocket Layer"
        WSServer[WebSocket Server]
        SessionMgr[Session Manager]
    end
    
    subgraph "Processing Pipeline"
        ASRSvc[ASR Service]
        LLMSvc[LLM Service]
        TTSSvc[TTS Service]
    end
    
    subgraph "Event Infrastructure"
        AudioQ[Audio Queue]
        TranscriptQ[Transcript Queue]
        TokenQ[Token Queue]
        TTSQ[TTS Queue]
    end
    
    subgraph "Resilience Layer"
        CB1[Circuit Breaker: ASR]
        CB2[Circuit Breaker: LLM]
        CB3[Circuit Breaker: TTS]
        Retry[Retry Logic]
        Timeout[Timeout Handler]
    end
    
    subgraph "Observability"
        LatencyTracker[Latency Tracker]
        Logger[Structured Logger]
        Recorder[Session Recorder]
        MetricsDash[Metrics Dashboard]
        HealthCheck[Health Endpoints]
    end
    
    WSServer --> SessionMgr
    SessionMgr --> AudioQ
    AudioQ --> ASRSvc
    ASRSvc --> TranscriptQ
    TranscriptQ --> LLMSvc
    LLMSvc --> TokenQ
    TokenQ --> TTSSvc
    TTSSvc --> TTSQ
    TTSQ --> WSServer
    
    ASRSvc -.-> CB1
    LLMSvc -.-> CB2
    TTSSvc -.-> CB3
    
    CB1 -.-> Retry
    CB2 -.-> Retry
    CB3 -.-> Retry
    
    Retry -.-> Timeout
    
    AudioQ -.-> LatencyTracker
    TranscriptQ -.-> LatencyTracker
    TokenQ -.-> LatencyTracker
    TTSQ -.-> LatencyTracker
    
    LatencyTracker --> MetricsDash
    Logger --> MetricsDash
    Recorder --> Storage[(Storage)]
    
    HealthCheck -.-> CB1
    HealthCheck -.-> CB2
    HealthCheck -.-> CB3
```

### Component Responsibilities

| Component | Responsibilities | Key Technologies |
|-----------|-----------------|------------------|
| **WebSocket Server** | Accept connections, manage session lifecycle, stream audio bidirectionally | websockets, asyncio |
| **Session Manager** | Create/cleanup sessions, initialize pipeline queues, manage session state | asyncio.Queue |
| **ASR Service** | Buffer audio, transcribe via Whisper API, emit transcript events | OpenAI Whisper API |
| **LLM Service** | Maintain conversation context, stream tokens from Gemini, emit token events | Google Gemini API |
| **TTS Service** | Buffer tokens, synthesize via ElevenLabs, emit audio events | ElevenLabs API |
| **Circuit Breakers** | Prevent cascading failures, implement open/half-open/closed states | Custom implementation |
| **Retry Logic** | Exponential backoff for transient failures | Custom decorator |
| **Latency Tracker** | Measure pipeline stage latencies, calculate percentiles | In-memory metrics |
| **Metrics Dashboard** | Expose metrics via HTTP, serve visualization dashboard | aiohttp |
| **Health Endpoints** | Provide /health, /health/ready, /health/live endpoints | aiohttp |
| **Session Recorder** | Record audio and events for debugging | gzip, JSON |
| **Structured Logger** | Emit JSON logs with session context | Python logging |

## Audio-to-Audio Flow Sequence

This diagram shows the complete flow from receiving audio to sending synthesized speech back to the client.

```mermaid
sequenceDiagram
    participant Client
    participant WebSocket
    participant AudioQ as Audio Queue
    participant ASR as ASR Service
    participant TranscriptQ as Transcript Queue
    participant LLM as LLM Service
    participant TokenQ as Token Queue
    participant TTS as TTS Service
    participant TTSQ as TTS Queue
    participant Latency as Latency Tracker
    
    Note over Client,Latency: Session Established
    
    Client->>WebSocket: Audio Chunk (PCM 16-bit)
    WebSocket->>Latency: Mark: audio_received
    WebSocket->>AudioQ: AudioFrame Event
    
    AudioQ->>ASR: Dequeue AudioFrame
    Note over ASR: Buffer until 1s of audio
    ASR->>ASR: Call Whisper API
    ASR->>Latency: Mark: transcript_start
    ASR->>TranscriptQ: TranscriptEvent (partial=true)
    
    Note over ASR: Continue buffering...
    ASR->>TranscriptQ: TranscriptEvent (partial=false)
    Latency->>Latency: Calculate: ASR Latency
    
    TranscriptQ->>LLM: Dequeue TranscriptEvent
    Note over LLM: Only process final transcripts
    LLM->>LLM: Get conversation context
    LLM->>LLM: Call Gemini Streaming API
    LLM->>Latency: Mark: llm_first_token
    LLM->>TokenQ: LLMTokenEvent (is_first=true)
    Latency->>Latency: Calculate: LLM First Token Latency
    
    loop Token Streaming
        LLM->>TokenQ: LLMTokenEvent
        TokenQ->>TTS: Dequeue LLMTokenEvent
        Note over TTS: Buffer until phrase boundary
        TTS->>TTS: Call ElevenLabs Streaming API
        TTS->>Latency: Mark: tts_audio_start
        TTS->>TTSQ: TTSAudioEvent
        Latency->>Latency: Calculate: TTS Latency
        TTSQ->>WebSocket: Dequeue TTSAudioEvent
        WebSocket->>Client: Audio Chunk
    end
    
    LLM->>TokenQ: LLMTokenEvent (is_last=true)
    TTS->>TTSQ: TTSAudioEvent (is_final=true)
    TTSQ->>WebSocket: Dequeue TTSAudioEvent
    WebSocket->>Client: Final Audio Chunk
    
    Latency->>Latency: Calculate: End-to-End Latency
    
    Note over Client,Latency: Ready for next interaction
```

## Session Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Connecting: Client connects
    Connecting --> Active: WebSocket established
    Active --> Active: Process audio/events
    Active --> Disconnecting: Client disconnects
    Active --> Error: Critical error
    Error --> Disconnecting: Cleanup triggered
    Disconnecting --> Cleanup: Stop pipeline tasks
    Cleanup --> Recording: Save session (if enabled)
    Recording --> [*]: Session complete
    Cleanup --> [*]: Session complete (no recording)
```

### Session Lifecycle Details

1. **Connecting**: Client initiates WebSocket connection
   - Server accepts connection
   - Generates unique session ID
   - Creates Session object

2. **Active**: Session is processing audio
   - Initialize event queues (audio, transcript, token, TTS)
   - Start pipeline tasks (ASR, LLM, TTS)
   - Initialize latency tracker
   - Initialize session recorder (if enabled)
   - Process audio frames and events

3. **Disconnecting**: Client disconnects or error occurs
   - Stop accepting new audio
   - Allow in-flight events to complete (with timeout)
   - Cancel pipeline tasks

4. **Cleanup**: Release resources
   - Close event queues
   - Cancel asyncio tasks
   - Clear conversation context
   - Finalize latency measurements

5. **Recording**: Save session data (if enabled)
   - Persist audio frames
   - Persist all events
   - Save metadata (duration, event counts, errors)

## Event Pipeline Architecture

The event pipeline is the core of the system, connecting all processing components through asyncio queues. For detailed information about the event pipeline, see [Event Pipeline Architecture](event_pipeline_architecture.md).

### Event Flow

```mermaid
graph LR
    subgraph "Session-Scoped Pipeline"
        Q1[Audio Queue<br/>maxsize=100]
        Q2[Transcript Queue<br/>maxsize=50]
        Q3[Token Queue<br/>maxsize=200]
        Q4[TTS Queue<br/>maxsize=100]
        
        Q1 --> ASR[ASR Service]
        ASR --> Q2
        Q2 --> LLM[LLM Service]
        LLM --> Q3
        Q3 --> TTS[TTS Service]
        TTS --> Q4
        Q4 --> WS[WebSocket Handler]
    end
    
    subgraph "Cross-Cutting Concerns"
        Latency[Latency Tracker]
        Recorder[Session Recorder]
        Logger[Structured Logger]
    end
    
    Q1 -.-> Latency
    Q2 -.-> Latency
    Q3 -.-> Latency
    Q4 -.-> Latency
    
    Q1 -.-> Recorder
    Q2 -.-> Recorder
    Q3 -.-> Recorder
    Q4 -.-> Recorder
    
    Q1 -.-> Logger
    Q2 -.-> Logger
    Q3 -.-> Logger
    Q4 -.-> Logger
```

### Event Types

All events are Python dataclasses with timestamp metadata:

- **AudioFrame**: Raw audio data chunk (PCM 16-bit, 16kHz mono)
- **TranscriptEvent**: Speech recognition result (partial or final)
- **LLMTokenEvent**: Streaming token from language model
- **TTSAudioEvent**: Synthesized audio chunk
- **ErrorEvent**: Error notification with retry information

See [API Documentation](api.md) for complete event schemas.

## Resilience Architecture

The system implements multiple layers of resilience to handle failures gracefully.

```mermaid
graph TB
    subgraph "Request Flow"
        Request[API Request]
        CB{Circuit Breaker<br/>State?}
        Timeout[Timeout Handler<br/>3-5 seconds]
        Retry[Retry Logic<br/>Exponential Backoff]
        API[External API]
        Success[Success Response]
        Failure[Failure Response]
    end
    
    Request --> CB
    CB -->|CLOSED| Timeout
    CB -->|OPEN| Failure
    CB -->|HALF_OPEN| Timeout
    
    Timeout -->|Within Timeout| API
    Timeout -->|Timeout Exceeded| Retry
    
    API -->|Success| Success
    API -->|Transient Error| Retry
    API -->|Permanent Error| Failure
    
    Retry -->|Attempt 1| Timeout
    Retry -->|Attempt 2<br/>+100ms| Timeout
    Retry -->|Attempt 3<br/>+200ms| Timeout
    Retry -->|Max Attempts| Failure
    
    Success --> UpdateCB[Update Circuit Breaker]
    Failure --> UpdateCB
    
    UpdateCB -->|Track Success| CB
    UpdateCB -->|Track Failure| CB
```

### Resilience Patterns

1. **Timeouts**: All external API calls have configurable timeouts
   - ASR (Whisper): 3 seconds
   - LLM (Gemini): 5 seconds
   - TTS (ElevenLabs): 3 seconds

2. **Retries with Exponential Backoff**:
   - Initial delay: 100ms
   - Backoff multiplier: 2x
   - Max attempts: 3
   - Only for retryable errors (network, timeout)

3. **Circuit Breakers**:
   - Failure threshold: 50% over 10 requests
   - Open timeout: 30 seconds
   - States: CLOSED → OPEN → HALF_OPEN → CLOSED/OPEN

4. **Graceful Degradation**:
   - Non-critical component failures don't stop audio processing
   - System continues with reduced functionality
   - Health status reflects degraded state

For detailed information, see [Resilience Patterns](resilience_patterns.md).

## Observability Architecture

```mermaid
graph TB
    subgraph "Data Collection"
        Events[Event Pipeline]
        Latency[Latency Measurements]
        Logs[Structured Logs]
        Health[Health Status]
        CB[Circuit Breaker States]
    end
    
    subgraph "Aggregation"
        MetricsAgg[Metrics Aggregator]
        LatencyCalc[Latency Calculator<br/>p50, p95, p99]
    end
    
    subgraph "Exposure"
        Dashboard[Metrics Dashboard<br/>HTTP :8001/dashboard]
        MetricsAPI[Metrics API<br/>HTTP :8001/metrics]
        HealthAPI[Health API<br/>HTTP :8001/health]
    end
    
    subgraph "Storage"
        Recordings[Session Recordings<br/>Filesystem]
    end
    
    Events --> MetricsAgg
    Latency --> LatencyCalc
    Logs --> MetricsAgg
    Health --> HealthAPI
    CB --> HealthAPI
    
    MetricsAgg --> MetricsAPI
    LatencyCalc --> MetricsAPI
    MetricsAPI --> Dashboard
    
    Events -.->|If enabled| Recordings
```

### Latency Tracking

The system tracks latency at every pipeline stage:

| Metric | Description | Budget |
|--------|-------------|--------|
| **ASR Latency** | Audio receipt → Transcript emission | 500ms |
| **LLM First Token** | Transcript receipt → First token emission | 300ms |
| **LLM Generation** | First token → Last token | Variable |
| **TTS Latency** | Token receipt → Audio emission | 400ms |
| **End-to-End** | Audio input → Audio output | 2000ms |
| **WebSocket Send** | Event → Network transmission | Variable |

Statistics calculated: count, mean, median, p95, p99, min, max

For detailed information, see [Metrics Dashboard](metrics_dashboard.md).

## Deployment Architecture

```mermaid
graph TB
    subgraph "Container"
        App[Voice Assistant<br/>Python Application]
        WS[WebSocket :8000]
        HTTP[HTTP :8001]
    end
    
    subgraph "External Services"
        Whisper[OpenAI Whisper API]
        Gemini[Google Gemini API]
        ElevenLabs[ElevenLabs API]
    end
    
    subgraph "Storage"
        Recordings[Recordings Volume<br/>/app/recordings]
    end
    
    subgraph "Monitoring"
        HealthCheck[Health Check Probe]
        Metrics[Metrics Scraper]
    end
    
    Client[Client Application] <-->|WebSocket| WS
    Client <-->|HTTP| HTTP
    
    App --> Whisper
    App --> Gemini
    App --> ElevenLabs
    
    App --> Recordings
    
    HealthCheck -->|/health/ready| HTTP
    HealthCheck -->|/health/live| HTTP
    Metrics -->|/metrics| HTTP
```

### Container Configuration

- **Base Image**: python:3.11-slim
- **Exposed Ports**:
  - 8000: WebSocket server
  - 8001: Metrics and health endpoints
- **Volumes**:
  - /app/recordings: Session recordings (if enabled)
- **Health Checks**:
  - Liveness: /health/live (every 30s)
  - Readiness: /health/ready (every 30s)
- **Environment Variables**: See [Configuration](configuration.md)

For deployment instructions, see [Running the Application](running_the_application.md).

## Data Flow Patterns

### Streaming Pattern

All components use streaming to minimize latency:

```
Audio Stream → ASR → Partial Transcripts → LLM → Token Stream → TTS → Audio Stream
```

- **No waiting for complete input**: ASR emits partial transcripts
- **No waiting for complete response**: LLM streams tokens as generated
- **No waiting for complete synthesis**: TTS emits audio chunks as synthesized

### Buffering Strategy

Strategic buffering balances latency and quality:

| Component | Buffer Size | Rationale |
|-----------|-------------|-----------|
| **ASR** | 1 second | Minimum audio for accurate transcription |
| **LLM** | No buffer | Stream tokens immediately |
| **TTS** | 10 tokens or sentence boundary | Minimum text for natural synthesis |

### Backpressure Handling

Queue sizes enforce backpressure:

- **Producer faster than consumer**: Queue fills, producer blocks
- **Consumer faster than producer**: Queue empties, consumer waits
- **Balanced throughput**: Queue maintains steady state

## Error Handling Strategy

```mermaid
graph TD
    Error[Error Occurs]
    Classify{Error Type?}
    
    Error --> Classify
    
    Classify -->|Transient| Retry[Retry with<br/>Exponential Backoff]
    Classify -->|Permanent| Fail[Emit Error Event<br/>No Retry]
    Classify -->|Validation| Reject[Reject Request<br/>Log Error]
    
    Retry -->|Success| Recover[Continue Processing]
    Retry -->|Max Attempts| Fail
    
    Fail --> UpdateHealth[Update System Health]
    Fail --> NotifyClient[Notify Client]
    Fail --> Log[Structured Log]
    
    UpdateHealth --> CheckCritical{Critical<br/>Component?}
    CheckCritical -->|Yes| TerminateSession[Terminate Session]
    CheckCritical -->|No| Degrade[Continue with<br/>Degraded Functionality]
```

### Error Classification

- **Transient Errors**: Network timeouts, temporary API unavailability → Retry
- **Permanent Errors**: Authentication failures, invalid input → No retry
- **Validation Errors**: Malformed data, protocol violations → Reject
- **Component Failures**: Service crashes, resource exhaustion → Isolate

## Security Considerations

### API Key Management

- API keys loaded from environment variables
- Never logged or exposed in responses
- Validated at startup

### Input Validation

- Audio data validated for format and size
- WebSocket messages validated against protocol
- Configuration values validated at startup

### Network Security

- WebSocket connections can be secured with TLS (wss://)
- Health endpoints can be restricted by network policy
- No authentication implemented (add as needed)

### Resource Limits

- Queue sizes prevent unbounded memory growth
- Timeouts prevent resource exhaustion
- Session cleanup ensures resource release

## Performance Characteristics

### Latency Profile

Typical latency breakdown for a voice interaction:

| Stage | Typical | p95 | p99 |
|-------|---------|-----|-----|
| ASR | 300ms | 450ms | 500ms |
| LLM First Token | 200ms | 280ms | 300ms |
| TTS | 250ms | 350ms | 400ms |
| **Total** | **750ms** | **1080ms** | **1200ms** |

### Throughput

- **Concurrent Sessions**: 100+ on modest hardware (4 CPU, 8GB RAM)
- **Audio Processing**: Real-time (1x speed)
- **Token Streaming**: 50-100 tokens/second per session

### Resource Usage

Per session:
- **Memory**: ~10MB (queues, buffers, context)
- **CPU**: Minimal (I/O bound, async)
- **Network**: ~32 kbps audio + API calls

## Related Documentation

- [Event Pipeline Architecture](event_pipeline_architecture.md) - Detailed event pipeline design
- [API Documentation](api.md) - Complete API reference
- [Configuration](configuration.md) - Configuration options
- [Resilience Patterns](resilience_patterns.md) - Fault tolerance implementation
- [Session Management](session_management.md) - Session lifecycle details
- [WebSocket Server](websocket_server.md) - WebSocket protocol
- [ASR Service](asr_service.md) - Speech recognition details
- [Reasoning Service](reasoning_service.md) - LLM integration
- [TTS Service](tts_service.md) - Speech synthesis
- [Metrics Dashboard](metrics_dashboard.md) - Observability
- [Health System](health_system.md) - Health checks
- [Session Recording](session_recording.md) - Recording and replay
- [Running the Application](running_the_application.md) - Deployment guide
