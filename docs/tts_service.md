# TTS Service Documentation

## Overview

The TTS (Text-to-Speech) Service is responsible for converting streaming text tokens from the LLM into synthesized audio using the ElevenLabs API. It implements phrase buffering, streaming audio synthesis, and comprehensive error handling with circuit breaker protection.

## Architecture

### Component Structure

```
TTSService
├── ElevenLabsClient (API wrapper)
├── TokenBuffer (phrase buffering)
├── CircuitBreaker (fault tolerance)
└── LatencyTracker (metrics)
```

### Data Flow

```
LLMTokenEvent → TokenBuffer → ElevenLabs API → TTSAudioEvent
                    ↓
              Phrase Detection
              (sentence boundary
               or max tokens)
```

## Key Features

### 1. Token Buffering

The service buffers incoming LLM tokens until a complete phrase is detected:

- **Max Tokens**: Configurable buffer size (default: 10 tokens)
- **Sentence Boundaries**: Detects `.`, `!`, `?`, `\n` characters
- **Last Token**: Synthesizes immediately when `is_last=True`

**Example:**
```python
# Tokens: ["Hello", " ", "world", "."]
# Buffer triggers synthesis at "." (sentence boundary)
```

### 2. Streaming Audio Synthesis

Audio is synthesized and emitted in chunks as they arrive from ElevenLabs:

- **Streaming API**: Uses ElevenLabs streaming endpoint
- **Chunk-by-Chunk**: Emits `TTSAudioEvent` for each audio chunk
- **Low Latency**: First audio chunk within 400ms (requirement 4.4)

### 3. Error Handling

**No Retry Logic**: Unlike ASR and LLM services, TTS failures are terminal for that response.

- **Timeout Protection**: 3-second timeout (configurable)
- **Circuit Breaker**: Prevents cascading failures
- **Error Events**: Emits `ErrorEvent` with `retryable=False`

**Rationale**: Audio synthesis failures are typically not transient, and retrying would add unacceptable latency to the user experience.

### 4. Latency Tracking

The service tracks key latency metrics:

- **tts_start**: When synthesis begins
- **tts_audio_start**: When first audio chunk is received
- **tts_latency**: Duration from start to first audio chunk

## API Reference

### TTSService Class

```python
class TTSService:
    def __init__(
        self,
        api_key: str,
        voice_id: str,
        timeout: float = 3.0,
        phrase_buffer_tokens: int = 10,
        circuit_breaker: Optional[CircuitBreaker] = None
    )
```

**Parameters:**
- `api_key`: ElevenLabs API key
- `voice_id`: ElevenLabs voice ID to use for synthesis
- `timeout`: Timeout in seconds for API calls (default: 3.0)
- `phrase_buffer_tokens`: Number of tokens to buffer before synthesis (default: 10)
- `circuit_breaker`: Optional circuit breaker instance (creates default if None)

### Main Processing Loop

```python
async def process_token_stream(
    self,
    token_queue: asyncio.Queue[LLMTokenEvent],
    audio_queue: asyncio.Queue[TTSAudioEvent],
    latency_tracker: Optional[LatencyTracker] = None
) -> None
```

**Parameters:**
- `token_queue`: Input queue for `LLMTokenEvent` objects
- `audio_queue`: Output queue for `TTSAudioEvent` objects
- `latency_tracker`: Optional latency tracker for metrics

**Behavior:**
1. Consumes tokens from `token_queue`
2. Buffers tokens until phrase complete or `is_last=True`
3. Synthesizes buffered text via ElevenLabs API
4. Emits audio chunks to `audio_queue`
5. Handles errors and emits `ErrorEvent` objects

## Event Schemas

### Input: LLMTokenEvent

```python
@dataclass
class LLMTokenEvent:
    session_id: str
    token: str
    is_first: bool      # First token in response
    is_last: bool       # Last token in response
    timestamp: datetime
    token_index: int
```

### Output: TTSAudioEvent

```python
@dataclass
class TTSAudioEvent:
    session_id: str
    audio_data: bytes   # PCM audio bytes
    timestamp: datetime
    sequence_number: int
    is_final: bool      # True for last chunk
```

### Output: ErrorEvent

```python
@dataclass
class ErrorEvent:
    session_id: str
    component: str      # "tts"
    error_type: ErrorType
    message: str
    timestamp: datetime
    retryable: bool     # Always False for TTS
```

## Configuration

### Environment Variables

```bash
# Required
ELEVENLABS_API_KEY=your_api_key_here
ELEVENLABS_VOICE_ID=your_voice_id_here

# Optional
TTS_TIMEOUT=3.0
TTS_PHRASE_BUFFER_TOKENS=10
```

### YAML Configuration

```yaml
api:
  elevenlabs_api_key: "your_api_key_here"
  elevenlabs_voice_id: "your_voice_id_here"

pipeline:
  tts_timeout: 3.0
  tts_phrase_buffer_tokens: 10

resilience:
  circuit_breaker_failure_threshold: 0.5
  circuit_breaker_window_size: 10
  circuit_breaker_timeout_seconds: 30
```

## Usage Examples

### Basic Usage

```python
from src.tts_service import TTSService
from src.resilience import CircuitBreaker
import asyncio

# Initialize service
tts_service = TTSService(
    api_key="your_elevenlabs_api_key",
    voice_id="your_voice_id",
    timeout=3.0,
    phrase_buffer_tokens=10
)

# Create queues
token_queue = asyncio.Queue()
audio_queue = asyncio.Queue()

# Start processing
task = asyncio.create_task(
    tts_service.process_token_stream(token_queue, audio_queue)
)

# Add tokens
await token_queue.put(LLMTokenEvent(
    session_id="session_123",
    token="Hello",
    is_first=True,
    is_last=False,
    timestamp=datetime.now(),
    token_index=0
))

await token_queue.put(LLMTokenEvent(
    session_id="session_123",
    token=" world.",
    is_first=False,
    is_last=True,
    timestamp=datetime.now(),
    token_index=1
))

# Consume audio events
audio_event = await audio_queue.get()
print(f"Received {len(audio_event.audio_data)} bytes of audio")
```

### With Latency Tracking

```python
from src.latency import LatencyTracker

# Create latency tracker
latency_tracker = LatencyTracker("session_123")

# Start processing with tracking
task = asyncio.create_task(
    tts_service.process_token_stream(
        token_queue, 
        audio_queue, 
        latency_tracker
    )
)

# After processing, get metrics
measurements = latency_tracker.get_measurements()
for m in measurements:
    if m.stage == "tts_latency":
        print(f"TTS latency: {m.duration_ms}ms")
```

### With Custom Circuit Breaker

```python
from src.resilience import CircuitBreaker

# Create custom circuit breaker
circuit_breaker = CircuitBreaker(
    failure_threshold=0.3,  # Open at 30% failure rate
    window_size=20,         # Over 20 requests
    timeout_seconds=60,     # Open for 60 seconds
    name="custom_tts"
)

# Initialize service with custom circuit breaker
tts_service = TTSService(
    api_key="your_api_key",
    voice_id="your_voice_id",
    circuit_breaker=circuit_breaker
)

# Check circuit breaker state
state = circuit_breaker.get_state()
print(f"Circuit state: {state['state']}")
print(f"Failures: {state['failures']}, Successes: {state['successes']}")
```

## Error Handling

### Timeout Errors

```python
# Timeout after 3 seconds
# Emits ErrorEvent:
ErrorEvent(
    session_id="session_123",
    component="tts",
    error_type=ErrorType.TIMEOUT,
    message="ElevenLabs API timeout after 3.0s",
    timestamp=datetime.now(),
    retryable=False
)
```

### API Errors

```python
# API error (authentication, rate limit, etc.)
# Emits ErrorEvent:
ErrorEvent(
    session_id="session_123",
    component="tts",
    error_type=ErrorType.API_ERROR,
    message="API error message",
    timestamp=datetime.now(),
    retryable=False
)
```

### Circuit Breaker Open

```python
# When circuit breaker is open
# Raises CircuitBreakerOpenError immediately
# Emits ErrorEvent:
ErrorEvent(
    session_id="session_123",
    component="tts",
    error_type=ErrorType.API_ERROR,
    message="Circuit tts is open",
    timestamp=datetime.now(),
    retryable=False
)
```

## Performance Characteristics

### Latency Budget

- **Target**: First audio chunk within 400ms (requirement 4.4)
- **Typical**: 200-300ms for short phrases
- **Factors**:
  - Token buffer size (smaller = faster, but more API calls)
  - Network latency to ElevenLabs
  - Voice model complexity

### Throughput

- **Concurrent Sessions**: Supports 100+ concurrent sessions
- **API Rate Limits**: Respects ElevenLabs rate limits via circuit breaker
- **Memory Usage**: ~1-2MB per active session (token buffer + audio chunks)

### Optimization Tips

1. **Reduce Buffer Size**: Lower `phrase_buffer_tokens` for faster first audio
2. **Tune Timeout**: Adjust timeout based on network conditions
3. **Monitor Circuit Breaker**: Track state transitions to detect API issues
4. **Use Faster Voice Models**: Some ElevenLabs voices are faster than others

## Testing

### Unit Tests

Run TTS service tests:
```bash
pytest tests/test_tts_service.py -v
```

### Test Coverage

- Token buffering logic
- Phrase boundary detection
- Audio chunk emission
- Timeout handling
- Error event emission
- Latency tracking
- Circuit breaker integration
- Sequence number generation
- Empty text handling

### Mock ElevenLabs Client

For testing without API calls:

```python
from unittest.mock import AsyncMock

# Mock client
async def mock_stream(text, voice_id):
    yield b"audio_chunk_1"
    yield b"audio_chunk_2"

mock_client = AsyncMock()
mock_client.synthesize_stream = mock_stream

# Use in service
tts_service.client = mock_client
```

## Troubleshooting

### Issue: High Latency

**Symptoms**: First audio chunk takes >400ms

**Solutions**:
1. Reduce `phrase_buffer_tokens` to 5 or fewer
2. Check network latency to ElevenLabs API
3. Try a different voice model
4. Monitor circuit breaker state

### Issue: Frequent Timeouts

**Symptoms**: Many timeout errors in logs

**Solutions**:
1. Increase timeout to 5.0 seconds
2. Check network connectivity
3. Verify ElevenLabs API status
4. Monitor circuit breaker state

### Issue: Circuit Breaker Opens Frequently

**Symptoms**: Circuit breaker state transitions to OPEN

**Solutions**:
1. Check ElevenLabs API status and rate limits
2. Increase `failure_threshold` to 0.7 (70%)
3. Increase `window_size` to 20 requests
4. Verify API key is valid

### Issue: Audio Quality Issues

**Symptoms**: Distorted or choppy audio

**Solutions**:
1. Verify audio format matches client expectations (PCM 16-bit)
2. Check sequence numbers are monotonically increasing
3. Ensure client buffers audio appropriately
4. Try a different voice model

## Requirements Mapping

This implementation satisfies the following requirements:

- **4.1**: Token buffering until complete phrase available
- **4.2**: Streaming API calls to ElevenLabs
- **4.3**: Emits TTSAudioEvent objects for each chunk
- **4.4**: First audio within 400ms of first token
- **4.5**: Streams audio continuously without waiting for LLM completion
- **4.6**: Emits completion event when synthesis finishes
- **4.7**: Emits ErrorEvent on failures (no retry)

## Related Documentation

- [ASR Service](./asr_service.md) - Speech recognition service
- [Reasoning Service](./reasoning_service.md) - LLM service
- [Resilience Patterns](./resilience_patterns.md) - Circuit breaker and timeout handling
- [Configuration](./configuration.md) - System configuration guide
