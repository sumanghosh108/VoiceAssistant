# Session Management

## Overview

The session management system coordinates the lifecycle of voice interaction sessions in the real-time voice assistant. Each session represents a single user connection and maintains isolated resources including event queues, pipeline tasks, and observability components.

## Architecture

### Session Dataclass

The `Session` dataclass encapsulates all state and resources for a single user connection:

```python
@dataclass
class Session:
    session_id: str                    # Unique session identifier (UUID)
    created_at: datetime               # Session creation timestamp
    websocket: Any                     # WebSocket connection object
    
    # Event queues for pipeline stages
    audio_queue: asyncio.Queue[AudioFrame]
    transcript_queue: asyncio.Queue[TranscriptEvent]
    token_queue: asyncio.Queue[LLMTokenEvent]
    tts_queue: asyncio.Queue[TTSAudioEvent]
    
    # Processing task references
    asr_task: Optional[asyncio.Task]   # ASR processing task
    llm_task: Optional[asyncio.Task]   # LLM processing task
    tts_task: Optional[asyncio.Task]   # TTS processing task
    
    # Observability components
    latency_tracker: LatencyTracker    # Latency metrics tracker
    recorder: Optional[SessionRecorder] # Optional session recorder
```

### SessionManager Class

The `SessionManager` coordinates multiple concurrent sessions:

- **Creates sessions** with initialized pipeline tasks
- **Manages session-scoped resources** (queues, tasks, trackers)
- **Starts pipeline tasks** (ASR, LLM, TTS) for each session
- **Cleans up sessions** with timeout enforcement
- **Saves recordings** when enabled

## Usage

### Initialization

```python
from src.session import SessionManager
from src.asr_service import ASRService
from src.reasoning_service import ReasoningService
from src.tts_service import TTSService

# Initialize services
asr_service = ASRService(api_key="...", timeout=3.0)
llm_service = ReasoningService(api_key="...", timeout=5.0)
tts_service = TTSService(api_key="...", voice_id="...")

# Create session manager
session_manager = SessionManager(
    asr_service=asr_service,
    llm_service=llm_service,
    tts_service=tts_service,
    enable_recording=False
)
```

### Creating a Session

```python
# When a WebSocket connection is established
websocket = await websocket_server.accept()

# Create session and start pipeline
session = await session_manager.create_session(websocket)

print(f"Session created: {session.session_id}")
print(f"Active sessions: {session_manager.get_active_session_count()}")
```

### Using Session Queues

```python
# Emit audio frame to pipeline
audio_frame = AudioFrame(
    session_id=session.session_id,
    data=audio_bytes,
    timestamp=datetime.now(),
    sequence_number=seq_num
)
await session.audio_queue.put(audio_frame)

# Consume TTS audio from pipeline
tts_event = await session.tts_queue.get()
await websocket.send(tts_event.audio_data)
```

### Cleaning Up a Session

```python
# When WebSocket disconnects
await session_manager.cleanup_session(
    session_id=session.session_id,
    timeout=5.0  # Maximum cleanup time in seconds
)
```

## Event Pipeline Flow

Each session has an isolated event pipeline:

```
WebSocket → audio_queue → ASR Service → transcript_queue → LLM Service → token_queue → TTS Service → tts_queue → WebSocket
```

### Queue Sizes

Queue sizes are configured for backpressure management:

- **audio_queue**: 100 frames (~6 seconds at 16kHz with 1s buffers)
- **transcript_queue**: 50 events (moderate buffering)
- **token_queue**: 200 tokens (large buffer for streaming)
- **tts_queue**: 100 chunks (audio chunk buffering)

## Session Lifecycle

### 1. Creation

When `create_session()` is called:

1. Generate unique session ID (UUID)
2. Create event queues with appropriate maxsize
3. Initialize LatencyTracker for metrics
4. Create SessionRecorder if recording is enabled
5. Start ASR, LLM, and TTS processing tasks
6. Store session in active sessions dictionary

### 2. Active Processing

During the session:

- Audio frames flow through the pipeline
- Each service processes events asynchronously
- Latency metrics are tracked
- Events are optionally recorded

### 3. Cleanup

When `cleanup_session()` is called:

1. Cancel all pipeline tasks (ASR, LLM, TTS)
2. Wait for tasks to complete with timeout
3. Save recording if enabled
4. Remove session from active sessions
5. Log session duration and metrics

## Timeout Enforcement

The cleanup process enforces a timeout (default: 5 seconds) to prevent indefinite blocking:

```python
try:
    await asyncio.wait_for(
        asyncio.gather(*tasks, return_exceptions=True),
        timeout=timeout
    )
except asyncio.TimeoutError:
    logger.warning("Session cleanup timed out, forcing termination")
```

If tasks don't complete within the timeout, cleanup proceeds anyway to ensure resources are released.

## Session Isolation

Each session has completely isolated resources:

- **Separate event queues**: No cross-session event leakage
- **Independent tasks**: Failures in one session don't affect others
- **Isolated latency tracking**: Per-session metrics
- **Separate recordings**: Each session recorded independently

This isolation ensures:
- Concurrent session processing without interference
- Fault isolation (one session failure doesn't cascade)
- Independent lifecycle management

## Recording Integration

When recording is enabled:

```python
session_manager = SessionManager(
    asr_service=asr_service,
    llm_service=llm_service,
    tts_service=tts_service,
    enable_recording=True,
    recording_storage_path="./recordings"
)
```

The SessionManager will:
1. Create a SessionRecorder for each session
2. Pass the recorder to the session
3. Save the recording during cleanup

## Error Handling

### Task Cancellation

Pipeline tasks are cancelled gracefully during cleanup:

```python
if session.asr_task and not session.asr_task.done():
    session.asr_task.cancel()
```

Tasks should handle `asyncio.CancelledError` appropriately.

### Recording Failures

If recording fails during cleanup, the error is logged but cleanup continues:

```python
try:
    await session.recorder.save()
except Exception as e:
    logger.error("Failed to save session recording", error=str(e))
```

### Non-existent Sessions

Attempting to cleanup a non-existent session is handled gracefully:

```python
await session_manager.cleanup_session("nonexistent-id")
# Logs warning but doesn't raise exception
```

## Monitoring

### Active Session Count

```python
count = session_manager.get_active_session_count()
print(f"Active sessions: {count}")
```

### Session IDs

```python
session_ids = session_manager.get_session_ids()
for sid in session_ids:
    print(f"Active session: {sid}")
```

### Session Retrieval

```python
session = session_manager.get_session(session_id)
if session:
    print(f"Session created at: {session.created_at}")
    print(f"ASR task running: {not session.asr_task.done()}")
```

## Best Practices

### 1. Always Cleanup Sessions

Ensure sessions are cleaned up when connections close:

```python
try:
    # Handle WebSocket connection
    await handle_websocket(session)
finally:
    # Always cleanup, even on errors
    await session_manager.cleanup_session(session.session_id)
```

### 2. Monitor Active Sessions

Track active session count for capacity planning:

```python
if session_manager.get_active_session_count() > MAX_SESSIONS:
    logger.warning("Maximum session capacity reached")
    # Reject new connections or scale up
```

### 3. Set Appropriate Timeouts

Configure cleanup timeout based on your requirements:

```python
# Quick cleanup for high-throughput scenarios
await session_manager.cleanup_session(session_id, timeout=2.0)

# Longer timeout for graceful shutdown
await session_manager.cleanup_session(session_id, timeout=10.0)
```

### 4. Handle Backpressure

Monitor queue sizes to detect backpressure:

```python
if session.audio_queue.qsize() > 80:  # 80% full
    logger.warning("Audio queue backpressure detected")
    # Consider dropping frames or slowing input
```

## Requirements Mapping

This implementation satisfies the following requirements:

- **Requirement 1.6**: WebSocket server maintains connection state for each active session
- **Requirement 1.7**: Session resources cleaned up within 5 seconds on disconnect
- **Requirement 6.2**: Event pipeline supports concurrent processing of multiple sessions
- **Requirement 13.1**: Session recording persists all audio frames when enabled
- **Requirement 13.2**: Session recording persists all events when enabled

## Testing

Comprehensive unit tests cover:

- Session dataclass creation and attributes
- SessionManager initialization
- Session creation with pipeline tasks
- Task cancellation during cleanup
- Timeout enforcement
- Multiple concurrent sessions
- Session isolation
- Recording integration

Run tests with:

```bash
pytest tests/test_session.py -v
```

## Future Enhancements

Potential improvements:

1. **Session persistence**: Save session state for recovery after crashes
2. **Session migration**: Move sessions between servers for load balancing
3. **Resource limits**: Per-session CPU/memory limits
4. **Session analytics**: Track session duration, event counts, error rates
5. **Graceful degradation**: Continue session with reduced functionality on service failures
